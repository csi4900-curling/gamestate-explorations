"""Loopback-only upload/workbench server. Uses the current Python environment."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from concurrent.futures import ThreadPoolExecutor
import argparse, json, re, uuid, shutil
from pipeline import analyse, PROFILES

ROOT = Path(__file__).resolve().parent
POOL = ThreadPoolExecutor(max_workers=1)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        if urlsplit(self.path).path == "/":
            self.path = "/upload.html"
        super().do_GET()

    def respond(self, code, obj):
        payload = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):
        if urlsplit(self.path).path != "/api/upload":
            return self.respond(404, {"error": "Unknown endpoint"})
        q = parse_qs(urlsplit(self.path).query)
        profile = q.get("profile", ["dual_end"])[0]
        try:
            size = int(self.headers.get("Content-Length", "0"))
            interval = float(q.get("interval", ["10"])[0])
            if size <= 0 or size > 8 * 1024**3:
                raise ValueError("Choose a video smaller than 8 GiB")
            if profile not in PROFILES or not 1 <= interval <= 300:
                raise ValueError("Invalid profile or interval")
        except ValueError as e:
            return self.respond(400, {"error": str(e)})
        name = Path(q.get("name", ["upload.mp4"])[0]).name
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", name)[:120] or "upload.mp4"
        run_id = uuid.uuid4().hex[:12]
        out = ROOT / "runs" / run_id
        out.mkdir(parents=True)
        folder = ROOT / "uploads" / run_id
        folder.mkdir(parents=True)
        video = folder / safe
        self.connection.settimeout(120)
        try:
            with video.open("wb") as f:
                remaining = size
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise ValueError("Upload ended early")
                    f.write(chunk)
                    remaining -= len(chunk)
        except Exception as e:
            video.unlink(missing_ok=True)
            return self.respond(400, {"error": str(e)})
        (out / "status.json").write_text(
            json.dumps({"state": "queued", "progress": 0, "message": "Queued for indexing"})
        )
        POOL.submit(analyse, video, out, profile, interval)
        self.respond(
            202,
            {
                "id": run_id,
                "status_url": f"/runs/{run_id}/status.json",
                "result_url": f"/runs/{run_id}/index.html",
            },
        )

    def send_head(self):
        # Byte-range support makes large local videos seekable in the browser.
        self._range = None
        path = Path(self.translate_path(self.path))
        value = self.headers.get("Range")
        if value and path.is_file() and path.suffix.lower() in {".mp4", ".webm", ".mov", ".mkv"}:
            size = path.stat().st_size

            def unsatisfiable():
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.send_header("Content-Length", "0")
                self.end_headers()

            m = re.fullmatch(r"bytes=(\d*)-(\d*)", value)
            if not m or not any(m.groups()):
                unsatisfiable()
                return None
            a, b = m.groups()
            if a:
                start = int(a)
                end = min(int(b), size - 1) if b else size - 1
            else:
                start = max(0, size - int(b))
                end = size - 1
            if start >= size or start > end:
                unsatisfiable()
                return None
            f = path.open("rb")
            f.seek(start)
            self._range = end - start + 1
            self.send_response(206)
            self.send_header("Content-Type", self.guess_type(str(path)))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Content-Length", str(self._range))
            self.end_headers()
            return f
        return super().send_head()

    def copyfile(self, source, outputfile):
        try:
            if self._range is None:
                return shutil.copyfileobj(source, outputfile)
            remaining = self._range
            while remaining:
                chunk = source.read(min(256 * 1024, remaining))
                if not chunk:
                    break
                outputfile.write(chunk)
                remaining -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8765)
    a = p.parse_args()
    s = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print(f"Workbench: http://127.0.0.1:{a.port}", flush=True)
    try:
        s.serve_forever()
    except KeyboardInterrupt:
        s.server_close()
        POOL.shutdown(wait=False, cancel_futures=True)
