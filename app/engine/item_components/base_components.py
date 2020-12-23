from app.utilities import utils

from app.data.item_components import ItemComponent
from app.data.components import Type

from app.engine import skill_system, target_system, item_system, item_funcs
from app.engine.game_state import game 

class Spell(ItemComponent):
    nid = 'spell'
    desc = "Item will be treated as a spell (cannot counterattack or double)"
    tag = 'base'

    def is_spell(self, unit, item):
        return True

    def is_weapon(self, unit, item):
        return False

    def equippable(self, unit, item):
        return False

    def wexp(self, playback, unit, item, target):
        return 1

class Weapon(ItemComponent):
    nid = 'weapon'
    desc = "Item will be treated as a normal weapon (can double, counterattack, be equipped, etc.)" 
    tag = 'base'

    def is_weapon(self, unit, item):
        return True

    def is_spell(self, unit, item):
        return False

    def equippable(self, unit, item):
        return True

    def can_be_countered(self, unit, item):
        return True

    def can_counter(self, unit, item):
        return True

    def can_double(self, unit, item):
        return True

    def wexp(self, playback, unit, item, target):
        return 1

class SiegeWeapon(ItemComponent):
    nid = 'siege_weapon'
    desc = "Item will be treated as a siege weapon (can not double or counterattack, but can still be equipped)"
    tag = 'base'

    def is_weapon(self, unit, item):
        return True

    def is_spell(self, unit, item):
        return False

    def equippable(self, unit, item):
        return True

    def can_double(self, unit, item):
        return True

    def wexp(self, playback, unit, item, target):
        return 1

class TargetsAnything(ItemComponent):
    nid = 'target_tile'
    desc = "Item targets any tile"
    tag = 'target'

    def ai_targets(self, unit, item) -> set:
        return {(x, y) for x in game.map.width for y in game.map.height}

    def valid_targets(self, unit, item) -> set:
        rng = item_funcs.get_range(unit, item)
        return target_system.find_manhattan_spheres(rng, *unit.position)

class TargetsUnits(ItemComponent):
    nid = 'target_unit'
    desc = "Item targets any unit"
    tag = 'target'

    def ai_targets(self, unit, item):
        return {other.position for other in game.level.units if other.position}

    def valid_targets(self, unit, item) -> set:
        targets = {other.position for other in game.level.units if other.position}
        return {t for t in targets if utils.calculate_distance(unit.position, t) in item_funcs.get_range(unit, item)}

class TargetsEnemies(ItemComponent):
    nid = 'target_enemy'
    desc = "Item targets any enemy"
    tag = 'target'

    def ai_targets(self, unit, item):
        return {other.position for other in game.level.units if other.position and 
                skill_system.check_enemy(unit, other)}

    def valid_targets(self, unit, item, ai=False) -> set:
        targets = {other.position for other in game.level.units if other.position and 
                   skill_system.check_enemy(unit, other)}        
        return {t for t in targets if utils.calculate_distance(unit.position, t) in item_funcs.get_range(unit, item)}

class TargetsAllies(ItemComponent):
    nid = 'target_ally'
    desc = "Item targets any ally"
    tag = 'target'

    def ai_targets(self, unit, item):
        return {other.position for other in game.level.units if other.position and 
                skill_system.check_ally(unit, other)}

    def valid_targets(self, unit, item, ai=False) -> set:
        targets = {other.position for other in game.level.units if other.position and 
                   skill_system.check_ally(unit, other)}        
        return {t for t in targets if utils.calculate_distance(unit.position, t) in item_funcs.get_range(unit, item)}

class MinimumRange(ItemComponent):
    nid = 'min_range'
    desc = "Set the minimum_range of the item to an integer"
    tag = 'target'

    expose = Type.Int
    value = 0

    def minimum_range(self, unit, item) -> int:
        return self.value

class MaximumRange(ItemComponent):
    nid = 'max_range'
    desc = "Set the maximum_range of the item to an integer"
    tag = 'target'

    expose = Type.Int
    value = 0

    def maximum_range(self, unit, item) -> int:
        return self.value

class Usable(ItemComponent):
    nid = 'usable'
    desc = "Item is usable"
    tag = 'base'

    def can_use(self, unit, item):
        return True

class Value(ItemComponent):
    nid = 'value'
    desc = "Item has a value and can be bought and sold. Items sell for half their value."
    tag = 'base'
    
    expose = Type.Int
    value = 0

    def buy_price(self, unit, item):
        if item.uses:
            frac = item.data['uses'] / item.data['starting_uses']
            return int(self.value * frac)
        return self.value

    def sell_price(self, unit, item):
        if item.uses:
            frac = item.data['uses'] / item.data['starting_uses']
            return int(self.value * frac // 2)
        return self.value // 2
