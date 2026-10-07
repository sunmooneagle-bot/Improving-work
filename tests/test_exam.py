import os
import tempfile
import unittest

from qrsaver import exam
from qrsaver.config import DEFAULTS
from qrsaver.hangul import normalize_code
from qrsaver.models import Store

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class ParseQrTest(unittest.TestCase):
    def test_new_format(self):
        self.assertEqual(exam.parse_qr("26C 054730;A;1;;FB0164;1"), ("26C 054730", "FB0164"))

    def test_hangul_scan(self):
        text = normalize_code("26ㅊ 054730;ㅁ;1;;류0164;1", amis_space=False)
        self.assertEqual(exam.parse_qr(text), ("26C 054730", "FB0164"))

    def test_old_format(self):
        self.assertEqual(exam.parse_qr("26-C -053637"), ("26-C -053637", ""))

    def test_amis_format(self):
        self.assertEqual(normalize_code("26C 054730"), "26-C -054730")
        self.assertEqual(normalize_code("26-S-082711"), "26-S -082711")


class TableTest(unittest.TestCase):
    def test_builtin(self):
        self.assertEqual(exam.ExamTable().name("FB0164"), "Voided urine (Des)[Liquid based cytology]")

    def test_xlsx(self):
        t = exam.ExamTable()
        n = t.load(os.path.join(ROOT, "검사코드.xlsx"))
        self.assertGreater(n, 100)
        self.assertEqual(t.name("fb0050"), "Cervical scrape (Des)[Liquid based cytology]")
        self.assertEqual(t.load(os.path.join(ROOT, "없는파일.xlsx")), 0)


class EnableTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.store = Store(os.path.join(self.dir.name, "q.json"))
        self.cfg = dict(DEFAULTS)
        self.t = exam.ExamTable()

    def tearDown(self):
        self.dir.cleanup()

    def enabled(self, code):
        item = self.store.add("26-C -%06d" % len(self.store.items), "", code, self.t.name(code))
        cols = ["Urine <30ml", "UC absent", "Inst 10~20", "Inst <10", "Vaginal", "Cell block 부적합"]
        return {c for c in cols if exam.check_enabled(item, c, self.cfg)}

    def test_categories(self):
        self.assertEqual(self.enabled("FB0164"), {"Urine <30ml", "UC absent"})                 # Voided urine
        self.assertEqual(self.enabled("FB0049"), {"Urine <30ml", "UC absent", "Inst 10~20", "Inst <10"})  # Catheter
        self.assertEqual(self.enabled("FB0161"), {"Vaginal"})                                   # Vaginal scrape
        self.assertEqual(self.enabled("FB0050"), {"Vaginal"})                                   # Cervical scrape
        self.assertEqual(self.enabled("FB0175"), {"Cell block 부적합"})                          # Pleural + cell block
        self.assertEqual(self.enabled("FB0125"), set())                                         # Pleural fluid

    def test_unknown_keeps_all(self):
        self.assertEqual(len(self.enabled("")), 6)
        self.assertEqual(len(self.enabled("ZZ9999")), 6)

    def test_effective_and_persist(self):
        item = self.store.add("26-C -1", "26C 1", "FB0164", self.t.name("FB0164"))
        self.store.set_checks(item.id, {"Urine <30ml": True, "Cell block 부적합": True})
        self.assertEqual(exam.effective_checks(item, self.cfg), {"Urine <30ml": True})
        again = Store(self.store.path).items[0]
        self.assertEqual((again.exam_code, again.raw), ("FB0164", "26C 1"))


if __name__ == "__main__":
    unittest.main()
