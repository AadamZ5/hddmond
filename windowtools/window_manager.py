import urwid


class WindowManager:

    @property
    def CurrentWidget(self):
        return self._loop.widget

    @CurrentWidget.setter
    def CurrentWidget(self, value):
        self._loop.widget = value

    def __init__(self, loop: urwid.MainLoop):
        self.pagestack = []
        self._loop = loop

    def OpenPage(self, page: urwid.Widget):
        if not ('box' in page._sizing):
            return False

        if(self.CurrentWidget != None):
            self.pagestack.append(self.CurrentWidget)
            self.CurrentWidget = page

    def PageClose(self, button=None, b):
