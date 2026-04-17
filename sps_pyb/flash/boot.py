try:
    import os
except ImportError:
    import uos as os


def _path_exists(path):
    try:
        os.stat(path)
        return True
    except OSError:
        return False


def _ensure_dir(path):
    if _path_exists(path):
        return

    parent = path.rsplit("/", 1)[0]
    if parent and parent != path and not _path_exists(parent):
        _ensure_dir(parent)

    try:
        os.mkdir(path)
    except OSError:
        pass


def _get_sd_device():
    try:
        from machine import SDCard

        return SDCard()
    except Exception:
        pass

    try:
        from pyb import SDCard

        return SDCard()
    except Exception:
        pass

    try:
        from pyb import SD

        return SD()
    except Exception:
        return None


def _mount_sd():
    if _path_exists("/sd"):
        return True

    sd = _get_sd_device()
    if sd is None:
        print("boot: no SDCard interface available")
        return False

    try:
        os.mount(sd, "/sd")
    except AttributeError:
        try:
            sd.mount()
        except Exception as exc:
            print("boot: SD mount failed:", exc)
            return False
    except OSError as exc:
        print("boot: SD mount failed:", exc)
        return False

    return _path_exists("/sd")


try:
    os.chdir("/flash")
except OSError:
    pass

if not _path_exists("/flash/SKIPSD"):
    print("boot: /flash/SKIPSD is missing; create it to force boot from internal flash")

if _mount_sd():
    _ensure_dir("/sd/history")
    _ensure_dir("/sd/queue")
    print("boot: SD storage ready at /sd")
else:
    print("boot: SD storage unavailable; live publish only")
