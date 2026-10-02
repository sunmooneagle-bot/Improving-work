"""qrsaver 패키지를 실행 파일 하나(amis_qr_saver.py)로 합친다.  사용: python tools/make_single.py"""
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORDER = ["__init__", "config", "hangul", "models", "win32", "uia", "worker", "gui"]

out = ['''# -*- coding: utf-8 -*-
"""AMIS QR 일괄저장 - 단일 실행 파일 (tools/make_single.py 로 자동 생성, 직접 수정하지 마세요)

실행:  python amis_qr_saver.py      (콘솔 없이: pythonw amis_qr_saver.py)
필요:  pip install pillow uiautomation
"""
import sys
import types

_SOURCES = {}
''']
for name in ORDER:
    with open(os.path.join(ROOT, "qrsaver", name + ".py"), encoding="utf-8") as f:
        src = f.read()
    assert "'''" not in src and not src.endswith("\\"), name
    out.append("\n_SOURCES[%r] = r'''%s'''\n" % (name, src))
out.append('''

def _load():
    pkg = types.ModuleType("qrsaver")
    pkg.__path__ = []
    sys.modules["qrsaver"] = pkg
    for name in %r:
        if name == "__init__":
            mod, full = pkg, "qrsaver"
        else:
            full = "qrsaver." + name
            mod = types.ModuleType(full)
            mod.__package__ = "qrsaver"
            sys.modules[full] = mod
        mod.__file__ = __file__
        exec(compile(_SOURCES[name], "<qrsaver/%%s.py>" %% name, "exec"), mod.__dict__)
        if name != "__init__":
            setattr(pkg, name, mod)
    return sys.modules["qrsaver.gui"]


if __name__ == "__main__":
    _load().main()
''' % ORDER)
with open(os.path.join(ROOT, "amis_qr_saver.py"), "w", encoding="utf-8", newline="\n") as f:
    f.write("".join(out))
print("생성: amis_qr_saver.py")
