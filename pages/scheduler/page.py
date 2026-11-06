"""Scheduler page implementation."""
from __future__ import annotations

import json
import re
from PySide6.QtCore import Qt, QProcess
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QMessageBox, QTableWidget, QTableWidgetItem, QWidget
from common.laravel.route_parser import parse_schedule_list
from common.processes.task_runner import Job
from common.projects.registry import laravel_version, project_valid
from pages.base import BasePage
from common.ui.widgets import hbox


class SchedulerPage(BasePage):
    def __init__(self, context, parent=None):
        super().__init__(context, parent)
        self._rebuild_schedules = None
        self.mount(self.build_scheduler)
        context.service_state_changed.connect(self.schedule_service_state)

    def on_activated(self):
        self.update_schedule_worker()
        if self.current and project_valid(self.current):
            self.refresh_schedules()

    def on_project_changed(self, _path):
        if hasattr(self, "schedule_table"):
            self._rebuild_schedules = None
            self.schedule_table.setRowCount(0)
            self.update_schedule_test_button()
            self.update_schedule_worker()

    def before_rebuild(self):
        if not hasattr(self, "schedule_table"):
            self._rebuild_schedules = None
            return
        rows = []
        for row in range(self.schedule_table.rowCount()):
            checkbox = self.schedule_table.item(row, 0)
            command = self.schedule_table.item(row, 1)
            rows.append((
                {
                    "test_name": command.data(Qt.ItemDataRole.UserRole) if command else None,
                    "command": command.text() if command else "",
                    "expression": self.schedule_table.item(row, 2).text() if self.schedule_table.item(row, 2) else "",
                    "next_due_date_human": self.schedule_table.item(row, 3).text() if self.schedule_table.item(row, 3) else "",
                    "description": self.schedule_table.item(row, 4).text() if self.schedule_table.item(row, 4) else "",
                },
                bool(checkbox and checkbox.checkState() == Qt.CheckState.Checked),
            ))
        self._rebuild_schedules = rows

    def after_rebuild(self):
        if self._rebuild_schedules is not None:
            rows = self._rebuild_schedules
            self.schedule_table.setRowCount(0)
            for schedule, checked in rows:
                self.add_schedule_row(schedule)
                if checked:
                    self.schedule_table.item(self.schedule_table.rowCount() - 1, 0).setCheckState(Qt.CheckState.Checked)
            self._rebuild_schedules = None
        self.update_schedule_worker()

    def build_scheduler(self):
        w,v=self.page('Scheduler','Run Laravel’s local scheduler worker, inspect scheduled tasks, and test an individual task.')
        worker,g=self.card('SCHEDULE WORKER','Runs php artisan schedule:work for the selected local project until you stop it.')
        self.schedule_worker_button=self.btn('Start scheduler worker',self.toggle_schedule_worker,'primary','play')
        self.schedule_worker_status=self.label('Worker stopped')
        g.addWidget(self.schedule_worker_button);g.addWidget(self.schedule_worker_status)
        v.addWidget(worker)

        schedules,g=self.card('SCHEDULED TASKS','Tick the tasks to test. Selected tasks run one at a time and may change project data.')
        g.addWidget(self.btn('Refresh schedules',self.refresh_schedules,'primary','play'))
        self.schedule_table=QTableWidget(0,5)
        self.schedule_table.setHorizontalHeaderLabels([self.tr(x) for x in ['Test','Command','Frequency','Next run','Description']])
        self.schedule_table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents)
        self.schedule_table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch)
        self.schedule_table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.ResizeToContents)
        self.schedule_table.horizontalHeader().setSectionResizeMode(3,QHeaderView.ResizeMode.ResizeToContents)
        self.schedule_table.horizontalHeader().setSectionResizeMode(4,QHeaderView.ResizeMode.Stretch)
        self.schedule_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.schedule_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.schedule_table.setMinimumHeight(230);g.addWidget(self.schedule_table)
        self.schedule_test_button=self.btn(self.tr('Test checked tasks ({count})').format(count=0),self.test_selected_schedules,'primary','play')
        self.schedule_table.itemChanged.connect(self.update_schedule_test_button)
        self.schedule_select_all_button=self.btn('Select all testable',self.select_all_schedules)
        self.schedule_clear_selection_button=self.btn('Clear selection',self.clear_schedule_selection)
        self.schedule_run_due_button=self.btn('Run due tasks now',self.run_due_schedules,'danger')
        actions=QWidget();actions.setObjectName('panelRow');actions.setLayout(hbox(self.schedule_select_all_button,self.schedule_clear_selection_button,self.schedule_test_button,self.schedule_run_due_button))
        g.addWidget(actions)
        v.addWidget(schedules,1)
        return w

    def schedule_worker_key(self):
        return 'scheduler|'+self.current

    def schedule_worker_running(self):
        process=self.runner.services.get(self.schedule_worker_key()) if self.current else None
        return bool(process and process.state()!=QProcess.ProcessState.NotRunning)

    def toggle_schedule_worker(self):
        p=self.require_project()
        if not p:return
        key=self.schedule_worker_key()
        if self.schedule_worker_running():
            self.runner.service_stop(key)
            return
        try:
            self.runner.service_start(key,'php',['artisan','schedule:work'],p)
        except (ValueError,FileNotFoundError) as exc:
            self.alert('Scheduler worker failed',str(exc),True)

    def update_schedule_worker(self):
        if not hasattr(self,'schedule_worker_button'):return
        running=self.schedule_worker_running()
        self.schedule_worker_button.setText(self.tr('Stop scheduler worker' if running else 'Start scheduler worker'))
        self.schedule_worker_button.setProperty('kind','danger' if running else 'primary')
        self.schedule_worker_button.setProperty('iconName','square' if running else 'play')
        self.schedule_worker_status.setText(self.tr('Worker running for the selected project' if running else 'Worker stopped'))
        self.schedule_worker_button.style().unpolish(self.schedule_worker_button)
        self.schedule_worker_button.style().polish(self.schedule_worker_button)
        self.refresh_icons()

    def schedule_service_state(self,key,running):
        if key.startswith('scheduler|'):self.update_schedule_worker()

    def refresh_schedules(self):
        p=self.require_project()
        if not p:return
        self.schedule_table.setRowCount(0)
        version = laravel_version(p)
        major_text = version.lstrip('v^~').split('.', 1)[0]
        supports_json = major_text.isdigit() and int(major_text) >= 11
        args = ['artisan', 'schedule:list']
        result_handler = self.show_schedules_text
        if supports_json:
            args.append('--json')
            result_handler = self.show_schedules_json
        self.enqueue_job(Job('List scheduled tasks','php',args,p,
                                success=lambda output,project=p:result_handler(output,project)))

    def show_schedules_json(self,output,project=None):
        if project is not None and project != self.current:
            return
        try:
            start=output.find('['); end=output.rfind(']')+1
            schedules=json.loads(output[start:end]) if start>=0 and end>start else []
            if not isinstance(schedules,list):raise ValueError('Unexpected schedule output')
        except (json.JSONDecodeError,ValueError):
            return
        self.schedule_table.setRowCount(0)
        test_names=[]
        for schedule in schedules:
            command=str(schedule.get('command') or '').strip()
            test_name=None if re.match(r'^Closure at:',command,re.IGNORECASE) else re.sub(r'^(?:.*?php(?:\.exe)?\s+)?artisan\s+', '', command, flags=re.IGNORECASE)
            if not test_name and not re.match(r'^Closure at:',command,re.IGNORECASE):test_name=command
            test_names.append(test_name)
        counts={name:test_names.count(name) for name in test_names if name}
        for schedule,test_name in zip(schedules,test_names):
            if test_name and counts[test_name]>1:test_name=None
            self.add_schedule_row({
                'command':str(schedule.get('command') or '').strip(),
                'expression':str(schedule.get('expression') or ''),
                'next_due_date_human':str(schedule.get('next_due_date_human') or schedule.get('next_due_date') or ''),
                'description':str(schedule.get('description') or ''),
                'test_name':test_name,
            })

    def show_schedules_text(self,output,project=None):
        if project is not None and project != self.current:
            return
        schedules=parse_schedule_list(output)
        self.schedule_table.setRowCount(0)
        for schedule in schedules:
            self.add_schedule_row(schedule)

    def add_schedule_row(self,schedule):
        row=self.schedule_table.rowCount();self.schedule_table.insertRow(row)
        test_name=schedule.get('test_name')
        check=QTableWidgetItem()
        check.setFlags(Qt.ItemFlag.ItemIsUserCheckable|Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsSelectable)
        check.setCheckState(Qt.CheckState.Unchecked)
        if not test_name:
            check.setFlags(check.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            check.setToolTip(self.tr('Laravel schedule:test cannot target an unnamed closure or duplicate command by name.'))
        self.schedule_table.setItem(row,0,check)
        values=(str(schedule.get('command') or ''),str(schedule.get('expression') or ''),str(schedule.get('next_due_date_human') or schedule.get('next_due_date') or ''),str(schedule.get('description') or ''))
        for col,value in enumerate(values,1):
            item=QTableWidgetItem(value)
            if col==1:item.setData(Qt.ItemDataRole.UserRole,test_name)
            self.schedule_table.setItem(row,col,item)
        self.update_schedule_test_button()

    def checked_schedule_names(self):
        names=[]
        for row in range(self.schedule_table.rowCount()):
            checkbox=self.schedule_table.item(row,0)
            command=self.schedule_table.item(row,1)
            name=command.data(Qt.ItemDataRole.UserRole) if command else None
            if checkbox and checkbox.checkState()==Qt.CheckState.Checked and name:
                names.append(str(name))
        return names

    def update_schedule_test_button(self,*_):
        if not hasattr(self,'schedule_test_button'):return
        count=len(self.checked_schedule_names())
        self.schedule_test_button.setText(self.tr('Test checked tasks ({count})').format(count=count))
        self.schedule_test_button.setEnabled(count>0)

    def select_all_schedules(self):
        for row in range(self.schedule_table.rowCount()):
            checkbox=self.schedule_table.item(row,0)
            command=self.schedule_table.item(row,1)
            if checkbox and command and command.data(Qt.ItemDataRole.UserRole):
                checkbox.setCheckState(Qt.CheckState.Checked)

    def clear_schedule_selection(self):
        for row in range(self.schedule_table.rowCount()):
            checkbox=self.schedule_table.item(row,0)
            if checkbox and checkbox.flags() & Qt.ItemFlag.ItemIsEnabled:
                checkbox.setCheckState(Qt.CheckState.Unchecked)

    def test_selected_schedules(self):
        p=self.require_project()
        if not p:return
        names=self.checked_schedule_names()
        if not names:return self.alert('No testable tasks selected','Tick one or more enabled task rows first. Unnamed closures and duplicate commands cannot be selected individually by Laravel.',True)
        preview='\n'.join('• '+name for name in names[:5])
        if len(names)>5:preview+=f'\n… and {len(names)-5} more'
        message=self.tr('This runs {count} selected task(s) immediately, one at a time. Tasks may change project data.\n\n{tasks}\n\nContinue?').format(count=len(names),tasks=preview)
        if self.confirm('Run selected scheduled tasks',message,warning=True)!=QMessageBox.StandardButton.Yes:return
        for name in names:
            self.enqueue_job(Job('Test scheduled task: '+name,'php',['artisan','schedule:test','--name='+name],p))

    def run_due_schedules(self):
        p=self.require_project()
        if not p:return
        if self.confirm('Run due scheduled tasks now','This runs every task that is due at the current time and may change project data. Continue?',warning=True)!=QMessageBox.StandardButton.Yes:return
        self.enqueue_job(Job('Run due scheduled tasks','php',['artisan','schedule:run'],p))
    def schedule_project_changed(self, _index):
        self.on_project_changed(self.current)
