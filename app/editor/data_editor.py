from PyQt5.QtWidgets import QDialog, QGridLayout, QDialogButtonBox
from PyQt5.QtCore import Qt, QSettings

from app.resources.resources import RESOURCES
from app.data.database import DB

class SingleDatabaseEditor(QDialog):
    def __init__(self, tab, parent=None):
        super().__init__(parent)
        self.window = parent
        self.setStyleSheet("font: 10pt;")
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self.save()

        self.grid = QGridLayout(self)
        self.setLayout(self.grid)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply, Qt.Horizontal, self)
        self.grid.addWidget(self.buttonbox, 1, 1)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)
        self.buttonbox.button(QDialogButtonBox.Apply).clicked.connect(self.apply)

        self.tab = tab.create(self)
        self.grid.addWidget(self.tab, 0, 0, 1, 2)

        self.setWindowTitle(self.tab.windowTitle())

    def accept(self):
        settings = QSettings("rainlash", "Lex Talionis")
        current_proj = settings.value("current_proj", None)
        if current_proj:
            DB.serialize(current_proj)
        super().accept()

    def reject(self):
        self.restore()
        settings = QSettings("rainlash", "Lex Talionis")
        current_proj = settings.value("current_proj", None)
        if current_proj:
            DB.serialize(current_proj)
        super().reject()

    def save(self):
        self.saved_data = DB.save()
        return self.saved_data

    def restore(self):
        DB.restore(self.saved_data)
        
    def apply(self):
        self.save()

class SingleResourceEditor(QDialog):
    def __init__(self, tab, resource_types=None, parent=None):
        super().__init__(parent)
        self.window = parent
        self.resource_types = resource_types
        self.setStyleSheet("font: 10pt;")
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self.grid = QGridLayout(self)
        self.setLayout(self.grid)

        self.buttonbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        self.grid.addWidget(self.buttonbox, 1, 1)
        self.buttonbox.accepted.connect(self.accept)
        self.buttonbox.rejected.connect(self.reject)

        self.tab = tab.create(self)
        self.grid.addWidget(self.tab, 0, 0, 1, 2)

        self.setWindowTitle(self.tab.windowTitle())

    def accept(self):
        settings = QSettings("rainlash", "Lex Talionis")
        current_proj = settings.value("current_proj", None)
        if current_proj:
            RESOURCES.save(current_proj, self.resource_types)
        super().accept()

    def reject(self):
        settings = QSettings("rainlash", "Lex Talionis")
        current_proj = settings.value("current_proj", None)
        if current_proj:
            RESOURCES.reload(current_proj)
        super().reject()
