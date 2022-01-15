from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import Qt

from PyQt5.QtCore import QAbstractListModel

class MapTerrainModel(QAbstractListModel):
    def __init__(self, data, window):
        super().__init__(window)
        self._data = data

    def rowCount(self, parent=None):
        return len(self._data)

    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            terrain = self._data[index.row()]
            text = terrain.name
            return text
        elif role == Qt.DecorationRole:
            terrain = self._data[index.row()]
            if not terrain.tileset_pixmap:
                terrain.tileset_pixmap = QPixmap(terrain.tileset_path)
                terrain.display_pixmap = terrain.tileset_pixmap.copy(*self.display_tile_coord, 16, 16)
            return QIcon(terrain.display_pixmap)
        return None
