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


class FakeCrosshair(object):

    def __init__(self):
        self.position = (1280, 625)
        self.onCrosshairPositionChanged = _Event()
        self.onCrosshairSizeChanged = _Event()
        self.onCrosshairScaleChanged = _Event()
        self.onCrosshairViewChanged = _Event()

    def getScaleFactor(self):
        return 1.0

    def getSize(self):
        return (2560, 1440)

    def getDisaredPosition(self):
        return self.position

    def move_to(self, x, y):
        self.position = (x, y)
        self.onCrosshairPositionChanged(x, y)


def _install_stubs(guiflash, ammo, crosshair, player_events, callbacks):
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
    battle_control = module('gui.battle_control', avatar_getter=module(
        'gui.battle_control.avatar_getter', isPlayerOnArena=lambda: True, isVehicleAlive=lambda: True))
    battle_control.__path__ = []
    controllers = module('gui.battle_control.controllers')
    controllers.__path__ = []

    class ChatCommandsController(object):
        sent = []
        cooldown = False
        chat_enabled = True
        broadcast_fails = False

        def sendReloadingCommand(self):
            ChatCommandsController.sent.append('game reload command')

    module('gui.battle_control.controllers.chat_cmd_ctrl', ChatCommandsController=ChatCommandsController)
    module('messenger').__path__ = []
    module('messenger.m_constants', PROTO_TYPE=_Obj(BW_CHAT2=2))
    module('messenger.ext', isBattleChatEnabled=lambda: ChatCommandsController.chat_enabled)

    def broadcast(text, channel):
        if ChatCommandsController.broadcast_fails:
            raise RuntimeError('broadcast failed')
        ChatCommandsController.sent.append((text, channel))

    team_chat = _Obj(isBroadcastInCooldown=lambda: ChatCommandsController.cooldown, broadcast=broadcast)

    class _ProtoGetter(object):
        def __init__(self, _):
            pass

        def __call__(self, fn):
            return property(lambda self: _Obj(arenaChat=team_chat))

    module('messenger.proto', proto_getter=_ProtoGetter)
    gambiter = module('gui.mods.gambiter', g_guiFlash=guiflash)
    gambiter.__path__ = []
    mods.gambiter = gambiter
    module('gui.mods.gambiter.flash',
           COMPONENT_ALIGN=_Obj(CENTER='center'),
           COMPONENT_TYPE=_Obj(LABEL='Label'),
           COMPONENT_EVENT=_Obj(UPDATED=_Event()))


class _StubbedGameTest(unittest.TestCase):

    def setUp(self):
        for name in [name for name in sys.modules if name.startswith('gui.mods.')]:
            del sys.modules[name]
        self.cwd = os.getcwd()
        self.tmp = tempfile.mkdtemp()
        os.chdir(self.tmp)
        self.guiflash = FakeGuiFlash()
        self.ammo = FakeAmmo()
        self.events = _Obj(onAvatarReady=_Event(), onAvatarBecomeNonPlayer=_Event())
        self.crosshair = FakeCrosshair()
        self.callbacks = []
        _install_stubs(self.guiflash, self.ammo, self.crosshair, self.events, self.callbacks)

    def tearDown(self):
        os.chdir(self.cwd)
        shutil.rmtree(self.tmp)


