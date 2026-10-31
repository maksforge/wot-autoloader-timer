import math

import BigWorld
from debug_utils import LOG_CURRENT_EXCEPTION
from gui.battle_control import avatar_getter
from gui.battle_control.controllers.chat_cmd_ctrl import ChatCommandsController
from messenger.m_constants import PROTO_TYPE
from messenger.proto import proto_getter

from . import schedule

TEAM_CHANNEL = 0
AFTER_QUICK_COMMAND_SECONDS = 1.0


class _TeamChat(object):

    @proto_getter(PROTO_TYPE.BW_CHAT2)
    def proto(self):
        return None

    def send(self, text):
        arena_chat = self.proto.arenaChat
        if arena_chat.isBroadcastInCooldown():
            return
        arena_chat.broadcast(text, TEAM_CHANNEL)


def _seconds(value):
    return int(math.ceil(max(0.0, value)))


def magazine_text(slots):
    loaded = sum(1 for slot in slots if slot.state == schedule.LOADED)
    pending = [slot for slot in slots if slot.state in (schedule.LOADING, schedule.QUEUED)]
    if not pending:
        return None
    text = 'Magazine %d/%d' % (loaded, len(slots))
    if loaded == 0:
        text += ', first shell %d s' % _seconds(pending[0].ready_in)
    return text + ', full in %d s' % _seconds(schedule.full_in(slots))


def install(get_slots):
    original = ChatCommandsController.sendReloadingCommand
    team_chat = _TeamChat()

    def send_magazine_status():
        try:
            if not avatar_getter.isPlayerOnArena() or not avatar_getter.isVehicleAlive():
                return
            slots = get_slots()
            text = magazine_text(slots) if slots else None
            if text:
                team_chat.send(text)
        except Exception:
            LOG_CURRENT_EXCEPTION()

    def sendReloadingCommand(self):
        original(self)
        # The game rejects a chat message sent within 0.5 s of a quick command.
        BigWorld.callback(AFTER_QUICK_COMMAND_SECONDS, send_magazine_status)

    ChatCommandsController.sendReloadingCommand = sendReloadingCommand
