from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QLineEdit, \
    QMessageBox, QSpinBox, QHBoxLayout, QPushButton, \
    QDialog, QVBoxLayout, QSizePolicy, QSpacerItem, QComboBox
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QIcon

from app.data.resources import RESOURCES
from app.data.data import Data
from app.data.database import DB
import app.data.item_components as IC

from app.extensions.custom_gui import PropertyBox, QHLine, QVLine, ComboBox, DeletionDialog
from app.editor.custom_widgets import ItemBox
from app.editor.base_database_gui import DatabaseTab, DragDropCollectionModel
from app.editor.equation_widget import EquationDialog
from app.editor.icons import ItemIcon16
from app.editor.multi_combo_box_list import MultiComboBoxListWithCheckbox
from app.editor import component_database
import app.editor.utilities as editor_utilities
from app import utilities

class ItemDatabase(DatabaseTab):
    @classmethod
    def create(cls, parent=None):
        data = DB.items
        title = "Item"
        right_frame = ItemProperties
        deletion_criteria = None
        collection_model = ItemModel
        dialog = cls(data, title, right_frame, deletion_criteria, collection_model, parent)
        return dialog

def get_pixmap(item):
    x, y = item.icon_index
    res = RESOURCES.icons16.get(item.icon_nid)
    if not res:
        return None
    if not res.pixmap:
        res.pixmap = QPixmap(res.full_path)
    pixmap = res.pixmap.copy(x*16, y*16, 16, 16)
    pixmap = QPixmap.fromImage(editor_utilities.convert_colorkey(pixmap.toImage()))
    return pixmap

class ItemModel(DragDropCollectionModel):
    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            item = self._data[index.row()]
            text = item.nid
            return text
        elif role == Qt.DecorationRole:
            item = self._data[index.row()]
            pix = get_pixmap(item)
            if pix:
                pix = pix.scaled(32, 32)
                return QIcon(pix)
        return None

    def delete(self, idx):
        # Check to make sure nothing else is using me!!!
        item = self._data[idx]
        nid = item.nid
        affected_units = [unit for unit in DB.units if nid in unit.get_items()]
        affected_levels = [level for level in DB.levels if any(nid in unit.get_items() for unit in level.units)]
        if affected_units or affected_levels:
            if affected_units:
                affected = Data(affected_units)
                from app.editor.unit_database import UnitModel
                model = UnitModel
            elif affected_levels:
                affected = Data(affected_levels)
                from app.editor.level_menu import LevelModel
                model = LevelModel
            msg = "Deleting Item <b>%s</b> would affect these objects." % nid
            swap, ok = DeletionDialog.get_swap(affected, model, msg, ItemBox(self.window, exclude=item), self.window)
            if ok:
                self.change_nid(swap.nid, nid)
            else:
                return
        # Delete watchers
        super().delete(idx)

    def change_nid(self, old_nid, new_nid):
        for unit in DB.units:
            unit.replace_item_nid(old_nid, new_nid)
        for level in DB.levels:
            for unit in level.units:
                unit.replace_item_nid(old_nid, new_nid)

    def create_new(self):
        nids = [d.nid for d in self._data]
        nid = name = utilities.get_next_name("New Item", nids)
        DB.create_new_item(nid, name)

