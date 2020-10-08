import os
import xml.etree.ElementTree as ET

from app.utilities import str_utils
from app.resources.resources import RESOURCES
from app.data.database import DB
from app.data import units

from app.data import stats, weapons, skills

def get_from_xml(parent_dir: str, xml_fn: str) -> list:
    unit_xml = ET.parse(xml_fn)
    unit_list = []
    for unit in unit_xml.getroot().findall('unit'):
        nid = unit.find('id').text
        name = unit.get('name')
        desc = unit.find('desc').text
        klass = unit.find('class').text.split(',')[-1]
        if klass not in DB.classes.keys():
            klass = DB.classes[0].nid
        level = int(unit.find('level').text)
        tags = set(unit.find('tags').text.split(',')) if unit.find('tags') is not None and unit.find('tags').text is not None else set()
        tags = [t for t in tags if t in DB.tags.keys()]

        # Handle stats
        stat_list = ('HP', 'STR', 'MAG', 'SKL', 'SPD', 'LCK', 'DEF', 'RES', 'CON', 'MOV')
        unit_stats = str_utils.intify(unit.find('bases').text)
        bases = stats.StatList.default(DB)
        for idx, num in enumerate(unit_stats):
            s = bases.get(stat_list[idx])
            if s:
                s.value = num
        unit_growths = str_utils.intify(unit.find('growths').text)
        growths = stats.StatList.default(DB)
        for idx, num in enumerate(unit_growths):
            s = growths.get(stat_list[idx])
            if s:
                s.value = num

        # Create weapon experience
        wexp = unit.find('wexp').text.split(',')
        wexp_gain = weapons.WexpGainList.default(DB)
        weapon_order = ['Sword', 'Lance', 'Axe', 'Bow', 'Light', 'Anima', 'Dark']
        if os.path.exists(parent_dir + '/weapon_triangle.txt'):
            with open(parent_dir + '/weapon_triangle.txt') as wfn:
                weapon_order = [l.strip().split(';')[0] for l in wfn.readlines() if l.strip()]
        for idx, w in enumerate(wexp):
            if w in DB.weapon_ranks.keys():
                num = DB.weapon_ranks.get(w).requirement
            else:
                num = int(w)
            if weapon_order[idx] in DB.weapons.keys():
                gain = wexp_gain.get(weapon_order[idx])
                gain.wexp_gain = num
                if num > 0:
                    gain.usable = True

        inventory = unit.find('inventory').text
        items = []
        for item in inventory.split(','):
            if item.startswith('d'):
                item = item[1:]
                if item in DB.items.keys():
                    items.append((item, True))
            elif item in DB.items.keys():
                items.append((item, False))

        personal_skills = unit.find('skills').text.split(',') if unit.find('skills') is not None and unit.find('skills').text is not None else []
        personal_skills = [skills.LearnedSkill(1, s) for s in personal_skills]
        portrait = nid if nid in RESOURCES.portraits.keys() else None
        new_unit = units.UnitPrefab(
            nid, name, desc, None, level, klass, tags, 
            bases, growths, items, personal_skills, 
            wexp_gain, None, portrait)
        unit_list.append(new_unit)

    return unit_list