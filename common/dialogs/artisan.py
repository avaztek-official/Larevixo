"""Validated Artisan generator parameter dialog."""
from PySide6.QtWidgets import QCheckBox, QDialogButtonBox, QFormLayout, QLineEdit, QVBoxLayout
from common.dialogs.base import LocalizedDialog
from common.laravel.packages import ARTISAN_PRESETS
from common.validation.commands import safe_artisan_args

class ArtisanDialog(LocalizedDialog):
    def __init__(self, command, parent=None, translator=None):
        super().__init__(parent, translator)
        self.command = command; self.setWindowTitle(self.tr('Artisan')+' · '+command)
        self.resize(470, 330)
        v = QVBoxLayout(self)
        v.addWidget(self.label(command, 'pageTitle'))
        form = QFormLayout()
        self.name = QLineEdit(); self.name.setPlaceholderText(self.tr('Example: Admin/UserController'))
        form.addRow(self.tr('Name'), self.name)
        self.opts = {}
        for opt in ARTISAN_PRESETS[command][1:]:
            if opt.endswith('=?'):
                field = QLineEdit(); field.setPlaceholderText(self.tr('Optional'))
                form.addRow(opt.removesuffix('=?'), field)
            else:
                field = QCheckBox(self.tr('Enable'))
                form.addRow(opt.removesuffix('?'), field)
            self.opts[opt.split('?')[0].split('=')[0]] = field
        v.addLayout(form)
        v.addStretch(1)
        b = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        b.button(QDialogButtonBox.StandardButton.Cancel).setText(self.tr('Cancel'))
        b.button(QDialogButtonBox.StandardButton.Ok).setText(self.tr('Run'))
        b.accepted.connect(self.validate); b.rejected.connect(self.reject)
        v.addWidget(b)

    def validate(self):
        try: self.args()
        except ValueError as exc: return self.alert('Invalid parameters', str(exc), True)
        self.accept()

    def args(self):
        args={k: (v.isChecked() if isinstance(v,QCheckBox) else v.text()) for k,v in self.opts.items()}
        return safe_artisan_args(self.command, self.name.text().strip(), args)
