"""Content-addressed resume checks for costly experiments.
Legacy outputs are evidence, not automatically reusable caches.
"""

from __future__ import annotations
import hashlib
import json
from pathlib import Path


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def context_for(files, parameters):
    return {
        "schema": 1,
        "inputs": {f"{i}:{Path(p).name}": file_sha256(p) for i, p in enumerate(files)},
        "parameters": parameters,
    }


def read_cache(path, context, force=False):
    path = Path(path)
    if force or not path.exists():
        return None
    data = json.loads(path.read_text())
    if data.get("cache_context") != context:
        raise ValueError(
            f"{path}: stale or unversioned cache. Use --force to recompute, "
            "or --output with an empty directory. Existing evidence was not modified."
        )
    return data


def write_cache(path, data, context):
    path = Path(path)
    payload = dict(data, cache_context=context)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, separators=(",", ":"), allow_nan=False))
    temporary.replace(path)