class ModSmokeTest(_StubbedGameTest):

    def label(self):
        return self.guiflash.components.get('maksforgeAutoloaderTimer', {})

    def test_renders_one_line_and_writes_default_config(self):
        mod = importlib.import_module("gui.mods.mod_autoloader_timer")
        mod.init()
        self.events.onAvatarReady()
        text = self.label()['text']
        self.assertTrue(self.label()['visible'])
        self.assertTrue(text.endswith("<font color='#D8D8D8'>1/3</font></font>"))
        self.assertIn("<font color='#FCAF1A'>4.0</font>", text)
        self.assertEqual((self.label()['x'], self.label()['y']), (0, -35))
        self.assertIn("<font color='#D8D8D8'>14.8</font>", text)

        self.crosshair.move_to(1280, 720)
        self.assertEqual((self.label()['x'], self.label()['y']), (0, 60))
        self.assertTrue(os.path.isfile(os.path.join('mods', 'configs', 'autoloader_timer', 'config.json')))

        chat_ctrl = sys.modules['gui.battle_control.controllers.chat_cmd_ctrl'].ChatCommandsController
        chat_ctrl().sendReloadingCommand()
        self.assertEqual(chat_ctrl.sent, [('Ready to fire! Magazine 1/3, full in 15 s', 0)])
        chat_ctrl.cooldown = True
        chat_ctrl().sendReloadingCommand()
        self.assertEqual(chat_ctrl.sent[-1], 'game reload command')

        self.ammo.shells = (30, 3)
        self.ammo.clip_state = FakeState(0.0, 0.0)
        self.ammo.shell_change_time = 6.75
        self.callbacks[-1]()
        text = self.label()['text']
        self.assertTrue(text.endswith("<font color='#C7FE48'>3/3</font></font>"))
        self.assertLess(text.index('>10.8<'), text.index('>11.7<'))
        self.assertLess(text.index('>11.7<'), text.index('>13.5<'))
        chat_ctrl.cooldown = False
        chat_ctrl().sendReloadingCommand()
        self.assertEqual(chat_ctrl.sent[-1], ('Ready to fire! Magazine 3/3', 0))

        self.ammo.gun.hasAutoReload = lambda: False
        self.callbacks[-1]()
        self.assertFalse(self.label()['visible'])
        mod.fini()
        self.assertEqual(self.guiflash.components, {})
        self.assertEqual(self.crosshair.onCrosshairPositionChanged.handlers, [])


def _slots(*states_and_times):
    schedule = sys.modules['gui.mods.autoloader_timer.schedule']
    return [schedule.Slot(number, state, ready_in=ready_in)
            for number, (state, ready_in) in enumerate(states_and_times, 1)]


class ReloadChatTest(_StubbedGameTest):

    def setUp(self):
        super(ReloadChatTest, self).setUp()
        self.reload_chat = importlib.import_module('gui.mods.autoloader_timer.reload_chat')
        self.chat_ctrl = sys.modules['gui.battle_control.controllers.chat_cmd_ctrl'].ChatCommandsController
        self.slots = []
        self.reload_chat.install(lambda: self.slots)

    def press_reload(self):
        self.chat_ctrl().sendReloadingCommand()
        return self.chat_ctrl.sent

    def test_empty_magazine_reports_first_shell_and_full_magazine(self):
        self.slots = _slots(('loading', 8.2), ('queued', 20.0), ('queued', 34.5))
        self.assertEqual(self.press_reload(), [('Reloading! First shell 9 s, full in 35 s', 0)])

    def test_rack_that_cannot_fill_the_magazine_reports_how_far_it_gets(self):
        self.slots = _slots(('loaded', 0.0), ('loading', 8.2), ('no_ammo', 0.0), ('no_ammo', 0.0))
        self.assertEqual(self.press_reload(), [('Ready to fire! Magazine 1/4, 2/4 in 9 s', 0)])

    def test_empty_magazine_with_short_rack_reports_how_far_it_gets(self):
        self.slots = _slots(('loading', 4.0), ('queued', 15.2), ('no_ammo', 0.0))
        self.assertEqual(self.press_reload(), [('Reloading! First shell 4 s, 2/3 in 16 s', 0)])

    def test_out_of_shells_sends_game_command(self):
        self.slots = _slots(('no_ammo', 0.0), ('no_ammo', 0.0), ('no_ammo', 0.0))
        self.assertEqual(self.press_reload(), ['game reload command'])

    def test_chat_disabled_sends_game_command(self):
        self.slots = _slots(('loaded', 0.0), ('loading', 8.2), ('queued', 20.0))
        self.chat_ctrl.chat_enabled = False
        self.assertEqual(self.press_reload(), ['game reload command'])

    def test_error_in_magazine_line_sends_game_command_once(self):
        logged = []
        self.reload_chat.LOG_CURRENT_EXCEPTION = lambda: logged.append(sys.exc_info()[0])
        self.slots = _slots(('loaded', 0.0), ('loading', 8.2), ('queued', 20.0))
        self.chat_ctrl.broadcast_fails = True
        self.assertEqual(self.press_reload(), ['game reload command'])
        self.assertEqual(logged, [RuntimeError])


if __name__ == '__main__':
    unittest.main()
