from functools import lru_cache
from app.utilities.data import Data
from app.data.database.components import ComponentType
from app.data.database.item_components import ItemComponent, ItemTags
from app.data.resources.resources import RESOURCES

@lru_cache(1)
def get_cached_item_components(proj_dir: str):
    # Necessary for get_item_components to find all the
    # item components defined in item_components folder
    from app.engine import item_components

    if RESOURCES.has_loaded_custom_components():
        # Necessary for get_item_components to find the item component subclasses
        # defined here
        import custom_components

    subclasses = ItemComponent.__subclasses__()
    # Sort by tag
    subclasses = sorted(subclasses, key=lambda x: list(ItemTags).index(x.tag) if x.tag in list(ItemTags) else 100)
    return Data(subclasses)

def get_item_components():
    from app.data.database.database import DB
    return get_cached_item_components(DB.current_proj_dir)

def get_item_tags():
    return list(ItemTags)

def get_component(nid):
    _item_components = get_item_components()
    base_class = _item_components.get(nid)
    if base_class:
        return base_class(base_class.value)
    return None

def restore_component(dat):
    nid, value = dat
    _item_components = get_item_components()
    base_class = _item_components.get(nid)
    if base_class:
        if isinstance(base_class.expose, tuple):
            if base_class.expose[0] == ComponentType.List:
                # Need to make a copy
                # so we don't keep the reference around
                copy = base_class(value.copy())
            elif base_class.expose[0] in (ComponentType.Dict, ComponentType.FloatDict):
                val = [v.copy() for v in value]
                copy = base_class(val)
            else:
                copy = base_class(value)
        else:
            copy = base_class(value)
        return copy
    return None

templates = {'Weapon Template': ('weapon', 'value', 'target_enemy', 'min_range', 'max_range', 'damage', 'hit', 'crit', 'weight', 'level_exp', 'weapon_type', 'weapon_rank'),
             'Magic Weapon Template': ('weapon', 'value', 'target_enemy', 'min_range', 'max_range', 'damage', 'hit', 'crit', 'weight', 'level_exp', 'weapon_type', 'weapon_rank', 'magic'),
             'Spell Template': ('spell', 'value', 'min_range', 'max_range', 'weapon_type', 'weapon_rank', 'magic'),
             'Usable Template': ('usable', 'value', 'target_ally', 'uses')}

def get_templates():
    return templates.items()
