"""Laravel project creation wizard."""
from pathlib import Path
from PySide6.QtWidgets import QCheckBox, QComboBox, QDialogButtonBox, QFileDialog, QFormLayout, QGridLayout, QLineEdit, QScrollArea, QVBoxLayout, QWidget
from common.dialogs.base import LocalizedDialog
from common.dialogs.package_selection import PackageSelectionWidget
from common.laravel.versions import DEFAULT_PACKAGES_BY_MAJOR, LARAVEL_MIN_PHP, OPTIONAL_PACKAGES, default_packages_for_major, latest_laravel_major, laravel_php_compatible
from common.validation.commands import IDENT
from common.ui.widgets import hbox

class CreateDialog(LocalizedDialog):
    def __init__(self, parent=None, php_version='', translator=None):
        super().__init__(parent, translator)
        self.php_version = php_version
        self.latest_major = latest_laravel_major(php_version)
        self.setWindowTitle(self.tr('Create a Laravel project'))
        self.resize(760, 850)
        layout = QVBoxLayout(self); layout.setContentsMargins(12, 12, 12, 12)
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        body = QWidget()
        root = QVBoxLayout(body); root.setContentsMargins(9, 6, 9, 10)
        scroll.setWidget(body)
        layout.addWidget(scroll, 1)
        root.addWidget(self.label('Create a new Laravel application', 'pageTitle'))
        root.addWidget(self.label('Choose a folder and select which packages to retain or install.'))
        form = QFormLayout(); form.setSpacing(11)
        self.name = QLineEdit(); self.name.setPlaceholderText(self.tr('my-app'))
        self.parent_path = QLineEdit(str(Path.home() / 'Projects'))
        browse = self.btn('Browse', self.browse)
        form.addRow(self.tr('Project name'), self.name)
        w = QWidget(); w.setLayout(hbox(self.parent_path, browse)); form.addRow(self.tr('Parent folder'), w)
        self.version = QComboBox()
        for version in ['Latest compatible', '13.x', '12.x', '11.x', '10.x']:
            self.version.addItem(self.tr(version), version)
        for index in range(self.version.count()):
            text = self.version.itemData(index)
            major = self.latest_major if text == 'Latest compatible' else text.split('.')[0]
            compatible = laravel_php_compatible(php_version, major)
            item = self.version.model().item(index)
            item.setEnabled(compatible)
            if not compatible:
                item.setToolTip(self.tr('Laravel {major} requires PHP {version} or newer.').format(major=major, version=f'{LARAVEL_MIN_PHP[major][0]}.{LARAVEL_MIN_PHP[major][1]}'))
        form.addRow(self.tr('Laravel skeleton'), self.version)
        root.addLayout(form)
        self.defaults_heading = self.label('', 'cardTitle')
        root.addWidget(self.defaults_heading)
        root.addWidget(self.label('Core laravel/framework is mandatory. Selected defaults already exist in the skeleton; deselected defaults are removed after creation.'))
        defaults = QWidget(); g = QGridLayout(defaults); g.setContentsMargins(0,0,0,0)
        self.default_checks = {}
        all_defaults = {}
        for major in ('10', '11', '12', '13'):
            for spec in DEFAULT_PACKAGES_BY_MAJOR[major]:
                all_defaults.setdefault(spec[0], spec)
        for idx, (pkg, dev, desc) in enumerate(all_defaults.values()):
            cb = QCheckBox(pkg); cb.setChecked(True); cb.setToolTip(self.tr(desc) + (self.tr(' (dev)') if dev else ''))
            g.addWidget(cb, idx//2, idx%2); self.default_checks[pkg] = cb
        self.default_layout = g
        root.addWidget(defaults)
        self.optional_heading = self.label('', 'cardTitle')
        root.addWidget(self.optional_heading)
        extras = QWidget(); ge = QGridLayout(extras); ge.setContentsMargins(0,0,0,0)
        self.extra_checks = {}
        for idx, (pkg, dev, desc) in enumerate(OPTIONAL_PACKAGES):
            cb = QCheckBox(pkg); cb.setToolTip(self.tr(desc) + (self.tr(' (dev)') if dev else ''))
            ge.addWidget(cb, idx//2, idx%2); self.extra_checks[pkg] = cb
        self.optional_layout = ge
        root.addWidget(extras)
        self.auth = QComboBox()
        self.auth.addItem(self.tr('No authentication starter'), '')
        self.auth.addItem(self.tr('Laravel Breeze · Blade'), 'blade')
        self.auth.addItem(self.tr('Laravel Breeze · React'), 'react')
        self.auth.addItem(self.tr('Laravel Breeze · Vue'), 'vue')
        self.auth.addItem(self.tr('Laravel Breeze · API'), 'api')
        root.addWidget(self.label('Authentication system', 'cardTitle'))
        root.addWidget(self.auth)

        root.addWidget(self.label('ADDITIONAL COMPOSER PACKAGES', 'cardTitle'))
        root.addWidget(self.label('Search Packagist or enter a package name. Leave version blank to install the latest version.'))
        self.composer_packages = PackageSelectionWidget('Packagist', self.translator, self)
        root.addWidget(self.composer_packages)

        root.addWidget(self.label('ADDITIONAL NPM PACKAGES', 'cardTitle'))
        root.addWidget(self.label('Search npm or enter a package name. Leave version blank to install the latest version.'))
        self.npm_packages = PackageSelectionWidget('npm', self.translator, self)
        root.addWidget(self.npm_packages)

        self.npm = QCheckBox(self.tr('Run npm install --ignore-scripts after creation'))
        root.addWidget(self.npm)
        root.addWidget(self.label('Composer hooks in the official skeleton may still execute during creation. Review third-party packages before selecting them.'))
        actions = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        actions.button(QDialogButtonBox.StandardButton.Ok).setText(self.tr('Create project'))
        actions.button(QDialogButtonBox.StandardButton.Cancel).setText(self.tr('Cancel'))
        actions.accepted.connect(self.validate); actions.rejected.connect(self.reject)
        layout.addWidget(actions)
        self.version.currentTextChanged.connect(self.refresh_package_choices)
        self.refresh_package_choices()

    def selected_major(self):
        text = self.version.currentData()
        return self.latest_major if text == 'Latest compatible' else text.split('.')[0]

    def refresh_package_choices(self):
        major = self.selected_major()
        defaults = default_packages_for_major(major)
        default_names = {pkg for pkg, _, _ in defaults}
        for layout, checks in ((self.default_layout, self.default_checks), (self.optional_layout, self.extra_checks)):
            for checkbox in checks.values():
                layout.removeWidget(checkbox)
                checkbox.hide()
        for index, (pkg, _, _) in enumerate(defaults):
            checkbox = self.default_checks[pkg]
            checkbox.show()
            self.default_layout.addWidget(checkbox, index // 2, index % 2)
        extras = [(pkg, checkbox) for pkg, checkbox in self.extra_checks.items() if pkg not in default_names]
        for index, (_, checkbox) in enumerate(extras):
            checkbox.show()
            self.optional_layout.addWidget(checkbox, index // 2, index % 2)
        selected = self.version.currentData()
        latest_note = self.tr(' · latest compatible with PHP {version}').format(version=self.php_version) if selected == 'Latest compatible' else ''
        self.defaults_heading.setText(self.tr('DEFAULT PACKAGES · Laravel {major}.x skeleton{note}').format(major=major, note=latest_note))
        self.optional_heading.setText(self.tr('OPTIONAL PACKAGES · not installed by default'))

    def browse(self):
        p = QFileDialog.getExistingDirectory(self, self.tr('Select parent directory'), self.parent_path.text())
        if p: self.parent_path.setText(p)

    def validate(self):
        name = self.name.text().strip()
        base = Path(self.parent_path.text().strip()).expanduser()
        if not IDENT.fullmatch(name):
            return self.alert('Invalid name', 'Use 2–64 characters: letters, digits, dashes and underscores; start with a letter.', True)
        if base.exists() and not base.is_dir():
            return self.alert('Invalid folder', 'The parent folder path points to a file.', True)
        if (base / name).exists():
            return self.alert('Directory exists', 'Choose an unused project directory.', True)
        self.accept()

    def settings(self):
        defaults = default_packages_for_major(self.selected_major())
        return (self.name.text().strip(), Path(self.parent_path.text().strip()).expanduser(),
                self.version.currentText(),
                [p for p,_,_ in defaults if not self.default_checks[p].isChecked()],
                [(p,d) for p,d,_ in OPTIONAL_PACKAGES if p not in {name for name,_,_ in defaults} and self.extra_checks[p].isChecked()],
                self.npm.isChecked(), self.auth.currentData(),
                self.composer_packages.entries(), self.npm_packages.entries())
