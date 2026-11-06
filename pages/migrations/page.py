"""Migrations page implementation."""
from __future__ import annotations

import re
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QHBoxLayout, QHeaderView, QInputDialog, QMessageBox, QTableWidget, QTableWidgetItem, QWidget
from common.processes.task_runner import Job
from common.projects.registry import project_valid
from pages.base import BasePage
from common.ui.widgets import hbox


class MigrationsPage(BasePage):
    def __init__(self, context, parent=None):
        super().__init__(context, parent)
        self._migration_status_inflight = set()
        self._migration_output_project = None
        self._migration_output = None
        self.mount(self.build_migrations)
        context.quick_action_requested.connect(self.handle_quick_action)

    def handle_quick_action(self, action):
        if action == "migration_status":
            self.migrate_status()

    def on_activated(self):
        if self.current and project_valid(self.current):
            self.migrate_status()

    def on_project_changed(self, path):
        self._migration_output_project = None
        self._migration_output = None
        if hasattr(self, "migration_table"):
            self.migration_table.setRowCount(0)
            self.set_migration_refreshing(path in self._migration_status_inflight)

    def after_rebuild(self):
        if self._migration_output_project == self.current and self._migration_output is not None:
            self.show_migrations(self.current, self._migration_output)
        self.set_migration_refreshing(self.current in self._migration_status_inflight)

    def build_migrations(self):
        w,v=self.page('Migrations','Inspect migration history and apply controlled database changes.')
        self.migration_refresh_button=self.btn('Refresh status',self.migrate_status,'primary')
        if self.current in self._migration_status_inflight:
            self.set_migration_refreshing(True)
        cmds=QWidget();cmds.setObjectName('panelRow');cmds.setLayout(hbox(
            self.migration_refresh_button,
            self.btn('Run all pending',lambda:self.migration_op('migrate')),
            self.btn('Rollback last batch',lambda:self.migration_op('migrate:rollback'), 'danger'),
            self.btn('Fresh database',lambda:self.migration_op('migrate:fresh'),'danger')))
        v.addWidget(cmds)
        f,g=self.card('MIGRATION STATUS', 'Migration files, execution order, and database status.')
        self.migration_table=QTableWidget(0,4)
        self.migration_table.setHorizontalHeaderLabels([self.tr('Priority'),self.tr('Migration'),self.tr('Status'),self.tr('Action')])
        self.migration_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.migration_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.migration_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.migration_table.verticalHeader().setVisible(False)
        self.migration_table.verticalHeader().setDefaultSectionSize(38)
        header=self.migration_table.horizontalHeader()
        header.setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2,QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3,QHeaderView.ResizeMode.Fixed)
        self.migration_table.setColumnWidth(3,96)
        g.addWidget(self.migration_table);v.addWidget(f,1)
        return w

    def migrate_status(self):
        p=self.require_project()
        if not p:return
        if p in self._migration_status_inflight:return
        self._migration_status_inflight.add(p)
        button_initiated = getattr(self.context, 'action_button', None) is self.migration_refresh_button
        if not button_initiated:
            self.set_migration_refreshing(True)
        self.migration_table.setRowCount(0)
        self.enqueue_job(Job('Migration status','php',['artisan','migrate:status','--no-ansi'],p,
                                success=lambda data,project=p:self.finish_migration_status(project,data),
                                failure=lambda _error:self.finish_migration_status(p),
                                cancelled=lambda:self.finish_migration_status(p)))

    def set_migration_refreshing(self,refreshing):
        button=self.migration_refresh_button
        button.setEnabled(not refreshing)
        button.setText(self.tr('Refreshing status…') if refreshing else self.tr('Refresh status'))
        button.setProperty('kind','secondary' if refreshing else 'primary')
        button.style().unpolish(button); button.style().polish(button)

    def finish_migration_status(self,project,output=None):
        self._migration_status_inflight.discard(project)
        if project != self.current:
            return
        self.set_migration_refreshing(False)
        if output is not None:
            self._migration_output_project = project
            self._migration_output = output
            self.show_migrations(project,output)

    def show_migrations(self,project,output):
        if project!=self.current:return
        migrations_dir=Path(project)/'database'/'migrations'
        files=sorted((path for path in migrations_dir.rglob('*.php') if path.is_file()),key=lambda path:path.relative_to(migrations_dir).as_posix()) if migrations_dir.is_dir() else []
        statuses={}
        for line in output.splitlines():
            line=re.sub(r'\x1b\[[0-9;]*m','',line)
            match=re.search(r'\b(?P<status>Ran|Pending|Skipped)\b',line,re.I)
            if match:
                name_part=line[:match.start()]
                name_parts=re.sub(r'\[\s*\d+\s*\]\s*$','',name_part).strip().split()
                if not name_parts:
                    continue
                name=name_parts[0].strip('|').rstrip('.').removesuffix('.php')
                if not name:
                    continue
                statuses[name]=match.group('status').capitalize()
        self.migration_table.setRowCount(len(files))
        for priority,path in enumerate(files,1):
            self.migration_table.setRowHeight(priority-1,38)
            relative=path.relative_to(Path(project)).as_posix()
            name=path.name
            status=statuses.get(path.stem,'Unknown')
            values=(str(priority),relative,status)
            for column,value in enumerate(values):
                item=QTableWidgetItem(self.tr(value) if column==2 else value)
                item.setData(Qt.ItemDataRole.UserRole,relative)
                self.migration_table.setItem(priority-1,column,item)
            run=self.btn('Run',lambda checked=False,rel=relative:self.run_migration(rel),'primary')
            run.setStyleSheet('padding: 2px 6px; text-align: center;')
            run.setFixedSize(68,24)
            run.setEnabled(status in ('Pending','Unknown'))
            action_cell=QWidget()
            action_layout=QHBoxLayout(action_cell)
            action_layout.setContentsMargins(4,0,4,0)
            action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            action_layout.addWidget(run)
            self.migration_table.setCellWidget(priority-1,3,action_cell)

    def run_migration(self,relative_path):
        p=self.require_project()
        if not p:return
        migrations_dir=Path(p)/'database'/'migrations'
        target=(Path(p)/relative_path).resolve()
        try:
            safe_relative=target.relative_to(migrations_dir.resolve()).as_posix()
        except ValueError:
            return
        if target.suffix.lower()!='.php' or not target.is_file():
            self.migrate_status()
            return
        prompt=self.tr('Run migration {name}? This will change the database configured in this project.').format(name=target.name)
        if self.confirm(self.tr('Apply migration'),prompt,warning=True)!=QMessageBox.StandardButton.Yes:return
        self.enqueue_job(Job(target.name,'php',['artisan','migrate',f'--path=database/migrations/{safe_relative}','--no-interaction','--no-ansi'],p,
                                success=lambda _:self.migrate_status()))

    def migration_op(self,what):
        if what in ('migrate:rollback','migrate:fresh'):
            prompt=self.tr('This action can irreversibly remove database data. Verify the .env database connection and make a backup.\n\nType {folder} to continue:').format(folder=Path(self.current).name)
            value,ok=QInputDialog.getText(self,self.tr('Destructive migration operation'),prompt)
            if not ok or value!=Path(self.current).name:
                return
        elif what=='migrate':
            if self.confirm('Apply migrations','Run pending migrations against the database configured in this project?')!=QMessageBox.StandardButton.Yes:return
        self.enqueue_job(Job(what, 'php', ['artisan', what, '--no-interaction'], self.current, success=lambda _: self.migrate_status()))
