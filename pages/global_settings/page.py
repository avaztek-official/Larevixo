"""GlobalSettings page implementation."""
from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QFormLayout, QLineEdit, QPushButton, QWidget
from common.processes.task_runner import Job
from pages.base import BasePage
from common.ui.widgets import hbox


class GlobalSettingsPage(BasePage):
    def __init__(self, context, parent=None):
        super().__init__(context, parent)
        self._rebuild_tools = None
        self.mount(self.build_settings)

    def before_rebuild(self):
        self._rebuild_tools = {
            tool: edit.text() for tool, edit in self.tool_edits.items()
        } if hasattr(self, "tool_edits") else None

    def after_rebuild(self):
        if self._rebuild_tools is None:
            return
        for tool, value in self._rebuild_tools.items():
            if tool in self.tool_edits:
                self.tool_edits[tool].setText(value)
        self._rebuild_tools = None

    def build_settings(self):
        w,v=self.page('Global & Settings','Manage the global Laravel installer and local executable paths.')
        f,g=self.card('GLOBAL LARAVEL / COMPOSER')
        for text,args in [('Install Laravel CLI globally',['global','require','laravel/installer','--no-interaction']),
                          ('Update Laravel CLI',['global','update','laravel/installer','--no-interaction']),
                          ('Show global packages',['global','show']),('Composer diagnostics',['diagnose']),
                          ('Clear Composer cache',['clear-cache'])]:
            g.addWidget(self.btn(text,lambda checked=False,a=args:self.composer_global(a)))
        v.addWidget(f)
        x,xv=self.card('EXECUTABLE LOCATIONS', 'Use executable names on PATH or absolute paths; composer.phar is supported.')
        self.tool_edits={}
        form=QFormLayout()
        for t in ('php','composer','npm'):
            edit=QLineEdit(str(self.store.data['tools'].get(t,t)))
            self.tool_edits[t]=edit
            browse=QPushButton('...')
            browse.setFixedSize(48,42)
            browse.setToolTip(self.tr('Browse for executable'))
            browse.setCursor(Qt.CursorShape.PointingHandCursor)
            browse.clicked.connect(lambda checked=False, tool=t: self.browse_tool_path(tool))
            field=QWidget();field.setStyleSheet('background:transparent;');field.setLayout(hbox(edit,browse,gap=8))
            form.addRow(t.upper(),field)
        xv.addLayout(form)
        r=QWidget();r.setObjectName('panelRow');r.setLayout(hbox(self.btn('Save tool paths',self.save_tools,'primary'),self.btn('Check versions',self.check_versions)))
        xv.addWidget(r);v.addWidget(x)
        return w

    def browse_tool_path(self, tool):
        edit = self.tool_edits[tool]
        current = Path(edit.text().strip()).expanduser()
        start_dir = str(current if current.is_dir() else current.parent if current.is_file() else Path.home())
        path, _ = QFileDialog.getOpenFileName(
            self, self.tr('Select executable'), start_dir,
            self.tr('Executable files') + ' (*.exe *.bat *.cmd *.phar);;' + self.tr('All files') + ' (*)',
        )
        if path:
            edit.setText(path)

    def composer_global(self,args):
        self.enqueue_job(Job('Composer '+' '.join(args),'composer',args,str(Path.home())))

    def save_tools(self):
        for k,e in self.tool_edits.items():self.store.data['tools'][k]=e.text().strip()
        self.store.save();self.runner.tools=self.store.data['tools']
        self.alert('Saved','Executable paths updated.')

    def check_versions(self):
        self.save_tools()
        for tool in ('php','composer','npm'):
            self.enqueue_job(Job(tool+' version',tool,['--version'],str(Path.home())))
