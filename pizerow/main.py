from pathlib import Path
import sys


def _bootstrap_package():
    root = Path(__file__).resolve().parent.parent
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


if __package__ in (None, ""):
    _bootstrap_package()
    from pizerow import config
    from pizerow.app.runtime import run_forever
else:
    from . import config
    from .app.runtime import run_forever


run_forever(config)
