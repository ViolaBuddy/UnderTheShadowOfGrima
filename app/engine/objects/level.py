from app.engine.objects.difficulty_mode import DifficultyModeObject
from app.utilities.data import Data

from app.engine.objects.unit import UnitObject
from app.engine.objects.tilemap import TileMapObject
from app.events.regions import Region
from app.data.database.level_units import UnitGroup
from app.utilities.typing import NID

# Main Level Object used by engine
class LevelObject():
    def __init__(self):
        self.nid: NID = None
        self.name: str = None
        self.tilemap: TileMapObject = None
        self.bg_tilemap: TileMapObject = None
        self.party: NID = None
        self.roam: bool = False
        self.roam_unit: NID = None

        self.music = {}
        self.objective = {}

        self.units: Data[UnitObject] = Data()
        self.regions = Data()
        self.unit_groups = Data()

    @classmethod
    def from_prefab(cls, prefab, tilemap, bg_tilemap, unit_registry, current_mode: DifficultyModeObject):
        level = cls()
        level.nid = prefab.nid
        level.name = prefab.name
        level.tilemap = tilemap
        level.bg_tilemap = bg_tilemap
        level.party = prefab.party
        level.roam = prefab.roam
        level.roam_unit = prefab.roam_unit

        level.music = {k: v for k, v in prefab.music.items()}
        level.objective = {k: v for k, v in prefab.objective.items()}

        # Load in units
        level.units = Data()
        for unit_prefab in prefab.units:
            if unit_prefab.nid in unit_registry:
                unit = unit_registry[unit_prefab.nid]
                unit.starting_position = tuple(unit_prefab.starting_position) if unit_prefab.starting_position else None
                if not unit.dead:
                    unit.position = unit.starting_position
                else:
                    unit.position = None
                level.units.append(unit)
            else:
                new_unit = UnitObject.from_prefab(unit_prefab, current_mode)
                level.units.append(new_unit)

        level.regions = Data([p for p in prefab.regions])
        level.unit_groups = Data([UnitGroup.from_prefab(p) for p in prefab.unit_groups])

        return level

    def save(self):
        s_dict = {'nid': self.nid,
                  'name': self.name,
                  'tilemap': self.tilemap.save(),
                  'bg_tilemap': self.bg_tilemap.save() if self.bg_tilemap else None,
                  'party': self.party,
                  'roam': self.roam,
                  'roam_unit': self.roam_unit,
                  'music': self.music,
                  'objective': self.objective,
                  'units': [unit.nid for unit in self.units],
                  'regions': [region.save() for region in self.regions],
                  'unit_groups': [unit_group.save() for unit_group in self.unit_groups],
                  }
        return s_dict

    @classmethod
    def restore(cls, s_dict: dict, game):
        level = cls()
        level.nid = s_dict['nid']
        level.name = s_dict.get('name', "")
        level.tilemap = TileMapObject.restore(s_dict['tilemap'])
        level.bg_tilemap = TileMapObject.restore(s_dict['bg_tilemap']) if s_dict.get('bg_tilemap', None) else None
        level.party = s_dict.get('party', "")
        level.roam = s_dict.get('roam', False)
        level.roam_unit = s_dict.get('roam_unit')

        level.music = s_dict.get('music', {})
        level.objective = s_dict.get('objective', {})

        level.units = Data([game.get_unit(unit_nid) for unit_nid in s_dict.get('units', [])])
        level.regions = Data([Region.restore(region) for region in s_dict.get('regions', [])])
        level.unit_groups = Data([UnitGroup.restore(unit_group) for unit_group in s_dict.get('unit_groups', [])])

        return level
