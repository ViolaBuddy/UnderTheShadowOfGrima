from PyQt5.QtWidgets import QWidget, QGridLayout, QPushButton, \
    QListView, QAction, QMenu, QMessageBox, QSizePolicy
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtCore import QAbstractListModel

from app.editor.custom_gui import EditDialog
from app import utilities

class DatabaseDialog(EditDialog):
    def __init__(self, data, title, right_frame, deletion_msg, creation_func, collection_model, parent):
        super().__init__(data, parent)
        self.window = parent
        self.title = title

        self.setWindowTitle('%s Editor' % self.title)
        self.setStyleSheet("font: 10pt;")

        self.left_frame = Collection(deletion_msg, creation_func, collection_model, self)
        self.right_frame = right_frame(self)
        self.left_frame.set_display(self.right_frame)

        self.grid.addWidget(self.left_frame, 0, 0)
        self.grid.addWidget(self.right_frame, 0, 1)

    def update_list(self):
        self.left_frame.update_list()

    @classmethod
    def edit(cls, parent=None):
        dialog = cls.create(parent)
        dialog.exec_()

class Collection(QWidget):
    def __init__(self, deletion_msg, creation_func, collection_model, parent):
        super().__init__(parent)
        self.window = parent
        self.database_editor = self.window.window

        self._data = self.window._data
        self.title = self.window.title
        self.creation_func = creation_func
        
        self.display = None

        grid = QGridLayout()
        self.setLayout(grid)

        self.view = RightClickListView(deletion_msg, self)
        self.view.currentChanged = self.on_item_changed

        self.model = collection_model(self._data, self)
        self.view.setModel(self.model)

        self.view.setIconSize(QSize(32, 32))

        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)

        self.button = QPushButton("Create %s" % self.title)
        self.button.clicked.connect(self.create_new)

        grid.addWidget(self.view, 0, 0)
        grid.addWidget(self.button, 1, 0)

    def create_new(self):
        nids = [d.nid for d in self._data]
        nid = name = utilities.get_next_name("New " + self.title, nids)
        self.creation_func(nid, name)
        self.model.dataChanged.emit(self.model.index(0), self.model.index(self.model.rowCount()))
        last_index = self.model.index(self.model.rowCount() - 1)
        self.view.setCurrentIndex(last_index)

    def on_item_changed(self, curr, prev):
        if self._data:
            new_data = self._data[curr.row()]
            if self.display:
                self.display.set_current(new_data)

    def set_display(self, disp):
        self.display = disp
        first_index = self.model.index(0)
        self.view.setCurrentIndex(first_index)

    def update_list(self):
        self.model.dataChanged.emit(self.model.index(0), self.model.index(self.model.rowCount()))                

class CollectionModel(QAbstractListModel):
    def __init__(self, data, window):
        super().__init__(window)
        self._data = data
        self.window = window

    def rowCount(self, parent=None):
        return len(self._data)

    def data(self, index, role):
        raise NotImplementedError

    def delete(self, idx):
        self._data.pop(idx)
        self.layoutChanged.emit()
        new_weapon = self._data[min(idx, len(self._data) - 1)]
        if self.window.display:
            self.window.display.set_current(new_weapon)

class RightClickListView(QListView):
    def __init__(self, msg, parent):
        super().__init__(parent)
        self.window = parent
        self.last_to_delete_msg = msg

        self.uniformItemSizes = True

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.customMenuRequested)

    def customMenuRequested(self, pos):
        idx = self.indexAt(pos).row()

        delete_action = QAction("Delete", self, triggered=lambda: self.delete(idx))
        menu = QMenu(self)
        menu.addAction(delete_action)

        menu.popup(self.viewport().mapToGlobal(pos))

    def delete(self, idx):
        if self.window.model.rowCount() > 1 and self.window._data[idx].nid != 'Default':
            self.window.model.delete(idx)
        else:
            QMessageBox.critical(self.window, 'Error', self.last_to_delete_msg)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if event.key() == Qt.Key_Delete:
            self.delete(self.currentIndex().row())