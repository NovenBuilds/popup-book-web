"""测试用的仓库相对路径。截图落在 shots/（已 gitignore）。"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SHOTS = os.path.join(ROOT, "shots")
BASE = os.environ.get("POPUP_BASE", "http://127.0.0.1:8123/index.html")
BRIDGE = os.path.join(ROOT, "backend", "bridge.py")


def shot_dir(name=""):
    d = os.path.join(SHOTS, name) if name else SHOTS
    os.makedirs(d, exist_ok=True)
    return d


def python_cmd():
    env = os.environ.get("POPUP_PYTHON")
    if env:
        return env
    venv = os.path.join(ROOT, "backend", ".venv", "bin", "python")
    if os.path.isfile(venv):
        return venv
    return sys.executable


def assert_ports_free(*ports):
    """占用时拒绝启动，避免把他人的服务当作测试实例。"""
    import socket
    sockets = []
    try:
        for port in ports:
            for family, host in ((socket.AF_INET, '127.0.0.1'), (socket.AF_INET6, '::1')):
                sock = socket.socket(family, socket.SOCK_STREAM)
                sockets.append(sock)
                if family == socket.AF_INET6:
                    sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
                try:
                    sock.bind((host, port))
                except OSError as error:
                    if family == socket.AF_INET6 and error.errno in (47, 49, 97, 99):
                        continue
                    raise RuntimeError(f'测试端口 {host}:{port} 不可用；未启动测试服务') from error
    finally:
        for sock in sockets:
            sock.close()
