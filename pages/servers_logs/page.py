"""Servers and logs page implementation."""
from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt, QProcess, QUrl
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QPlainTextEdit, QSpinBox, QWidget
from common.processes.task_runner import Job
from common.ui.service_button import service_toggle_button
from common.ui.widgets import LogHighlighter
from pages.base import BasePage
from common.ui.widgets import hbox


class ServersLogsPage(BasePage):
    def __init__(self, context, parent=None):
        super().__init__(context, parent)
        self.service_buttons = {"laravel": [], "vite": []}
        self.log_file_offset = 0
        self._rebuild_state = None
        self.mount(self.build_servers)
        context.quick_action_requested.connect(self.handle_quick_action)
        context.service_state_changed.connect(self.service_state)

    def handle_quick_action(self, action):
        if action == "open_browser":
            self.open_browser()
        elif action.startswith("toggle_service:"):
            self.toggle_service(action.split(":", 1)[1])

    def on_project_changed(self, _path):
        self.log_file_offset = 0
        if hasattr(self, "log_view"):
            self.log_view.clear()
            self.update_service_buttons()

    def before_rebuild(self):
        if hasattr(self, "log_view"):
            self._rebuild_state = {
                "php_port": self.php_port.value(),
                "vite_port": self.vite_port.value(),
                "log_text": self.log_view.toPlainText(),
            }
        self.service_buttons = {"laravel": [], "vite": []}

    def after_rebuild(self):
        if self._rebuild_state is not None:
            self.php_port.setValue(self._rebuild_state["php_port"])
            self.vite_port.setValue(self._rebuild_state["vite_port"])
            self.log_view.setPlainText(self._rebuild_state["log_text"])
            self._rebuild_state = None
        # The status label is recreated with default text; recover it from the
        # runner because services keep running while the page is translated.
        self.service_state("", False)

    def build_servers(self):
        w,v=self.page('Servers & Logs','Run local Laravel and Vite services; follow application log files live.')
        f,g=self.card('LOCAL DEVELOPMENT SERVERS')
        row=QWidget();row.setObjectName('panelRow')
        self.php_port=QSpinBox();self.php_port.setRange(1024,65535);self.php_port.setValue(8000)
        self.vite_port=QSpinBox();self.vite_port.setRange(1024,65535);self.vite_port.setValue(5173)
        row.setLayout(hbox(self.label('Laravel port'),self.php_port,self.service_button('laravel'),self.label('Vite port'),self.vite_port,self.service_button('vite')))
        g.addWidget(row)
        self.service_status=self.label('Laravel: stopped    •    Vite: stopped')
        g.addWidget(self.service_status);v.addWidget(f)
        f,g=self.card('LARAVEL APPLICATION LOG', 'Follows storage/logs/laravel.log; some apps use dated or custom log channels.')
        self.log_view=QPlainTextEdit();self.log_view.setReadOnly(True)
        self.log_highlighter = LogHighlighter(self.log_view.document())
        self.log_view.setMaximumBlockCount(2000)
        self.log_view.setFont(QFont('Consolas',10))
        g.addWidget(self.log_view)
        r=QWidget();r.setObjectName('panelRow');r.setLayout(hbox(self.btn('Refresh log',lambda:self.tail_log(reset=True)),self.btn('Open log folder',self.open_logs),self.btn('Clear view',self.log_view.clear)))
        g.addWidget(r);v.addWidget(f,1)
        return w

    def service_key(self,which):
        return which+'|'+self.current

    def service_is_running(self,which):
        process=self.runner.services.get(self.service_key(which)) if self.current else None
        return bool(process and process.state()!=QProcess.ProcessState.NotRunning)

    def update_service_buttons(self):
        for which,buttons in self.service_buttons.items():
            running=self.service_is_running(which)
            for button in buttons:
                button.setText(self.tr(('Stop ' if running else 'Start ')+which.capitalize()))
                button.setProperty('kind','danger' if running else 'primary')
                button.setProperty('iconName','square' if running else 'play')
                button.style().unpolish(button); button.style().polish(button)
        self.refresh_icons()

    def toggle_service(self,which):
        if self.service_is_running(which): self.stop_service(which)
        else: self.start_service(which)

    def start_service(self,which):
        p=self.require_project()
        if not p:return
        try:
            if which=='laravel':
                self.runner.service_start(self.service_key(which),'php',['artisan','serve','--host=127.0.0.1','--port='+str(self.php_port.value())],p)
            else:
                if not (Path(p)/'package.json').is_file():return self.alert('Vite not configured','No package.json in this project.',True)
                self.runner.service_start(self.service_key(which),'npm',['run','dev','--','--host','127.0.0.1','--port',str(self.vite_port.value())],p)
        except (ValueError,FileNotFoundError) as exc: self.alert('Server failed',str(exc),True)

    def stop_service(self,which):
        if self.current:self.runner.service_stop(self.service_key(which))

    def service_state(self,key,running):
        self.update_service_buttons()
        running_keys=[k for k,p in self.runner.services.items() if p.state()!=QProcess.ProcessState.NotRunning]
        self.service_status.setText(self.tr('Running: {services}').format(services=', '.join(k.split('|')[0]+': '+Path(k.split('|',1)[1]).name for k in running_keys) or self.tr('none')))

    def tail_log(self,reset=False):
        if not self.current:return
        folder=Path(self.current)/'storage'/'logs'
        if not folder.is_dir(): return
        filepath=folder/'laravel.log'
        if not filepath.exists():
            logs=sorted(folder.glob('laravel-*.log'),key=lambda x:x.stat().st_mtime,reverse=True)
            if not logs:return
            filepath=logs[0]
        try:
            if reset:self.log_file_offset=0;self.log_view.clear()
            if getattr(self,'_last_log_path',None)!=filepath:
                self.log_file_offset=0;self._last_log_path=filepath;self.log_view.clear()
            size=filepath.stat().st_size
            if size < self.log_file_offset:self.log_file_offset=0;self.log_view.clear()
            with filepath.open('rb') as f:
                if self.log_file_offset==0 and size>100_000:self.log_file_offset=size-100_000
                f.seek(self.log_file_offset);chunk=f.read(75_000)
                self.log_file_offset=f.tell()
            if chunk:self.log_view.appendPlainText(chunk.decode('utf-8',errors='replace').rstrip())
        except OSError:pass

    def open_logs(self):
        p=self.require_project()
        if p:
            folder=Path(p)/'storage'/'logs';folder.mkdir(parents=True,exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def open_browser(self):
        webbrowser.open('http://127.0.0.1:'+str(self.php_port.value()))
    def service_button(self, which):
        button = service_toggle_button(which, self.context, self.context.translator, self)
        self.service_buttons[which].append(button)
        return button
