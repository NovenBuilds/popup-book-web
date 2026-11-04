"""测试入口：端口冲突不得复用别人的服务，缺依赖不得触发安装。"""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests'))
from paths import assert_ports_free


class RuntimeTest(unittest.TestCase):
    def test_occupied_port_is_rejected_without_closing_owner(self):
        with socket.socket() as owner:
            owner.bind(('127.0.0.1', 0))
            owner.listen()
            port = owner.getsockname()[1]
            with self.assertRaisesRegex(RuntimeError, str(port)):
                assert_ports_free(port)
            self.assertEqual(owner.getsockname()[1], port)

    def test_no_install_reports_missing_python_and_exits(self):
        with tempfile.TemporaryDirectory() as directory:
            env = dict(os.environ, POPUP_PYTHON=os.path.join(directory, 'missing-python'))
            result = subprocess.run(['bash', str(ROOT / 'start.sh'), 'test', '--no-install'],
                                    cwd=ROOT, env=env, capture_output=True, text=True, timeout=10)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('缺少检查依赖', result.stderr)
            self.assertIn('missing-python', result.stderr)
