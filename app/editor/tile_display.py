from PyQt5.QtWidgets import QFileDialog, QWidget, QHBoxLayout, \
    QMessageBox, QPushButton, QVBoxLayout
from PyQt5.QtCore import QDir, QSettings, Qt
from PyQt5.QtGui import QPixmap, QImage, QPainter, QIcon

import os

from app.data.constants import TILEWIDTH, TILEHEIGHT
from app.data.data import Data
from app.data.tilemap_prefab import TileMapPrefab
from app.data.resources import RESOURCES
from app.data.database import DB

from app.editor.base_database_gui import DatabaseTab, ResourceCollectionModel
from app.extensions.custom_gui import ResourceListView, DeletionDialog
from app.editor.icon_display import IconView
from app.editor.tilemap_editor import MapEditor

from app import utilities

class TileSetDisplay(DatabaseTab):
    @classmethod
    def create(cls, parent=None):
        data = RESOURCES.tilesets
        title = "Tilesets"
        right_frame = TileSetProperties
        collection_model = TileSetModel
        
        dialog = cls(data, title, right_frame, None,
                     collection_model, parent, button_text="Add New %s...",
                     view_type=ResourceListView)
        return dialog

class TileMapDisplay(DatabaseTab):
    @classmethod
    def create(cls, parent=None):
        data = RESOURCES.tilemaps
        title = "Tilemap"
        right_frame = TileMapProperties
        collection_model = TileMapModel
        
        dialog = cls(data, title, right_frame, None,
                     collection_model, parent, button_text="Create New %s...",
                     view_type=ResourceListView)
        return dialog

class TileSetModel(ResourceCollectionModel):
    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            tileset = self._data[index.row()]
            text = tileset.nid
            return text
        elif role == Qt.DecorationRole:
            tileset = self._data[index.row()]
            pixmap = tileset.pixmap
            return QIcon(pixmap)
        return None
        
    def create_new(self):
        settings = QSettings("rainlash", "Lex Talionis")
        starting_path = str(settings.value("last_open_path", QDir.currentPath()))
        fns, ok = QFileDialog.getOpenFileNames(self.window, "Choose %s", starting_path, "PNG Files (*.png);;All Files(*)")
        if ok:
            for fn in fns:
                if fn.endswith('.png'):
                    nid = os.path.split(fn)[-1][:-4]
                    pix = QPixmap(fn)
                    nid = utilities.get_next_name(nid, RESOURCES.tilesets.keys())
                    if pix.width() % TILEWIDTH != 0:
                        QMessageBox.critical(self, 'Error', "Image width must be exactly divisible by %d pixels!" % TILEWIDTH)
                        continue
                    elif pix.height() % TILEHEIGHT != 0:
                        QMessageBox.critical(self, 'Error', "Image height must be exactly divisible by %d pixels!" % TILEHEIGHT)
                        continue
                    RESOURCES.create_new_tileset(nid, fn, pix)
                else:
                    QMessageBox.critical(self.window, "File Type Error!", "Tileset must be PNG format!") 
            parent_dir = os.path.split(fns[-1])[0]
            settings.setValue("last_open_path", parent_dir)

    def delete(self, idx):
        # Check to see what is using me?
        res = self._data[idx]
        nid = res.nid
        affected_tilemaps = [tilemap for tilemap in RESOURCES.tilemaps if nid in tilemap.tilesets]
        if affected_tilemaps:
            affected = Data(affected_tilemaps)
            model = TileMapModel
            msg = "Deleting Tileset <b>%s</b> would affect these tilemaps."
            ok = DeletionDialog.inform(affected, model, msg, self.window)
            if ok:
                pass
            else:
                return
        super().delete(idx)

    def nid_change_watchers(self, icon, old_nid, new_nid):
        # What uses tilesets
        # Tilemaps use tilesets
        for tilemap in RESOURCES.tilemaps:
            for idx, nid in enumerate(tilemap.tilesets):
                if nid == old_nid:
                    tilemap.tilesets[idx] = new_nid
            for layer in tilemap.layers:
                for coord, tile_sprite in layer.sprite_grid.items():
                    if tile_sprite.tileset_nid == old_nid:
                        tile_sprite.tileset_nid = new_nid

