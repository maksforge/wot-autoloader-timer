from gui.mods.gambiter import g_guiFlash
from gui.mods.gambiter.flash import COMPONENT_ALIGN, COMPONENT_EVENT, COMPONENT_TYPE

from . import schedule

ALIAS_PREFIX = 'maksforgeAutoloaderTimerLine'
MAX_LINES = 12

_STATE_COLOR_KEYS = {
    schedule.LOADED: 'loaded',
    schedule.LOADING: 'loading',
    schedule.QUEUED: 'queued',
    schedule.NO_AMMO: 'noAmmo',
}

_SHADOW = {'color': 0x000000, 'alpha': 0.9, 'blurX': 3, 'blurY': 3, 'strength': 3, 'quality': 2}


def _seconds(value):
    return '%.1fs' % max(0.0, value)


def format_lines(slots, settings):
    colors = settings['colors']
    loaded = sum(1 for slot in slots if slot.state == schedule.LOADED)
    remaining = schedule.full_in(slots)
    header = 'Autoloader %d/%d' % (loaded, len(slots))
    if remaining > 0:
        header += '   full in %s' % _seconds(remaining)
    lines = [(header, colors['header'])]
    for slot in slots:
        if slot.state == schedule.LOADED:
            text = '#%d  ready' % slot.number
        elif slot.state == schedule.NO_AMMO:
            text = '#%d  no ammo' % slot.number
        else:
            text = '#%d  %s' % (slot.number, _seconds(slot.ready_in))
            if settings['showOwnTime']:
                text += '  (%s)' % _seconds(slot.own_time)
        lines.append((text, colors[_STATE_COLOR_KEYS[slot.state]]))
    return lines


class PanelView(object):

    def __init__(self, settings, on_moved):
        self._settings = settings
        self._on_moved = on_moved
        self._shown = [None] * MAX_LINES
        for index in range(MAX_LINES):
            g_guiFlash.createComponent(self._alias(index), COMPONENT_TYPE.LABEL, self._base_props(index))
        COMPONENT_EVENT.UPDATED += self._on_component_updated

    def destroy(self):
        COMPONENT_EVENT.UPDATED -= self._on_component_updated
        for index in range(MAX_LINES):
            g_guiFlash.deleteComponent(self._alias(index))

    def show(self, lines):
        lines = lines[:MAX_LINES]
        for index in range(MAX_LINES):
            text = self._html(*lines[index]) if index < len(lines) else None
            if text == self._shown[index]:
                continue
            self._shown[index] = text
            if text is None:
                g_guiFlash.updateComponent(self._alias(index), {'visible': False})
            else:
                g_guiFlash.updateComponent(self._alias(index), {'text': text, 'visible': True})

    def hide(self):
        self.show([])

    def reposition(self):
        for index in range(MAX_LINES):
            g_guiFlash.updateComponent(self._alias(index), self._position(index))

    def _alias(self, index):
        return '%s%d' % (ALIAS_PREFIX, index)

    def _position(self, index):
        return {'x': self._settings['x'], 'y': self._settings['y'] + index * self._settings['lineHeight']}

    def _base_props(self, index):
        props = {
            'text': '',
            'isHtml': True,
            'visible': False,
            'alignX': COMPONENT_ALIGN.CENTER,
            'alignY': COMPONENT_ALIGN.CENTER,
            'glowfilter': _SHADOW,
            'drag': index == 0,
        }
        props.update(self._position(index))
        return props

    def _html(self, text, color):
        return "<font face='$FieldFont' size='%d' color='#%s'>%s</font>" % (self._settings['fontSize'], color, text)

    def _on_component_updated(self, alias, props):
        if alias != self._alias(0) or 'x' not in props or 'y' not in props:
            return
        self._settings['x'] = int(props['x'])
        self._settings['y'] = int(props['y'])
        self.reposition()
        self._on_moved()
