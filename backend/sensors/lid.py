"""macOS 上的 pybooklid 合页。实测范围见项目知识中的验收记录。"""

import threading
import time
import sys
import ctypes

from sensors.ambient import AmbientProbe
from sensors.base import AngleSource


def configure_shared_hid():
    """只允许共享打开；扩展不兼容时给出诊断，不退回独占设备。"""
    try:
        import hid
    except ImportError as error:
        raise RuntimeError("合页共享读取：无法导入 hid 扩展，请检查当前传感器环境") from error
    try:
        library = ctypes.CDLL(hid.__file__)
        shared_open = library.hid_darwin_set_open_exclusive
        shared_open.argtypes = [ctypes.c_int]
        shared_open.restype = None
        shared_open(0)
    except (OSError, AttributeError, TypeError) as error:
        raise RuntimeError(
            f"合页共享读取配置失败：{type(error).__name__}；"
            "需要 hid 扩展导出 hid_darwin_set_open_exclusive，"
            "请核对实际 hidapi 版本及动态库，未尝试独占打开"
        ) from error


class PyBookLidSource(AngleSource):
    """后台线程按 hz 读，read() 只返回最近一次落在 0~360 的值。超过 1 秒没有新值则 None。"""

    name = "pybooklid"
    mode = "sensor"

    def __init__(self, hz):
        try:
            from pybooklid import LidSensor, LidSensorError  # noqa: F401
        except Exception as e:
            raise RuntimeError(
                f"无法导入 pybooklid：{e}\n"
                "  请执行：pip install -r backend/requirements-sensor.txt\n"
                "  若提示找不到 hidapi：brew install hidapi\n"
                "  或直接 ./start.sh --sensor"
            )
        if sys.platform == "darwin":
            configure_shared_hid()

        try:
            self.sensor = LidSensor()
        except Exception as e:
            raise RuntimeError(f"合页初始化失败（共享打开已配置）：{type(e).__name__}: {e}") from e
        self._latest = None
        self._last_ok = 0.0
        self._stop = False
        self._interval = 1.0 / max(hz, 1)
        self._als = AmbientProbe()
        self._th = threading.Thread(target=self._loop, daemon=True)
        self._th.start()

    def read_light(self):
        try:
            return self._als.read()
        except Exception:
            return None

    def _loop(self):
        while not self._stop:
            t = time.time()
            try:
                a = self.sensor.read_angle()
            except Exception:
                a = None
            if a is not None and 0.0 <= a <= 360.0:
                self._latest = a
                self._last_ok = t
            time.sleep(max(0.0, self._interval - (time.time() - t)))

    def read(self):
        if self._latest is None or time.time() - self._last_ok > 1.0:
            return None
        return self._latest

    def close(self):
        self._stop = True
        try:
            self.sensor.disconnect()
        except Exception:
            pass
