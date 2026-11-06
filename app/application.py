"""Qt application shell, navigation, global state, and lifecycle."""
from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt, QTimer, QEvent, QPoint, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, QAbstractAnimation
from PySide6.QtGui import QIcon, QPixmap, QFont
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QComboBox, QScrollArea, QStackedWidget, QFrame, QPlainTextEdit, QTabWidget, QSplitter, QSizePolicy, QGraphicsOpacityEffect, QProgressBar, QMessageBox
from app.context import ApplicationContext
from common.dialogs.messages import alert as show_alert, confirm as show_confirm
from common.dialogs.about import AboutDialog
from common.localization.translator import Translator
from common.projects.registry import Registry, laravel_version
from common.processes.task_runner import TaskRunner
from common.resources.paths import BASE, ICON, LANG_DIR, LOGO
from common.resources.theme import DARK, LIGHT
from common.ui.widgets import btn as make_button, card as make_card, configure_searchable_combo as configure_combo, hbox, label as make_label, lucide_icon as render_lucide_icon, LogHighlighter, strip_ansi
from common.validation.commands import redacted
from app.window_chrome import OperationToast
from pages.overview.page import OverviewPage
from pages.projects.page import ProjectsPage
from pages.artisan.page import ArtisanPage
from pages.migrations.page import MigrationsPage
from pages.environment.page import EnvironmentPage
from pages.routes.page import RoutesPage
from pages.composer.page import ComposerPage
from pages.scheduler.page import SchedulerPage
from pages.servers_logs.page import ServersLogsPage
from pages.global_settings.page import GlobalSettingsPage

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.store = Registry()
        self.runner = TaskRunner(self.store.data['tools'], self)
        self.translator = Translator(LANG_DIR, self.store.data.get('language', 'en'))
        self.context = ApplicationContext(self.store, self.runner, self.translator, self)
        self._console_records = {}
        self._closed_console_keys = set()
        self._console_expanded = False
        self._console_footer_size = 230
        self.context.combo_configurator = self.configure_searchable_combo
        self.context.console_message.connect(self.append_console)
        self.context.icon_refresh_requested.connect(self.refresh_icons)
        self.context.projects_changed.connect(self.refresh_project_selector)
        self.context.navigate_requested.connect(self.switch)
        self.runner.console_entry_created.connect(self.ensure_console_entry)
        self.runner.console_output.connect(self.append_operation_console)
        self.runner.job_started.connect(self.toast_job_started)
        self.runner.job_succeeded.connect(self.toast_job_succeeded)
        self.runner.job_failed.connect(self.toast_job_failed)
        self.runner.running_changed.connect(self.context.service_state_changed.emit)
        QApplication.instance().setLayoutDirection(Qt.LayoutDirection.RightToLeft if self.translator.language == 'fa' else Qt.LayoutDirection.LeftToRight)
        self.setWindowTitle(self.tr('Larevixo · Laravel Development Manager'))
        if ICON.is_file():
            self.setWindowIcon(QIcon(str(ICON)))
        self.resize(1410, 920)
        self.setMinimumSize(1020, 480)
        self.searchable_combos = []
        self.nav = {}
        self.pages = {}
        self._setup_ui()
        self.apply_theme()
        self.refresh_project_selector()
        self.switch('Overview')
        self.log_timer = QTimer(self)
        self.log_timer.timeout.connect(self.tail_log)
        self.log_timer.start(1500)

    @property
    def current(self):
        return self.context.current_project

    def tr(self, text):
        return self.translator(text)

    def btn(self, text, callback, kind='secondary', icon_name=None):
        return make_button(text, callback, self.translator, kind, icon_name)

    def label(self, text, role='muted'):
        return make_label(text, self.translator, role)

    def card(self, title, subtitle=None):
        return make_card(title, self.translator, subtitle)

    def alert(self, title, text, critical=False):
        return show_alert(self, title, text, self.translator, critical)

    def confirm(self, title, text, warning=False, default=None):
        if default is None:
            return show_confirm(self, title, text, self.translator, warning)
        return show_confirm(self, title, text, self.translator, warning, default)

    def lucide_icon(self, name, color):
        return render_lucide_icon(name, color, BASE)

    def configure_searchable_combo(self, combo):
        return configure_combo(combo, self, self.searchable_combos.append)

    def switch(self, name, refresh=True):
        current_widget = self.stack.currentWidget()
        if current_widget is not None and current_widget is not self.pages[name]:
            current_widget.deactivate()
        self.stack.setCurrentWidget(self.pages[name])
        self.project_toolbar.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Fixed if name in {'Artisan', 'Overview'} else QSizePolicy.Policy.Preferred,
        )
        if name == 'Global & Settings':
            # These pages have short content; keep the shared console directly below it.
            self.stack.setMaximumHeight(self.pages[name].sizeHint().height())
        else:
            self.stack.setMaximumHeight(16777215)
        self.pages[name].activate(refresh=refresh)
        for page_name, button in self.nav.items():
            button.setChecked(page_name == name)
        self.refresh_icons()

    def toggle_language(self):
        page_name = next((name for name, widget in self.pages.items() if widget is self.stack.currentWidget()), 'Overview')
        current_page = self.pages.get(page_name)
        if current_page is not None:
            current_page.deactivate()
        language = 'fa' if self.translator.language == 'en' else 'en'
        self.store.data['language'] = language
        self.store.save()
        self.translator.set_language(language)
        self.context.language_changed.emit(language)
        QApplication.instance().setLayoutDirection(Qt.LayoutDirection.RightToLeft if language == 'fa' else Qt.LayoutDirection.LeftToRight)
        self.setWindowTitle(self.tr('Larevixo · Laravel Development Manager'))
        for entry in list(self.operation_toasts):
            self._stop_toast_animation(entry)
            if entry.get('progress_animation'):
                entry['progress_animation'].stop()
            entry['widget'].deleteLater()
        self.operation_toasts.clear()
        self.searchable_combos = []
        self.nav = {}
        self._setup_ui()
        self.apply_theme()
        self.refresh_project_selector()
        self.switch(page_name, refresh=False)

    def request_project_import(self):
        self.context.quick_action_requested.emit('import_project')

    def request_project_create(self):
        self.context.quick_action_requested.emit('create_project')

    def show_about(self):
        AboutDialog(self, self.translator).exec()

    def refresh_project_selector(self):
        if not hasattr(self, 'project_combo'):
            return
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        for project in self.store.projects:
            self.project_combo.addItem(f'{Path(project).name}  ·  Laravel {laravel_version(project)}', project)
        index = self.project_combo.findData(self.current)
        if index >= 0:
            self.project_combo.setCurrentIndex(index)
        self.project_combo.blockSignals(False)

    def combo_changed(self, index):
        if index < 0:
            return
        project = self.project_combo.itemData(index)
        self.context.select_project(project)

    def toggle_theme(self):
        theme = 'light' if self.store.data.get('theme') == 'dark' else 'dark'
        self.store.data['theme'] = theme
        self.store.save()
        self.context.theme_changed.emit(theme)
        self.apply_theme()

    def tail_log(self):
        page = self.pages.get('Servers & Logs')
        if page is not None:
            page.tail_log()

    def closeEvent(self, event):
        if self.runner.active or self.runner.services:
            answer = self.confirm('Stop active tasks?', 'Closing Larevixo will stop tasks and servers launched by this app. Continue?')
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self.runner.stop_all()
        event.accept()


    def _setup_ui(self):
        old_splitter = getattr(self, 'content_splitter', None)
        if old_splitter is not None and self._console_expanded:
            sizes = old_splitter.sizes()
            if len(sizes) == 2 and sizes[1] > 0:
                self._console_footer_size = sizes[1]
        existing_pages = self.pages.copy()
        old_stack = getattr(self, 'stack', None)
        if old_stack is not None:
            for widget in existing_pages.values():
                old_stack.removeWidget(widget)
                widget.setParent(None)
        self.pages = {}
        root = QWidget()
        root.setObjectName('windowRoot')
        self.window_root_layout = QVBoxLayout(root)
        self.window_root_layout.setContentsMargins(0, 0, 0, 0)
        self.window_root_layout.setSpacing(0)
        self.window_frame = QFrame()
        self.window_frame.setObjectName('windowFrame')
        self.operation_toasts = []
        window_layout = QVBoxLayout(self.window_frame)
        window_layout.setContentsMargins(0, 0, 0, 0)
        window_layout.setSpacing(0)
        self.window_root_layout.addWidget(self.window_frame)
        content = QWidget()
        shell = QHBoxLayout(content); shell.setContentsMargins(0,0,0,0); shell.setSpacing(0)
        self.setCentralWidget(root)

        sidebar_scroll = QScrollArea()
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sidebar_scroll.setFixedWidth(230 + sidebar_scroll.verticalScrollBar().sizeHint().width())
        left = QFrame(); left.setObjectName('sidebar'); left.setFixedWidth(230)
        lv = QVBoxLayout(left); lv.setContentsMargins(17, 23, 17, 20); lv.setSpacing(8)
        brand = QWidget(); brand.setObjectName('sidebarBrand'); br = QHBoxLayout(brand); br.setContentsMargins(4,0,0,22)
        pic = QLabel(); pic.setProperty('role', 'sidebarLogo')
        if LOGO.is_file(): pic.setPixmap(QPixmap(str(LOGO)).scaled(53,53,Qt.AspectRatioMode.KeepAspectRatio,Qt.TransformationMode.SmoothTransformation))
        br.addWidget(pic)
        br.addWidget(self.label('Larevixo','brand')); br.addStretch()
        lv.addWidget(brand)
        for item, icon in [('Overview','layout-dashboard'),('Projects','folder'),('Artisan','terminal'),('Migrations','database'),('Environment','sliders-horizontal'),('Routes','route'),('Composer','package'),('Scheduler','clock'),('Servers & Logs','server'),('Global & Settings','settings')]:
            b = self.btn(item, lambda checked=False, i=item: self.switch(i), 'nav', icon)
            b.setCheckable(True); self.nav[item]=b; lv.addWidget(b)
        lv.addWidget(self.btn('About', self.show_about, 'nav', 'info'))
        lv.addStretch()
        sidebar_scroll.setWidget(left)
        shell.addWidget(sidebar_scroll)

        main_scroll = QScrollArea()
        main_scroll.setWidgetResizable(True)
        main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        main_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        main = QWidget(); mv = QVBoxLayout(main); mv.setContentsMargins(29,23,29,19); mv.setSpacing(16)
        toolbar = QWidget(); top = QHBoxLayout(toolbar); top.setContentsMargins(0,0,0,0)
        top.addWidget(self.label('CURRENT PROJECT'))
        self.project_combo = self.configure_searchable_combo(QComboBox()); self.project_combo.setMinimumWidth(260)
        self.project_combo.currentIndexChanged.connect(self.combo_changed)
        top.addWidget(self.project_combo, 1)
        top.addWidget(self.btn('Import', self.request_project_import, icon_name='folder-input'))
        top.addWidget(self.btn('New project', self.request_project_create, 'primary', 'folder-plus'))
        self.theme_button = self.btn('Theme', self.toggle_theme); top.addWidget(self.theme_button)
        self.language_button = self.btn('فارسی' if self.translator.language == 'en' else 'English', self.toggle_language); top.addWidget(self.language_button)
        self.project_toolbar = toolbar
        mv.addWidget(toolbar)
        self.stack = QStackedWidget(); mv.addWidget(self.stack)
        page_classes = [
            ('Overview', OverviewPage), ('Projects', ProjectsPage), ('Artisan', ArtisanPage),
            ('Migrations', MigrationsPage), ('Environment', EnvironmentPage), ('Routes', RoutesPage),
            ('Composer', ComposerPage), ('Scheduler', SchedulerPage),
            ('Servers & Logs', ServersLogsPage), ('Global & Settings', GlobalSettingsPage),
        ]
        for name, page_class in page_classes:
            widget = existing_pages.get(name)
            if widget is None:
                widget = page_class(self.context)
            else:
                widget.rebuild()
                widget.after_rebuild()
            self.pages[name] = widget
            self.stack.addWidget(widget)
        main_scroll.setWidget(main)
        shell.addWidget(main_scroll,1)
        self.content_splitter = QSplitter(Qt.Orientation.Vertical)
        self.content_splitter.setObjectName('contentConsoleSplitter')
        self.content_splitter.setHandleWidth(7 if self._console_expanded else 1)
        self.content_splitter.setChildrenCollapsible(False)
        self.content_splitter.setStretchFactor(0, 1)
        self.content_splitter.setStretchFactor(1, 0)
        self.content_splitter.addWidget(content)
        self.console_footer = self._build_console_footer()
        self.content_splitter.addWidget(self.console_footer)
        self.content_splitter.splitterMoved.connect(self._console_splitter_moved)
        splitter_handle = self.content_splitter.handle(1)
        splitter_handle.setEnabled(self._console_expanded)
        splitter_handle.setCursor(Qt.CursorShape.SplitVCursor)
        splitter_handle.setToolTip(self.tr('Drag to resize console'))
        window_layout.addWidget(self.content_splitter, 1)
        QTimer.singleShot(0, self._apply_console_splitter_size)

    def append_console(self, text):
        if text:
            self.ensure_console_entry('activity', 'Activity')
            self.append_operation_console('activity', text)

    def ensure_console_entry(self, key, label):
        if key in self._console_records:
            return self._console_records[key]
        self._closed_console_keys.discard(key)
        duplicate_count = sum(1 for item in self._console_records.values() if item['label'] == label)
        if duplicate_count:
            label = f'{label} #{duplicate_count + 1}'
        self._console_records[key] = {'label': label, 'text': ''}
        if hasattr(self, 'console_tabs'):
            self._add_console_tab(key)
            self._update_console_toggle()
        return self._console_records[key]

    def append_operation_console(self, key, text):
        if not text or key in self._closed_console_keys:
            return
        record = self._console_records.get(key)
        if record is None:
            record = self.ensure_console_entry(key, 'Activity' if key == 'activity' else key)
        clean = redacted(strip_ansi(text)).rstrip('\n')
        if not clean:
            return
        record['text'] = '\n'.join((record['text'] + clean + '\n').splitlines()[-1500:])
        edit = self._console_tab_widgets.get(key) if hasattr(self, '_console_tab_widgets') else None
        if edit is not None:
            edit.appendPlainText(clean)

    def _build_console_footer(self):
        footer = QFrame()
        footer.setObjectName('consoleFooter')
        footer.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(footer)
        layout.setContentsMargins(16, 5, 16, 8)
        layout.setSpacing(5)
        header = QWidget()
        header.setObjectName('panelRow')
        row = QHBoxLayout(header)
        row.setContentsMargins(0, 0, 0, 0)
        title_group = QWidget()
        title_group.setStyleSheet('background: transparent;')
        title_group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        title_layout = QVBoxLayout(title_group)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(1)
        self.console_toggle = QPushButton()
        self.console_toggle.setProperty('kind', 'consoleToggle')
        self.console_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self.console_toggle.clicked.connect(self.toggle_console_footer)
        title_layout.addWidget(self.console_toggle, 0, Qt.AlignmentFlag.AlignLeft)
        self.console_status = self.label('Separate console for each operation', 'muted')
        self.console_status.setObjectName('consoleStatus')
        self.console_status.setWordWrap(True)
        self.console_status.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.console_status.setStyleSheet('background: transparent;')
        title_layout.addWidget(self.console_status)
        row.addWidget(title_group, 1)
        layout.addWidget(header)
        self.console_tabs = QTabWidget()
        self.console_tabs.setObjectName('operationConsoleTabs')
        self.console_tabs.setTabsClosable(True)
        self._console_tab_widgets = {}
        self.console_tabs.currentChanged.connect(self._current_console_changed)
        self.console_tabs.tabCloseRequested.connect(self.close_console_tab)
        layout.addWidget(self.console_tabs, 1)
        self.console_tabs.setVisible(self._console_expanded)
        for key in self._console_records:
            self._add_console_tab(key)
        self._update_console_toggle()
        return footer

    def _add_console_tab(self, key):
        if key in self._console_tab_widgets:
            return
        record = self._console_records[key]
        edit = QPlainTextEdit()
        edit.setObjectName('operationConsole')
        edit.setReadOnly(True)
        edit.setMaximumBlockCount(1500)
        edit.setMinimumHeight(125)
        edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        edit.setFont(QFont('Consolas', 10))
        LogHighlighter(edit.document())
        if record['text']:
            edit.setPlainText(record['text'])
        self._console_tab_widgets[key] = edit
        self.console_tabs.addTab(edit, self.tr(record['label']))
        self.console_tabs.setCurrentWidget(edit)
        if self.console_tabs.count() == 1:
            self._current_console_changed(0)

    def _current_console_changed(self, index):
        if not hasattr(self, 'console_tabs') or index < 0:
            return
        self.console = self.console_tabs.widget(index)

    def close_console_tab(self, index):
        widget = self.console_tabs.widget(index)
        if widget is None:
            return
        key = next((key for key, edit in self._console_tab_widgets.items() if edit is widget), None)
        if key is None:
            return
        state = self.runner.console_entry_state(key)
        if state in {'running', 'queued'}:
            operation = self._console_records[key]['label']
            title = 'Terminate running operation?' if state == 'running' else 'Cancel queued operation?'
            message = (
                'Operation "{operation}" is still running. Terminate it and close this console?'
                if state == 'running' else
                'Operation "{operation}" is queued. Cancel it and close this console?'
            ).format(operation=operation)
            if self.confirm(title, message, warning=True) != QMessageBox.StandardButton.Yes:
                return
            self.runner.stop_console_entry(key)
        self._closed_console_keys.add(key)
        self._console_records.pop(key, None)
        self._console_tab_widgets.pop(key, None)
        self.console_tabs.removeTab(index)
        widget.deleteLater()
        self._update_console_toggle()

    def toggle_console_footer(self):
        if self._console_expanded:
            sizes = self.content_splitter.sizes()
            if len(sizes) == 2 and sizes[1] > 100:
                self._console_footer_size = sizes[1]
        self._console_expanded = not self._console_expanded
        self.content_splitter.setHandleWidth(7 if self._console_expanded else 1)
        self.content_splitter.handle(1).setEnabled(self._console_expanded)
        self.console_tabs.setVisible(self._console_expanded)
        self._update_console_toggle()
        QTimer.singleShot(0, self._apply_console_splitter_size)

    def _apply_console_splitter_size(self):
        splitter = getattr(self, 'content_splitter', None)
        if splitter is None or splitter.height() <= splitter.handleWidth():
            return
        splitter.setHandleWidth(7 if self._console_expanded else 1)
        splitter.handle(1).setEnabled(self._console_expanded)
        total = splitter.height()
        footer_minimum = max(1, self.console_footer.sizeHint().height())
        footer_size = self._console_footer_size if self._console_expanded else footer_minimum
        footer_size = min(max(footer_size, footer_minimum), max(footer_minimum, total - 120))
        splitter.setSizes([total - footer_size, footer_size])

    def _console_splitter_moved(self, _position, _index):
        if not self._console_expanded:
            return
        sizes = self.content_splitter.sizes()
        if len(sizes) == 2 and sizes[1] > 100:
            self._console_footer_size = sizes[1]

    def _update_console_toggle(self):
        if hasattr(self, 'console_toggle'):
            terminal_count = sum(1 for key in self._console_records if key != 'activity')
            self.console_toggle.setEnabled(terminal_count > 0)
            if terminal_count == 0:
                was_expanded = self._console_expanded
                self._console_expanded = False
                if hasattr(self, 'content_splitter') and self.content_splitter.count() > 1:
                    self.content_splitter.setHandleWidth(1)
                    self.content_splitter.handle(1).setEnabled(False)
                if hasattr(self, 'console_tabs'):
                    self.console_tabs.setVisible(False)
                if was_expanded:
                    QTimer.singleShot(0, self._apply_console_splitter_size)
            arrow = '▾' if self._console_expanded else '▴'
            self.console_toggle.setText(f'{arrow}  {self.tr("Activity Console")} ({terminal_count})')

    def toast_job_started(self, operation):
        self.show_operation_toast('Operation started', self.tr(operation), 'info')

    def toast_job_succeeded(self, operation):
        self.show_operation_toast('Operation completed successfully', self.tr(operation), 'success')

    def toast_job_failed(self, operation, error):
        summary = next((line.strip() for line in reversed(error.splitlines()) if line.strip()), '')
        summary = redacted(summary)
        if len(summary) > 180:
            summary = summary[:177].rstrip() + '…'
        detail = self.tr(operation)
        if summary:
            detail = self.tr('{operation}: {message}').format(operation=detail, message=summary)
        self.show_operation_toast('Operation failed', detail, 'error')

    def show_operation_toast(self, title, message, level, duration=None):
        dark = self.store.data.get('theme') == 'dark'
        palettes = {
            'info': ('#24384b', '#b9dcff', '#73bfff') if dark else ('#edf6ff', '#174d78', '#2784c7'),
            'success': ('#203d30', '#c2f0d2', '#68d391') if dark else ('#edf9f0', '#205c35', '#29934d'),
            'error': ('#482a2a', '#ffd0cc', '#ff796c') if dark else ('#fff0ee', '#8d281b', '#d34331'),
        }
        background, foreground, accent = palettes[level]
        toast = OperationToast(self, self.window_frame)
        toast.setObjectName('operationToast')
        toast.setFixedWidth(min(390, max(240, self.window_frame.width() - 36)))
        toast.setStyleSheet(
            'QFrame#operationToast {'
            f'background:{background}; color:{foreground}; border:1px solid {accent}; '
            f'border-left:4px solid {accent}; border-radius:10px;'
            '}'
            'QProgressBar {background:transparent; border:0; border-radius:2px;}'
            f'QProgressBar::chunk {{background:{accent}; border-radius:2px;}}'
        )
        opacity_effect = QGraphicsOpacityEffect(toast)
        opacity_effect.setOpacity(0.0)
        toast.setGraphicsEffect(opacity_effect)

        layout = QVBoxLayout(toast)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(0)
        content = QWidget(toast)
        content.setStyleSheet('background:transparent;')
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 12, 16, 9)
        content_layout.setSpacing(4)
        title_label = QLabel(self.tr(title))
        title_label.setStyleSheet('font-weight:700; background:transparent;')
        title_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet('background:transparent;')
        message_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        message_row = QWidget(content)
        message_layout = QHBoxLayout(message_row)
        message_layout.setContentsMargins(0, 0, 0, 0)
        message_layout.setSpacing(8)
        copy_button = QPushButton(self.tr('Copy'), message_row)
        copy_button.setObjectName('toastCopyButton')
        message_row.setMinimumHeight(copy_button.sizeHint().height())
        copy_button.setVisible(False)
        copy_reset_timer = QTimer(copy_button)
        copy_reset_timer.setSingleShot(True)
        copy_reset_timer.timeout.connect(lambda: copy_button.setText(self.tr('Copy')))

        def copy_message():
            clipboard = QApplication.clipboard()
            clipboard.setText(message)
            if clipboard.text() == message:
                copy_button.setText(self.tr('Copied ✔'))
                copy_reset_timer.start(3000)

        copy_button.clicked.connect(copy_message)
        message_layout.addWidget(message_label, 1)
        message_layout.addWidget(copy_button)
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(0)
        progress.setTextVisible(False)
        progress.setFixedHeight(3)
        progress.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        content_layout.addWidget(title_label)
        content_layout.addWidget(message_row)
        layout.addWidget(content)
        layout.addWidget(progress)
        toast.adjustSize()

        duration = duration if duration is not None else (6500 if level == 'error' else 4200)
        entry = {
            'widget': toast,
            'opacity': opacity_effect,
            'progress': progress,
            'progress_animation': None,
            'copy_button': copy_button,
            'copy_reset_timer': copy_reset_timer,
            'animation': None,
            'dismissing': False,
            'duration': duration,
        }
        toast.clicked.connect(lambda current=entry: self.dismiss_operation_toast(current))
        toast.hovered.connect(lambda hovered, current=entry: self._set_toast_hovered(current, hovered))
        self.operation_toasts.append(entry)
        target = self._operation_toast_position(entry)
        toast.move(target + self._operation_toast_offset(entry))
        toast.show()
        toast.raise_()
        self._animate_toast(entry, target, 260, QEasingCurve.Type.OutCubic, 0.0, 1.0)

        progress_animation = QPropertyAnimation(progress, b'value', toast)
        progress_animation.setDuration(duration)
        progress_animation.setStartValue(0)
        progress_animation.setEndValue(100)
        progress_animation.setEasingCurve(QEasingCurve.Type.Linear)
        progress_animation.finished.connect(lambda current=entry: self.dismiss_operation_toast(current))
        entry['progress_animation'] = progress_animation
        progress_animation.start()
        return toast

    def _set_toast_hovered(self, entry, hovered):
        animation = entry['progress_animation']
        if animation is None or entry['dismissing']:
            return
        entry['copy_button'].setVisible(hovered)
        if hovered and animation.state() == QAbstractAnimation.State.Running:
            animation.pause()
        elif not hovered and animation.state() == QAbstractAnimation.State.Paused:
            animation.resume()

    def _operation_toast_offset(self, entry):
        distance = entry['widget'].width() + 18
        return QPoint(-distance, 0) if self.translator.language == 'fa' else QPoint(distance, 0)

    def _operation_toast_position(self, entry):
        widget = entry['widget']
        width = widget.width()
        origin = self.window_frame.mapTo(self, QPoint(0, 0))
        x = origin.x() + (18 if self.translator.language == 'fa' else self.window_frame.width() - width - 18)
        y = origin.y() + 48
        for current in self.operation_toasts:
            if current is entry:
                break
            y += current['widget'].height() + 10
        return QPoint(max(0, x), y)

    def _stop_toast_animation(self, entry):
        animation = entry.get('animation')
        if animation:
            animation.stop()
            animation.deleteLater()
            entry['animation'] = None

    def _animate_toast(self, entry, target, duration, easing, start_opacity, end_opacity, on_finished=None):
        self._stop_toast_animation(entry)
        animation = QParallelAnimationGroup(self)
        movement = QPropertyAnimation(entry['widget'], b'pos', animation)
        movement.setDuration(duration)
        movement.setStartValue(entry['widget'].pos())
        movement.setEndValue(target)
        movement.setEasingCurve(easing)
        opacity = QPropertyAnimation(entry['opacity'], b'opacity', animation)
        opacity.setDuration(duration)
        opacity.setStartValue(start_opacity)
        opacity.setEndValue(end_opacity)
        opacity.setEasingCurve(easing)
        animation.addAnimation(movement)
        animation.addAnimation(opacity)
        entry['animation'] = animation
        entry['animation_easing'] = easing
        entry['animation_end_opacity'] = end_opacity

        def finished(current=entry, group=animation):
            if current['animation'] is not group:
                return
            current['animation'] = None
            group.deleteLater()
            if on_finished:
                on_finished(current)
            elif not current['dismissing']:
                current['widget'].move(self._operation_toast_position(current))
                current['widget'].show()
                current['widget'].raise_()

        animation.finished.connect(finished)
        animation.start()

    def dismiss_operation_toast(self, entry):
        if entry not in self.operation_toasts or entry['dismissing']:
            return
        entry['dismissing'] = True
        progress_animation = entry['progress_animation']
        if progress_animation:
            progress_animation.stop()
            progress_animation.deleteLater()
            entry['progress_animation'] = None
        target = entry['widget'].pos() + self._operation_toast_offset(entry)
        self._animate_toast(
            entry, target, 220, QEasingCurve.Type.InCubic,
            entry['opacity'].opacity(), 0.0, self._remove_operation_toast,
        )

    def _remove_operation_toast(self, entry):
        if entry not in self.operation_toasts:
            return
        self.operation_toasts.remove(entry)
        entry['widget'].hide()
        entry['widget'].deleteLater()
        self._reposition_operation_toasts()

    def _reposition_operation_toasts(self):
        for entry in self.operation_toasts:
            if entry['dismissing']:
                continue
            target = self._operation_toast_position(entry)
            if target != entry['widget'].pos():
                self._animate_toast(
                    entry, target, 220, QEasingCurve.Type.OutCubic,
                    entry['opacity'].opacity(), entry['opacity'].opacity(),
                )

    def _position_operation_toasts(self):
        for entry in self.operation_toasts:
            target = self._operation_toast_position(entry)
            if entry['dismissing']:
                target += self._operation_toast_offset(entry)
            animation = entry.get('animation')
            if animation and animation.state() == QParallelAnimationGroup.State.Running:
                remaining = max(1, animation.duration() - animation.currentTime())
                self._animate_toast(
                    entry, target, remaining, entry.get('animation_easing', QEasingCurve.Type.OutCubic),
                    entry['opacity'].opacity(), entry.get('animation_end_opacity', 1.0),
                    self._remove_operation_toast if entry['dismissing'] else None,
                )
            else:
                entry['widget'].move(target)
                entry['widget'].update_clip()

    def _schedule_toast_reposition(self):
        if getattr(self, 'operation_toasts', None):
            QTimer.singleShot(0, self._position_operation_toasts)

    def clear_console(self):
        if not hasattr(self, 'console_tabs') or self.console_tabs.currentIndex() < 0:
            return
        widget = self.console_tabs.currentWidget()
        widget.clear()
        key = next((key for key, edit in self._console_tab_widgets.items() if edit is widget), None)
        if key is not None:
            self._console_records[key]['text'] = ''

    def apply_theme(self):
        dark = self.store.data.get('theme') == 'dark'
        for highlighter in self.findChildren(LogHighlighter):
            highlighter.set_theme('dark' if dark else 'light')
        stylesheet = DARK if dark else LIGHT
        theme_name = 'dark' if dark else 'light'
        if self.translator.language == 'fa':
            stylesheet = stylesheet.replace('border-top-right-radius:8px;', 'border-top-left-radius:8px;')
            stylesheet = stylesheet.replace('border-bottom-right-radius:8px;', 'border-bottom-left-radius:8px;')
        for direction in ('up', 'down'):
            asset = (BASE / 'assets' / 'lucide-theme' / f'spin-{direction}-{theme_name}.png').as_posix()
            stylesheet = stylesheet.replace(f'@SPIN_{direction.upper()}@', asset)
        combo_arrow = (BASE / 'assets' / 'lucide-theme' / f'combo-down-{theme_name}.png').as_posix()
        stylesheet = stylesheet.replace('@COMBO_ARROW@', combo_arrow)
        stylesheet = stylesheet.replace('@TREE_CLOSED@', (BASE / 'assets' / 'lucide-theme' / f'tree-closed-{theme_name}.svg').as_uri())
        stylesheet = stylesheet.replace('@CHECK_MARK@', (BASE / 'assets' / 'lucide-theme' / 'check-white.svg').as_uri())
        QApplication.instance().setStyleSheet(stylesheet)
        self.theme_button.setText(self.tr('Light mode' if dark else 'Dark mode'))
        self.theme_button.setProperty('iconName', 'sun' if dark else 'moon')
        self.refresh_icons()

    def refresh_icons(self):
        dark = self.store.data.get('theme') == 'dark'
        accent = '#ff553d' if dark else '#f53003'
        for button in self.findChildren(QPushButton):
            name = button.property('iconName')
            if name:
                color = '#ffffff' if (
                    button.property('kind') == 'primary'
                    or (button.property('kind') == 'nav' and button.isChecked())
                ) else accent
                button.setIcon(self.lucide_icon(name, color))
            else:
                button.setIcon(QIcon())

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.Type.WindowStateChange:
            self._schedule_toast_reposition()
            QTimer.singleShot(320, self._position_operation_toasts)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            for combo in self.searchable_combos:
                if watched is combo.lineEdit():
                    QTimer.singleShot(0, lambda target=combo: self.open_combo_search(target))
                    break
        return super().eventFilter(watched, event)

    def open_combo_search(self, combo):
        if not combo.count(): return
        combo.lineEdit().selectAll()
        completer = combo.completer()
        completer.setCompletionPrefix('')
        completer.complete()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._schedule_toast_reposition()
