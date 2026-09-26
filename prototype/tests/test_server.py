import http.client
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import server


class QuietHandler(server.Handler):
    def log_message(self, *args):
        pass


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.folder = tempfile.TemporaryDirectory()
        cls.old_root = server.ROOT
        server.ROOT = Path(cls.folder.name)
        (server.ROOT / "test.mp4").write_bytes(b"0123456789")
        cls.http = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
        cls.thread = threading.Thread(target=cls.http.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        cls.thread.join()
        server.ROOT = cls.old_root
        cls.folder.cleanup()

    def request(self, method, path, headers=None, body=None):
        c = http.client.HTTPConnection("127.0.0.1", self.http.server_port, timeout=5)
        c.request(method, path, body=body, headers=headers or {})
        r = c.getresponse()
        result = (r.status, dict(r.headers), r.read())
        c.close()
        return result

    def test_range_and_suffix(self):
        for value, content in [("bytes=2-5", b"2345"), ("bytes=-3", b"789"), ("bytes=8-", b"89")]:
            status, headers, data = self.request("GET", "/test.mp4", {"Range": value})
            self.assertEqual(status, 206)
            self.assertEqual(data, content)
            self.assertEqual(int(headers["Content-Length"]), len(content))

    def test_invalid_range(self):
        status, headers, data = self.request("GET", "/test.mp4", {"Range": "bytes=99-100"})
        self.assertEqual(status, 416)
        self.assertEqual(headers["Content-Range"], "bytes */10")
        self.assertEqual(data, b"")

    def test_invalid_upload_metadata(self):
        status, _, _ = self.request("POST", "/api/upload?interval=nan", body=b"x")
        self.assertEqual(status, 400)

    def test_unknown_endpoint(self):
        self.assertEqual(self.request("POST", "/api/nope")[0], 404)
