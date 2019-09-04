from PyQt5.QtWidgets import QGridLayout, QPushButton, QSlider, QLabel, QCheckBox, QListView, \
    QWidget, QFileDialog, QMessageBox
from PyQt5.QtCore import Qt, QSize, QDir
from PyQt5.QtGui import QPixmap

from app.data.constants import TILEWIDTH, TILEHEIGHT
from app.data.database import DB

from app.editor.terrain_database import TerrainDatabase, TerrainModel

class TerrainPainterMenu(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_editor = parent

        grid = QGridLayout()
        self.setLayout(grid)

        self.import_button = QPushButton('Import New Map PNG...')
        self.import_button.clicked.connect(self.import_new_map)
        grid.addWidget(self.import_button, 0, 0, 1, 2)

        self.alpha_slider = QSlider(Qt.Horizontal, self)
        self.alpha_slider.setRange(0, 255)
        self.alpha_slider.setValue(192)
        grid.addWidget(QLabel("Transparency"), 1, 0)
        grid.addWidget(self.alpha_slider, 1, 1)

        self.num_check = QCheckBox(self)
        self.num_check.clicked.connect(self.num_check_changed)
        grid.addWidget(QLabel("Show IDs?"), 2, 0)
        grid.addWidget(self.num_check, 2, 1)

        self.list_view = QListView(self)
        self.list_view.currentChanged = self.on_item_changed

        self.model = TerrainModel(self)
        self.list_view.setModel(self.model)
        self.list_view.setIconSize(QSize(32, 32))

        grid.addWidget(self.list_view, 3, 0, 1, 2)

        self.reset_button = QPushButton('Reset Terrain')
        self.reset_button.clicked.connect(self.reset_terrain)
        self.edit_button = QPushButton('Edit Terrain...')
        self.edit_button.clicked.connect(self.edit_terrain)
        grid.addWidget(self.reset_button, 4, 0)
        grid.addWidget(self.edit_button, 4, 1)

    def tilemap(self):
        return self.main_editor.current_level.tilemap

    def get_alpha(self):
        return int(self.alpha_slider.value())

    def import_new_map(self):
        image_file, _ = QFileDialog.getOpenFileName(self, "Choose Map PNG", QDir.currentPath(),
                                                    "PNG Files (*.png);;All Files (*)")
        im = QPixmap(image_file)
        if im:
            if im.width() % TILEWIDTH != 0: 
                QMessageBox.critical(self.main_editor, 'Error', "Image width must be exactly divisible by %d pixels!" % TILEWIDTH)
                return
            elif im.height() % TILEHEIGHT != 0:
                QMessageBox.critical(self.main_editor, 'Error', "Image height must be exactly divisible by %d pixels!" % TILEHEIGHT)
                return
            else:
                self.tilemap().change_image(image_file, im.width()//TILEWIDTH, im.height()//TILEHEIGHT)
                self.main_editor.set_current_level(self.current_level)  # For reset
                self.main_editor.update_view()

    def num_check_changed(self, state):
        self.main_editor.map_view.display_terrain_ids = state

    def on_item_changed(self, curr, prev):
        pass

    def reset_terrain(self):
        self.tilemap().reset_terrain()
        self.main_editor.update_view()

    def edit_terrain(self):
        TerrainDatabase.edit(self)
        self.main_editor.update_view()

    def paint_tile(self, pos):
        current_terrain = DB.terrain.values()[self.list_view.currentIndex().row()]
        self.tilemap().tiles[pos].terrain = current_terrain
        self.main_editor.update_view()

    def set_current_nid(self, nid):
        idx = self.model.index(DB.terrain.index(nid))
        self.list_view.setCurrentIndex(idx)
