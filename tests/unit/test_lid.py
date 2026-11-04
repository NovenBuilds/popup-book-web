"""共享打开的兼容错误；所有设备与动态库均为模拟对象。"""
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from sensors.lid import configure_shared_hid


class SharedLidTest(unittest.TestCase):
    def test_shared_open_disables_exclusive(self):
        fn = Mock()
        with patch.dict(sys.modules, hid=SimpleNamespace(__file__='mock-hid')):
            with patch('sensors.lid.ctypes.CDLL', return_value=SimpleNamespace(hid_darwin_set_open_exclusive=fn)):
                configure_shared_hid()
        fn.assert_called_once_with(0)

    def test_missing_symbol_explains_shared_open_requirement(self):
        with patch.dict(sys.modules, hid=SimpleNamespace(__file__='mock-hid')):
            with patch('sensors.lid.ctypes.CDLL', return_value=object()):
                with self.assertRaisesRegex(RuntimeError, '未尝试独占打开'):
                    configure_shared_hid()

    def test_unloadable_extension_is_diagnostic(self):
        with patch.dict(sys.modules, hid=SimpleNamespace(__file__='mock-hid')):
            with patch('sensors.lid.ctypes.CDLL', side_effect=OSError('模拟动态库失败')):
                with self.assertRaisesRegex(RuntimeError, '共享读取配置失败'):
                    configure_shared_hid()
