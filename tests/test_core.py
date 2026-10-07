import os
import tempfile
import unittest

from qrsaver.hangul import hangul_to_qwerty, looks_like_accession, normalize_code
from qrsaver.models import DONE, FAIL, RUN, WAIT, Store
from qrsaver.win32 import tick_diff


class HangulTest(unittest.TestCase):
    def test_jamo(self):
        self.assertEqual(normalize_code("26-ㅊ -053637\r\n"), "26-C -053637")

    def test_syllable(self):
        self.assertEqual(hangul_to_qwerty("한"), "gks")
        self.assertEqual(normalize_code("26-ㅠㄴ -1234"), "26-BS -1234")

    def test_plain(self):
        self.assertEqual(normalize_code("  26-c -053637 "), "26-C -053637")
        self.assertEqual(normalize_code("26-c -053637", fix_hangul=False, uppercase=False, amis_space=False), "26-c -053637")

    def test_pattern(self):
        self.assertTrue(looks_like_accession("26-C -053637"))
        self.assertTrue(looks_like_accession("26-B-004198"))
        self.assertFalse(looks_like_accession("hello"))


class StoreTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "q.json")

    def tearDown(self):
        self.dir.cleanup()

    def test_flow(self):
        s = Store(self.path)
        a = s.add("26-C -000001")
        b = s.add("26-C -000002")
        self.assertIsNone(s.add("26-C -000001"))
        self.assertIs(s.next_pending(), a)
        s.update(a, status=RUN)
        self.assertIs(s.next_pending(), b)
        s.update(a, status=DONE)
        s.update(b, status=FAIL, note="x")
        self.assertTrue(a.time)
        self.assertIsNone(s.next_pending())
        s.reset(statuses=(FAIL,))
        self.assertEqual(b.status, WAIT)
        c = s.counts()
        self.assertEqual((c["total"], c[DONE], c[WAIT]), (2, 1, 1))
        s.clear((DONE,))
        self.assertEqual([i.code for i in s.items], ["26-C -000002"])

    def test_persist_resets_running(self):
        s = Store(self.path)
        s.update(s.add("26-C -1"), status=RUN)
        s2 = Store(self.path)
        self.assertEqual(s2.items[0].status, WAIT)
        self.assertEqual(s2.add("26-C -2").id, 2)


class TickTest(unittest.TestCase):
    def test_wrap(self):
        self.assertEqual(tick_diff(5, 0xFFFFFFFF), 6)
        self.assertEqual(tick_diff(100, 300), -200)


if __name__ == "__main__":
    unittest.main()
