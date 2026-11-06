"""Application color themes."""

LIGHT = '''
QWidget {background:#ffffff; color:#262222; font-family:'Segoe UI'; font-size:13px;}
QWidget#panelRow {background:transparent;}
QMainWindow {background:#ffffff; border:0;}
QWidget#windowRoot {background:#ffffff;}
QFrame#windowFrame {background:#ffffff; border:0;}
QFrame#consoleFooter {background:#fff5f2; border:0; border-top:1px solid #efdbd5;}
QFrame#sidebar {background:#fff5f2; border-right:1px solid #f3dad3;}
QWidget#sidebarBrand,QLabel[role="sidebarLogo"],QLabel[role="brand"] {background:transparent;}
QFrame#panel {background:#ffffff; border:1px solid #efdbd5; border-radius:15px;}
QLabel[role="pageTitle"] {font-size:24px; font-weight:750; color:#301f1c;}
QLabel[role="cardTitle"] {font-size:15px; font-weight:700; color:#352622;}
QLabel[role="muted"] {color:#966e64; font-size:12px;}
QLabel[role="brand"] {font-size:22px; font-weight:800; color:#f53003;}
QPushButton {border:1px solid #efd7d0; background:#fff9f7; color:#612d22; border-radius:9px; padding:9px 14px; font-weight:600;}
QPushButton:hover {background:#ffece6; border-color:#f8ad9c;}
QPushButton[kind="primary"] {background:#f53003; color:white; border-color:#f53003;}
QPushButton[kind="primary"]:hover {background:#e52a00;}
QPushButton[kind="danger"] {color:#d33310; border-color:#ffc3b5;}
QPushButton[kind="nav"] {border:0; text-align:left; padding:12px 15px; background:transparent; border-radius:10px;}
QPushButton[kind="nav"]:checked {background:#f53003; color:#ffffff;}
QPushButton[kind="consoleToggle"] {border:0; background:transparent; padding:5px 8px; color:#612d22; font-weight:700;}
QPushButton[kind="consoleToggle"]:hover {color:#f53003;}
QPushButton[kind="sidebarLink"] {border:0; border-radius:0; background:transparent; color:#966e64; padding:0; font-size:12px; font-weight:400; text-align:left;}
QPushButton[kind="sidebarLink"]:hover {text-decoration:underline;}
QLineEdit,QComboBox,QSpinBox,QPlainTextEdit,QTreeWidget,QTableWidget {background:#fffdfc; color:#332b29; border:1px solid #efd9d2; border-radius:9px; padding:7px; selection-background-color:#f53003;}
QComboBox {padding-right:26px;}
QComboBox::drop-down {subcontrol-origin:border; subcontrol-position:top right; width:22px; border-left:1px solid #efd9d2; background:#fff0eb; border-top-right-radius:8px; border-bottom-right-radius:8px;}
QComboBox::down-arrow {image:url("@COMBO_ARROW@"); width:12px; height:12px;}
QComboBox QAbstractItemView,QListView#searchableComboCompleter {background:#fffdfc; color:#332b29; border:1px solid #efd9d2; border-radius:9px; padding:4px; outline:0; selection-background-color:#f53003; selection-color:#ffffff;}
QComboBox QAbstractItemView::item,QListView#searchableComboCompleter::item {min-height:22px; padding:6px 9px; border-radius:5px;}
QComboBox QAbstractItemView::item:hover,QListView#searchableComboCompleter::item:hover {background:#ffece6; color:#612d22;}
QComboBox QAbstractItemView::item:selected,QListView#searchableComboCompleter::item:selected {background:#f53003; color:#ffffff;}
QHeaderView::section {background:#fff0eb; color:#884936; padding:10px; border:none; font-weight:600;}
QTableWidget::item {padding:5px;}
QCheckBox {spacing:10px;}
QCheckBox::indicator {width:16px; height:16px; border:1px solid #efd9d2; border-radius:4px; background:#fffdfc;}
QCheckBox::indicator:hover {border-color:#f53003;}
QCheckBox::indicator:checked {background:#f53003; border-color:#f53003; image:url("@CHECK_MARK@");}
QScrollArea {border:0;}
QSplitter#contentConsoleSplitter::handle:vertical {background:#efdbd5;}
QSplitter#contentConsoleSplitter::handle:vertical:hover {background:#f53003;}
QTabWidget#operationConsoleTabs::pane {border:1px solid #efdbd5; border-radius:8px;}
QTabBar::tab {background:#fff0eb; border:1px solid #efdbd5; padding:7px 12px; margin-right:3px; border-top-left-radius:6px; border-top-right-radius:6px;}
QTabBar::tab:selected {background:#ffffff; color:#f53003;}
QScrollBar:vertical {background:#fff0eb; width:10px; margin:0; border:0; border-radius:5px;}
QScrollBar:horizontal {background:#fff0eb; height:10px; margin:0; border:0; border-radius:5px;}
QScrollBar::handle:vertical {background:#e8b9ad; min-height:26px; border-radius:5px;}
QScrollBar::handle:horizontal {background:#e8b9ad; min-width:26px; border-radius:5px;}
QScrollBar::handle:vertical:hover,QScrollBar::handle:horizontal:hover {background:#f53003;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0; border:0;}
QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal {width:0; border:0;}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical,QScrollBar::add-page:horizontal,QScrollBar::sub-page:horizontal {background:transparent;}
QSpinBox {padding:7px 25px 7px 7px;}
QSpinBox::up-button,QSpinBox::down-button {subcontrol-origin:border; width:22px; border:0; border-left:1px solid #efd9d2; background:#fff0eb;}
QSpinBox::up-button {subcontrol-position:right top; border-top-right-radius:8px;}
QSpinBox::down-button {subcontrol-position:right bottom; border-top:1px solid #efd9d2; border-bottom-right-radius:8px;}
QSpinBox::up-button:hover,QSpinBox::down-button:hover {background:#ffe3da;}
QSpinBox::up-arrow {image:url("@SPIN_UP@"); width:14px; height:14px;}
QSpinBox::down-arrow {image:url("@SPIN_DOWN@"); width:14px; height:14px;}
'''

