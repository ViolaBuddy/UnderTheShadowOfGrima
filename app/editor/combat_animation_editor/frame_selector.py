import os

from PyQt5.QtWidgets import QHBoxLayout, QVBoxLayout, QListView, QDialog, \
    QPushButton, QFileDialog, QMessageBox, QGroupBox, QFormLayout, QSpinBox
from PyQt5.QtCore import Qt, QDir
from PyQt5.QtGui import QPixmap, QIcon, QImage, QPainter

from app.constants import WINWIDTH, WINHEIGHT

from app import utilities
from app.resources import combat_anims, combat_palettes
from app.resources.resources import RESOURCES

from app.editor.settings import MainSettingsController

from app.extensions.custom_gui import Dialog
from app.editor.base_database_gui import ResourceCollectionModel
from app.editor.icon_editor.icon_view import IconView
from app.editor.combat_animation_editor import combat_animation_imports, combat_animation_model
import app.editor.utilities as editor_utilities

class FrameModel(ResourceCollectionModel):
    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            frame = self._data[index.row()]
            text = frame.nid
            return text
        elif role == Qt.DecorationRole:
            frame = self._data[index.row()]
            im = combat_animation_model.palette_swap(frame.pixmap, self.window.current_palette_nid)
            pix = QPixmap.fromImage(im)
            return QIcon(pix)
        return None

