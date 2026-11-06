"""Qt smoke test, run on a Windows builder with PySide6 installed."""
import os
import sys
import tempfile
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
scale = float(os.environ.get('QT_SCALE_FACTOR', '1'))
smoke_profile = os.environ.get('LAREVIXO_SMOKE_PROFILE')
profile = tempfile.TemporaryDirectory(prefix='larevixo-smoke-') if not smoke_profile else None
profile_path = Path(smoke_profile) if smoke_profile else Path(profile.name)
profile_path.mkdir(parents=True, exist_ok=True)
os.environ['APPDATA'] = str(profile_path / 'Roaming')
os.environ['LOCALAPPDATA'] = str(profile_path / 'Local')
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QMessageBox, QPushButton, QWidget, QStyle, QStyleOptionSpinBox
from PySide6.QtCore import QTimer, Qt, QPoint, QRect, QProcess, QAbstractAnimation
from PySide6.QtGui import QRegion
from PySide6.QtTest import QTest
from main import App, ArtisanDialog, CreateDialog, DARK, LIGHT
from runner import Job
app = QApplication([])
window = App()
assert window.windowTitle().startswith('Larevixo')
assert window.stack.count() == 10
assert window.project_combo is not None
assert window.project_combo.completer().popup() is not None
assert window.project_combo.completer().filterMode() == Qt.MatchFlag.MatchContains
assert window.project_combo.completer().caseSensitivity() == Qt.CaseSensitivity.CaseInsensitive
window.show()
app.processEvents()
assert window.isVisible()
assert abs(app.primaryScreen().devicePixelRatio() - scale) < 0.05
for name, widget in window.pages.items():
    window.nav[name].click()
    app.processEvents()
    assert window.stack.currentWidget() is widget, f'Could not open {name}'
    assert window.nav[name].isChecked(), f'Navigation state did not update for {name}'
for name in ('Global & Settings',):
    window.nav[name].click()
    app.processEvents()
    page = window.pages[name]
    last_card = page.findChildren(QFrame, 'panel')[-1]
    card_bottom = last_card.mapTo(window, QPoint(0, last_card.height())).y()
    console_top = window.console_footer.mapTo(window, QPoint(0, 0)).y()
    assert 0 <= console_top - card_bottom <= 40, f'Excessive gap above Activity Console in {name}'
for name, title in (('Overview', 'Your Laravel workspace'), ('Artisan', 'Artisan studio')):
    window.nav[name].click()
    app.processEvents()
    labels = window.pages[name].findChildren(QLabel)
    page_title = next(label for label in labels if label.text() == title)
    project_row_bottom = window.project_combo.mapTo(window, QPoint(0, window.project_combo.height())).y()
    title_top = page_title.mapTo(window, QPoint(0, 0)).y()
    assert 0 <= title_top - project_row_bottom <= 50, (
        f'{name} content is not aligned below the project toolbar: gap={title_top - project_row_bottom}'
    )
    if name == 'Overview':
        subtitle = next(label for label in labels if label.text().startswith('A single cockpit'))
        first_card = window.pages[name].findChildren(QFrame, 'panel')[0]
        title_bottom = page_title.mapTo(window, QPoint(0, page_title.height())).y()
        subtitle_top = subtitle.mapTo(window, QPoint(0, 0)).y()
        subtitle_bottom = subtitle.mapTo(window, QPoint(0, subtitle.height())).y()
        card_top = first_card.mapTo(window, QPoint(0, 0)).y()
        assert 0 <= subtitle_top - title_bottom <= 30, (
            f'Overview title and subtitle are too far apart: gap={subtitle_top - title_bottom}'
        )
        assert 0 <= card_top - subtitle_bottom <= 35, (
            f'Overview subtitle and cards are too far apart: gap={card_top - subtitle_bottom}'
        )
