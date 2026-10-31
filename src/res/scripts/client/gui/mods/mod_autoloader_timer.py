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
        if _timer.settings['enabled'] and _timer.settings['reloadChatLine']:
            from gui.mods.autoloader_timer import reload_chat
            reload_chat.install(_timer.slots)
    except Exception:
        LOG_CURRENT_EXCEPTION()


def fini():
    if _timer is not None:
        _timer.stop()
