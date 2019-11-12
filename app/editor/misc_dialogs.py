from app.data.database import DB

from app.editor.custom_gui import SingleListDialog, MultiAttrListDialog

class TagDialog(SingleListDialog):
    @classmethod
    def create(cls):
        return cls(DB.tags, "Tag")

    def accept(self):
        for action in self.actions:
            kind = action[0]
            if kind == 'Delete':
                self.on_delete(action[1])
            elif kind == 'Change':
                self.on_change(*action[1:])
            elif kind == 'Append':
                self.on_change(action[1])
        super().accept()

    def on_delete(self, element):
        for klass in DB.classes:
            if element in klass.tags:
                klass.tags.remove(element)

    def on_change(self, old, new):
        for klass in DB.classes:
            if old in klass.tags:
                klass.tags.remove(old)
                klass.tags.append(new)

    def on_append(self, element):
        pass

class StatDialog(MultiAttrListDialog):
    @classmethod
    def create(cls):
        return cls(DB.stats, "Stat", ("nid", "name", "maximum", "desc"), 
                   {"HP", "MOV"})

    def on_delete(self, element):
        for klass in DB.classes:
            for row in klass.get_stat_lists():
                row.remove_key(element.nid)

    def on_change(self, element, attr, old_value, new_value):
        if attr == 'nid':
            for klass in DB.classes:
                for row in klass.get_stat_lists():
                    row.change_key(old_value, new_value)

    def on_append(self, element):
        for klass in DB.classes:
            for row in klass.get_stat_lists():
                row.new_key(element.nid)

class RankDialog(MultiAttrListDialog):
    @classmethod
    def create(cls):
        return cls(DB.weapon_ranks, "Weapon Rank", 
                   ("rank", "requirement", "accuracy", "damage", "crit"))

class EquationDialog(MultiAttrListDialog):
    @classmethod
    def create(cls):
        dlg = cls(DB.equations, "Equation", ("nid", "expression"), 
                  {"ATTACKSPEED", "HIT", "AVOID", "CRIT_HIT", "CRIT_AVOID", 
                   "DAMAGE", "DEFENSE", "MAGIC_DAMAGE", "MAGIC_DEFENSE", 
                   "CRIT_ADD", "CRIT_MULT",
                   "DOUBLE_ATK", "DOUBLE_DEF", "STEAL_ATK", "STEAL_DEF", 
                   "HEAL", "RESCUE_AID", "RESCUE_WEIGHT", "RATING"})
        return dlg

# Testing
# Run "python -m app.editor.misc_dialogs" from main directory
if __name__ == '__main__':
    import sys
    from PyQt5.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = StatDialog.create()
    window.show()
    app.exec_()