"""Composer page implementation."""
from __future__ import annotations

import json
from pathlib import Path
from PySide6.QtWidgets import QInputDialog, QMessageBox, QTableWidgetItem, QWidget
from common.processes.task_runner import Job
from common.projects.registry import project_valid
from common.validation.commands import PACKAGE
from pages.base import BasePage
from common.ui.widgets import hbox


class ComposerPage(BasePage):
    def __init__(self, context, parent=None):
        super().__init__(context, parent)
        self.mount(self.build_composer)
        context.quick_action_requested.connect(self.handle_quick_action)

    def handle_quick_action(self, action):
        if action == "composer_install":
            self.composer_simple(["install", "--no-interaction"])

    def on_activated(self):
        self.show_packages()

    def after_rebuild(self):
        self.show_packages()

    def on_project_changed(self, _path):
        if hasattr(self, "packages_table"):
            self.show_packages()

    def build_composer(self):
        w,v=self.page('Composer','Local dependency health, installed packages and safe dependency operations.')
        tools=QWidget();tools.setObjectName('panelRow');tools.setLayout(hbox(
            self.btn('Install',lambda:self.composer_simple(['install','--no-interaction']),'primary'),
            self.btn('Validate',lambda:self.composer_simple(['validate'])),
            self.btn('Outdated',lambda:self.composer_simple(['outdated'])),
            self.btn('Audit',lambda:self.composer_simple(['audit'])),
            self.btn('Update',self.composer_update,'danger')))
        v.addWidget(tools)
        f,g=self.card('DEPENDENCIES · composer.json')
        self.packages_table=self.editable_table(['Package','Constraint','Environment'])
        g.addWidget(self.packages_table)
        x=QWidget();x.setObjectName('panelRow');x.setLayout(hbox(self.btn('Require a package',self.require_package,'primary'),self.btn('Remove selected',self.remove_package,'danger'),self.btn('Reload list',self.show_packages)))
        g.addWidget(x);v.addWidget(f,1)
        return w

    def show_packages(self):
        self.packages_table.setRowCount(0)
        if not self.current or not project_valid(self.current): return
        try:
            conf=json.loads((Path(self.current)/'composer.json').read_text(encoding='utf-8'))
            for section,title in [('require','production'),('require-dev','development')]:
                for pkg,constraint in conf.get(section,{}).items():
                    row=self.packages_table.rowCount();self.packages_table.insertRow(row)
                    for col,txt in enumerate((pkg,str(constraint),title)):
                        self.packages_table.setItem(row,col,QTableWidgetItem(txt))
        except (OSError,ValueError): pass

    def composer_simple(self,args):
        p=self.require_project()
        if p:self.enqueue_job(Job('Composer '+' '.join(args),'composer',args,p,success=lambda _:self.context.projects_changed.emit()))

    def composer_update(self):
        if self.confirm('Composer update','This may upgrade dependency versions and change composer.lock. Commit your files first. Continue?',warning=True)==QMessageBox.StandardButton.Yes:
            self.composer_simple(['update','--no-interaction'])

    def require_package(self):
        pkg,ok=QInputDialog.getText(self,self.tr('Composer require'),self.tr('Package (vendor/name)'))
        if not ok:return
        pkg=pkg.strip().lower()
        if not PACKAGE.fullmatch(pkg):return self.alert('Invalid package','Use vendor/package (lowercase).',True)
        dev=self.confirm('Development only?','Add this dependency to require-dev?')
        args=['require',pkg,'--no-interaction'] + (['--dev'] if dev==QMessageBox.StandardButton.Yes else [])
        self.composer_simple(args)

    def remove_package(self):
        i=self.packages_table.currentRow()
        if i<0:return
        pkg=self.packages_table.item(i,0).text()
        if pkg in ('php','laravel/framework'):
            return self.alert('Protected dependency','Core framework / PHP requirements cannot be removed here.',True)
        if self.confirm('Remove package','Run composer remove {package}?'.format(package=pkg))==QMessageBox.StandardButton.Yes:
            self.composer_simple(['remove',pkg,'--no-interaction'])
