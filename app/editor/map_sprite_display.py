from PyQt5.QtWidgets import QFileDialog, QWidget, QHBoxLayout, QVBoxLayout, QMessageBox, \
    QGridLayout, QPushButton, QSizePolicy, QFrame, QSplitter, QButtonGroup
from PyQt5.QtCore import Qt, QDir, QSettings
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QImage, QColor, QTransform

import os

from app.resources.map_sprites import MapSprite
from app.resources.resources import RESOURCES

from app.utilities.data import Data
from app.data.database import DB

from app.extensions.custom_gui import PropertyBox, ResourceListView, DeletionDialog

from app.editor.timer import TIMER
from app.editor.base_database_gui import DatabaseTab, ResourceCollectionModel
from app.editor.icon_display import IconView
import app.editor.utilities as editor_utilities

from app import utilities

class MapSpriteDisplay(DatabaseTab):
    @classmethod
    def create(cls, parent=None):
        data = RESOURCES.map_sprites
        title = "Map Sprite"
        right_frame = MapSpriteProperties
        collection_model = MapSpriteModel
        deletion_criteria = None

        dialog = cls(data, title, right_frame, deletion_criteria,
                     collection_model, parent, button_text="Add New %s...",
                     view_type=ResourceListView)
        return dialog

def get_basic_icon(pixmap, num, active=False, team='player'):
    if active:
        one_frame = pixmap.copy(num*64 + 16, 96 + 16, 32, 32)
    else:
        one_frame = pixmap.copy(num*64 + 16, 0 + 16, 32, 32)
    # pixmap = pixmap.copy(16, 16, 32, 32)
    image = one_frame.toImage()
    one_frame = editor_utilities.convert_colorkey(image)
    if team == 'player':
        pass
    elif team == 'enemy':
        one_frame = editor_utilities.color_convert(one_frame, editor_utilities.enemy_colors)
    elif team == 'other':
        one_frame = editor_utilities.color_convert(one_frame, editor_utilities.other_colors)
    elif team == 'enemy2':
        one_frame = editor_utilities.color_convert(one_frame, editor_utilities.enemy2_colors)
    pixmap = QPixmap.fromImage(one_frame)
    return pixmap