class TileMapModel(ResourceCollectionModel):
    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            tilemap = self._data[index.row()]
            text = tilemap.nid
            return text
        elif role == Qt.DecorationRole:
            tilemap = self._data[index.row()]
            pixmap = tilemap.pixmap
            if pixmap:
                return QIcon(pixmap)
        return None

    def create_new(self):
        new_nid = utilities.get_next_name('New Tilemap', self._data.keys())
        new_tilemap = TileMapPrefab(new_nid)
        map_editor = MapEditor(self.window, new_tilemap)
        map_editor.exec_()
        create_tilemap_pixmap(new_tilemap)
        RESOURCES.tilemaps.append(new_tilemap)
        
    def delete(self, idx):
        # Check to see what is using me?
        res = self._data[idx]
        nid = res.nid
        affected_levels = [level for level in DB.levels if level.tilemap == nid]
        if affected_levels:
            affected = Data(affected_levels)
            from app.editor.level_menu import LevelModel
            model = LevelModel
            msg = "Deleting Tilemap <b>%s</b> would affect these levels."
            ok = DeletionDialog.inform(affected, model, msg, self.window)
            if ok:
                pass
            else:
                return
        super().delete(idx)

    def nid_change_watchers(self, icon, old_nid, new_nid):
        # What uses tilemaps
        # Levels use tilemaps
        for level in DB.levels:
            if level.tilemap == old_nid:
                level.tilemap = new_nid

class TileSetProperties(QWidget):
    def __init__(self, parent, current=None):
        super().__init__(parent)
        self.window = parent

        self._data = self.window._data
        self.resource_editor = self.window.window

        for resource in self._data:
            resource.set_pixmap(QPixmap(resource.full_path))

        self.current = current

        self.view = IconView(self)

        layout = QHBoxLayout()
        self.setLayout(layout)
        layout.addWidget(self.view)

    def set_current(self, current):
        self.current = current
        self.view.set_image(self.current.pixmap)
        self.view.show_image()

def create_tilemap_pixmap(tilemap):
    base_layer = tilemap.layers.get('base')
    image = QImage(tilemap.width * TILEWIDTH,
                   tilemap.height * TILEHEIGHT,
                   QImage.Format_ARGB32)

    painter = QPainter()
    painter.begin(image)
    for coord, tile_sprite in base_layer.sprite_grid.items():
        tileset = RESOURCES.tilesets.get(tile_sprite.tileset_nid)
        pix = tileset.get_pixmap(tile_sprite.tileset_position)
        if pix:
            painter.drawImage(coord[0] * TILEWIDTH,
                              coord[1] * TILEHEIGHT,
                              pix.toImage())
    painter.end()
    tilemap.pixmap = QPixmap.fromImage(image)

class TileMapProperties(QWidget):
    def __init__(self, parent, current=None):
        super().__init__(parent)
        self.window = parent
        self._data = self.window._data
        self.resource_editor = self.window.window

        # Populate resources
        for resource in self._data:
            create_tilemap_pixmap(resource)

        self.current = current

        self.view = IconView(self)

        self.edit_button = QPushButton("Edit Tilemap...")
        self.edit_button.clicked.connect(self.on_edit)
        if not self.current:
            self.edit_button.setEnabled(False)

        layout = QVBoxLayout()
        self.setLayout(layout)
        layout.addWidget(self.view)
        layout.addWidget(self.edit_button)

    def set_current(self, current):
        self.current = current
        if self.current:
            self.edit_button.setEnabled(True)
            if not self.current.pixmap:
                create_tilemap_pixmap(self.current)
                self.view.set_image(self.current.pixmap)
                self.view.show_image()

    def on_edit(self):
        from app.editor.tilemap_editor import MapEditor
        map_editor = MapEditor(self, self.current)
        map_editor.exec_()
        create_tilemap_pixmap(self.current)