assert {'Scheduler', 'Servers & Logs', 'Global & Settings'} <= window.pages.keys()
assert window.pages['Scheduler'].schedule_worker_button.text() == 'Start scheduler worker'
assert window.pages['Scheduler'].schedule_table.columnCount() == 5
assert '#171717' in DARK and '#f61500' in DARK
assert '#ffffff' in LIGHT and '#f53003' in LIGHT
window.nav['Artisan'].click()
app.processEvents()
artisan = window.pages['Artisan'].artisan_combo
field_top = artisan.mapToGlobal(QPoint(0, 0)).y()
field_bottom = artisan.mapToGlobal(QPoint(0, artisan.height())).y()
artisan.showPopup()
app.processEvents()
popup = artisan.view().window()
assert popup.isVisible()
popup_rect = popup.geometry()
assert popup_rect.bottom() < field_top or popup_rect.top() >= field_bottom
artisan.hidePopup()
artisan_line_edit = artisan.lineEdit()
artisan_completer = artisan.completer()
QTest.mouseClick(artisan_line_edit, Qt.MouseButton.LeftButton)
app.processEvents()
assert artisan_line_edit.hasSelectedText()
assert artisan_completer.popup().isVisible() and artisan_completer.completionCount() == artisan.count()
QTest.keyClicks(artisan_line_edit, 'make:model')
app.processEvents()
assert artisan_completer.popup().isVisible() and artisan_completer.completionCount() == 1
artisan_match = artisan_completer.completionModel().index(0, 0)
artisan_match_rect = artisan_completer.popup().visualRect(artisan_match)
QTest.mouseClick(artisan_completer.popup().viewport(), Qt.MouseButton.LeftButton, pos=artisan_match_rect.center())
app.processEvents()
assert artisan.currentText() == 'make:model'

def spin_arrow_contrast_pixels(image, rect, dark_theme):
    visible = 0
    for y in range(rect.top() + 1, rect.bottom()):
        for x in range(rect.left() + 1, rect.right()):
            color = image.pixelColor(x, y)
            if dark_theme and color.red() > 200 and color.green() > 180 and color.blue() > 175:
                visible += 1
            elif not dark_theme and color.red() < 180 and color.green() < 150 and color.blue() < 140:
                visible += 1
    return visible

window.theme_button.click()
app.processEvents()
assert window.store.data['theme'] == 'light'
light_stylesheet = QApplication.instance().styleSheet()
assert '#fffdfc' in light_stylesheet
assert 'QComboBox QAbstractItemView' in light_stylesheet
assert 'QListView#searchableComboCompleter' in light_stylesheet
assert 'QComboBox::drop-down' in light_stylesheet
assert 'QComboBox::down-arrow' in light_stylesheet and 'combo-down-light.png' in light_stylesheet
assert '@COMBO_ARROW@' not in light_stylesheet
assert '@SPIN_' not in light_stylesheet
assert 'spin-up-light.png' in light_stylesheet and 'spin-down-light.png' in light_stylesheet
spin = window.pages['Servers & Logs'].php_port
spin_image = spin.grab().toImage()
spin_option = QStyleOptionSpinBox()
spin.initStyleOption(spin_option)
for control in (QStyle.SubControl.SC_SpinBoxUp, QStyle.SubControl.SC_SpinBoxDown):
    control_rect = spin.style().subControlRect(QStyle.ComplexControl.CC_SpinBox, spin_option, control, spin)
    visible_pixels = spin_arrow_contrast_pixels(spin_image, control_rect, dark_theme=False)
    assert visible_pixels >= 5, f'Light theme spin arrow is not visible: {control.name} has {visible_pixels} dark pixels'
window.theme_button.click()
app.processEvents()
assert window.store.data['theme'] == 'dark'
dark_stylesheet = QApplication.instance().styleSheet()
assert '#201d1d' in dark_stylesheet
assert 'QComboBox QAbstractItemView' in dark_stylesheet
assert 'QListView#searchableComboCompleter' in dark_stylesheet
assert 'QComboBox::drop-down' in dark_stylesheet
assert 'QComboBox::down-arrow' in dark_stylesheet and 'combo-down-dark.png' in dark_stylesheet
assert '@COMBO_ARROW@' not in dark_stylesheet
assert '@SPIN_' not in dark_stylesheet
assert 'spin-up-dark.png' in dark_stylesheet and 'spin-down-dark.png' in dark_stylesheet
spin_image = spin.grab().toImage()
for control in (QStyle.SubControl.SC_SpinBoxUp, QStyle.SubControl.SC_SpinBoxDown):
    control_rect = spin.style().subControlRect(QStyle.ComplexControl.CC_SpinBox, spin_option, control, spin)
    visible_pixels = spin_arrow_contrast_pixels(spin_image, control_rect, dark_theme=True)
    assert visible_pixels >= 5, f'Dark theme spin arrow is not visible: {control.name} has {visible_pixels} light pixels'
