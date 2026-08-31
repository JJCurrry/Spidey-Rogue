"""静态文件服务器（带 pygbag/wasm 需要的 COOP/COEP 安全头）。

用法：python serve.py [port] [directory]
默认端口 8123，默认目录 build/web。
"""
from http.server import SimpleHTTPRequestHandler
import sys, os


class COOPHandler(SimpleHTTPRequestHandler):
    """给每个响应加上 Cross-Origin 安全头，让 Emscripten/SharedArrayBuffer 可用。"""

    def end_headers(self) -> None:
        # pygbag / Emscripten 要求这两条头才能启用 SharedArrayBuffer（多线程 WASM 必需）
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Cross-Origin-Embedder-Policy", "require-corp")
        super().end_headers()

    def log_message(self, format: str, *args) -> None:
        # 减少噪音，只显示关键请求
        print(f"  [{self.log_date_time_string()}] {format % args}")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8123
    directory = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), "build", "web")
    os.chdir(directory)
    print(f"=== Pygame-web 静态服务器（带 COOP/COEP） ===")
    print(f"  目录 : {os.path.abspath(directory)}")
    print(f"  端口 : {port}")
    print(f"  URL  : http://localhost:{port}")
    print(f"==========================================")
    from http.server import HTTPServer
    HTTPServer(("0.0.0.0", port), COOPHandler).serve_forever()
