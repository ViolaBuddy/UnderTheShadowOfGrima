from app.constants import TILEX, TILEY

from app.utilities.data import Prefab
import app.map_maker.utilities as map_utils

class MapPrefab(Prefab):
    def __init__(self, nid):
        self.nid = nid
        self.width, self.height = TILEX, TILEY
        self.autotile_fps = 29

        self.pixmap = None
        
        self.terrain_grid = {}  # Key: Position, Value: Terrain Nids
        self.terrain_grid_to_update = set()  # Positions
        self.tile_grid = {}  # Key: Position, Value: Tileset Coordinate (twice as large on each axis)

        self.cliff_markers = [(0, 0)]  # Markers for how to point cliffs

    def reset_all(self):
        for position in self.terrain_grid:
            self.terrain_grid_to_update.add(position)

    def set(self, pos: tuple, old_terrain, new_terrain):
        if old_terrain and old_terrain.check_flood_fill:
            self._update_flood_fill(pos, old_terrain.check_flood_fill == 'diagonal')  # Need to check flood fill both before and after changing terrain
        self.terrain_grid[pos] = new_terrain.nid
        self.terrain_grid_to_update.add(pos)
        self._update_adjacent(pos)
        self._update_diagonal(pos)
        if new_terrain.check_flood_fill:
            self._update_flood_fill(pos, new_terrain.check_flood_fill == 'diagonal')

    def _update_adjacent(self, pos):
        # Now ask to update all the adjacent ones as well
        north, east, south, west = (pos[0], pos[1] - 1), (pos[0] + 1, pos[1]), (pos[0], pos[1] + 1), (pos[0] - 1, pos[1])
        if self.check_bounds(north) and self.get_terrain(north):
            self.terrain_grid_to_update.add(north)
        if self.check_bounds(east) and self.get_terrain(east):
            self.terrain_grid_to_update.add(east)
        if self.check_bounds(south) and self.get_terrain(south):
            self.terrain_grid_to_update.add(south)
        if self.check_bounds(west) and self.get_terrain(west):
            self.terrain_grid_to_update.add(west)

    def _update_diagonal(self, pos):
        # Now ask to update all the adjacent ones as well
        northeast, southeast, southwest, northwest = (pos[0] + 1, pos[1] - 1), (pos[0] + 1, pos[1] + 1), (pos[0] - 1, pos[1] + 1), (pos[0] - 1, pos[1] - 1)
        if self.check_bounds(northeast) and self.get_terrain(northeast):
            self.terrain_grid_to_update.add(northeast)
        if self.check_bounds(southeast) and self.get_terrain(southeast):
            self.terrain_grid_to_update.add(southeast)
        if self.check_bounds(southwest) and self.get_terrain(southwest):
            self.terrain_grid_to_update.add(southwest)
        if self.check_bounds(northwest) and self.get_terrain(northwest):
            self.terrain_grid_to_update.add(northwest)

    def _update_flood_fill(self, pos, diagonal=False):
        blob_positions = map_utils.flood_fill(self, pos, diagonal)
        for p in blob_positions:
            self.terrain_grid_to_update.add(p)

    def get_terrain(self, pos: tuple) -> str:
        return self.terrain_grid.get(pos)

    def erase_terrain(self, pos: tuple, old_terrain):
        if old_terrain and old_terrain.check_flood_fill:
            self._update_flood_fill(pos, old_terrain.check_flood_fill == 'diagonal')
        if pos in self.terrain_grid:
            del self.terrain_grid[pos]

        if (pos[0] * 2, pos[1] * 2) in self.tile_grid:
            del self.tile_grid[(pos[0] * 2, pos[1] * 2)]
        if (pos[0] * 2 + 1, pos[1] * 2) in self.tile_grid:
            del self.tile_grid[(pos[0] * 2 + 1, pos[1] * 2)]
        if (pos[0] * 2 + 1, pos[1] * 2 + 1) in self.tile_grid:
            del self.tile_grid[(pos[0] * 2 + 1, pos[1] * 2 + 1)]
        if (pos[0] * 2, pos[1] * 2 + 1) in self.tile_grid:
            del self.tile_grid[(pos[0] * 2, pos[1] * 2 + 1)]

        self._update_adjacent(pos)
        self._update_diagonal(pos)

    def get_cardinal_terrain(self, pos: tuple) -> tuple:
        north = self.get_terrain((pos[0], pos[1] - 1))
        east = self.get_terrain((pos[0] + 1, pos[1]))
        south = self.get_terrain((pos[0], pos[1] + 1))
        west = self.get_terrain((pos[0] - 1, pos[1]))
        return north, east, south, west

    def get_diagonal_terrain(self, pos: tuple) -> tuple:
        northeast = self.get_terrain((pos[0] + 1, pos[1] - 1))
        southeast = self.get_terrain((pos[0] + 1, pos[1] + 1))
        southwest = self.get_terrain((pos[0] - 1, pos[1] + 1))
        northwest = self.get_terrain((pos[0] - 1, pos[1] - 1))
        return northeast, southeast, southwest, northwest

    def clear(self):
        self.width, self.height = TILEX, TILEY
        self.terrain_grid.clear()
        self.terrain_grid_to_update.clear()
        self.tile_grid.clear()

    def check_bounds(self, pos):
        return 0 <= pos[0] < self.width and 0 <= pos[1] < self.height

    def get_all_terrain(self, terrain_nid: str) -> set:
        all_positions = set()
        for position, nid in self.terrain_grid.items():
            if nid == terrain_nid:
                all_positions.add(position)
        return all_positions

    def resize(self, width, height, x_offset, y_offset):
        self.width = width
        self.height = height

        new_terrain_grid = {}
        for pos, terrain_nid in self.terrain_grid.items():
            new_pos = pos[0] + x_offset, pos[1] + y_offset
            if self.check_bounds(new_pos):
                new_terrain_grid[new_pos] = terrain_nid
        self.terrain_grid = new_terrain_grid

        new_tile_grid = {}
        for pos, tile_coord in self.tile_grid.items():
            new_pos = pos[0] + x_offset * 2, pos[1] + y_offset * 2
            if self.check_bounds((new_pos[0]//2, new_pos[1]//2)):
                new_tile_grid[new_pos] = tile_coord
        self.tile_grid = new_tile_grid

    def save(self):
        s_dict = {}
        s_dict['nid'] = self.nid
        s_dict['size'] = self.width, self.height
        if self.width == 0 or self.height == 0:
            print("TileMap: Width or Height == 0!!!")
        s_dict['autotile_fps'] = self.autotile_fps
        s_dict['cliff_markers'] = self.cliff_markers[:]
        s_dict['terrain_grid'] = {}
        for coord, terrain_nid in self.terrain_grid.items():
            str_coord = "%d,%d" % (coord[0], coord[1])
            s_dict['terrain_grid'][str_coord] = terrain_nid
        s_dict['tile_grid'] = {}
        for coord, tile_coord in self.terrain_grid.items():
            str_coord = "%d,%d" % (coord[0], coord[1])
            str_tile_coord = "%d,%d" % (tile_coord[0], tile_coord[1])
            s_dict['tile_grid'][str_coord] = str_tile_coord
        return s_dict

    @classmethod
    def restore(cls, s_dict):
        self = cls(s_dict['nid'])
        self.width, self.height = s_dict['size']
        self.autotile_fps = s_dict.get('autotile_fps', 29)
        self.cliff_markers = s_dict.get('cliff_markers', [(0, 0)])
        self.cliff_markers = [tuple(_) for _ in self.cliff_markers]
        for str_coord, terrain_nid in s_dict['terrain_grid'].items():
            coord = tuple(int(_) for _ in str_coord.split(','))
            self.terrain_grid[coord] = terrain_nid
        for str_coord, str_tile_coord in s_dict['tile_grid'].items():
            coord = tuple(int(_) for _ in str_coord.split(','))
            tile_coord = tuple(int(_) for _ in str_tile_coord.split(','))
            self.tile_grid[coord] = tile_coord
        return self

    # Used only in tilemap editor
    def restore_edits(self, s_dict):
        self.width, self.height = s_dict['size']
        for str_coord, terrain_nid in s_dict['terrain_grid'].items():
            coord = tuple(int(_) for _ in str_coord.split(','))
            self.terrain_grid[coord] = terrain_nid
        for str_coord, str_tile_coord in s_dict['tile_grid'].items():
            coord = tuple(int(_) for _ in str_coord.split(','))
            tile_coord = tuple(int(_) for _ in str_tile_coord.split(','))
            self.tile_grid[coord] = tile_coord
        return self
