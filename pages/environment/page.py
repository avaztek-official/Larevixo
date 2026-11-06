"""Environment page implementation."""
from __future__ import annotations

import hashlib
import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QInputDialog, QLineEdit, QTableWidgetItem, QWidget
from common.environment.env_file import ENV_KEY, atomic_write_env, parse_env, read_env_file, update_env
from common.projects.registry import project_valid
from pages.base import BasePage
from common.ui.widgets import hbox


class EnvironmentPage(BasePage):
    def __init__(self, context, parent=None):
        super().__init__(context, parent)
        self.active_env = ""
        self.env_lines = []
        self._loaded_project = None
        self._rebuild_env_rows = None
        self.mount(self.build_environment)

    def on_activated(self):
        if self._loaded_project != self.current:
            self.load_env()

    def on_project_changed(self, _path):
        self.active_env = ""
        self.env_lines = []
        self._loaded_project = None
        self._rebuild_env_rows = None
        if hasattr(self, "env_table"):
            self.env_table.setRowCount(0)
            self.load_env()

    def before_rebuild(self):
        if not hasattr(self, "env_table"):
            self._rebuild_env_rows = None
            return
        self._rebuild_env_rows = [
            (
                self.env_table.item(row, 0).text(),
                str(self.env_table.item(row, 1).data(Qt.ItemDataRole.UserRole)),
            )
            for row in range(self.env_table.rowCount())
        ]

    def after_rebuild(self):
        if self._rebuild_env_rows is None:
            return
        self.env_table.setRowCount(0)
        for key, value in self._rebuild_env_rows:
            row = self.env_table.rowCount()
            self.env_table.insertRow(row)
            self._env_item(row, key, value)
        self._rebuild_env_rows = None

    def build_environment(self):
        w,v=self.page('Environment editor','Edit .env keys with secret masking and automatic backups.')
        f,g=self.card('PROJECT ENVIRONMENT', 'Double-click a row to edit. Sensitive keys are masked until you explicitly edit them.')
        self.env_table=self.editable_table(['Key','Value'])
        self.env_table.cellDoubleClicked.connect(self.edit_env_row)
        g.addWidget(self.env_table)
        actions=QWidget();actions.setObjectName('panelRow');actions.setLayout(hbox(self.btn('Add key',self.add_env),self.btn('Delete selected',self.delete_env,'danger'),self.btn('Reload',self.load_env),self.btn('Save .env',self.save_env,'primary')))
        g.addWidget(actions);v.addWidget(f,1)
        v.addWidget(self.label('Backups are stored outside the project in your local Larevixo data folder. Never commit .env to Git.'))
        return w

    def secret(self, key):
        return bool(re.search(r'PASSWORD|SECRET|TOKEN|KEY|CREDENTIAL|PRIVATE',key,re.I))

    def _env_item(self,row,key,value):
        self.env_table.setItem(row,0,QTableWidgetItem(key))
        item=QTableWidgetItem('••••••••' if self.secret(key) else value)
        item.setData(Qt.ItemDataRole.UserRole,value)
        self.env_table.setItem(row,1,item)

    def load_env(self):
        self.env_table.setRowCount(0)
        self.active_env=''
        self.env_lines=[]
        self._loaded_project = self.current
        if not self.current or not project_valid(self.current): return
        file=Path(self.current)/'.env'
        if not file.is_file():
            self.append_console('ℹ No .env found. Create it from .env.example with Laravel tooling.\n');return
        try:
            self.active_env=read_env_file(file)
            self.env_lines=parse_env(self.active_env)
            for key,val,_ in self.env_lines:
                row=self.env_table.rowCount();self.env_table.insertRow(row);self._env_item(row,key,val)
        except (OSError,UnicodeError) as err: self.alert('Read error',str(err),True)

    def edit_env_row(self,row,column):
        key=self.env_table.item(row,0).text()
        item=self.env_table.item(row,1)
        old=item.data(Qt.ItemDataRole.UserRole)
        mode=QLineEdit.EchoMode.Password if self.secret(key) else QLineEdit.EchoMode.Normal
        value,ok=QInputDialog.getText(self,self.tr('Edit {key}').format(key=key),self.tr('New value'),mode,str(old))
        if ok:self._env_item(row,key,value)

    def add_env(self):
        key,ok=QInputDialog.getText(self,self.tr('New environment key'),self.tr('Key (e.g. APP_LOCALE)'))
        if not ok:return
        if not ENV_KEY.fullmatch(key) or any(self.env_table.item(i,0).text()==key for i in range(self.env_table.rowCount())):
            return self.alert('Invalid key','Key must be unique and contain only letters, digits or underscores.',True)
        val,ok=QInputDialog.getText(self,self.tr('New environment value'),self.tr('Value'),QLineEdit.EchoMode.Password if self.secret(key) else QLineEdit.EchoMode.Normal)
        if ok:
            row=self.env_table.rowCount();self.env_table.insertRow(row);self._env_item(row,key,val)

    def delete_env(self):
        row=self.env_table.currentRow()
        if row>=0:self.env_table.removeRow(row)

    def save_env(self):
        p=self.require_project()
        if not p:return
        file=Path(p)/'.env'
        if not file.is_file(): return self.alert('Missing .env','A .env file must exist before editing it.',True)
        pairs=[(self.env_table.item(i,0).text(),str(self.env_table.item(i,1).data(Qt.ItemDataRole.UserRole))) for i in range(self.env_table.rowCount())]
        try:
            updated=update_env(self.active_env,pairs)
            # Prevent silent overwriting if another editor has modified the source.
            current=read_env_file(file)
            if current!=self.active_env:
                return self.alert('File changed','The .env file was changed outside Larevixo. Reload and retry.',True)
            if updated==current: return self.alert('No changes','The .env contents are unchanged.')
            stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f')
            root=Path(os.environ.get('LOCALAPPDATA') or str(Path.home() / '.local' / 'share')) / 'Larevixo' / 'env-backups'
            safe_folder=hashlib.sha256(str(file.resolve()).encode('utf-8')).hexdigest()[:20]
            backup_dir=root/safe_folder
            backup_dir.mkdir(parents=True,exist_ok=True)
            backup=backup_dir/(stamp+'.env.bak')
            shutil.copy2(file,backup)
            atomic_write_env(file,updated,file.stat().st_mode)
            self.active_env=updated
            self.append_console('.env saved; backup: '+str(backup)+'\n')
            self.alert('Saved','Changes saved with a local backup. You may need to clear Laravel config cache.')
        except (OSError,ValueError) as exc: self.alert('Save error',str(exc),True)
