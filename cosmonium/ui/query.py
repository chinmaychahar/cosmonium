from __future__ import print_function
from __future__ import absolute_import

from panda3d.core import LVector3, KeyboardButton, TextNode, LColor
from direct.gui.DirectGui import DirectEntry
from direct.gui.DirectFrame import DirectFrame
from direct.gui.OnscreenText import OnscreenText

from .. import settings

class Query:
    text_size = 12 * 1.5
    suggestions_text_size = 12

    def __init__(self, scale, font):
        self.scale = scale
        self.font = font
        self.background = None
        self.prefix = None
        self.query = None
        self.suggestions = None
        self.owner = None
        self.current_selection = -1
        self.current_list = []
        self.completion_task = None
        self.max_columns = 4
        self.max_lines = 3
        self.max_elems = self.max_columns * self.max_lines

    def do_query(self, text):
        if self.current_selection >= 0 and self.current_selection < len(self.current_list):
            body = self.current_list[self.current_selection][1]
            self.owner.select_object(body)
        self.close()

    def close(self):
        self.background.destroy()
        self.background = None
        self.prefix.destroy()
        self.prefix = None
        self.query.destroy()
        self.query = None
        self.suggestions.destroy()
        self.suggestions = None
        self.current_selection = -1
        self.current_list = []
        if self.completion_task is not None:
            taskMgr.remove(self.completion_task)
            self.completion_task = None

    def escape(self, event):
        self.close()

    def update_suggestions(self):
        page = self.current_selection // self.max_elems
        start = page * self.max_elems
        end = min(start + self.max_elems - 1, len(self.current_list) - 1)
        suggestions = ""
        for i in range(start, end + 1):
            if i != start and ((i - start) % self.max_columns) == 0:
                suggestions += '\n'
            if i == self.current_selection:
                suggestions += "\1md_bold\1%s\2" % self.current_list[i][0]
            else:
                suggestions += self.current_list[i][0]
            suggestions += '\t'
        self.suggestions.setText(suggestions)

    def completion(self, event):
        text = self.query.get()
        if text != '':
            self.current_list = self.owner.list_objects(text)
        else:
            self.current_list = []
        self.current_selection = 0
        if self.completion_task is not None:
            taskMgr.remove(self.completion_task)
        self.completion_task = taskMgr.doMethodLater(settings.query_delay, self.update_suggestions, 'completion task', extraArgs=[])

    def select(self, event):
        modifiers = event.getModifierButtons()
        if modifiers.isDown(KeyboardButton.shift()):
            incr = -1
        else:
            incr = 1
        new_selection = self.current_selection + incr
        if new_selection < 0:
            new_selection = len(self.current_list) - 1
        if new_selection >= len(self.current_list):
            new_selection = 0
        self.current_selection = new_selection
        self.update_suggestions()

    def open_query(self, owner):
        self.owner = owner
        bg_color = LColor(*settings.hud_color)
        bg_color[3] = 0.2
        scale3 = LVector3(self.scale[0], 1.0, self.scale[1])
        self.background = DirectFrame(frameColor=bg_color,
                                      frameSize=(-1 / self.scale[0], 1.0 / self.scale[0],
                                                 0.15 + self.scale[1] * self.text_size, 0.0),
                                      parent=base.a2dBottomLeft)
        self.prefix = OnscreenText(text="Target name:",
                                   font=self.font,
                                   fg=settings.hud_color,
                                   align=TextNode.ALeft,
                                   parent=base.a2dBottomLeft,
                                   scale=tuple(self.scale * self.text_size),
                                   pos=(0, .15),
                                   )
        bounds = self.prefix.getTightBounds()
        length = bounds[1][0] - bounds[0][0] + self.scale[0] * self.text_size / 2
        self.query = DirectEntry(text="",
                                 text_fg=settings.hud_color,
                                 scale=tuple(scale3 * self.text_size),
                                 command=self.do_query,
                                 parent=base.a2dBottomLeft,
                                 frameColor=(0, 0, 0, 0),
                                 pos=(length, 0, .15),
                                 initialText = "",
                                 numLines = 1,
                                 width = 200,
                                 entryFont=self.font,
                                 focus=1,
                                 suppressKeys=1)
        self.query.bind("press-escape-", self.escape)
        self.query.bind("press-tab-", self.select)
        self.query.accept(self.query.guiItem.getTypeEvent(), self.completion)
        self.query.accept(self.query.guiItem.getEraseEvent(), self.completion)
        pos = self.prefix.getPos()
        bounds = self.query.getBounds()
        llz = bounds[2] / self.text_size
        self.suggestions = OnscreenText(text = "",
                                       font=self.font,
                                       fg=settings.hud_color,
                                       align=TextNode.ALeft,
                                       mayChange=True,
                                       parent=base.a2dBottomLeft,
                                       scale=tuple(self.scale * self.suggestions_text_size),
                                       pos=(pos[0], pos[1] + llz),
                                       )
