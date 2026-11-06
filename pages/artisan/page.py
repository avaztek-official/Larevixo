"""Artisan page implementation."""
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QMessageBox, QWidget
from common.dialogs.artisan import ArtisanDialog
from common.laravel.packages import ARTISAN_PRESETS
from common.processes.task_runner import Job
from common.ui.widgets import AnchoredComboBox
from pages.base import BasePage
from common.ui.widgets import hbox


class ArtisanPage(BasePage):
    def __init__(self, context, parent=None):
        super().__init__(context, parent)
        self._rebuild_command = None
        self.mount(self.build_artisan)

    def before_rebuild(self):
        self._rebuild_command = self.artisan_combo.currentText() if hasattr(self, "artisan_combo") else None

    def after_rebuild(self):
        if self._rebuild_command:
            index = self.artisan_combo.findText(self._rebuild_command)
            if index >= 0:
                self.artisan_combo.setCurrentIndex(index)
        self._rebuild_command = None

    def build_artisan(self):
        w,v=self.page('Artisan studio','Generate controllers, models, migrations and more—without memorizing flags.')
        f,g=self.card('GENERATORS', 'Select a preset and fill in its parameters.')
        self.artisan_combo=self.configure_searchable_combo(AnchoredComboBox());self.artisan_combo.addItems(ARTISAN_PRESETS.keys())
        r=QWidget();r.setObjectName('panelRow');r.setLayout(hbox(self.artisan_combo,self.btn('Configure & run',self.artisan_dialog,'primary')));g.addWidget(r)
        v.addWidget(f)
        quick, qv=self.card('COMMON COMMANDS')
        for name,command in [('Clear caches',['optimize:clear']),('Generate app key',['key:generate']),('List artisan commands',['list']),('Run tests',['test'])]:
            qv.addWidget(self.btn(name,lambda checked=False,cmd=command,lab=name:self.artisan(cmd,lab)))
        v.addWidget(quick)
        v.addStretch(1)
        return w

    def artisan(self,args,title='Artisan command',success=None):
        p=self.require_project()
        if not p:return
        if args==['key:generate'] and self.confirm('Rotate encryption key?','Changing APP_KEY can invalidate encrypted data and sessions. Continue?',warning=True)!=QMessageBox.StandardButton.Yes:return
        self.enqueue_job(Job(title,'php',['artisan',*args],p,success=success))

    def artisan_dialog(self):
        cmd=self.artisan_combo.currentText(); dialog=ArtisanDialog(cmd,self,self.context.translator)
        if dialog.exec()==QDialog.DialogCode.Accepted:
            self.artisan(dialog.args(),cmd)