DARK = '''
QWidget {background:#171717; color:#f1eeee; font-family:'Segoe UI'; font-size:13px;}
QLabel {background:transparent;}
QMainWindow {background:#171717; border:0;}
QWidget#windowRoot {background:#171717;}
QFrame#windowFrame {background:#171717; border:0;}
QFrame#consoleFooter {background:#1d1b1b; border:0; border-top:1px solid #373030;}
QFrame#sidebar {background:#1d1b1b; border-right:1px solid #373030;}
QWidget#sidebarBrand,QLabel[role="sidebarLogo"],QLabel[role="brand"] {background:transparent;}
QWidget#panelRow {background:transparent;}
QFrame#panel {background:#222020; border:1px solid #3a3030; border-radius:15px;}
QLabel[role="pageTitle"] {font-size:24px; font-weight:750; color:#ffffff;}
QLabel[role="cardTitle"] {font-size:15px; font-weight:700; color:#fff4f1;}
QLabel[role="muted"] {color:#bba7a4; font-size:12px;}
QLabel[role="brand"] {font-size:22px; font-weight:800; color:#ff553d;}
QPushButton {border:1px solid #4a3431; background:#2b2524; color:#f3e5e1; border-radius:9px; padding:9px 14px; font-weight:600;}
QPushButton:hover {background:#44302a; border-color:#875043;}
QPushButton[kind="primary"] {background:#f61500; border-color:#f61500; color:#ffffff;}
QPushButton[kind="primary"]:hover {background:#df1707;}
QPushButton[kind="danger"] {color:#ff796c; border-color:#743d33;}
QPushButton[kind="nav"] {border:0; text-align:left; padding:12px 15px; background:transparent; border-radius:10px;}
QPushButton[kind="nav"]:checked {background:#f61500; color:#ffffff;}
QPushButton[kind="consoleToggle"] {border:0; background:transparent; padding:5px 8px; color:#f3e5e1; font-weight:700;}
QPushButton[kind="consoleToggle"]:hover {color:#ff553d;}
QPushButton[kind="sidebarLink"] {border:0; border-radius:0; background:transparent; color:#bba7a4; padding:0; font-size:12px; font-weight:400; text-align:left;}
QPushButton[kind="sidebarLink"]:hover {text-decoration:underline;}
QLineEdit,QComboBox,QSpinBox,QPlainTextEdit,QTreeWidget,QTableWidget {background:#201d1d; color:#f8f1ef; border:1px solid #473532; border-radius:9px; padding:7px; selection-background-color:#f61500;}
QComboBox {padding-right:26px;}
QComboBox::drop-down {subcontrol-origin:border; subcontrol-position:top right; width:22px; border-left:1px solid #473532; background:#312523; border-top-right-radius:8px; border-bottom-right-radius:8px;}
QComboBox::down-arrow {image:url("@COMBO_ARROW@"); width:12px; height:12px;}
QComboBox QAbstractItemView,QListView#searchableComboCompleter {background:#201d1d; color:#f8f1ef; border:1px solid #473532; border-radius:9px; padding:4px; outline:0; selection-background-color:#f61500; selection-color:#ffffff;}
QComboBox QAbstractItemView::item,QListView#searchableComboCompleter::item {min-height:22px; padding:6px 9px; border-radius:5px;}
QComboBox QAbstractItemView::item:hover,QListView#searchableComboCompleter::item:hover {background:#44302a; color:#f3e5e1;}
QComboBox QAbstractItemView::item:selected,QListView#searchableComboCompleter::item:selected {background:#f61500; color:#ffffff;}
QHeaderView::section {background:#312523; color:#f8ccc3; padding:10px; border:none; font-weight:600;}
QTableWidget::item {padding:5px;}
QCheckBox {spacing:10px;}
QCheckBox::indicator {width:16px; height:16px; border:1px solid #473532; border-radius:4px; background:#201d1d;}
QCheckBox::indicator:hover {border-color:#f61500;}
QCheckBox::indicator:checked {background:#f61500; border-color:#f61500; image:url("@CHECK_MARK@");}
QScrollArea {border:0;}
QSplitter#contentConsoleSplitter::handle:vertical {background:#373030;}
QSplitter#contentConsoleSplitter::handle:vertical:hover {background:#f61500;}
QTabWidget#operationConsoleTabs::pane {border:1px solid #473532; border-radius:8px;}
QTabBar::tab {background:#312523; border:1px solid #473532; padding:7px 12px; margin-right:3px; border-top-left-radius:6px; border-top-right-radius:6px;}
QTabBar::tab:selected {background:#201d1d; color:#ff553d;}
QScrollBar:vertical {background:#312523; width:10px; margin:0; border:0; border-radius:5px;}
QScrollBar:horizontal {background:#312523; height:10px; margin:0; border:0; border-radius:5px;}
QScrollBar::handle:vertical {background:#65504c; min-height:26px; border-radius:5px;}
QScrollBar::handle:horizontal {background:#65504c; min-width:26px; border-radius:5px;}
QScrollBar::handle:vertical:hover,QScrollBar::handle:horizontal:hover {background:#f61500;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0; border:0;}
QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal {width:0; border:0;}
QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical,QScrollBar::add-page:horizontal,QScrollBar::sub-page:horizontal {background:transparent;}
QSpinBox {padding:7px 25px 7px 7px;}
QSpinBox::up-button,QSpinBox::down-button {subcontrol-origin:border; width:22px; border:0; border-left:1px solid #473532; background:#312523;}
QSpinBox::up-button {subcontrol-position:right top; border-top-right-radius:8px;}
QSpinBox::down-button {subcontrol-position:right bottom; border-top:1px solid #473532; border-bottom-right-radius:8px;}
QSpinBox::up-button:hover,QSpinBox::down-button:hover {background:#44302a;}
QSpinBox::up-arrow {image:url("@SPIN_UP@"); width:14px; height:14px;}
QSpinBox::down-arrow {image:url("@SPIN_DOWN@"); width:14px; height:14px;}
'''