class ItemProperties(QWidget):
    def __init__(self, parent, current=None):
        super().__init__(parent)
        self.window = parent
        self.model = self.window.left_frame.model
        self._data = self.window._data
        self.database_editor = self.window.window
        self.main_editor = self.database_editor.window

        self.current = current

        top_section = QHBoxLayout()

        self.icon_edit = ItemIcon16(self)
        top_section.addWidget(self.icon_edit)

        horiz_spacer = QSpacerItem(40, 10, QSizePolicy.Fixed, QSizePolicy.Fixed)
        top_section.addSpacerItem(horiz_spacer)

        name_section = QVBoxLayout()

        self.nid_box = PropertyBox("Unique ID", QLineEdit, self)
        self.nid_box.edit.textChanged.connect(self.nid_changed)
        self.nid_box.edit.editingFinished.connect(self.nid_done_editing)
        name_section.addWidget(self.nid_box)

        self.name_box = PropertyBox("Display Name", QLineEdit, self)
        self.name_box.edit.setMaxLength(13)
        self.name_box.edit.textChanged.connect(self.name_changed)
        name_section.addWidget(self.name_box)

        top_section.addLayout(name_section)

        main_section = QGridLayout()

        self.desc_box = PropertyBox("Description", QLineEdit, self)
        self.desc_box.edit.textChanged.connect(self.desc_changed)
        main_section.addWidget(self.desc_box, 0, 0, 1, 3)

        self.total_value_box = PropertyBox("Total Value", QSpinBox, self)
        self.total_value_box.edit.setKeyboardTracking(False)
        self.total_value_box.edit.setMaximum(100000000)
        self.total_value_box.edit.setAlignment(Qt.AlignRight)
        self.total_value_box.edit.valueChanged.connect(self.total_value_changed)
        main_section.addWidget(self.total_value_box, 1, 0)

        self.value_per_use_box = PropertyBox("Value per use", QSpinBox, self)
        self.value_per_use_box.edit.setKeyboardTracking(False)
        self.value_per_use_box.edit.setMaximum(1000000)
        self.value_per_use_box.edit.setAlignment(Qt.AlignRight)
        self.value_per_use_box.edit.valueChanged.connect(self.value_per_use_changed)
        main_section.addWidget(self.value_per_use_box, 1, 1)

        self.min_range_box = PropertyBox("Minimum Range", ComboBox, self)
        self.min_range_box.edit.setEditable(True)
        self.min_range_box.edit.setInsertPolicy(QComboBox.NoInsert)
        self.min_range_box.edit.addItems(DB.equations.keys())
        # self.min_range_box.edit.currentTextChanged.connect(self.min_range_changed)
        self.min_range_box.edit.lineEdit().editingFinished.connect(self.check_min_range)
        main_section.addWidget(self.min_range_box, 1, 2)

        self.min_range_box.add_button(QPushButton('...'))
        self.min_range_box.button.setMaximumWidth(40)
        self.min_range_box.button.clicked.connect(self.access_equations)

        self.max_range_box = PropertyBox("Maximum Range", ComboBox, self)
        self.max_range_box.edit.setEditable(True)
        self.max_range_box.edit.setInsertPolicy(QComboBox.NoInsert)
        self.max_range_box.edit.addItems(DB.equations.keys())
        # self.max_range_box.edit.currentTextChanged.connect(self.max_range_changed)
        self.max_range_box.edit.lineEdit().editingFinished.connect(self.check_max_range)
        main_section.addWidget(self.max_range_box, 1, 3)

        self.max_range_box.add_button(QPushButton('...'))
        self.max_range_box.button.setMaximumWidth(40)
        self.max_range_box.button.clicked.connect(self.access_equations)

        component_section = QGridLayout()
        component_label = QLabel("Components")
        component_label.setAlignment(Qt.AlignBottom)
        component_section.addWidget(component_label, 0, 0, Qt.AlignBottom)

        self.add_component_button = QPushButton("Add Components...")
        self.add_component_button.clicked.connect(self.add_components)
        component_section.addWidget(self.add_component_button, 0, 1)

        self.component_list = component_database.ComponentList(self)
        component_section.addWidget(self.component_list, 1, 0, 1, 2)
        self.component_list.order_swapped.connect(self.component_moved)

        total_section = QVBoxLayout()
        self.setLayout(total_section)
        total_section.addLayout(top_section)
        total_section.addLayout(main_section)
        h_line = QHLine()
        total_section.addWidget(h_line)
        total_section.addLayout(component_section)

    def nid_changed(self, text):
        # Also change name if they are identical
        if self.current.name == self.current.nid:
            self.name_box.edit.setText(text)
        self.current.nid = text
        self.window.update_list()

    def nid_done_editing(self):
        # Check validity of nid!
        other_nids = [d.nid for d in self._data.values() if d is not self.current]
        if self.current.nid in other_nids:
            QMessageBox.warning(self.window, 'Warning', 'Item Type ID %s already in use' % self.current.nid)
            self.current.nid = utilities.get_next_name(self.current.nid, other_nids)
        self.model.change_nid(self._data.find_key(self.current), self.current.nid)
        self._data.update_nid(self.current, self.current.nid)
        self.window.update_list()

    def name_changed(self, text):
        self.current.name = text
        self.window.update_list()

    def total_value_changed(self, val):
        val = int(val)
        if 'uses' in [c.nid for c in self.current.components]:
            num_uses = self.current.components.get('uses').value
            new_value_per_use = val // num_uses
            old_total_value = self.total_value_box.edit.value()
            new_total_value = new_value_per_use * num_uses
            if val % num_uses != 0 and old_total_value > new_total_value:
                new_value_per_use += 1  # Try making it one bigger
            self.current.value = new_total_value
            self.value_per_use_box.edit.setValue(new_value_per_use)
            self.total_value_box.edit.setValue(self.current.value)
        else:
            self.value_per_use_box.edit.setValue(val)

    def value_per_use_changed(self, val):
        val = int(val)
        if 'uses' in [c.nid for c in self.current.components]:
            num_uses = self.current.components.get('uses').value
            self.current.value = val * num_uses
            self.total_value_box.edit.setValue(self.current.value)
        else:
            self.current.value = val
            self.total_value_box.edit.setValue(val)

    def update_value_boxes(self):
        # print("Updating Value Boxes", flush=True)
        old_value = self.current.value
        self.total_value_box.edit.setValue(0)  # Force a change
        self.total_value_box.edit.setValue(old_value)

    def desc_changed(self, text):
        self.current.desc = text

    def check_min_range(self):
        min_val = self.min_range_box.edit.currentText()
        self.current.min_range = min_val
        max_val = self.max_range_box.edit.currentText()
        # Max range can't be lower than min range
        if utilities.is_int(min_val) and utilities.is_int(max_val):
            if min_val > max_val:
                self.max_range_box.edit.setEditText(str(min_val))

    def check_max_range(self):
        max_val = self.max_range_box.edit.currentText()
        self.current.max_range = max_val
        min_val = self.min_range_box.edit.currentText()
        # Min range can't be higher than max range
        if utilities.is_int(min_val) and utilities.is_int(max_val):
            if max_val < min_val:
                self.min_range_box.edit.setEditText(str(max_val))

    def min_range_changed(self, val):
        self.current.min_range = val

    def max_range_changed(self, val):
        self.current.max_range = val

    def access_equations(self):
        dlg = EquationDialog.create()
        result = dlg.exec_()
        if result == QDialog.Accepted:
            # current_min = self.min_range_box.edit.currentText()
            # current_max = self.max_range_box.edit.currentText()
            self.min_range_box.edit.clear()
            self.min_range_box.edit.addItems(DB.equations.keys())
            self.max_range_box.edit.clear()
            self.max_range_box.edit.addItems(DB.equations.keys())
            self.set_current(self.current)
            # self.min_range_box.edit.setEditText(current_min)
            # self.max_range_box.edit.setEditText(current_max)
        else:
            pass

    def add_component(self, component):
        self.add_component_widget(component)
        self.current.components.append(component)
        self.update_value_boxes()

    def add_component_widget(self, component):
        c = component_database.get_display_widget(component, self)
        self.component_list.add_component(c)

    def remove_component(self, component_widget):
        data = component_widget._data
        self.component_list.remove_component(component_widget)
        self.current.components.delete(data)
        self.update_value_boxes()

    def component_moved(self, start, end):
        self.current.components.move_index(start, end)

    def set_current(self, current):
        self.current = current
        self.nid_box.edit.setText(current.nid)
        self.name_box.edit.setText(current.name)
        self.desc_box.edit.setText(current.desc)
        if utilities.is_int(current.min_range):
            self.min_range_box.edit.setEditText(current.min_range)
        else:
            self.min_range_box.edit.setValue(current.min_range)
        if utilities.is_int(current.max_range):
            self.max_range_box.edit.setEditText(current.max_range)
        else:
            self.max_range_box.edit.setValue(current.max_range)
        self.icon_edit.set_current(current.icon_nid, current.icon_index)
        self.component_list.clear()
        for component in current.components.values():
            self.add_component_widget(component)

        self.total_value_box.edit.setValue(current.value)

    def add_components(self):
        dlg = component_database.ComponentDialog(IC.item_components, "Item Components", self)
        result = dlg.exec_()
        if result == QDialog.Accepted:
            checked = dlg.get_checked()
            for nid in checked:
                c = IC.get_component(nid)
                self.add_component(c)
        else:
            pass

