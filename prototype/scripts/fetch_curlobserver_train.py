"""Fetch a pinned, reproducible development sample of public stone boxes."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import random
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "prototype"))
from cache_contract import file_sha256

REVISION = "2cfe61efede3c446957ee94aefa8df1345fc4684"
BASE = (
    "https://raw.githubusercontent.com/CurlObserver/dataset/"
    + REVISION
    + "/curling_dataset/curling_detect_dataset/"
)


def fetch_one(output, index, kind, suffix):
    target = output / f"{index:04d}.{suffix}"
    if not target.exists():
        url = BASE + f"{kind}/{index:04d}.{suffix}"
        for attempt in range(4):
            try:
                with urllib.request.urlopen(url, timeout=60) as response:
                    data = response.read()
                temporary = target.with_suffix(target.suffix + ".part")
                temporary.write_bytes(data)
                temporary.replace(target)
                break
            except OSError:
                if attempt == 3:
                    raise
                time.sleep(1 + attempt)
    return {"index": index, "kind": kind, "sha256": file_sha256(target)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--count", type=int, default=300)
    parser.add_argument("--seed", type=int, default=20261007)
    args = parser.parse_args()
    if not 1 <= args.count <= 1000:
        parser.error("Count must be between 1 and 1000")
    excluded = json.loads((ROOT / "validation/curlobserver-probe/manifest.json").read_text())[
        "sample_indices"
    ]
    # Guard nearby frames too; this still does not prove match-level separation.
    pool = [
        index
        for index in range(5000)
        if all(abs(index - fixed) > 20 for fixed in excluded)
    ]
    chosen = sorted(random.Random(args.seed).sample(pool, args.count))
    selection = {
        "status": "published_label_development_sample",
        "revision": REVISION,
        "seed": args.seed,
        "count": args.count,
        "indices": chosen,
        "excluded_probe_indices": excluded,
        "exclusion_radius": 20,
        "limitation": "No source-match IDs; this is not a match-independent train/test split.",
    }
    selection_path = args.output / "selection.json"
    if args.output.exists():
        if not selection_path.exists() or json.loads(selection_path.read_text()) != selection:
            parser.error("Existing output has a different or missing selection")
    else:
        args.output.mkdir(parents=True)
        selection_path.write_text(json.dumps(selection, indent=2) + "\n")
    tasks = [
        (index, kind, suffix)
        for index in chosen
        for kind, suffix in (("images", "jpg"), ("labels", "txt"))
    ]
    rows = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [
            executor.submit(fetch_one, args.output, index, kind, suffix)
            for index, kind, suffix in tasks
        ]
        for future in as_completed(futures):
            rows.append(future.result())
    selection["files"] = sorted(rows, key=lambda row: (row["index"], row["kind"]))
    (args.output / "manifest.json").write_text(json.dumps(selection, indent=2) + "\n")
    print(json.dumps({"images": args.count, "files": len(rows)}))


if __name__ == "__main__":
    main()