assert 'QWidget#panelRow {background:transparent;}' in dark_stylesheet

for existing_entry in list(window.operation_toasts):
    window.dismiss_operation_toast(existing_entry)
QTest.qWait(260)
assert not window.operation_toasts, 'Could not isolate the toast UI checks from earlier app operations'

edge_toast = window.show_operation_toast('Toast edge animation', 'Motion must stay clipped to the app frame', 'info', duration=5000)
edge_entry = window.operation_toasts[-1]
frame = window.window_frame
frame_rect = QRect(frame.mapTo(window, QPoint(0, 0)), frame.size())
start_x = frame_rect.x() + frame.width() if window.layoutDirection() == Qt.LayoutDirection.LeftToRight else frame_rect.x() - edge_toast.width()
assert edge_toast.pos().x() == start_x, 'Toast entrance did not start exactly at the visible frame edge'
assert not frame_rect.intersects(edge_toast.geometry()), 'Toast entrance starts inside the app frame'
QTest.qWait(110)
visible_edge_region = edge_toast.mask().intersected(QRegion(edge_toast.rect())).boundingRect()
visible_edge_rect = QRect(edge_toast.pos() + visible_edge_region.topLeft(), visible_edge_region.size())
assert visible_edge_rect.isValid() and frame_rect.contains(visible_edge_rect), 'Entering toast painted outside the app frame'
QTest.qWait(180)
assert frame_rect.contains(edge_toast.geometry()), 'Toast did not settle fully inside the app frame'
dismiss_x = edge_toast.x() + window._operation_toast_offset(edge_entry).x()
expected_dismiss_x = start_x
assert dismiss_x == expected_dismiss_x, 'Toast exit did not end exactly at the visible frame edge'
window.dismiss_operation_toast(edge_entry)
QTest.qWait(110)
visible_edge_region = edge_toast.mask().intersected(QRegion(edge_toast.rect())).boundingRect()
visible_edge_rect = QRect(edge_toast.pos() + visible_edge_region.topLeft(), visible_edge_region.size())
assert not visible_edge_region.isEmpty() and frame_rect.contains(visible_edge_rect), 'Exiting toast painted outside the app frame'
QTest.qWait(140)
for _ in range(10):
    if edge_entry not in window.operation_toasts:
        break
    QTest.qWait(50)
assert edge_entry not in window.operation_toasts

