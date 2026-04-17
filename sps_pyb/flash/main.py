import sys


def _add_lib_path(path):
    if path not in sys.path:
        sys.path.append(path)


_add_lib_path("/flash/lib")
_add_lib_path("lib")

try:
    import config
except ImportError as exc:
    raise SystemExit("Missing config.py on the board filesystem") from exc

from app.runtime import run_forever


run_forever(config)
