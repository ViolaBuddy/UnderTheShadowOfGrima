from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QColor

from app.resources.resources import RESOURCES

from app.utilities import utils
from app.utilities.data import Data

from app.resources.combat_palettes import Palette
from app.extensions.custom_gui import DeletionDialog
from app.editor.base_database_gui import DragDropCollectionModel
from app.utilities import str_utils

def get_palette_pixmap(palette) -> QPixmap:
    painter = QPainter()
    main_pixmap = QPixmap(32, 32)
    main_pixmap.fill(QColor(0, 0, 0, 0))
    painter.begin(main_pixmap)
    colors = palette.colors.values()
    colors = sorted(colors, key=lambda color: utils.rgb2hsv(*color)[0])
    for idx, color in enumerate(colors[:16]):
        left = idx % 4
        top = idx // 4
        painter.fillRect(left * 8, top * 8, 8, 8, QColor(*color))
    painter.end()
    return main_pixmap

class PaletteModel(DragDropCollectionModel):
    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.EditRole:
            return self._data[index.row()]
        if role == Qt.DisplayRole:
            palette = self._data[index.row()]
            text = palette.nid
            return text
        elif role == Qt.DecorationRole:
            palette = self._data[index.row()]
            pixmap = get_palette_pixmap(palette)
            if pixmap:
                return QIcon(pixmap)
        return None

    def create_new(self):
        nids = RESOURCES.combat_palettes.keys()
        nid = str_utils.get_next_name('New Palette', nids)
        new_palette = Palette(nid)
        RESOURCES.combat_palettes.append(new_palette)
        return new_palette

    def delete(self, idx):
        # Delete watchers
        res = self._data[idx]
        nid = res.nid
        affected_combat_anims = [anim for anim in RESOURCES.combat_anims if nid in anim.palettes]
        if affected_combat_anims:
            affected = Data(affected_combat_anims)
            from app.editor.combat_animation_editor.combat_animation_model import CombatAnimationModel
            model = CombatAnimationModel
            msg = "Deleting Palette <b>%s</b> would affect these combat animations."
            ok = DeletionDialog.inform(affected, model, msg, self.window)
            if ok:
                pass
            else:
                return
        super().delete(idx)

    def on_nid_changed(self, old_nid, new_nid):
        # What uses combat palettes
        for combat_anim in RESOURCES.combat_anims:
            palette_nids = [palette[1] for palette in combat_anim.palettes]
            if old_nid in palette_nids:
                idx = palette_nids.index(old_nid)
                combat_anim.palettes[idx][1] = new_nid
