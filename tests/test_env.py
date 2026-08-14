# -*- coding: utf-8 -*-
import os
import tempfile
import unittest
from pathlib import Path

from truthhistory.utils.env import load_env


class TestLoadEnv(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env_path = str(Path(self.tmp.name) / ".env")
        # 테스트 간 환경 변수 오염 방지
        self._saved = {k: os.environ.get(k) for k in
                       ("TH_TEST_A", "TH_TEST_B", "TH_TEST_C", "TH_TEST_D")}
        for k in self._saved:
            os.environ.pop(k, None)

    def tearDown(self):
        for k, v in self._saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    def _write(self, content: str):
        Path(self.env_path).write_text(content, encoding="utf-8")

    def test_loads_key_value_pairs(self):
        self._write("TH_TEST_A=secret1\nTH_TEST_B=secret2\n")
        loaded = load_env(self.env_path)
        self.assertEqual(loaded, 2)
        self.assertEqual(os.environ["TH_TEST_A"], "secret1")
        self.assertEqual(os.environ["TH_TEST_B"], "secret2")

    def test_skips_comments_blanks_and_malformed_lines(self):
        self._write("# 주석\n\nTH_TEST_A=value\ninvalid-line\n=nonkey\n")
        loaded = load_env(self.env_path)
        self.assertEqual(loaded, 1)
        self.assertEqual(os.environ["TH_TEST_A"], "value")

    def test_strips_quotes_and_export_prefix(self):
        self._write('TH_TEST_A="quoted"\nexport TH_TEST_B=\'single\'\n')
        loaded = load_env(self.env_path)
        self.assertEqual(loaded, 2)
        self.assertEqual(os.environ["TH_TEST_A"], "quoted")
        self.assertEqual(os.environ["TH_TEST_B"], "single")

    def test_existing_os_env_takes_precedence(self):
        os.environ["TH_TEST_A"] = "from_os"
        self._write("TH_TEST_A=from_file\nTH_TEST_B=loaded\n")
        loaded = load_env(self.env_path)
        self.assertEqual(loaded, 1)
        self.assertEqual(os.environ["TH_TEST_A"], "from_os")
        self.assertEqual(os.environ["TH_TEST_B"], "loaded")

    def test_missing_file_returns_zero(self):
        self.assertEqual(load_env(str(Path(self.tmp.name) / "nope.env")), 0)


if __name__ == "__main__":
    unittest.main()
