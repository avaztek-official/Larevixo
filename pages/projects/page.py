"""Projects page implementation."""
from __future__ import annotations

import json
import re
from pathlib import Path
from PySide6.QtWidgets import QDialog, QFileDialog, QMessageBox, QTableWidgetItem, QWidget
from common.dialogs.create_project import CreateDialog
from common.laravel.versions import LARAVEL_MIN_PHP, latest_laravel_major, laravel_php_compatible, php_version_tuple
from common.projects.registry import laravel_version, project_valid
from common.processes.task_runner import Job
from pages.base import BasePage
from common.ui.widgets import hbox


class ProjectsPage(BasePage):
    def __init__(self, context, parent=None):
        super().__init__(context, parent)
        self._rebuild_selected_path = None
        self.mount(self.build_projects)
        context.projects_changed.connect(self.refresh_projects)
        context.quick_action_requested.connect(self.handle_quick_action)
        self.refresh_projects()

    def handle_quick_action(self, action):
        if action == "import_project":
            self.import_project()
        elif action == "create_project":
            self.create_project()

    def refresh_projects(self):
        if not hasattr(self, "projects_table"):
            return
        self.projects_table.setRowCount(0)
        for project in self.store.projects:
            row = self.projects_table.rowCount()
            self.projects_table.insertRow(row)
            values = (Path(project).name, laravel_version(project), project, self.tr("Ready") if project_valid(project) else self.tr("Missing / invalid"))
            for column, value in enumerate(values):
                self.projects_table.setItem(row, column, QTableWidgetItem(value))

    def on_activated(self):
        self.refresh_projects()

    def on_project_changed(self, _path):
        if hasattr(self, "projects_table"):
            self.refresh_projects()

    def after_rebuild(self):
        self.refresh_projects()
        if self._rebuild_selected_path:
            for row in range(self.projects_table.rowCount()):
                path = self.projects_table.item(row, 2)
                if path and path.text() == self._rebuild_selected_path:
                    self.projects_table.selectRow(row)
                    break
        self._rebuild_selected_path = None

    def before_rebuild(self):
        row = self.projects_table.currentRow() if hasattr(self, "projects_table") else -1
        item = self.projects_table.item(row, 2) if row >= 0 else None
        self._rebuild_selected_path = item.text() if item else None

    def build_projects(self):
        w,v=self.page('Projects','Your Laravel installations, remembered across sessions.')
        self.projects_table=self.editable_table(['Project','Laravel','Path','Status'])
        self.projects_table.doubleClicked.connect(self.select_project_table)
        v.addWidget(self.projects_table,1)
        r=QWidget();r.setObjectName('panelRow');r.setLayout(hbox(self.btn('Import project',self.import_project,icon_name='folder-input'),self.btn('Create new project',self.create_project,'primary','folder-plus'),self.btn('Remove from list',self.remove_project,'danger'),self.btn('Refresh',self.refresh_projects)))
        v.addWidget(r)
        v.addWidget(self.label('Removing a project only forgets the saved path. It never deletes files.'))
        return w

    def select_project_table(self):
        i=self.projects_table.currentRow()
        if i < 0: return
        p=self.projects_table.item(i,2).text()
        self.context.select_project(p)

    def remove_project(self):
        i=self.projects_table.currentRow()
        if i<0: return
        p=self.projects_table.item(i,2).text()
        if self.confirm('Forget project','Forget {path}? The project files will not be touched.'.format(path=p)) != QMessageBox.StandardButton.Yes:return
        self.context.remove_project(p)

    def import_project(self):
        p=QFileDialog.getExistingDirectory(self, self.tr('Choose an existing Laravel project'), str(Path.home()))
        if not p: return
        try: self.context.add_project(p)
        except ValueError as exc: return self.alert('Not a Laravel project', str(exc), True)
        self.refresh_projects()
        self.append_console('Imported: '+p+'\n')

    def handle_php_version(self, output):
        try:
            match = re.search(r'LAREVIXO_PHP_VERSION=(\d+\.\d+(?:\.\d+)?)', output)
            if not match:
                raise ValueError('Could not determine the PHP version.')
            version = match.group(1)
            php_version_tuple(version)
            latest_laravel_major(version)
        except ValueError as exc:
            self.alert('PHP unavailable or unsupported', 'Configure a working PHP 8.1–8.x executable before creating a Laravel project.\n\n'+str(exc), True)
            return
        self.show_create_project_dialog(version)

    def create_project(self):
        self.enqueue_job(Job('Check PHP version', 'php', ['-r', 'echo "LAREVIXO_PHP_VERSION=" . PHP_VERSION;'], str(Path.home()),
                             success=self.handle_php_version,
                             failure=lambda error: self.alert('PHP unavailable or unsupported', 'Configure a working PHP 8.1–8.x executable before creating a Laravel project.\n\n'+error, True)))

    def show_create_project_dialog(self, php_version):
        dialog=CreateDialog(self, php_version, self.context.translator)
        if dialog.exec() != QDialog.DialogCode.Accepted: return
        settings = dialog.settings()
        name,base,version,remove,add,with_npm = settings[:6]
        auth_stack, composer_packages, npm_packages = settings[6:] if len(settings) > 6 else ('', [], [])
        major = dialog.selected_major()
        if not laravel_php_compatible(php_version, major):
            minimum = LARAVEL_MIN_PHP[major]
            return self.alert('Unsupported PHP version', f'Laravel {major}.x requires PHP {minimum[0]}.{minimum[1]} or newer; configured PHP is {php_version}.', True)
        target=base/name
        try:
            base.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return self.alert('Cannot create parent folder', str(exc), True)
        args=['create-project','laravel/laravel',str(target),'--no-interaction']
        args.insert(3,'^'+major+'.0')
        def created(_):
            if project_valid(target):
                self.context.add_project(target)
                self.append_console('Project created. Applying package selections…\n')
                # Read the actual generated composer file; versions differ in default dependencies.
                try:
                    conf=json.loads((target/'composer.json').read_text(encoding='utf-8'))
                    installed=set(conf.get('require',{})) | set(conf.get('require-dev',{}))
                except (OSError,ValueError): installed=set()
                for package in remove:
                    if package in installed:
                        self.enqueue_job(Job('Remove unchecked default: '+package,'composer',['remove',package,'--no-interaction'],str(target)))
                for package,dev in add:
                    a=['require',package,'--no-interaction']
                    if dev: a.append('--dev')
                    self.enqueue_job(Job('Install: '+package,'composer',a,str(target)))
                for package, package_version in composer_packages:
                    spec = package + (':' + package_version if package_version else '')
                    self.enqueue_job(Job('Install: '+spec,'composer',['require',spec,'--no-interaction'],str(target)))
                if auth_stack:
                    def install_auth(_):
                        self.enqueue_job(Job(
                            'Install Laravel Breeze authentication', 'php',
                            ['artisan', 'breeze:install', auth_stack, '--no-interaction'], str(target)))
                    self.enqueue_job(Job(
                        'Install Laravel Breeze', 'composer',
                        ['require', 'laravel/breeze', '--dev', '--no-interaction'], str(target),
                        success=install_auth))
                frontend_packages = [package + ('@' + package_version if package_version else '')
                                     for package, package_version in npm_packages]
                if with_npm or auth_stack in {'react', 'vue'} or frontend_packages:
                    self.enqueue_job(Job('Install frontend packages','npm',
                                         ['install','--ignore-scripts',*frontend_packages],str(target)))
                self.context.navigate_requested.emit('Projects')
            else:
                self.alert('Incomplete installation', 'Composer finished but no valid artisan/composer.json found. Check Activity Console.', True)
        self.enqueue_job(Job('Create Laravel '+major+' · '+name,'composer',args,str(base),success=created))
        self.append_console('ℹ Project creation uses Composer. Installed package versions are resolved by Composer.\n')