class ItemListWidget(QWidget):
    items_updated = pyqtSignal()

    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.window = parent
        
        self.item_list = MultiComboBoxListWithCheckbox(DB.items, get_pixmap, self)
        self.item_list.item_changed.connect(self.activate)

        self.layout = QGridLayout(self)
        self.layout.setSpacing(0)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.addWidget(self.item_list, 3, 0, 1, 2)
        self.setLayout(self.layout)

        label = QLabel(title)
        label.setAlignment(Qt.AlignBottom)
        self.layout.addWidget(label, 0, 0)

        header1 = QLabel("Item ID")
        header1.setAlignment(Qt.AlignBottom | Qt.AlignLeft)
        self.layout.addWidget(header1, 2, 0)

        header2 = QLabel("Droppable")
        header2.setAlignment(Qt.AlignBottom | Qt.AlignRight)
        self.layout.addWidget(header2, 2, 1)

        hline = QHLine()
        self.layout.addWidget(hline, 1, 0, 1, 2)

        hbox = QHBoxLayout()
        hbox.setSpacing(0)
        hbox.setContentsMargins(0, 0, 0, 0)

        add_button = QPushButton("+")
        add_button.setMaximumWidth(30)
        add_button.clicked.connect(self.add_new_item)

        remove_button = QPushButton("-")
        remove_button.setMaximumWidth(30)
        remove_button.clicked.connect(self.remove_last_item)

        hbox.addWidget(remove_button, alignment=Qt.AlignRight)
        hbox.addWidget(add_button, alignment=Qt.AlignRight)

        self.layout.addLayout(hbox, 0, 1, alignment=Qt.AlignRight)

    def set_current(self, items):
        self.item_list.set_current(items)

    def add_new_item(self):
        new_item = DB.items[0].nid
        self.item_list.add_item(new_item)
        self.activate()

    def remove_last_item(self):
        self.item_list.remove_item_at_index(self.item_list.length() - 1)
        self.activate()

    def activate(self):
        self.items_updated.emit()

    def get_items(self):
        return self.item_list.index_list[:]

    def set_color(self, color_list):
        self.item_list.set_color(color_list)


# Testing
# Run "python -m app.editor.item_database" from main directory
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = ItemDatabase.create()
    window.show()
    app.exec_()
