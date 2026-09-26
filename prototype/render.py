from pathlib import Path
import json


def render(data, path):
    template = (Path(__file__).parent / "viewer.html").read_text()
    payload = (
        json.dumps(data, separators=(",", ":"))
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    Path(path).write_text(template.replace("__DATA__", payload))