first_toast = window.show_operation_toast('Toast test one', 'Click to dismiss', 'info', duration=5000)
first_entry = window.operation_toasts[-1]
app.processEvents()
QTest.qWait(300)
assert first_toast.isVisible() and first_entry['opacity'].opacity() > 0.99
second_toast = window.show_operation_toast('Toast test two', 'The stack should grow downward', 'success', duration=5000)
second_entry = window.operation_toasts[-1]
app.processEvents()
QTest.qWait(300)
first_y = first_toast.y()
second_y = second_toast.y()
assert len(window.operation_toasts) == 2 and second_y > first_y, (
    f'Toast stack did not grow downward: count={len(window.operation_toasts)}, '
    f'positions={first_toast.pos()}, {second_toast.pos()}, '
    f'frame={window.window_frame.geometry()}, frameInWindow={window.window_frame.mapTo(window, QPoint(0, 0))}'
)
assert second_entry['progress'].value() > 0 and second_entry['progress'].value() < 100
assert not second_entry['copy_button'].isVisible()
QTest.mouseMove(second_toast, second_toast.rect().center())
QTest.qWait(50)
assert second_entry['progress_animation'].state() == QAbstractAnimation.State.Paused
assert second_entry['copy_button'].isVisible()
assert second_entry['copy_button'].height() >= second_entry['copy_button'].sizeHint().height()
QTest.mouseMove(second_entry['copy_button'], second_entry['copy_button'].rect().center())
QTest.qWait(50)
assert second_entry['progress_animation'].state() == QAbstractAnimation.State.Paused
second_entry['copy_button'].click()
assert app.clipboard().text() == 'The stack should grow downward'
assert second_entry['copy_button'].text() == window.tr('Copied ✔')
assert second_entry['copy_reset_timer'].isActive()
assert second_entry['copy_reset_timer'].interval() == 3000
QTest.qWait(3100)
assert second_entry['copy_button'].text() == window.tr('Copy')
QTest.mouseMove(window.nav['Overview'], window.nav['Overview'].rect().center())
QTest.qWait(50)
assert second_entry['progress_animation'].state() == QAbstractAnimation.State.Running
assert not second_entry['copy_button'].isVisible()
progress_rect = second_entry['progress'].geometry()
assert progress_rect.left() >= 4 and progress_rect.right() <= second_toast.width() - 5
assert progress_rect.bottom() == second_toast.contentsRect().bottom(), 'The time bar should touch the toast bottom border'
toast_mask = second_toast.mask()
assert not toast_mask.isEmpty() and toast_mask.contains(second_toast.rect().center())
assert not toast_mask.contains(QPoint(0, second_toast.height() - 1))
assert not toast_mask.contains(QPoint(second_toast.width() - 1, second_toast.height() - 1))
QTest.mouseClick(first_toast, Qt.MouseButton.LeftButton, pos=first_toast.rect().center())
QTest.qWait(500)
assert first_entry not in window.operation_toasts and len(window.operation_toasts) == 1
assert second_toast.y() < second_y, 'The remaining toast did not move up after its neighbor closed'

timed_toast = window.show_operation_toast('Toast timer test', 'The time bar should dismiss this toast', 'error', duration=350)
timed_entry = window.operation_toasts[-1]
for _ in range(30):
    if timed_entry not in window.operation_toasts:
        break
    QTest.qWait(50)
assert timed_entry not in window.operation_toasts

restore_toast = window.show_operation_toast('Restore test', 'Stay visible at the restored window edge', 'info', duration=5000)
restore_entry = window.operation_toasts[-1]
original_size = window.size()
QTest.qWait(70)
window.showMaximized()
app.processEvents()
window.showNormal()
window.resize(1120, 720)
app.processEvents()
QTest.qWait(320)
assert restore_entry in window.operation_toasts and restore_toast.isVisible()
assert restore_toast.parentWidget() is window
for _ in range(10):
    target = window._operation_toast_position(restore_entry)
    if restore_toast.pos() == target:
        break
    QTest.qWait(50)
assert restore_toast.pos() == window._operation_toast_position(restore_entry)
frame_rect = QRect(window.window_frame.mapTo(window, QPoint(0, 0)), window.window_frame.size())
assert frame_rect.contains(restore_toast.geometry()), 'Toast escaped the visible app frame after restore down'
if window.layoutDirection() == Qt.LayoutDirection.RightToLeft:
    assert restore_toast.x() == frame_rect.x() + 18
else:
    assert restore_toast.geometry().right() == frame_rect.right() - 18, (
        f'Toast missed the restored frame edge: toast={restore_toast.geometry()}, '
        f'frame={frame_rect}, target={window._operation_toast_position(restore_entry)}'
    )
window.dismiss_operation_toast(restore_entry)
QTest.qWait(250)
assert restore_entry not in window.operation_toasts
window.resize(original_size)
app.processEvents()

