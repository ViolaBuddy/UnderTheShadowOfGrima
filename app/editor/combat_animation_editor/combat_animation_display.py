import time, os, glob
import json
import pickle

from PyQt5.QtWidgets import QSplitter, QFrame, QVBoxLayout, \
    QWidget, QGroupBox, QFormLayout, QSpinBox, QFileDialog, \
    QMessageBox, QStyle, QHBoxLayout, QPushButton, QLineEdit, \
    QLabel, QToolButton, QInputDialog
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, QIcon, QPainter

from app.constants import WINWIDTH, WINHEIGHT
from app.resources import combat_anims, combat_palettes
from app.resources.resources import RESOURCES
from app.data.database import DB

from app.editor.settings import MainSettingsController

from app.editor import timer
from app.editor.icon_editor.icon_view import IconView
from app.editor.combat_animation_editor.palette_menu import PaletteMenu
from app.editor.combat_animation_editor.timeline_menu import TimelineMenu
from app.editor.combat_animation_editor.frame_selector import FrameSelector
from app.editor.combat_animation_editor.combat_animation_model import palette_swap
import app.editor.combat_animation_editor.combat_animation_imports as combat_animation_imports
from app.extensions.custom_gui import ComboBox

import app.editor.utilities as editor_utilities
from app.utilities import str_utils

# Game interface
import app.editor.game_actions.game_actions as GAME_ACTIONS

def populate_anim_pixmaps(combat_anim):
    for weapon_anim in combat_anim.weapon_anims:
        weapon_anim.pixmap = QPixmap(weapon_anim.full_path)
        for frame in weapon_anim.frames:
            x, y, width, height = frame.rect
            frame.pixmap = weapon_anim.pixmap.copy(x, y, width, height)

