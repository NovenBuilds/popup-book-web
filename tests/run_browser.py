"""仅运行浏览器回归：独占专用端口，日志落盘，只关闭自己创建的服务。"""
import os
import signal
import http.client
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

from paths import ROOT, assert_ports_free


def main():
    logs = Path(ROOT) / '.run'
    logs.mkdir(exist_ok=True)
    assert_ports_free(8133, 18665, 18666)
    env = dict(os.environ, POPUP_PYTHON=sys.executable,
               PYTHONUNBUFFERED='1', POPUP_BASE='http://127.0.0.1:8133/index.html', POPUP_WS='18665', POPUP_HTTP='18666')
    with (logs / 'test-web.log').open('w') as log:
        web = subprocess.Popen([sys.executable, 'backend/static_server.py', '--port', '8133',
                                '--directory', 'frontend', '--bind', 'loopback'], cwd=ROOT,
                               stdout=log, stderr=subprocess.STDOUT)
        try:
            for _ in range(60):
                if web.poll() is not None:
                    raise RuntimeError('测试静态服务提前退出，见 .run/test-web.log')
                try:
                    with urllib.request.urlopen(env['POPUP_BASE'], timeout=0.5) as response:
                        if response.status == 200:
                            break
                except OSError:
                    time.sleep(0.1)
            else:
                raise RuntimeError('测试静态服务启动超时')
            modules = sorted((Path(ROOT) / 'frontend/js').glob('*.js'))
            def load_module(path):
                with urllib.request.urlopen(f'http://127.0.0.1:8133/js/{path.name}', timeout=10) as response:
                    assert response.status == 200 and response.read(), path.name
            for _ in range(3):
                with ThreadPoolExecutor(max_workers=32) as pool:
                    list(pool.map(load_module, modules))
            connection = http.client.HTTPConnection('127.0.0.1', 8133, timeout=5)
            try:
                original = None
                for _ in range(5):
                    connection.request('GET', '/index.html')
                    response = connection.getresponse()
                    assert response.status == 200 and response.version == 11
                    assert response.getheader('Cache-Control') == 'no-store'
                    response.read()
                    if original is None:
                        original = connection.sock
                    assert connection.sock is original and original is not None
            finally:
                connection.close()
            print(f'静态服务通过：3轮×{len(modules)}模块并发、5次同连接请求', flush=True)
            names = sys.argv[1:] or ['smoke', 'share_card', 'season_catchup']
            assert all(name in ('smoke', 'share_card', 'season_catchup') for name in names)
            for name in names:
                path = logs / f'test-{name}.log'
                print(f'浏览器检查：{name}；日志：{path}', flush=True)
                with path.open('w') as output:
                    process = subprocess.Popen([sys.executable, f'tests/e2e/{name}.py'],
                                               cwd=ROOT, env=env, stdout=output,
                                               stderr=subprocess.STDOUT, start_new_session=True)
                    try:
                        code = process.wait(timeout=240)
                    except subprocess.TimeoutExpired:
                        print(f'{name} 超时，见 {path}', flush=True)
                        code = 1
                    finally:
                        # 整个进程组均由本次测试创建，包括其假桥；超时也不会遗留。
                        try:
                            os.killpg(process.pid, signal.SIGTERM)
                        except ProcessLookupError:
                            pass
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                            process.wait()
                print(path.read_text(), flush=True)
                if code:
                    return code
        finally:
            web.terminate()
            try:
                web.wait(timeout=5)
            except subprocess.TimeoutExpired:
                web.kill()
                web.wait()
    return 0


if __name__ == '__main__':
    sys.exit(main())