class FrameSelector(Dialog):
    def __init__(self, combat_anim, weapon_anim, parent=None):
        super().__init__(parent)
        self.window = parent
        self.setWindowTitle("Animation Frames")
        self.settings = MainSettingsController()

        self.combat_anim = combat_anim
        self.weapon_anim = weapon_anim
        self.current_palette_nid = self.window.get_current_palette()
        # Get a reference to the color change function
        self.frames = weapon_anim.frames
        if self.frames:
            self.current = self.frames[0]
        else:
            self.current = None

        self.display = IconView(self)
        self.display.static_size = True
        self.display.setSceneRect(0, 0, WINWIDTH, WINHEIGHT)

        offset_section = QGroupBox(self)
        offset_section.setTitle("Offset")
        offset_layout = QFormLayout()
        self.x_box = QSpinBox()
        self.x_box.setValue(0)
        self.x_box.setRange(-WINWIDTH, WINWIDTH)
        self.x_box.valueChanged.connect(self.on_x_changed)
        offset_layout.addRow("X:", self.x_box)
        self.y_box = QSpinBox()
        self.y_box.setValue(0)
        self.y_box.setRange(-WINHEIGHT, WINHEIGHT)
        self.y_box.valueChanged.connect(self.on_y_changed)
        offset_layout.addRow("Y:", self.y_box)
        offset_section.setLayout(offset_layout)

        self.view = QListView(self)
        self.view.currentChanged = self.on_item_changed

        self.model = FrameModel(self.frames, self)
        self.view.setModel(self.model)

        self.delete_button = QPushButton("Delete Current Frame")
        self.delete_button.clicked.connect(self.delete_frame)
        self.add_button = QPushButton("Add Frames...")
        self.add_button.clicked.connect(self.import_frames)
        self.export_button = QPushButton("Export Frames...")
        self.export_button.clicked.connect(self.export_frames)

        layout = QVBoxLayout()
        main_layout = QHBoxLayout()
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.view)
        left_layout.addWidget(self.add_button)
        left_layout.addWidget(self.delete_button)
        left_layout.addWidget(self.export_button)
        right_layout = QVBoxLayout()
        right_layout.addWidget(self.display)
        right_layout.addWidget(offset_section)
        main_layout.addLayout(left_layout)
        main_layout.addLayout(right_layout)
        layout.addLayout(main_layout)
        layout.addWidget(self.buttonbox)
        self.setLayout(layout)

        self.set_current(self.current)

    def on_item_changed(self, curr, prev):
        if self.frames:
            new_data = curr.internalPointer()
            if not new_data:
                new_data = self.frames[curr.row()]
            self.set_current(new_data)

    def on_x_changed(self, val):
        self.current.offset = (val, self.current.offset[1])
        self.draw()

    def on_y_changed(self, val):
        self.current.offset = (self.current.offset[0], val)
        self.draw()

    def export_frames(self):
        starting_path = self.settings.get_last_open_path()
        fn_dir = QFileDialog.getExistingDirectory(
            self, "Export Frames", starting_path)
        if fn_dir:
            self.settings.set_last_open_path(fn_dir)
            self.export(fn_dir)
            QMessageBox.information(self, "Export Complete", "Export of frames complete!")

    def set_current(self, frame):
        self.current = frame
        if self.current:
            self.x_box.setValue(self.current.offset[0])
            self.y_box.setValue(self.current.offset[1])
            self.draw()

    def delete_frame(self):
        idx = self.frames.index(self.current.nid)
        new_idx = self.model.delete(idx)
        if new_idx:
            new_frame = self.frames[new_idx.row()]
            self.set_current(new_frame)

    def draw(self):
        base_image = QImage(WINWIDTH, WINHEIGHT, QImage.Format_ARGB32)
        base_image.fill(editor_utilities.qCOLORKEY)
        painter = QPainter()
        painter.begin(base_image)
        pixmap = self.current.pixmap
        im = combat_animation_model.palette_swap(pixmap, self.current_palette_nid)
        painter.drawImage(self.current.offset[0], self.current.offset[1], im)
        painter.end()
        self.display.set_image(QPixmap.fromImage(base_image))
        self.display.show_image()

    @classmethod
    def get(cls, combat_anim, weapon_anim, parent=None):
        dlg = cls(combat_anim, weapon_anim, parent)
        result = dlg.exec_()
        if result == QDialog.Accepted:
            return dlg.current, True
        else:
            return None, False

    def import_frames(self):
        starting_path = self.settings.get_last_open_path()
        fns, ok = QFileDialog.getOpenFileNames(self.window, "Select Frames", starting_path, "PNG Files (*.png);;All Files(*)")
        error = False
        if fns and ok:
            pixmaps = []
            crops = []
            nids = []
            # Get files and crop them to right size
            for fn in fns:
                if fn.endswith('.png'):
                    nid = os.path.split(fn)[-1][:-4]
                    nids.append(nid)
                    pix = QPixmap(fn)
                    x, y, width, height = editor_utilities.get_bbox(pix.toImage())
                    pix = pix.copy(x, y, width, height)
                    pixmaps.append(pix)
                    crops.append((x, y, width, height))
                elif not error:
                    error = True
                    QMessageBox.critical(self.window, "File Type Error!", "Frame must be PNG format!")

            # Now determine palette to use for ingestion
            all_palette_colors = editor_utilities.find_palette_from_multiple([pix.toImage() for pix in pixmaps])
            my_palette = None
            for palette_name, palette_nid in self.combat_anim.palettes:
                palette = RESOURCES.combat_palettes.get(palette_nid)
                if palette.is_similar(all_palette_colors):
                    my_palette = palette
                    break
            else:
                print("Generating new palette...")
                nid = utilities.get_next_name("New Palette", RESOURCES.combat_palettes.keys())
                my_palette = combat_palettes.Palette(nid)
                RESOURCES.combat_palettes.append(my_palette)
                self.combat_anim.palettes.append(["New Palette", my_palette.nid])
                my_palette.assign_colors(all_palette_colors)

            convert_dict = editor_utilities.get_color_conversion(my_palette)
            for idx, pixmap in enumerate(pixmaps):
                im = pix.toImage()
                im = editor_utilities.color_convert(im, convert_dict)
                pix = QPixmap.fromImage(im)
                nid = utilities.get_next_name(nids[idx], self.frames.keys())
                x, y, width, height = crops[idx]
                new_frame = combat_anims.Frame(nid, None, (x, y), pix)
                self.frames.append(new_frame)
                self.set_current(new_frame)

            combat_animation_imports.update_weapon_anim_full_image(self.weapon_anim)
            self.model.layoutChanged.emit()

            parent_dir = os.path.split(fns[-1])[0]
            self.settings.set_last_open_path(parent_dir)

    def export(self, fn_dir):
        index = {}
        for frame in self.frames:
            index[frame.nid] = (frame.rect, frame.offset)
            # Draw frame
            base_image = QImage(WINWIDTH, WINHEIGHT, QImage.Format_ARGB32)
            base_image.fill(editor_utilities.qCOLORKEY)
            painter = QPainter()
            painter.begin(base_image)
            pixmap = frame.pixmap
            im = combat_animation_model.palette_swap(pixmap, self.current_palette_nid)
            painter.drawImage(frame.offset[0], frame.offset[1], im)
            painter.end()
            path = os.path.join(fn_dir, '%s.png' % frame.nid)
            base_image.save(path)

        index_path = os.path.join(fn_dir, '%s-%s-Index.txt' % (self.combat_anim.nid, self.weapon_anim.nid))
        with open(index_path, 'w') as fn:
            frames = sorted(index.items())
            for frame in frames:
                nid, (rect, offset) = frame
                fn.write('%s;%d,%d;%d,%d;%d,%d\n' % (nid, *rect, *offset))
