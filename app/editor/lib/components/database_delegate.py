from app.data.database import DB
from PyQt5.QtWidgets import QLineEdit, QItemDelegate
from PyQt5 import QtCore
from app.extensions.custom_gui import ComboBox

class DBNamesDelegate(QItemDelegate):
    key_column = 0
    value_column = 1

    def createEditor(self, parent, option, index):
        if index.column() == self.key_column:
            editor = QLineEdit(parent)
            self.editor = None
            return editor
        else:
            all_relevant_strings = []
            all_relevant_strings += DB.units.keys()
            all_relevant_strings += DB.skills.keys()
            all_relevant_strings += DB.items.keys()
            all_relevant_strings += DB.classes.keys()
            all_relevant_strings += DB.tags.keys()
            all_relevant_strings += DB.game_var_slots.keys()
            all_relevant_strings = list(set(all_relevant_strings))
            editor = ComboBox(parent)
            editor.addItems(all_relevant_strings)
            editor.setEditable(True)
            self.editor = editor
            return editor

    def eventFilter(self, obj, event): # disable default tab behavior for accurate autocomplete on combobox
        if (event.type() == QtCore.QEvent.KeyPress):
            key = event.key()
            if key == QtCore.Qt.Key_Tab:
                if self.editor:
                    self.editor.setValue(self.editor.completer().currentCompletion())
        return super().eventFilter(obj, event)
