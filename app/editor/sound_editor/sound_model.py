import os, math

from PyQt5.QtWidgets import QFileDialog, QMessageBox, QDialog
from PyQt5.QtCore import Qt, QSettings, QDir

from app.utilities import str_utils
from app.resources.sounds import SFX, Song
from app.resources.resources import RESOURCES

from app.editor.table_model import TableModel
from app.editor.sound_editor.sound_dialog import ModifySFXDialog, ModifyMusicDialog

class SoundModel(TableModel):
    rows = ['nid', 'length', 'tag']

    def headerData(self, idx, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Vertical:  # Row
            return '   '
        elif orientation == Qt.Horizontal:  # Column
            val = self.rows[idx]
            if val == 'nid':
                return 'Name'
            elif val == 'length':
                return 'Time'
            elif val == 'extra':
                return "Variant"
            else:
                return val.capitalize()
        return None

    def data(self, index, role):
        if not index.isValid():
            return None
        if role == Qt.DisplayRole:
            d = self._data[index.row()]
            str_attr = self.rows[index.column()]
            if str_attr == 'extra':
                if d.intro_full_path:
                    return 'Intro'
                elif d.battle_full_path:
                    return 'Battle'
                else:
                    return None
            attr = getattr(d, str_attr)
            if str_attr == 'length' and attr is not None:
                minutes = int(attr / 60)
                seconds = math.ceil(attr % 60)
                return "%02d:%02d" % (minutes, seconds)
            return attr
        elif role == Qt.TextAlignmentRole:
            str_attr = self.rows[index.column()]
            if str_attr == 'length':
                return Qt.AlignRight + Qt.AlignVCenter
        return None

class SFXModel(SoundModel):
    def create_new(self) -> bool:
        settings = QSettings("rainlash", "Lex Talionis")
        starting_path = str(settings.value("last_open_path", QDir.currentPath()))
        fns, ok = QFileDialog.getOpenFileNames(self.window, "Select SFX File", starting_path, "OGG Files (*.ogg);;All FIles (*)")
        created = False
        if ok:
            ogg_msg = False
            for fn in fns:
                if fn.endswith('.ogg'):
                    nid = os.path.split(fn)[-1][:-4]
                    nid = str_utils.get_next_name(nid, [d.nid for d in RESOURCES.sfx])
                    new_sfx = SFX(nid, fn)
                    new_sfx.length = self.window.audio_widget.find_length(new_sfx)
                    RESOURCES.sfx.append(new_sfx)
                    created = True
                elif not ogg_msg:
                    ogg_msg = True  # So it doesn't happen more than once
                    QMessageBox.critical(self.window, "File Type Error!", "Sound Effect must be in OGG format!")
            parent_dir = os.path.split(fns[-1])[0]
            settings.setValue("last_open_path", parent_dir)
        return created

    def modify(self, indices):
        idxs = {i.row() for i in indices}
        current = [self._data[idx] for idx in idxs]
        saved_d = [c.save() for c in current]
        dialog = ModifySFXDialog(self._data, current, self.window)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            pass
        else:
            for idx, c in enumerate(current):
                c.tag = saved_d[idx][1]
                c.nid = saved_d[idx][0]
                self._data.update_nid(c, c.nid)

class MusicModel(SoundModel):
    rows = ['nid', 'length', 'extra']

    def create_new(self) -> bool:
        settings = QSettings("rainlash", "Lex Talionis")
        starting_path = str(settings.value("last_open_path", QDir.currentPath()))
        fns, ok = QFileDialog.getOpenFileNames(self.window, "Select SFX File", starting_path, "OGG Files (*.ogg);;All FIles (*)")
        created = False
        if ok:
            ogg_msg = False
            for fn in fns:
                if fn.endswith('.ogg'):
                    nid = os.path.split(fn)[-1][:-4]
                    nid = str_utils.get_next_name(nid, [d.nid for d in RESOURCES.music])
                    new_music = Song(nid, fn)
                    new_music.length = self.window.audio_widget.find_length(new_music)
                    RESOURCES.music.append(new_music)
                    created = True
                elif not ogg_msg:
                    ogg_msg = True  # So it doesn't happen more than once
                    QMessageBox.critical(self.window, "File Type Error!", "Music must be in OGG format!")
            parent_dir = os.path.split(fns[-1])[0]
            settings.setValue("last_open_path", parent_dir)
        return created

    def modify(self, indices):
        idxs = {i.row() for i in indices}
        if len(idxs) > 1:
            QMessageBox.critical(self.window, "Selection Error!", "Cannot modify multiple songs at the same time!")
            return
        # Only the last index
        current = [self._data[idx] for idx in idxs]
        saved_d = [c.full_save() for c in current]
        dialog = ModifyMusicDialog(self._data, current, self.window)
        result = dialog.exec_()
        if result == QDialog.Accepted:
            pass
        else:
            for idx, c in enumerate(current):
                c.nid = saved_d[idx][0]
                c.intro_full_path = saved_d[idx][1]
                c.battle_full_path = saved_d[idx][2]
                self._data.update_nid(c, c.nid)