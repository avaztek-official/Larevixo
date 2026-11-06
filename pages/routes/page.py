"""Routes page implementation."""
from __future__ import annotations

from PySide6.QtWidgets import QLineEdit, QTreeWidget, QTreeWidgetItem, QWidget
from common.laravel.route_parser import group_route_segments, parse_routes
from common.processes.task_runner import Job
from pages.base import BasePage
from common.ui.widgets import hbox


class RoutesPage(BasePage):
    def __init__(self, context, parent=None):
        super().__init__(context, parent)
        self.routes = []
        self._rebuild_filter_text = None
        self.mount(self.build_routes)
        context.quick_action_requested.connect(self.handle_quick_action)

    def handle_quick_action(self, action):
        if action == "fetch_routes":
            self.fetch_routes()

    def on_project_changed(self, _path):
        self.routes = []
        if hasattr(self, "routes_tree"):
            self.routes_tree.clear()

    def after_rebuild(self):
        if self._rebuild_filter_text is not None:
            self.route_filter.setText(self._rebuild_filter_text)
            self._rebuild_filter_text = None
        self.render_routes()

    def before_rebuild(self):
        self._rebuild_filter_text = self.route_filter.text() if hasattr(self, "route_filter") else None

    def build_routes(self):
        w,v=self.page('Route explorer','Routes grouped automatically by URI segments, with names, methods, actions and middleware.')
        tools=QWidget()
        self.route_filter=QLineEdit();self.route_filter.setPlaceholderText(self.tr('Filter routes by URI, name or action…'))
        self.route_filter.textChanged.connect(self.render_routes)
        tools.setLayout(hbox(self.route_filter,self.btn('Refresh from Laravel',self.fetch_routes,'primary')))
        v.addWidget(tools)
        self.routes_tree=QTreeWidget();self.routes_tree.setHeaderLabels(['Folder / URI','Method','Name','Action','Middleware'])
        self.routes_tree.setColumnWidth(0,300);self.routes_tree.setColumnWidth(1,110);self.routes_tree.setColumnWidth(2,180)
        v.addWidget(self.routes_tree,1)
        return w

    def fetch_routes(self):
        p=self.require_project()
        if p:self.enqueue_job(Job('Load Laravel routes','php',['artisan','route:list','--json'],p,success=lambda data,project=p:self.got_routes(data,project)))

    def got_routes(self,data,project=None):
        if project is not None and project != self.current:
            return
        # Some packages may emit bootstrap noise, but valid Laravel route:list should emit pure JSON.
        try:self.routes=parse_routes(data)
        except (ValueError,TypeError) as exc:
            return self.alert('Could not parse route:list',str(exc)+ '\nCheck Activity Console.',True)
        self.render_routes()
        self.append_console(f'Loaded {len(self.routes)} routes\n')

    def render_routes(self):
        self.routes_tree.clear(); nodes={}
        term=self.route_filter.text().casefold().strip()
        for r in self.routes:
            if term and not any(term in str(value).casefold() for value in r.values()):continue
            parent=self.routes_tree.invisibleRootItem()
            path=[]
            for seg in group_route_segments(r['uri']):
                path.append(seg);t=tuple(path)
                if t not in nodes:
                    node=QTreeWidgetItem([seg+'/'])
                    parent.addChild(node);nodes[t]=node
                parent=nodes[t]
            node=QTreeWidgetItem([r['uri'],r['method'],r['name'],r['action'],r['middleware']]);parent.addChild(node)
        self.routes_tree.expandToDepth(1)
