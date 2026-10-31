"""Loads the mod against stubbed game modules and renders one frame (run with Python 2.7)."""
import importlib
import os
import shutil
import sys
import tempfile
import types
import unittest

MODS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'res', 'scripts', 'client', 'gui', 'mods')


class _Event(object):

    def __init__(self):
        self.handlers = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self

    def __isub__(self, handler):
        self.handlers.remove(handler)
        return self

    def __call__(self, *args):
        for handler in list(self.handlers):
            handler(*args)


class FakeGuiFlash(object):

    def __init__(self):
        self.components = {}

    def createComponent(self, alias, compType, props=None, battle=True, lobby=False):
        self.components[alias] = dict(props or {})

    def updateComponent(self, alias, props, params=None):
        self.components[alias].update(props)

    def deleteComponent(self, alias):
        del self.components[alias]


class FakeState(object):

    def __init__(self, left, base):
        self.left, self.base = left, base

    def isReloading(self):
        return self.left > 0

    def getTimeLeft(self):
        return self.left

    def getBaseValue(self):
        return self.base


class FakeAmmo(object):

    def __init__(self):
        self.gun = _Obj(clip=_Obj(size=3), autoReload=_Obj(reloadTime=(12.0, 13.0, 15.0)))
        self.gun.hasAutoReload = lambda: True
        self.gun.hasShellChangeFactor = lambda: True
        self.gun.getShellChangeFactor = lambda: 0.5
        self.shell_change_time = 0.0
        self.shells = (30, 1)
        self.clip_state = FakeState(4.0, 11.7)

    def getGunSettings(self):
        return self.gun

    def getCurrentShellCD(self):
        return 1234

    def getCurrentShells(self):
        return self.shells

    def getPartiallyReloadingClipState(self):
        return self.clip_state

    def getShellChangeTime(self):
        return self.shell_change_time

    def getGunReloadingState(self):
        return FakeState(0.0, 0.0)


class _Obj(object):

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def _install_stubs(guiflash, ammo, player_events, callbacks):
    def module(name, **attrs):
        mod = types.ModuleType(name)
        mod.__dict__.update(attrs)
        sys.modules[name] = mod
        return mod

    module('BigWorld', callback=lambda delay, fn: callbacks.append(fn) or len(callbacks),
           cancelCallback=lambda cid: None)
    module('PlayerEvents', g_playerEvents=player_events)
    module('debug_utils', LOG_CURRENT_EXCEPTION=lambda: (_ for _ in ()).throw(sys.exc_info()[1]),
           LOG_ERROR=lambda *a: None)

    crosshair = _Obj(getScaleFactor=lambda: 1.0, getSize=lambda: (2560, 1440), getDisaredPosition=lambda: (1280, 625))
    provider = _Obj(shared=_Obj(ammo=ammo, crosshair=crosshair))

    class _Descriptor(object):
        def __init__(self, _):
            pass

        def __get__(self, obj, owner):
            return provider

    module('helpers', dependency=module('helpers.dependency', descriptor=_Descriptor))
    module('skeletons')
    module('skeletons.gui')
    module('skeletons.gui.battle_session', IBattleSessionProvider=object)
    gui = module('gui')
    gui.__path__ = []
    mods = module('gui.mods')
    mods.__path__ = [MODS_DIR]
    gui.mods = mods
    gambiter = module('gui.mods.gambiter', g_guiFlash=guiflash)
    gambiter.__path__ = []
    mods.gambiter = gambiter
    module('gui.mods.gambiter.flash',
           COMPONENT_ALIGN=_Obj(CENTER='center'),
           COMPONENT_TYPE=_Obj(LABEL='Label'),
           COMPONENT_EVENT=_Obj(UPDATED=_Event()))


class ModSmokeTest(unittest.TestCase):

    def setUp(self):
        self.cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        os.chdir(self.tmp)
        self.guiflash = FakeGuiFlash()
        self.ammo = FakeAmmo()
        self.events = _Obj(onAvatarReady=_Event(), onAvatarBecomeNonPlayer=_Event())
        self.callbacks = []
        _install_stubs(self.guiflash, self.ammo, self.events, self.callbacks)

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp)

    def label(self):
        return self.guiflash.components.get('maksforgeAutoloaderTimer', {})

    def test_renders_one_line_and_writes_default_config(self):
        mod = importlib.import_module("gui.mods.mod_autoloader_timer")
        mod.init()
        self.events.onAvatarReady()
        text = self.label()['text']
        self.assertTrue(self.label()['visible'])
        self.assertIn('1/3', text)
        self.assertNotIn('4.0', text)
        self.assertEqual((self.label()['x'], self.label()['y']), (0, -35))
        self.assertIn("<font color='#D8D8D8'>14.8</font>", text)
        self.assertTrue(os.path.isfile(os.path.join('mods', 'configs', 'autoloader_timer', 'config.json')))

        self.ammo.shells = (30, 3)
        self.ammo.clip_state = FakeState(0.0, 0.0)
        self.ammo.shell_change_time = 6.75
        self.callbacks[-1]()
        text = self.label()['text']
        self.assertIn("<font color='#C7FE48'>3/3</font>", text)
        self.assertLess(text.index('>10.8<'), text.index('>11.7<'))
        self.assertLess(text.index('>11.7<'), text.index('>13.5<'))

        self.ammo.gun.hasAutoReload = lambda: False
        self.callbacks[-1]()
        self.assertFalse(self.label()['visible'])
        mod.fini()
        self.assertEqual(self.guiflash.components, {})


if __name__ == '__main__':
    unittest.main()