window.nav['Routes'].click()
window.pages['Routes'].routes = [
    {'uri': 'admin/users/{id}/edit', 'method': 'GET', 'name': 'users.edit', 'action': 'UserController@edit', 'middleware': 'web'},
    {'uri': 'admin/users', 'method': 'GET', 'name': 'users.index', 'action': 'UserController@index', 'middleware': 'web'},
]
window.pages['Routes'].render_routes()
app.processEvents()
tree = window.pages['Routes'].routes_tree
admin = tree.topLevelItem(0)
users = admin.child(0)
assert admin.text(0) == 'admin/' and admin.isExpanded()
assert users.text(0) == 'users/' and users.isExpanded()
for item, expanded in ((admin, True), (users, True)):
    index = tree.indexFromItem(item)
    rect = tree.visualRect(index)
    branch_point = QPoint(max(1, rect.left() - tree.indentation() // 2), rect.center().y())
    QTest.mouseClick(tree.viewport(), Qt.MouseButton.LeftButton, pos=branch_point)
    app.processEvents()
    assert item.isExpanded() is not expanded, f'Route branch at {item.text(0)} did not toggle'
    QTest.mouseClick(tree.viewport(), Qt.MouseButton.LeftButton, pos=branch_point)
    app.processEvents()
    assert item.isExpanded() is expanded, f'Route branch at {item.text(0)} did not toggle back'
users.setExpanded(False)
app.processEvents()
if screenshot_path := os.environ.get('LAREVIXO_SMOKE_SCREENSHOT'):
    assert tree.grab().save(screenshot_path)

for page_name in ('Overview', 'Environment', 'Composer', 'Scheduler', 'Servers & Logs', 'Global & Settings'):
    assert window.pages[page_name].findChild(QWidget, 'panelRow') is not None, f'Missing transparent row in {page_name}'
assert window.findChild(QWidget, 'panelRow') is not None, 'Missing transparent activity-console row'
window.nav['Overview'].click()
app.processEvents()
quick_actions = window.pages['Overview'].findChildren(QWidget, 'panel')[1]
action_row = quick_actions.findChild(QWidget, 'panelRow')
action_buttons = action_row.findChildren(QPushButton)
assert action_row is not None and len(action_buttons) >= 2
quick_image = quick_actions.grab().toImage()
gap_x = (action_buttons[0].geometry().right() + action_buttons[1].geometry().left()) // 2
gap_point = action_row.mapTo(quick_actions, QPoint(gap_x, action_row.height() // 2))
pixel_ratio = quick_image.devicePixelRatio()
sampled_color = quick_image.pixelColor(round(gap_point.x() * pixel_ratio), round(gap_point.y() * pixel_ratio)).name()
assert sampled_color == '#222020', f'Dark background leaked into a card action row: {sampled_color}'

projects = [profile_path / 'Projects ü' / 'Láravel A', profile_path / 'Projects ü' / 'Laravel B']
for index, project in enumerate(projects):
    project.mkdir(parents=True)
    (project / 'artisan').write_text('<?php // isolated UI fixture\n', encoding='utf-8')
    (project / 'composer.json').write_text(
        '{"require":{"laravel/framework":"^12.0"}}', encoding='utf-8'
    )
    (project / 'composer.lock').write_text(
        '{"packages":[{"name":"laravel/framework","version":"v12.0.0"}],"packages-dev":[]}',
        encoding='utf-8',
    )
    (project / '.env').write_text(f'APP_NAME=Fixture{index}\n', encoding='utf-8')
    if index == 1:
        (project / 'package.json').write_text('{"scripts":{"dev":"vite"}}', encoding='utf-8')
    window.context.add_project(project)
window.context.projects_changed.emit()
assert window.project_combo.count() == 2
window.project_combo.showPopup()
app.processEvents()
assert window.project_combo.view().isVisible()
window.project_combo.hidePopup()
window.project_combo.setCurrentIndex(1)
line_edit = window.project_combo.lineEdit()
QTest.mouseClick(line_edit, Qt.MouseButton.LeftButton)
app.processEvents()
completer = window.project_combo.completer()
assert line_edit.hasSelectedText()
assert completer.popup().isVisible() and completer.completionCount() == 2
QTest.keyClicks(line_edit, 'RAVEL A')
app.processEvents()
assert completer.popup().isVisible() and completer.completionCount() == 1
match = completer.completionModel().index(0, 0)
match_rect = completer.popup().visualRect(match)
assert match_rect.isValid()
QTest.mouseClick(completer.popup().viewport(), Qt.MouseButton.LeftButton, pos=match_rect.center())
app.processEvents()
assert Path(window.current) == projects[0].resolve()
window.project_combo.setCurrentIndex(0)
app.processEvents()
assert Path(window.current) == projects[0].resolve()
assert 'APP_NAME=Fixture0' in window.pages['Environment'].active_env
window.project_combo.setCurrentIndex(1)
app.processEvents()
assert Path(window.current) == projects[1].resolve()
assert 'APP_NAME=Fixture1' in window.pages['Environment'].active_env

selected_before_language_change = window.current
log_timer = window.log_timer
window.language_button.click()
app.processEvents()
assert window.translator.language == 'fa'
assert app.layoutDirection() == Qt.LayoutDirection.RightToLeft
assert window.current == selected_before_language_change
assert window.stack.count() == 10 and window.log_timer is log_timer and log_timer.isActive()
assert type(window.pages['Projects']).__name__ == 'ProjectsPage'
window.language_button.click()
app.processEvents()
assert window.translator.language == 'en'
assert app.layoutDirection() == Qt.LayoutDirection.LeftToRight
assert window.current == selected_before_language_change
assert window.stack.count() == 10 and window.log_timer is log_timer and log_timer.isActive()

queued_jobs = []
original_enqueue = window.runner.enqueue
window.runner.enqueue = queued_jobs.append
window.nav['Scheduler'].click()
app.processEvents()
assert queued_jobs[-1].args == ['artisan', 'schedule:list', '--json']
window.pages['Scheduler'].show_schedules_json(
    '[{"command":"php artisan reports:send --daily","expression":"0 0 * * *","next_due_date_human":"tomorrow","description":"Send reports"},'
    '{"command":"php artisan users:sync","expression":"*/5 * * * *","next_due_date_human":"in 5 minutes","description":""}]'
)
assert window.pages['Scheduler'].schedule_table.rowCount() == 2
assert not window.pages['Scheduler'].schedule_test_button.isEnabled()
window.pages['Scheduler'].select_all_schedules()
assert window.pages['Scheduler'].checked_schedule_names() == ['reports:send --daily','users:sync']
window.pages['Scheduler'].clear_schedule_selection()
assert window.pages['Scheduler'].checked_schedule_names() == []
window.pages['Scheduler'].schedule_table.item(0,0).setCheckState(Qt.CheckState.Checked)
window.pages['Scheduler'].schedule_table.item(1,0).setCheckState(Qt.CheckState.Checked)
app.processEvents()
assert window.pages['Scheduler'].schedule_test_button.isEnabled()
assert window.pages['Scheduler'].schedule_test_button.text() == 'Test checked tasks (2)'
assert window.pages['Scheduler'].checked_schedule_names() == ['reports:send --daily','users:sync']
scheduled_jobs_before_rebuild = len(queued_jobs)
for _ in range(6):
    window.toggle_language()
    app.processEvents()
assert len(queued_jobs) == scheduled_jobs_before_rebuild, 'Language rebuild queued duplicate scheduler refreshes'
assert window.pages['Scheduler'].checked_schedule_names() == ['reports:send --daily','users:sync']

class FakeService:
    def state(self):
        return QProcess.ProcessState.Running

service_calls = []
fake_service = FakeService()
original_service_start = window.runner.service_start
original_service_stop = window.runner.service_stop
def fake_service_start(key, tool, args, cwd):
    service_calls.append(('start', key, tool, args, cwd))
    window.runner.services[key] = fake_service
def fake_service_stop(key):
    service_calls.append(('stop', key))
    window.runner.services.pop(key, None)
window.runner.service_start = fake_service_start
window.runner.service_stop = fake_service_stop
window.pages['Scheduler'].schedule_worker_button.click()
app.processEvents()
assert window.pages['Scheduler'].schedule_worker_running()
assert service_calls[-1][0:4] == ('start', 'scheduler|' + str(projects[1].resolve()), 'php', ['artisan', 'schedule:work'])
window.pages['Scheduler'].schedule_worker_button.click()
app.processEvents()
assert not window.pages['Scheduler'].schedule_worker_running() and service_calls[-1][0] == 'stop'
window.runner.service_start = original_service_start
window.runner.service_stop = original_service_stop

original_warning = QMessageBox.warning
QMessageBox.warning = lambda *args: QMessageBox.StandardButton.Yes
window.pages['Scheduler'].schedule_test_button.click()
assert [job.args for job in queued_jobs[-2:]] == [
    ['artisan', 'schedule:test', '--name=reports:send --daily'],
    ['artisan', 'schedule:test', '--name=users:sync'],
]
window.pages['Scheduler'].schedule_run_due_button.click()
assert queued_jobs[-1].args == ['artisan', 'schedule:run']
QMessageBox.warning = original_warning
window.runner.enqueue = original_enqueue

window.pages['Scheduler'].show_schedules_text('''
  */5  *        * * *  php artisan summarize:missing .......................................... Next Due: 2 دقیقه دیگر
  0    8        * * *  Closure at: app\\Console\\Kernel.php:67 .............................. Next Due: 19 ساعت دیگر
  0    8        * * *  sends KPI reports every first jalali mounths ........................... Next Due: 19 ساعت دیگر
''')
assert window.pages['Scheduler'].schedule_table.rowCount() == 3
assert window.pages['Scheduler'].schedule_table.item(0,1).data(Qt.ItemDataRole.UserRole) == 'summarize:missing'
window.pages['Scheduler'].schedule_table.item(0,0).setCheckState(Qt.CheckState.Checked)
app.processEvents()
assert window.pages['Scheduler'].checked_schedule_names() == ['summarize:missing']
window.pages['Scheduler'].schedule_table.selectRow(1)
app.processEvents()
assert not window.pages['Scheduler'].schedule_table.item(1,0).flags() & Qt.ItemFlag.ItemIsEnabled
assert 'unnamed closure' in window.pages['Scheduler'].schedule_table.item(1,0).toolTip().lower()

missing_php = str(profile_path / 'missing-php.exe')
missing_composer = str(profile_path / 'missing-composer.exe')
missing_npm = str(profile_path / 'missing-npm.exe')
window.runner.tools.update(php=missing_php, composer=missing_composer, npm=missing_npm)
error_dialogs = []

def dismiss_error_dialog():
    dialog = QApplication.activeModalWidget()
    if dialog is not None:
        error_dialogs.append((dialog.windowTitle(), dialog.text()))
        dialog.accept()

QTimer.singleShot(0, dismiss_error_dialog)
window.pages['Projects'].create_project()
app.processEvents()
QTimer.singleShot(0, dismiss_error_dialog)
window.pages['Servers & Logs'].start_service('laravel')
QTimer.singleShot(0, dismiss_error_dialog)
window.pages['Servers & Logs'].start_service('vite')
window.runner.enqueue(Job('Missing Composer fixture', 'composer', ['--version'], str(projects[1])))
app.processEvents()
console_text = '\n'.join(record['text'] for record in window._console_records.values())
assert 'php not found' in error_dialogs[0][1].lower()
assert 'php not found' in error_dialogs[1][1].lower()
assert 'npm not found' in error_dialogs[2][1].lower()
assert 'composer not found' in console_text.lower()

window.close()
create = CreateDialog(None, '8.2.12')
assert create.selected_major() == '12'
assert not create.default_checks['laravel/sail'].isHidden()
assert create.default_checks['laravel/pao'].isHidden()
assert not create.extra_checks['laravel/sanctum'].isHidden()
assert not create.version.model().item(1).isEnabled()
create.version.setCurrentText('10.x')
assert create.selected_major() == '10'
assert not create.default_checks['laravel/sanctum'].isHidden()
assert create.extra_checks['laravel/sanctum'].isHidden()
assert create.default_checks['laravel/pail'].isHidden()
create.close()

artisan = ArtisanDialog('make:controller')
artisan.name.setText('Admin/UserController')
assert artisan.args() == ['make:controller', 'Admin/UserController']
artisan.name.clear()
try:
    artisan.args()
except ValueError:
    pass
else:
    raise AssertionError('Artisan dialog accepted an empty class name')
artisan.close()

print(f'Larevixo Qt smoke OK: 10 pages, scheduler controls, themes, two isolated projects, missing-tool dialogs, forms, scale={scale:g}x')
if profile:
    profile.cleanup()
