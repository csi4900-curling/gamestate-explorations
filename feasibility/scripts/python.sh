#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
PYTHON_BIN="${CURLING_PYTHON:-$ROOT/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Python environment missing. Create .venv and install requirements.txt (see README.md)." >&2
  exit 1
fi
# Nix host: Python wheels require system zlib and C++ runtime.
if [[ -d /nix/store ]]; then
  EXTRA="$("$PYTHON_BIN" - <<'PY'
import glob,struct,os
out=[]
for pat in ['/nix/store/*zlib*/lib/libz.so.1','/nix/store/*gcc*/lib/libstdc++.so.6']:
 for f in glob.glob(pat):
  h=open(f,'rb').read(20)
  if h[4]==2 and struct.unpack('<H',h[18:20])[0]==62:
   out.append(os.path.dirname(f));break
print(':'.join(out))
PY
)"
  export LD_LIBRARY_PATH="$EXTRA${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi
exec "$PYTHON_BIN" "$@"
