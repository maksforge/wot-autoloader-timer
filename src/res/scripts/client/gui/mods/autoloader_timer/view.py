from gui.mods.gambiter import g_guiFlash
from gui.mods.gambiter.flash import COMPONENT_ALIGN, COMPONENT_EVENT, COMPONENT_TYPE

from . import schedule

ALIAS = 'maksforgeAutoloaderTimer'
SEPARATOR = '  |  '

_SHADOW = {'color': 0x000000, 'alpha': 0.9, 'blurX': 3, 'blurY': 3, 'strength': 3, 'quality': 2}


def format_segments(slots, settings):
    colors = settings['colors']
    loaded = sum(1 for slot in slots if slot.state == schedule.LOADED)
    if loaded == len(slots):
        return [('%d/%d' % (loaded, len(slots)), colors['loaded'])]
    segments = [('%d/%d' % (loaded, len(slots)), colors['count'])]
    for slot in slots:
        if slot.state == schedule.LOADING:
            segments.append(('%.1f' % max(0.0, slot.ready_in), colors['loading']))
        elif slot.state == schedule.QUEUED:
            segments.append(('%.1f' % max(0.0, slot.ready_in), colors['queued']))
    return segments


class PanelView(object):

    def __init__(self, settings, on_moved):
        self._settings = settings
        self._on_moved = on_moved
        self._shown = None
        props = {
            'text': '',
            'isHtml': True,
            'visible': False,
            'alignX': COMPONENT_ALIGN.CENTER,
            'alignY': COMPONENT_ALIGN.CENTER,
            'glowfilter': _SHADOW,
            'drag': True,
            'x': settings['x'],
            'y': settings['y'],
        }
        g_guiFlash.createComponent(ALIAS, COMPONENT_TYPE.LABEL, props)
        COMPONENT_EVENT.UPDATED += self._on_component_updated

    def destroy(self):
        COMPONENT_EVENT.UPDATED -= self._on_component_updated
        g_guiFlash.deleteComponent(ALIAS)

    def show(self, segments):
        text = self._html(segments) if segments else None
        if text == self._shown:
            return
        self._shown = text
        if text is None:
            g_guiFlash.updateComponent(ALIAS, {'visible': False})
        else:
            g_guiFlash.updateComponent(ALIAS, {'text': text, 'visible': True})

    def hide(self):
        self.show(None)

    def _html(self, segments):
        parts = ["<font color='#%s'>%s</font>" % (color, text) for text, color in segments]
        separator = "<font color='#%s'>%s</font>" % (self._settings['colors']['count'], SEPARATOR)
        return "<font face='$FieldFont' size='%d'>%s</font>" % (self._settings['fontSize'], separator.join(parts))

    def _on_component_updated(self, alias, props):
        if alias != ALIAS or 'x' not in props or 'y' not in props:
            return
        self._settings['x'] = int(props['x'])
        self._settings['y'] = int(props['y'])
        self._on_moved()
