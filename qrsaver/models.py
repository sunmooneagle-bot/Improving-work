"""QR 태그 목록 (작업 큐) - 파일로 자동 저장되어 프로그램을 다시 켜도 유지된다."""
import json
import os
import threading
import time

WAIT, RUN, DONE, FAIL = "대기중", "진행중", "저장완료", "저장실패"


class Item:
    __slots__ = ("id", "code", "status", "time", "note", "tries", "added", "raw", "checks")

    def __init__(self, id, code, status=WAIT, time="", note="", tries=0, added="", raw="", checks=None):
        self.id = id
        self.code = code
        self.status = status
        self.time = time
        self.note = note
        self.tries = tries
        self.added = added
        self.raw = raw        # QR 스캐너가 실제로 친 원문 (예: '26-C -053447') - 저장 시 그대로 다시 입력
        self.checks = dict(checks) if isinstance(checks, dict) else {}   # 목록 체크박스 {컬럼제목: True/False}

    def to_dict(self):
        return {k: getattr(self, k) for k in self.__slots__}


class Store:
    def __init__(self, path):
        self.path = path
        self.lock = threading.RLock()
        self.items = []
        self._next_id = 1
        self.load()

    # ------------------------------------------------------------ 파일
    def load(self):
        try:
            with open(self.path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        for d in data:
            item = Item(**{k: d.get(k, "") for k in Item.__slots__ if k in d})
            if item.status == RUN:
                item.status = WAIT
            item.tries = int(item.tries or 0)
            self.items.append(item)
        self._next_id = max([i.id for i in self.items], default=0) + 1

    def save(self):
        with self.lock:
            data = [i.to_dict() for i in self.items]
        tmp = self.path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            os.replace(tmp, self.path)
        except OSError:
            pass

    # ------------------------------------------------------------ 조작
    def add(self, code, raw=""):
        """추가된 Item 반환, 이미 목록에 있으면 None. raw = QR 원문."""
        with self.lock:
            if any(i.code == code for i in self.items):
                return None
            item = Item(self._next_id, code, added=time.strftime("%H:%M:%S"), raw=raw)
            self._next_id += 1
            self.items.append(item)
        self.save()
        return item

    def set_checks(self, item_id, values):
        """대기중 항목의 여러 체크 상태를 한 번에 설정 (values: {제목: bool})."""
        with self.lock:
            for i in self.items:
                if i.id == item_id and i.status == WAIT:
                    i.checks.update(values)
                    break
            else:
                return False
        self.save()
        return True

    def toggle_check(self, item_id, key):
        """대기중 항목의 목록 체크박스 켜기/끄기. 바뀐 상태 반환 (대기중이 아니면 None)."""
        with self.lock:
            for i in self.items:
                if i.id == item_id:
                    if i.status != WAIT:
                        return None
                    i.checks[key] = not i.checks.get(key, False)
                    val = i.checks[key]
                    break
            else:
                return None
        self.save()
        return val

    def get(self, item_id):
        with self.lock:
            for i in self.items:
                if i.id == item_id:
                    return i
        return None

    def remove(self, ids):
        ids = set(ids)
        with self.lock:
            self.items = [i for i in self.items if i.id not in ids or i.status == RUN]
        self.save()

    def clear(self, statuses=None):
        with self.lock:
            self.items = [i for i in self.items
                          if i.status == RUN or (statuses is not None and i.status not in statuses)]
        self.save()

    def update(self, item, **kw):
        with self.lock:
            for k, v in kw.items():
                setattr(item, k, v)
            if kw.get("status") in (DONE, FAIL):
                item.time = time.strftime("%H:%M:%S")
        self.save()

    def reset(self, ids=None, statuses=(FAIL,)):
        """지정 항목(또는 해당 상태 전체)을 다시 대기중으로."""
        with self.lock:
            for i in self.items:
                if i.status == RUN:
                    continue
                if (ids is not None and i.id in ids) or (ids is None and i.status in statuses):
                    i.status, i.tries, i.note, i.time = WAIT, 0, "", ""
        self.save()

    def next_pending(self):
        with self.lock:
            for i in self.items:
                if i.status == WAIT:
                    return i
        return None

    def counts(self):
        with self.lock:
            c = {WAIT: 0, RUN: 0, DONE: 0, FAIL: 0}
            for i in self.items:
                c[i.status] = c.get(i.status, 0) + 1
            c["total"] = len(self.items)
            return c

    def snapshot(self):
        with self.lock:
            return list(self.items)