class CombatAnimProperties(QWidget):
    def __init__(self, parent, current=None):
        QWidget.__init__(self, parent)
        self.window = parent
        self._data = self.window._data

        # Populate resources
        for combat_anim in self._data:
            populate_anim_pixmaps(combat_anim)

        self.control_setup(current)

        self.info_form = QFormLayout()

        self.nid_box = QLineEdit()
        self.nid_box.textChanged.connect(self.nid_changed)
        self.nid_box.editingFinished.connect(self.nid_done_editing)

        self.settings = MainSettingsController()
        theme = self.settings.get_theme(0)
        if theme == 0:
            icon_folder = 'icons/icons'
        else:
            icon_folder = 'icons/dark_icons'

        weapon_row = self.weapon_box(icon_folder)
        pose_row = self.pose_box(icon_folder)

        self.info_form.addRow("Unique ID", self.nid_box)
        self.info_form.addRow("Weapon", weapon_row)
        self.info_form.addRow("Pose", pose_row)

        self.build_frames()
        self.set_layout()

    def save_state(self) -> str:
        return [self.main_splitter.saveState(), self.right_splitter.saveState()]

    def restore_state(self, state):
        self.main_splitter.restoreState(state[0])
        self.right_splitter.restoreState(state[1])

    def control_setup(self, current):
        self.current = current
        self.playing = False
        self.paused = False
        self.loop = False

        self.last_update = 0
        self.next_update = 0
        self.num_frames = 0
        self.processing = False
        self.frame_nid = None
        self.over_frame_nid = None
        self.under_frame_nid = None
        self.custom_frame_offset = None

        self.anim_view = IconView(self)
        self.anim_view.static_size = True
        self.anim_view.setSceneRect(0, 0, WINWIDTH, WINHEIGHT)

        self.palette_menu = PaletteMenu(self)
        self.timeline_menu = TimelineMenu(self)

        self.view_section = QVBoxLayout()

        self.button_section = QHBoxLayout()
        self.button_section.setAlignment(Qt.AlignTop)

        self.play_button = QToolButton(self)
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.play_button.clicked.connect(self.play_clicked)

        self.stop_button = QToolButton(self)
        self.stop_button.setIcon(self.style().standardIcon(QStyle.SP_MediaStop))
        self.stop_button.clicked.connect(self.stop_clicked)

        self.loop_button = QToolButton(self)
        self.loop_button.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.loop_button.clicked.connect(self.loop_clicked)
        self.loop_button.setCheckable(True)

        self.export_button = QToolButton(self)
        self.export_button.setIcon(self.style().standardIcon(QStyle.SP_DirLinkIcon))
        self.export_button.clicked.connect(self.export_clicked)
        self.export_button.setToolTip("Export Animation as PNGs...")

        self.test_combat_button = QToolButton(self)
        self.test_combat_button.setIcon(QIcon('favicon.ico'))
        self.test_combat_button.clicked.connect(self.test_combat)
        self.test_combat_button.setToolTip("Display Animation in Engine")

        label = QLabel("FPS ")
        label.setAlignment(Qt.AlignRight)

        self.speed_box = QSpinBox(self)
        self.speed_box.setValue(60)
        self.speed_box.setRange(1, 240)
        self.speed_box.valueChanged.connect(self.speed_changed)

        self.button_section.addWidget(self.play_button)
        self.button_section.addWidget(self.stop_button)
        self.button_section.addWidget(self.loop_button)
        self.button_section.addWidget(self.export_button)
        self.button_section.addWidget(self.test_combat_button)
        self.button_section.addSpacing(40)
        self.button_section.addWidget(label, Qt.AlignRight)
        self.button_section.addWidget(self.speed_box, Qt.AlignRight)

    def weapon_box(self, icon_folder):
        weapon_row = QHBoxLayout()
        self.weapon_box = ComboBox()
        self.weapon_box.currentIndexChanged.connect(self.weapon_changed)
        self.new_weapon_button = QPushButton("+")
        self.new_weapon_button.setMaximumWidth(30)
        self.new_weapon_button.clicked.connect(self.add_new_weapon)
        self.delete_weapon_button = QPushButton()
        self.delete_weapon_button.setMaximumWidth(30)
        self.delete_weapon_button.setIcon(QIcon(f"{icon_folder}/x.png"))
        self.delete_weapon_button.clicked.connect(self.delete_weapon)
        self.duplicate_weapon_button = QPushButton()
        self.duplicate_weapon_button.setMaximumWidth(30)
        self.duplicate_weapon_button.setIcon(QIcon(f"{icon_folder}/duplicate.png"))
        self.duplicate_weapon_button.clicked.connect(self.duplicate_weapon)
        weapon_row.addWidget(self.weapon_box)
        weapon_row.addWidget(self.new_weapon_button)
        weapon_row.addWidget(self.duplicate_weapon_button)
        weapon_row.addWidget(self.delete_weapon_button)
        return weapon_row

    def pose_box(self, icon_folder):
        pose_row = QHBoxLayout()
        self.pose_box = ComboBox()
        self.pose_box.currentIndexChanged.connect(self.pose_changed)
        self.new_pose_button = QPushButton("+")
        self.new_pose_button.setMaximumWidth(30)
        self.new_pose_button.clicked.connect(self.add_new_pose)
        self.delete_pose_button = QPushButton()
        self.delete_pose_button.setMaximumWidth(30)
        self.delete_pose_button.setIcon(QIcon(f"{icon_folder}/x.png"))
        self.delete_pose_button.clicked.connect(self.delete_pose)
        self.duplicate_pose_button = QPushButton()
        self.duplicate_pose_button.setMaximumWidth(30)
        self.duplicate_pose_button.setIcon(QIcon(f"{icon_folder}/duplicate.png"))
        self.duplicate_pose_button.clicked.connect(self.duplicate_pose)
        pose_row.addWidget(self.pose_box)
        pose_row.addWidget(self.new_pose_button)
        pose_row.addWidget(self.duplicate_pose_button)
        pose_row.addWidget(self.delete_pose_button)
        return pose_row

    def build_frames(self):
        self.frame_group_box = QGroupBox()
        self.frame_group_box.setTitle("Image Frames")
        frame_layout = QVBoxLayout()
        self.frame_group_box.setLayout(frame_layout)
        self.import_from_lt_button = QPushButton("Import Legacy Weapon Animation...")
        self.import_from_lt_button.clicked.connect(self.import_legacy)
        self.import_from_gba_button = QPushButton("Import GBA Weapon Animation...")
        self.import_from_gba_button.clicked.connect(self.import_gba)
        self.import_png_button = QPushButton("View Frames...")
        self.import_png_button.clicked.connect(self.select_frame)

        self.import_anim_button = QPushButton("Import...")
        self.import_anim_button.clicked.connect(self.import_anim)
        self.export_anim_button = QPushButton("Export...")
        self.export_anim_button.clicked.connect(self.export_anim)

        self.window.left_frame.layout().addWidget(self.import_anim_button, 3, 0)
        self.window.left_frame.layout().addWidget(self.export_anim_button, 3, 1)
        frame_layout.addWidget(self.import_from_lt_button)
        frame_layout.addWidget(self.import_from_gba_button)
        frame_layout.addWidget(self.import_png_button)

    def set_layout(self):
        self.view_section.addWidget(self.anim_view)
        self.view_section.addLayout(self.button_section)
        self.view_section.addLayout(self.info_form)
        self.view_section.addWidget(self.frame_group_box)

        view_frame = QFrame()
        view_frame.setLayout(self.view_section)

        self.main_splitter = QSplitter(self)
        self.main_splitter.setChildrenCollapsible(False)

        self.right_splitter = QSplitter(self)
        self.right_splitter.setOrientation(Qt.Vertical)
        self.right_splitter.setChildrenCollapsible(False)
        self.right_splitter.addWidget(self.palette_menu)
        self.right_splitter.addWidget(self.timeline_menu)

        self.main_splitter.addWidget(view_frame)
        self.main_splitter.addWidget(self.right_splitter)

        final_section = QHBoxLayout()
        self.setLayout(final_section)
        final_section.addWidget(self.main_splitter)

        timer.get_timer().tick_elapsed.connect(self.tick)

    def tick(self):
        self.draw_frame()

    def play(self):
        self.playing = True
        self.paused = False
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))

    def pause(self):
        self.playing = False
        self.paused = True
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    def stop(self):
        self.playing = False
        self.paused = False
        self.play_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    def play_clicked(self):
        if self.playing:
            self.pause()
        else:
            self.play()

    def stop_clicked(self):
        self.stop()

    def loop_clicked(self, val):
        if val:
            self.loop = True
        else:
            self.loop = False

    def speed_changed(self, val):
        pass

    def export_clicked(self):
        if self.current:
            starting_path = self.settings.get_last_open_path()
            fn_dir = QFileDialog.getExistingDirectory(
                self, "Export Current Animation", starting_path)
            if fn_dir:
                self.settings.set_last_open_path(fn_dir)
                self.export_all_frames(fn_dir)
                QMessageBox.information(self, "Export Complete", "Export of frames complete!")

    def nid_changed(self, text):
        self.current.nid = text
        self.window.update_list()

    def nid_done_editing(self):
        other_nids = [d.nid for d in self._data if d is not self.current]
        if self.current.nid in other_nids:
            QMessageBox.warning(self.window, 'Warning', 'ID %s already in use' % self.current.nid)
            self.current.nid = str_utils.get_next_name(self.current.nid, other_nids)
        self.on_nid_changed(self._data.find_key(self.current), self.current.nid)
        self._data.update_nid(self.current, self.current.nid)
        self.window.update_list()

    def on_nid_changed(self, old_nid, new_nid):
        for klass in DB.classes:
            if klass.combat_anim_nid == old_nid:
                klass.combat_anim_nid = new_nid

    def ask_permission(self, obj, text: str) -> bool:
        ret = QMessageBox.warning(self, "Deletion Warning", 
                                  "Really delete %s <b>%s</b>?" % (text, obj.nid),
                                  QMessageBox.Ok | QMessageBox.Cancel)
        if ret == QMessageBox.Ok:
            return True
        else:
            return False

    def has_weapon(self, b: bool):
        self.duplicate_weapon_button.setEnabled(b)
        self.delete_weapon_button.setEnabled(b)
        self.new_pose_button.setEnabled(b)

    def has_pose(self, b: bool):
        self.timeline_menu.setEnabled(b)
        self.duplicate_pose_button.setEnabled(b)
        self.delete_pose_button.setEnabled(b)
        self.export_button.setEnabled(b)
        self.test_combat_button.setEnabled(b)

    def weapon_changed(self, idx):
        weapon_nid = self.weapon_box.currentText()
        weapon_anim = self.current.weapon_anims.get(weapon_nid)
        if not weapon_anim:
            self.pose_box.clear()
            self.timeline_menu.clear()
            self.has_weapon(False)
            self.has_pose(False)
            return
        self.has_weapon(True)
        self.timeline_menu.set_current_frames(weapon_anim.frames)
        if weapon_anim.poses:
            poses = self.reset_pose_box(weapon_anim)
            current_pose_nid = self.pose_box.currentText()
            current_pose = poses.get(current_pose_nid)
            self.has_pose(True)
            self.timeline_menu.set_current_pose(current_pose)
        else:
            self.pose_box.clear()
            self.timeline_menu.clear_pose()
            self.has_pose(False)

    def get_available_weapon_types(self) -> list:
        items = []
        for weapon in DB.weapons:
            items.append(weapon.nid)
            items.append("Ranged" + weapon.nid)
            items.append("Magic" + weapon.nid)
        items.append("MagicGeneric")
        items.append("Neutral")
        items.append("RangedNeutral")
        items.append("MagicNeutral")
        items.append("Unarmed")
        items.append("Custom")
        for weapon_nid in self.current.weapon_anims.keys():
            if weapon_nid in items:
                items.remove(weapon_nid)
        return items

    def add_new_weapon(self):
        items = self.get_available_weapon_types()

        new_nid, ok = QInputDialog.getItem(self, "New Weapon Animation", "Select Weapon Type", items, 0, False)
        if not new_nid or not ok:
            return
        if new_nid == "Custom":
            new_nid, ok = QInputDialog.getText(self, "Custom Weapon Animation", "Enter New Name for Weapon: ")
            if not new_nid or not ok:
                return
            new_nid = str_utils.get_next_name(new_nid, self.current.weapon_anims.keys())
        new_weapon = combat_anims.WeaponAnimation(new_nid)
        self.current.weapon_anims.append(new_weapon)
        self.weapon_box.addItem(new_nid)
        self.weapon_box.setValue(new_nid)

    def duplicate_weapon(self):
        items = self.get_available_weapon_types()

        new_nid, ok = QInputDialog.getItem(self, "Duplicate Weapon Animation", "Select Weapon Type", items, 0, False)
        if not new_nid or not ok:
            return
        if new_nid == "Custom":
            new_nid, ok = QInputDialog.getText(self, "Custom Weapon Animation", "Enter New Name for Weapon: ")
            if not new_nid or not ok:
                return
            new_nid = str_utils.get_next_name(new_nid, self.current.weapon_anims.keys())

        current_weapon_nid = self.weapon_box.currentText()
        current_weapon = self.current.weapon_anims.get(current_weapon_nid)

        # Make a copy
        has_pixmap = False

        main_pixmap_backup = None
        if current_weapon.pixmap:
            main_pixmap_backup = current_weapon.pixmap #Could contain references
            current_weapon.pixmap = None
            has_pixmap = True

            for index in range(len(current_weapon.frames)):
                frame = current_weapon.frames[index]
                frame.pixmap = None

        # Pickle (Serialize)
        ser = pickle.dumps(current_weapon)
        new_weapon = pickle.loads(ser)

        new_weapon.nid = new_nid

        # Restore pixmaps
        if has_pixmap:
            current_weapon.pixmap = main_pixmap_backup           
            new_weapon.pixmap = QPixmap(current_weapon.full_path)

            for index in range(len(current_weapon.frames)):
                frame = current_weapon.frames[index]
                new_frame = new_weapon.frames[index]
                x, y, width, height = frame.rect

                frame.pixmap = current_weapon.pixmap.copy(x, y, width, height)
                
                new_frame.nid = frame.nid
                new_frame.rect = frame.rect 
                new_frame.pixmap = current_weapon.pixmap.copy(x, y, width, height)

        self.current.weapon_anims.append(new_weapon)
        self.weapon_box.addItem(new_nid)
        self.weapon_box.setValue(new_nid)

        return new_weapon

    def delete_weapon(self):
        weapon = self.get_current_weapon_anim()
        if self.ask_permission(weapon, 'Weapon Animation'):
            self.current.weapon_anims.delete(weapon)
            self.reset_weapon_box()

    def pose_changed(self, idx):
        current_pose_nid = self.pose_box.currentText()
        weapon_anim = self.get_current_weapon_anim()
        if not weapon_anim:
            self.timeline_menu.clear_pose()
            self.has_pose(False)
            return
        poses = weapon_anim.poses
        current_pose = poses.get(current_pose_nid)
        if current_pose:
            self.has_pose(True)
            self.timeline_menu.set_current_pose(current_pose)
        else:
            self.timeline_menu.clear_pose()
            self.has_pose(False)

    def get_available_pose_types(self, weapon_anim) -> float:
        items = [_ for _ in combat_anims.required_poses] + ['Critical']
        items.append("Custom")
        for pose_nid in weapon_anim.poses.keys():
            if pose_nid in items:
                items.remove(pose_nid)
        return items

    def make_pose(self, weapon_anim) -> str:
        items = self.get_available_pose_types(weapon_anim)

        new_nid, ok = QInputDialog.getItem(self, "New Pose", "Select Pose", items, 0, False)
        if not new_nid or not ok:
            return
        if new_nid == "Custom":
            new_nid, ok = QInputDialog.getText(self, "Custom Pose", "Enter New Name for Pose: ")
            if not new_nid or not ok:
                return
            new_nid = str_utils.get_next_name(new_nid, self.current.weapon_anims.keys())
        return new_nid

    def add_new_pose(self):
        weapon_anim = self.get_current_weapon_anim()
        new_nid = self.make_pose(weapon_anim)
        if not new_nid:
            return
        
        new_pose = combat_anims.Pose(new_nid)
        weapon_anim.poses.append(new_pose)
        self.pose_box.addItem(new_nid)
        self.pose_box.setValue(new_nid)

    def duplicate_pose(self):
        weapon_anim = self.get_current_weapon_anim()
        new_nid = self.make_pose(weapon_anim)
        if not new_nid:
            return

        current_pose_nid = self.pose_box.currentText()
        current_pose = weapon_anim.poses.get(current_pose_nid)
        # Make a copy
        ser = current_pose.serialize()
        new_pose = combat_anims.Pose.deserialize(ser)
        new_pose.nid = new_nid
        weapon_anim.poses.append(new_pose)
        self.pose_box.addItem(new_nid)
        self.pose_box.setValue(new_nid)
        return new_pose

    def delete_pose(self):
        weapon_anim = self.get_current_weapon_anim()
        pose = weapon_anim.poses.get(self.pose_box.currentText())
        if self.ask_permission(pose, 'Pose'):
            weapon_anim.poses.delete(pose)
            self.reset_pose_box(weapon_anim)

    def get_current_weapon_anim(self):
        weapon_nid = self.weapon_box.currentText()
        return self.current.weapon_anims.get(weapon_nid)

    def reset_weapon_box(self):
        self.weapon_box.clear()
        weapon_anims = self.current.weapon_anims
        if weapon_anims:
            self.weapon_box.addItems([d.nid for d in weapon_anims])
            self.weapon_box.setValue(weapon_anims[0].nid)
        return weapon_anims

    def reset_pose_box(self, weapon_anim):
        self.pose_box.clear()
        poses = weapon_anim.poses
        if poses:
            self.pose_box.addItems([d.nid for d in poses])
            self.pose_box.setValue(poses[0].nid)
        return poses

    def import_legacy(self):
        starting_path = self.settings.get_last_open_path()
        fns, ok = QFileDialog.getOpenFileNames(self.window, "Select Legacy Script Files", starting_path, "Script Files (*-Script.txt);;All Files (*)")
        if fns and ok:
            parent_dir = os.path.split(fns[-1])[0]
            self.settings.set_last_open_path(parent_dir)

            for fn in fns:
                if fn.endswith('-Script.txt'):
                    combat_animation_imports.import_from_legacy(self.current, fn)

            # Reset
            self.set_current(self.current)
            if self.current.weapon_anims:
                self.weapon_box.setValue(self.current.weapon_anims[-1].nid)

    def import_gba(self):
        starting_path = self.settings.get_last_open_path()
        fns, ok = QFileDialog.getOpenFileNames(self.window, "Select Legacy Script Files", starting_path, "Text Files (*.txt);;All Files (*)")
        if fns and ok:
            parent_dir = os.path.split(fns[-1])[0]
            self.settings.set_last_open_path(parent_dir)

            for fn in fns:
                if fn.endswith('.txt'):
                    combat_animation_imports.import_from_gba(self.current, fn)

            # Reset
            self.set_current(self.current)
            if self.current.weapon_anims:
                self.weapon_box.setValue(self.current.weapon_anims[-1].nid)

    def select_frame(self):
        weapon_anim = self.get_current_weapon_anim()
        if weapon_anim:
            dlg = FrameSelector(self.current, weapon_anim, self)
            dlg.exec_()

    def set_current(self, current):
        self.stop()

        self.current = current
        self.nid_box.setText(self.current.nid)

        self.weapon_box.clear()
        weapon_anims = self.current.weapon_anims
        self.weapon_box.addItems([d.nid for d in weapon_anims])
        if weapon_anims:
            self.weapon_box.setValue(weapon_anims[0].nid)
            weapon_anim = self.get_current_weapon_anim()
            poses = self.reset_pose_box(weapon_anim)
            self.timeline_menu.set_current_frames(weapon_anim.frames)
        else:
            self.pose_box.clear()
            weapon_anim, poses = None, None

        self.palette_menu.set_current(self.current)

        if weapon_anim and poses:
            current_pose_nid = self.pose_box.currentText()
            current_pose = poses.get(current_pose_nid)
            self.timeline_menu.set_current_pose(current_pose)
        else:
            self.timeline_menu.clear_pose()

    def get_current_palette(self):
        return self.palette_menu.get_palette()

    def get_combat_palette(self):
        return self.palette_menu.get_palette()

    def modify_for_palette(self, pixmap: QPixmap) -> QImage:
        current_palette_nid = self.get_current_palette()
        return palette_swap(pixmap, current_palette_nid)

    def update(self):
        if self.playing:
            current_time = int(time.time_ns() / 1e6)
            framerate = 1000 / self.speed_box.value()
            milliseconds_past = current_time - self.last_update
            num_frames_passed = int(milliseconds_past / framerate)
            unspent_time = milliseconds_past % framerate
            self.next_update = current_time - unspent_time
            if num_frames_passed >= self.num_frames:
                self.processing = True
                self.read_script()
        elif self.paused:
            pass
        else:
            # Get selected frame
            current_command = self.timeline_menu.get_current_command()
            if current_command:
                self.do_command(current_command)

    def read_script(self):
        if self.timeline_menu.finished():
            if self.loop:
                self.timeline_menu.reset()
            else:
                self.timeline_menu.reset()
                self.stop()
            return

        while not self.timeline_menu.finished() and self.processing:
            current_command = self.timeline_menu.get_current_command()
            self.do_command(current_command)
            self.timeline_menu.inc_current_idx()

    def do_command(self, command):
        self.custom_frame_offset = None
        self.under_frame_nid = None
        if command.nid in ('frame', 'over_frame', 'under_frame'):
            num_frames, image = command.value
            self.num_frames = num_frames
            self.last_update = self.next_update
            self.processing = False
            self.frame_nid = image
        elif command.nid == 'wait':
            self.num_frames = command.value[0]
            self.last_update = self.next_update
            self.processing = False
            self.frame_nid = None
        elif command.nid == 'dual_frame':
            num_frames, image1, image2 = command.value
            self.num_frames = num_frames
            self.last_update = self.next_update
            self.processing = False
            self.frame_nid = image1
            self.under_frame_nid = image2
        elif command.nid == 'frame_with_offset':
            num_frames, image, x, y = command.value
            self.num_frames = num_frames
            self.last_update = self.next_update
            self.processing = False
            self.frame_nid = image
            self.custom_frame_offset = (x, y)
        elif command.nid == 'wait_for_hit':
            image1, image2 = command.value
            self.num_frames = 27
            self.last_update = self.next_update
            self.processing = False
            self.frame_nid = image1
            self.under_frame_nid = image2
        else:
            pass

    def draw_frame(self):
        self.update()

        # Actually show current frame
        # Need to draw 240x160 area
        # And place in space according to offset
        actor_im = None
        offset_x, offset_y = 0, 0
        under_actor_im = None
        under_offset_x, under_offset_y = 0, 0

        if self.frame_nid:
            weapon_anim = self.get_current_weapon_anim()
            if weapon_anim:
                frame = weapon_anim.frames.get(self.frame_nid)
                if frame:
                    if self.custom_frame_offset:
                        offset_x, offset_y = self.custom_frame_offset
                    else:
                        offset_x, offset_y = frame.offset
                    actor_im = self.modify_for_palette(frame.pixmap)
        if self.under_frame_nid:
            weapon_anim = self.get_current_weapon_anim()
            if weapon_anim:
                frame = weapon_anim.frames.get(self.under_frame_nid)
                if frame:
                    under_offset_x, under_offset_y = frame.offset
                    under_actor_im = self.modify_for_palette(frame.pixmap)

        self.set_anim_view(actor_im, (offset_x, offset_y), under_actor_im, (under_offset_x, under_offset_y))

    def set_anim_view(self, actor_im, offset, under_actor_im, under_offset):
        offset_x, offset_y = offset
        under_offset_x, under_offset_y = under_offset
        base_image = QImage(WINWIDTH, WINHEIGHT, QImage.Format_ARGB32)
        base_image.fill(editor_utilities.qCOLORKEY)
        if actor_im or under_actor_im:
            painter = QPainter()
            painter.begin(base_image)
            if under_actor_im:
                painter.drawImage(under_offset_x, under_offset_y, under_actor_im)
            if actor_im:
                painter.drawImage(offset_x, offset_y, actor_im)
            painter.end()
        self.anim_view.set_image(QPixmap.fromImage(base_image))
        self.anim_view.show_image()

    def import_palettes(self, fn_dir) -> dict:
        palette_path = os.path.join(fn_dir, '*_palette.json')
        palettes = sorted(glob.glob(palette_path))
        if not palettes:
            QMessageBox.warning(self, "File Not Found", "Could not find any valid *_palette.json Palette files.")
        palette_nid_swap = {}
        for palette_fn in palettes:
            with open(palette_fn) as load_file:
                data = json.load(load_file)
            palette = combat_palettes.Palette.restore(data)
            new_nid = str_utils.get_next_name(palette.nid, RESOURCES.combat_palettes.keys())
            if new_nid != palette.nid:
                palette_nid_swap[palette.nid] = new_nid
                palette.nid = new_nid
            RESOURCES.combat_palettes.append(palette)
        return palette_nid_swap

    def import_anim(self):
        # Ask user for location
        starting_path = self.settings.get_last_open_path()
        fn_dir = QFileDialog.getExistingDirectory(
            self, "Import *.ltanim", starting_path)
        if not fn_dir:
            return
        self.settings.set_last_open_path(fn_dir)
        # Determine the palettes in the folder
        palette_nid_swap = self.import_palettes(fn_dir)
        # Determine the combat_anims in the folder
        anim_path = os.path.join(fn_dir, '*_anim.json')
        anims = sorted(glob.glob(anim_path))
        if not anims:
            QMessageBox.warning(self, "File Not Found", "Could not find any valid *_anim.json Combat Animation files.")
        for anim_fn in anims:
            with open(anim_fn) as load_file:
                data = json.load(load_file)
            anim = combat_anims.CombatAnimation.restore(data)
            for weapon_anim in anim.weapon_anims:
                short_path = "%s-%s.png" % (anim.nid, weapon_anim.nid)
                weapon_anim.set_full_path(os.path.join(fn_dir, short_path))
            anim.nid = str_utils.get_next_name(anim.nid, RESOURCES.combat_anims.keys())
            # Update any palette references that changed
            for idx, palette in enumerate(anim.palettes[:]):
                name, nid = palette
                if nid in palette_nid_swap:
                    anim.palettes[idx][1] = palette_nid_swap[nid]
            populate_anim_pixmaps(anim)
            RESOURCES.combat_anims.append(anim)
        # Print done import! Import complete!
        self.window.update_list()
        QMessageBox.information(self, "Import Complete", "Import of combat animation %s complete!" % fn_dir)

    def export_anim(self):
        # Ask user for location
        if not self.current:
            return
        starting_path = self.settings.get_last_open_path()
        fn_dir = QFileDialog.getExistingDirectory(
            self, "Export Current Combat Animation", starting_path)
        if not fn_dir:
            return
        self.settings.set_last_open_path(fn_dir)
        # Create folder at location named effect_nid.lteffect
        path = os.path.join(fn_dir, '%s.ltanim' % self.current.nid)
        if not os.path.exists(path):
            os.mkdir(path)
        
        # Store all of this in anim_nid.ltanim folder
        # Gather reference to images for this effect
        RESOURCES.combat_anims.save_image(path, self.current)
        # Serialize into json form
        serialized_data = self.current.save()
        serialized_path = os.path.join(path, '%s_anim.json' % self.current.nid)
        with open(serialized_path, 'w') as serialize_file:
            json.dump(serialized_data, serialize_file, indent=4)
        # Gather reference to palettes
        palette_nids = [palette[1] for palette in self.current.palettes]
        for palette_nid in palette_nids:
            palette = RESOURCES.combat_palettes.get(palette_nid)
            if not palette:
                continue
            # Serialize into json form
            serialized_data = palette.save()
            serialized_path = os.path.join(path, '%s_palette.json' % palette_nid)
            with open(serialized_path, 'w') as serialize_file:
                json.dump(serialized_data, serialize_file, indent=4)
        # Print done export! Export to %s complete!
        QMessageBox.information(self, "Export Complete", "Export of combat animation to %s complete!" % path)

    def export_all_frames(self, fn_dir: str):
        weapon_anim = self.get_current_weapon_anim()
        poses = weapon_anim.poses
        current_pose_nid = self.pose_box.currentText()
        current_pose = poses.get(current_pose_nid)
        counter = 0
        for command in current_pose.timeline:
            self.processing = True
            self.do_command(command)
            if self.processing:  # Don't bother drawing anything if we are still processing
                continue
            im = QImage(WINWIDTH, WINHEIGHT, QImage.Format_ARGB32)
            im.fill(editor_utilities.qCOLORKEY)
            frame, under_frame = None, None
            if self.under_frame_nid:
                under_frame = weapon_anim.frames.get(self.under_frame_nid)
                under_offset_x, under_offset_y = under_frame.offset
                under_frame = self.modify_for_palette(under_frame.pixmap)
            if self.frame_nid:
                frame = weapon_anim.frames.get(self.frame_nid)
                if self.custom_frame_offset:
                    offset_x, offset_y = self.custom_frame_offset
                else:
                    offset_x, offset_y = frame.offset
                frame = self.modify_for_palette(frame.pixmap)
            if frame or under_frame:
                painter = QPainter()
                painter.begin(im)
                if under_frame:
                    painter.drawImage(under_offset_x, under_offset_y, under_frame)
                if frame:
                    painter.drawImage(offset_x, offset_y, frame)
                painter.end()
            for i in range(self.num_frames):
                path = '%s_%s_%s_%04d.png' % (self.current.nid, weapon_anim.nid, current_pose.nid, counter)
                full_path = os.path.join(fn_dir, path)
                im.save(full_path)
                counter += 1

    def get_test_palettes(self, combat_anim):
        palettes = combat_anim.palettes
        if not palettes:
            print("No palettes!")
            return
        palette_names = [palette[0] for palette in palettes]
        palette_nids = [palette[1] for palette in palettes]
        current_palette_nid = self.get_combat_palette()
        if current_palette_nid in palette_nids:
            idx = palette_nids.index(current_palette_nid)
            right_palette_name = palette_names[idx]
            right_palette_nid = palette_nids[idx]
        elif 'GenericBlue' in palette_names:
            idx = palette_names.index('GenericBlue')
            right_palette_name = 'GenericBlue'
            right_palette_nid = palette_nids[idx]
        else:
            right_palette_name = palette_names[0]
            right_palette_nid = palette_nids[0]
        if 'GenericRed' in palette_names:
            idx = palette_names.index('GenericRed')
            left_palette_name = 'GenericRed'
            left_palette_nid = palette_nids[idx]
        elif len(palette_nids) > 1:
            left_palette_nid = palette_nids[1]
            left_palette_name = palette_names[1]
        else:
            left_palette_nid = palette_nids[0]
            left_palette_name = palette_names[0]
        right_palette = RESOURCES.combat_palettes.get(right_palette_nid)
        left_palette = RESOURCES.combat_palettes.get(left_palette_nid)
        return left_palette_name, left_palette, right_palette_name, right_palette

    def test_combat(self):
        if self.current:
            weapon_nid = self.weapon_box.currentText()
            weapon_anim = self.current.weapon_anims.get(weapon_nid)
            if not weapon_anim:
                return
            current_pose_nid = self.pose_box.currentText()
            if 'Stand' in weapon_anim.poses.keys() and 'Attack' in weapon_anim.poses.keys():
                pass
            else:
                print("Missing Stand or Attack pose!")
                return
            
            left_palette_name, left_palette, right_palette_name, right_palette = self.get_test_palettes(self.current)

            item_nid = None
            for item in DB.items:
                if item.magic and item.nid in RESOURCES.combat_effects.keys():
                    item_nid = item.nid
            
            timer.get_timer().stop()
            GAME_ACTIONS.test_combat(
                self.current, weapon_anim, left_palette_name, left_palette, item_nid, 
                self.current, weapon_anim, right_palette_name, right_palette, item_nid, current_pose_nid)
            timer.get_timer().start()
