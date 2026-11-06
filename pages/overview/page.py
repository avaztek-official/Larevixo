"""Overview page implementation."""
from __future__ import annotations

from pathlib import Path
from PySide6.QtWidgets import QWidget
from common.projects.registry import laravel_version
from common.ui.service_button import service_toggle_button
from pages.base import BasePage
from common.ui.widgets import hbox


class OverviewPage(BasePage):
    def __init__(self, context, parent=None):
        super().__init__(context, parent)
        self.mount(self.build_overview)
        context.projects_changed.connect(self.update_overview)
        self.update_overview()

    def service_button(self, which):
        return service_toggle_button(which, self.context, self.context.translator, self)

    def on_project_changed(self, _path):
        if hasattr(self, "overview_name"):
            self.update_overview()

    def after_rebuild(self):
        self.update_overview()

    def build_overview(self):
        w,v=self.page('Your Laravel workspace','A single cockpit for local projects, dependencies and development servers.')
        f,g=self.card('CURRENT WORKSPACE')
        self.overview_name=self.label('No project selected','cardTitle')
        self.overview_path=self.label('Import a project to get started.')
        self.overview_ver=self.label('Laravel version: —')
        g.addWidget(self.overview_name);g.addWidget(self.overview_path);g.addWidget(self.overview_ver)
        v.addWidget(f)
        q,cl=self.card('QUICK ACTIONS')
        for row in [
            [self.service_button('laravel'),self.service_button('vite'),self.btn('Open in browser',lambda: self.context.quick_action_requested.emit('open_browser'))],
            [self.btn('Migrate status',lambda: self.context.quick_action_requested.emit('migration_status')),self.btn('Refresh routes',lambda: self.context.quick_action_requested.emit('fetch_routes')),self.btn('Composer install',lambda: self.context.quick_action_requested.emit('composer_install'))],
        ]:
            ww=QWidget();ww.setObjectName('panelRow');ww.setLayout(hbox(*row));cl.addWidget(ww)
        v.addWidget(q)
        tips, tl=self.card('SAFE BY DEFAULT','Only local Laravel folders are managed. Destructive database actions require a confirmation, and environment values stay masked.')
        tl.addWidget(self.label('Tip: project versions are read from composer.lock; no Composer command is needed to scan your projects.'))
        v.addWidget(tips)
        v.addStretch(1)
        return w

    def update_overview(self):
        p=self.current
        self.overview_name.setText(Path(p).name if p else self.tr('No project selected'))
        self.overview_path.setText(p or self.tr('Import a project to get started.'))
        self.overview_ver.setText(self.tr('Laravel version: {version}').format(version=laravel_version(p) if p else '—'))
