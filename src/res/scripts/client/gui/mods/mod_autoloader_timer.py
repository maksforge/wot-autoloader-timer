from debug_utils import LOG_CURRENT_EXCEPTION, LOG_ERROR

_timer = None


def init():
    global _timer
    try:
        import gui.mods.gambiter  # noqa: F401
    except ImportError:
        LOG_ERROR('[autoloader_timer] GUIFlash (gambiter.guiflash) is not installed; the mod is disabled.')
        return
    try:
        from gui.mods.autoloader_timer.timer import AutoloaderTimer
        _timer = AutoloaderTimer()
        _timer.start()
    except Exception:
        LOG_CURRENT_EXCEPTION()


def fini():
    if _timer is not None:
        _timer.stop()