class MapSpriteModel(ResourceCollectionModel):
    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            map_sprite = self._data[index.row()]
            text = map_sprite.nid
            return text
        elif role == Qt.DecorationRole:
            map_sprite = self._data[index.row()]
            if not map_sprite.standing_pixmap:
                map_sprite.standing_pixmap = QPixmap(map_sprite.stand_full_path)
            pixmap = map_sprite.standing_pixmap
            # num = TIMER.passive_counter.count
            num = 0
            pixmap = get_basic_icon(pixmap, num, index == self.window.view.currentIndex())
            if pixmap:
                return QIcon(pixmap)
        return None

    def create_new(self):
        settings = QSettings("rainlash", "Lex Talionis")
        starting_path = str(settings.value("last_open_path", QDir.currentPath()))
        nid = None
        stand_full_path, move_full_path = None, None
        standing_pix, moving_pix = None, None
        lion_throne_mode = True
        fn, sok = QFileDialog.getOpenFileName(self.window, "Choose Standing Map Sprite", starting_path)
        if sok:
            if fn.endswith('.png'):
                nid = os.path.split(fn)[-1][:-4]
                standing_pix = QPixmap(fn)
                nid = utilities.get_next_name(nid, [d.nid for d in RESOURCES.map_sprites])
                stand_full_path = fn
                if standing_pix.width() == 192 and standing_pix.height() == 144:
                    lion_throne_mode = True
                elif standing_pix.width() >= 16 and standing_pix.height() % 3 == 0:  # Try for GBA mode
                    lion_throne_mode = False
                else:   
                    QMessageBox.critical(self.window, "Error", "Standing Map Sprite is not correct size for Lion Throne import (192x144 px)")
                    return
            else:
                QMessageBox.critical(self.window, "Error", "Image must be PNG format")
                return
            parent_dir = os.path.split(fn)[0]
            settings.setValue("last_open_path", parent_dir)
        starting_path = str(settings.value("last_open_path", QDir.currentPath()))
        fn, mok = QFileDialog.getOpenFileName(self.window, "Choose Moving Map Sprite", starting_path)
        if mok:
            if fn.endswith('.png'):
                moving_pix = QPixmap(fn)
                move_full_path = fn
                if lion_throne_mode:
                    if moving_pix.width() == 192 and moving_pix.height() == 160:
                        pass
                    else:
                        QMessageBox.critical(self.window, "Error", "Moving Map Sprite is not correct size for Lion Throne import (192x160 px)")
                        return
                else:
                    if moving_pix.width() == 32 and moving_pix.height() == 32 * 15:
                        pass
                    else:
                        QMessageBox.critical(self.window, "Error", "Moving Map Sprite is not correct size for GBA import (32x480 px)")
                        return

            else:
                QMessageBox.critical(self.window, "Error", "Image must be png format")
                return
        if sok and mok and nid:
            if lion_throne_mode: 
                new_map_sprite = MapSprite(nid, stand_full_path, move_full_path, standing_pix, moving_pix)
            else:
                standing_pix, moving_pix = self.import_gba_map_sprite(standing_pix, moving_pix)
                new_map_sprite = MapSprite(nid, None, None, standing_pix, moving_pix)
            RESOURCES.map_sprites.append(new_map_sprite)
            parent_dir = os.path.split(fn)[0]
            settings.setValue("last_open_path", parent_dir)

    def delete(self, idx):
        # Check to see what is using me?
        res = self._data[idx]
        nid = res.nid
        affected_classes = [klass for klass in DB.classes if nid == klass.map_sprite_nid]
        if affected_classes:
            affected = Data(affected_classes)
            from app.editor.class_database import ClassModel
            model = ClassModel
            msg = "Deleting Map Sprite <b>%s</b> would affect these classes." % nid
            ok = DeletionDialog.inform(affected, model, msg, self.window)
            if ok:
                pass
            else:
                return
        # Delete watchers
        super().delete(idx)

    def nid_change_watchers(self, portrait, old_nid, new_nid):
        # What uses map sprites
        # Classes
        for klass in DB.classes:
            if klass.map_sprite_nid == old_nid:
                klass.map_sprite_nid = new_nid

    def import_gba_map_sprite(self, standing_pix, moving_pix):
        s_width = standing_pix.width()
        s_height = standing_pix.height()
        new_s = QPixmap(192, 144)
        new_s.fill(QColor(editor_utilities.qCOLORKEY))
        new_m = QPixmap(192, 160)
        new_m.fill(QColor(editor_utilities.qCOLORKEY))

        passive1 = standing_pix.copy(0, 0, s_width, s_height//3)
        passive2 = standing_pix.copy(0, s_height//3, s_width, s_height//3)
        passive3 = standing_pix.copy(0, 2*s_height//3, s_width, s_height//3)

        left1 = moving_pix.copy(0, 0, 32, 32)
        left2 = moving_pix.copy(0, 32, 32, 32)
        left3 = moving_pix.copy(0, 32*2, 32, 32)
        left4 = moving_pix.copy(0, 32*3, 32, 32)

        down1 = moving_pix.copy(0, 32*4, 32, 32)
        down2 = moving_pix.copy(0, 32*5, 32, 32)
        down3 = moving_pix.copy(0, 32*6, 32, 32)
        down4 = moving_pix.copy(0, 32*7, 32, 32)

        up1 = moving_pix.copy(0, 32*8, 32, 32)
        up2 = moving_pix.copy(0, 32*9, 32, 32)
        up3 = moving_pix.copy(0, 32*10, 32, 32)
        up4 = moving_pix.copy(0, 32*11, 32, 32)

        focus1 = moving_pix.copy(0, 32*12, 32, 32)
        focus2 = moving_pix.copy(0, 32*13, 32, 32)
        focus3 = moving_pix.copy(0, 32*14, 32, 32)

        if s_height//3 == 16:
            new_height = 24
        else:
            new_height = 8
        if s_width == 16:
            new_width = 24
        else:
            new_width = 16

        painter = QPainter()
        # Standing pixmap
        painter.begin(new_s)
        painter.drawPixmap(new_width, new_height, passive1)
        painter.drawPixmap(new_width + 64, new_height, passive2)
        painter.drawPixmap(new_width + 128, new_height, passive3)
        painter.drawPixmap(16, 8 + 96, focus1)
        painter.drawPixmap(16 + 64, 8 + 96, focus2)
        painter.drawPixmap(16 + 128, 8 + 96, focus3)
        painter.end()
        # Moving pixmap
        painter.begin(new_m)
        painter.drawPixmap(8, 8, down1)
        painter.drawPixmap(8 + 48, 8, down2)
        painter.drawPixmap(8 + 48 * 2, 8, down3)
        painter.drawPixmap(8 + 48 * 3, 8, down4)
        painter.drawPixmap(8, 48, left1)
        painter.drawPixmap(8 + 48, 48, left2)
        painter.drawPixmap(8 + 48 * 2, 48, left3)
        painter.drawPixmap(8 + 48 * 3, 48, left4)
        # Right direction pixmaps
        painter.drawPixmap(8, 88, left1.transformed(QTransform().scale(-1, 1)))
        painter.drawPixmap(8 + 48, 88, left2.transformed(QTransform().scale(-1, 1)))
        painter.drawPixmap(8 + 48 * 2, 88, left3.transformed(QTransform().scale(-1, 1)))
        painter.drawPixmap(8 + 48 * 3, 88, left4.transformed(QTransform().scale(-1, 1)))
        painter.drawPixmap(8, 128, up1)
        painter.drawPixmap(8 + 48, 128, up2)
        painter.drawPixmap(8 + 48 * 2, 128, up3)
        painter.drawPixmap(8 + 48 * 3, 128, up4)
        painter.end()

        return new_s, new_m

class MapSpriteProperties(QWidget):
    standing_width, standing_height = 192, 144
    moving_width, moving_height = 192, 160

    def __init__(self, parent, current=None):
        QWidget.__init__(self, parent)
        self.window = parent
        self._data = self.window._data
        self.resource_editor = self.window.window

        # Populate resources
        for resource in self._data:
            if resource.stand_full_path:
                resource.standing_pixmap = QPixmap(resource.stand_full_path)
            if resource.move_full_path:
                resource.moving_pixmap = QPixmap(resource.move_full_path)

        self.current = current

        left_section = QHBoxLayout()

        self.frame_view = IconView(self)
        left_section.addWidget(self.frame_view)

        right_section = QVBoxLayout()

        button_section = QGridLayout()
        self.up_arrow = QPushButton(self)
        self.left_arrow = QPushButton(self)
        self.right_arrow = QPushButton(self)
        self.down_arrow = QPushButton(self)
        self.focus = QPushButton(self)
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(False)
        self.button_group.buttonPressed.connect(self.button_clicked)
        self.buttons = [self.up_arrow, self.left_arrow, self.right_arrow, self.down_arrow, self.focus]
        positions = [(0, 1), (1, 0), (1, 2), (2, 1), (1, 1)]
        text = ["^", "<-", "->", "v", "O"]
        for idx, button in enumerate(self.buttons):
            button_section.addWidget(button, *positions[idx])
            button.setCheckable(True)
            button.setText(text[idx])
            button.setMaximumWidth(40)
            # button.clicked.connect(self.a_button_clicked)
            self.button_group.addButton(button)
            self.button_group.setId(button, idx)
        button_section.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        color_section = QGridLayout()
        self.current_color = 0
        self.player_button = QPushButton(self)
        self.enemy_button = QPushButton(self)
        self.other_button = QPushButton(self)
        self.enemy2_button = QPushButton(self)
        self.button_group = QButtonGroup(self)
        self.button_group.buttonPressed.connect(self.color_clicked)
        self.colors = [self.player_button, self.enemy_button, self.other_button, self.enemy2_button]
        text = ["Player", "Enemy", "Other", "Enemy 2"]
        pos = [(0, 0), (1, 0), (0, 1), (1, 1)]
        for idx, button in enumerate(self.colors):
            color_section.addWidget(button, *pos[idx])
            button.setCheckable(True)
            button.setText(text[idx])
            self.button_group.addButton(button)
            self.button_group.setId(button, idx)
        self.player_button.setChecked(True)
        color_section.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

        right_section.addLayout(button_section)
        right_section.addLayout(color_section)

        left_frame = QFrame(self)
        left_frame.setLayout(left_section)
        right_frame = QFrame(self)
        right_frame.setLayout(right_section)

        top_splitter = QSplitter(self)
        top_splitter.setChildrenCollapsible(False)
        top_splitter.addWidget(left_frame)
        top_splitter.addWidget(right_frame)

        self.raw_view = PropertyBox("Raw Sprite", IconView, self)
        self.raw_view.edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        final_splitter = QSplitter(self)
        final_splitter.setOrientation(Qt.Vertical)
        final_splitter.setChildrenCollapsible(False)
        final_splitter.addWidget(top_splitter)
        final_splitter.addWidget(self.raw_view)

        final_section = QHBoxLayout()
        self.setLayout(final_section)
        final_section.addWidget(final_splitter)

        TIMER.tick_elapsed.connect(self.tick)

    def set_current(self, current):
        self.current = current
        # Painting
        base_image = QImage(self.standing_width + self.moving_width, 
                            max(self.standing_height, self.moving_height),
                            QImage.Format_ARGB32)
        base_image.fill(QColor(0, 0, 0, 0))
        painter = QPainter()
        painter.begin(base_image)
        if self.current.standing_pixmap:
            painter.drawImage(0, 8, self.current.standing_pixmap.toImage())
        if self.current.moving_pixmap:
            painter.drawImage(self.standing_width, 0, self.current.moving_pixmap.toImage())
        painter.end()

        self.raw_view.edit.set_image(QPixmap.fromImage(base_image))
        self.raw_view.edit.show_image()

        if self.current:
            self.draw_frame()

    def tick(self):
        # self.window.update_list()
        if self.current:
            self.draw_frame()

    def draw_frame(self):
        if self.left_arrow.isChecked():
            num = TIMER.active_counter.count
            frame = self.current.moving_pixmap.copy(num*48, 40, 48, 40)
        elif self.right_arrow.isChecked():
            num = TIMER.active_counter.count
            frame = self.current.moving_pixmap.copy(num*48, 80, 48, 40)
        elif self.up_arrow.isChecked():
            num = TIMER.active_counter.count
            frame = self.current.moving_pixmap.copy(num*48, 120, 48, 40)
        elif self.down_arrow.isChecked():
            num = TIMER.active_counter.count
            frame = self.current.moving_pixmap.copy(num*48, 0, 48, 40)
        elif self.focus.isChecked():
            num = TIMER.passive_counter.count
            frame = self.current.standing_pixmap.copy(num*64, 96, 64, 48)
        else:
            num = TIMER.passive_counter.count
            frame = self.current.standing_pixmap.copy(num*64, 0, 64, 48)
        frame = frame.toImage()
        frame = editor_utilities.convert_colorkey(frame)
        if self.current_color == 0:
            pass
        elif self.current_color == 1:
            frame = editor_utilities.color_convert(frame, editor_utilities.enemy_colors)
        elif self.current_color == 2:
            frame = editor_utilities.color_convert(frame, editor_utilities.other_colors)
        elif self.current_color == 3:
            frame = editor_utilities.color_convert(frame, editor_utilities.enemy2_colors)
        frame = QPixmap.fromImage(frame)
        self.frame_view.set_image(frame)
        self.frame_view.show_image()

    def button_clicked(self, spec_button):
        """
        Needs to first uncheck all buttons, then, set
        the specific button to its correct state
        """
        checked = spec_button.isChecked()
        for button in self.buttons:
            button.setChecked(False)
        spec_button.setChecked(checked)
        self.draw_frame()

    def color_clicked(self, spec_button):
        self.current_color = self.colors.index(spec_button)
        self.draw_frame()
