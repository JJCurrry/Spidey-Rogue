"""M29 网页版存档（localStorage 后端）测试。

只验证「传输层」作为纯 dict ↔ 存储的桥接：
- localStorage 往返与文件往返在 dict 层面逐字节等价（序列化仍走 Game.to_dict，#26）；
- 浏览器环境（localStorage 可用）下默认选 LocalStorageBackend、否则回退文件；
- _handle_key 的 S/L 分支经由可插拔 SAVE_BACKEND，不写死路径（#29）；
- 无存档 / 存储不可用时走既有的 try/except 兜底（不崩、给友好提示）。

不引入任何新随机；全部走既有 Game 方法。
"""
import os
import sys
import json
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from rogue import Game  # noqa: E402
from rogue.rng import RandomSource  # noqa: E402
import rogue.web_storage as ws  # noqa: E402
import main as _main  # noqa: E402
from main import _handle_key  # noqa: E402

SEED = 19


def _build_full(**over):
    kw = dict(fov=True, stealth=True, noise=True, light=True,
              flashlight=True, switches=True, boss=True, boss_depth=3)
    kw.update(over)
    return Game.procedural(RandomSource(SEED), depth=1, **kw)


class FakeStorage:
    """模拟浏览器 localStorage（dict 后端，方法签名对齐 JS 接口）。"""

    def __init__(self):
        self._d = {}

    def setItem(self, key, value):
        self._d[key] = value

    def getItem(self, key):
        return self._d.get(key)

    def removeItem(self, key):
        self._d.pop(key, None)


class TestLocalStorageBackend(unittest.TestCase):
    def setUp(self):
        self._orig = ws._local_storage
        self.fake = FakeStorage()
        ws._local_storage = lambda: self.fake

    def tearDown(self):
        ws._local_storage = self._orig

    def test_roundtrip_preserves_full_state(self):
        g = _build_full()
        backend = ws.LocalStorageBackend()
        backend.save(g)
        self.assertIn(ws.SAVE_KEY, self.fake._d)
        g2 = _build_full(boss=False)
        backend.load_into(g2)
        # 与文件后端同一套 to_dict 序列化 ⇒ dict 逐字节等价（#26 / #29）
        self.assertEqual(g2.to_dict(), g.to_dict())
        self.assertEqual(g2.rng.get_state(), g.rng.get_state())

    def test_stored_json_is_deterministic(self):
        g = _build_full()
        blob = json.dumps(g.to_dict(), ensure_ascii=False, indent=2, sort_keys=True)
        ws.LocalStorageBackend().save(g)
        self.assertEqual(self.fake._d[ws.SAVE_KEY], blob)

    def test_missing_save_raises_filenotfound(self):
        backend = ws.LocalStorageBackend()
        g = _build_full()
        with self.assertRaises(FileNotFoundError):
            backend.load_into(g)

    def test_save_raises_when_unavailable(self):
        ws._local_storage = lambda: None  # 模拟无 localStorage 环境
        backend = ws.LocalStorageBackend()
        g = _build_full()
        with self.assertRaises(RuntimeError):
            backend.save(g)


class TestBackendAutoDetect(unittest.TestCase):
    def setUp(self):
        self._orig = ws._local_storage

    def tearDown(self):
        ws._local_storage = self._orig

    def test_prefers_local_storage_when_available(self):
        ws._local_storage = lambda: FakeStorage()
        backend = ws.get_default_backend("/tmp/x.json")
        self.assertIsInstance(backend, ws.LocalStorageBackend)

    def test_falls_back_to_file_when_unavailable(self):
        ws._local_storage = lambda: None
        backend = ws.get_default_backend("/tmp/x.json")
        self.assertIsInstance(backend, ws.FileSaveBackend)
        self.assertEqual(backend.path, "/tmp/x.json")


class TestFileBackendFallback(unittest.TestCase):
    """回退路径与 M26 文件语义一致（本地预览 / headless 用）。"""

    def test_file_roundtrip(self):
        g = _build_full()
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "save.json")
            ws.FileSaveBackend(path).save(g)
            self.assertTrue(os.path.exists(path))
            g2 = Game.load(path)
        self.assertEqual(g2.to_dict(), g.to_dict())


class TestHandleKeyUsesBackend(unittest.TestCase):
    """_handle_key 的 S/L 经由可插拔 SAVE_BACKEND，不写死路径（#29）。"""

    def setUp(self):
        self._orig_backend = _main.SAVE_BACKEND
        self._orig_local = ws._local_storage
        self.fake = FakeStorage()
        ws._local_storage = lambda: self.fake
        _main.SAVE_BACKEND = ws.LocalStorageBackend()

    def tearDown(self):
        ws._local_storage = self._orig_local
        _main.SAVE_BACKEND = self._orig_backend

    def test_S_writes_to_backend_storage(self):
        g = _build_full()
        acted, msg = _handle_key(g, "S")
        self.assertTrue(acted)
        self.assertEqual(msg, "已存档")
        self.assertIn(ws.SAVE_KEY, self.fake._d)

    def test_L_restores_state(self):
        g = _build_full()
        _handle_key(g, "S")
        g2 = _build_full(boss=False)  # 初值不同，验证被原地覆盖
        acted, msg = _handle_key(g2, "L")
        self.assertTrue(acted)
        self.assertEqual(msg, "已读档")
        self.assertEqual(g2.to_dict(), g.to_dict())

    def test_L_without_save_returns_friendly_message(self):
        g = _build_full()
        acted, msg = _handle_key(g, "L")
        self.assertFalse(acted)
        self.assertIn("先用 S 存档", msg)

    def test_backend_unavailable_returns_error(self):
        ws._local_storage = lambda: None  # 模拟 localStorage 不可用
        g = _build_full()
        acted, msg = _handle_key(g, "L")
        self.assertFalse(acted)
        self.assertIn("读档失败", msg)


if __name__ == "__main__":
    unittest.main()
