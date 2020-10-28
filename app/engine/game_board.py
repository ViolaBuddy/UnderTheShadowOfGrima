from app.data.database import DB

from app.engine import target_system

class Node():
    __slots__ = ['reachable', 'cost', 'x', 'y', 'parent', 'g', 'h', 'f']

    def __init__(self, x: int, y: int, reachable: bool, cost: float):
        """
        Initialize new cell
        reachable - is cell reachable? is not a wall?
        cost - how many movement points to reach
        """
        self.reachable = reachable
        self.cost = cost
        self.x = x
        self.y = y
        self.reset()

    def reset(self):
        self.parent = None
        self.g = 0
        self.h = 0
        self.f = 0

    def __gt__(self, n):
        return self.cost > n

    def __lt__(self, n):
        return self.cost < n

    def __repr__(self):
        return "Node(%d, %d): cost=%d, g=%d, h=%d, f=%f, %s" % (self.x, self.y, self.cost, self.g, self.h, self.f, self.reachable)

class GameBoard(object):
    # __slots__ = ['width', 'height', 'grids', 'team_grid', 'unit_grid', 
    #              'aura_grid', 'known_auras']

    def __init__(self, tilemap):
        self.width = tilemap.width
        self.height = tilemap.height
        self.mcost_grids = {}

        # For each movement type
        for idx, mode in enumerate(DB.mcost.unit_types):
            self.mcost_grids[mode] = self.init_grid(mode, tilemap)

        # Keeps track of what team occupies which tile
        self.team_grid = self.init_unit_grid()
        # Keeps track of which unit occupies which tile
        self.unit_grid = self.init_unit_grid()

        # Fog of War -- one for each team
        self.fog_of_war_grids = {}
        for team in DB.teams:
            self.fog_of_war_grids[team] = self.init_aura_grid()
        self.fow_vantage_point = {}  # Unit: Position where the unit is that's looking

        # For Auras
        self.aura_grid = self.init_aura_grid()
        # Key: Aura, Value: Set of positions
        self.known_auras = {}  

    def check_bounds(self, pos):
        return 0 <= pos[0] < self.width and 0 <= pos[1] < self.height

    # For movement
    def init_grid(self, mode, tilemap):
        cells = []
        for x in range(self.width):
            for y in range(self.height):
                terrain_nid = tilemap.get_terrain((x, y))
                terrain = DB.terrain.get(terrain_nid)
                tile_cost = DB.mcost.get_mcost(mode, terrain.mtype)
                cells.append(Node(x, y, tile_cost < 99, tile_cost))
        return cells

    def get_grid(self, mode):
        return self.mcost_grids[mode]

    def init_unit_grid(self):
        cells = []
        for x in range(self.width):
            for y in range(self.height):
                cells.append(None)
        return cells

    def set_unit(self, pos, unit):
        idx = pos[0] * self.height + pos[1]
        self.unit_grid[idx] = unit
        if unit:
            self.team_grid[idx] = unit.team
        else:
            self.team_grid[idx] = None

    def update_fow(self, pos, unit, sight_range: int):
        grid = self.fog_of_war_grids[unit.team]
        # Remove the old vision
        self.fow_vantage_point[unit.nid] = None
        for cell in grid:
            cell.discard(unit.nid)
        # Add new vision
        if pos:
            self.fow_vantage_point[unit.nid] = pos
            positions = target_system.find_manhattan_spheres(range(sight_range + 1), pos[0], pos[1])
            positions = {pos for pos in positions if 0 <= pos[0] < self.width and 0 <= pos[1] < self.height}
            for position in positions:
                idx = position[0] * self.height + position[1]
                grid[idx].add(unit.nid)

    def in_vision(self, pos, team='player') -> bool:
        idx = pos[0] * self.height + pos[1]
        if team == 'player':
            player_grid = self.fog_of_war_grids['player']
            if player_grid[idx]:
                return True
            other_grid = self.fog_of_war_grids['other']
            if other_grid[idx]:
                return True
        else:
            grid = self.fog_of_war_grids[team]
            if grid[idx]:
                return True
        return False

    def get_unit(self, pos):
        return self.unit_grid[pos[0] * self.height + pos[1]]

    def get_team(self, pos):
        return self.team_grid[pos[0] * self.height + pos[1]]

    def init_aura_grid(self):
        cells = []
        for x in range(self.width):
            for y in range(self.height):
                cells.append(set())
        return cells
