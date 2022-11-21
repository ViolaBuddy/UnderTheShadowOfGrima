from __future__ import annotations

import json
import logging
import os
import re
import shutil
from typing import Any, Dict, List

from app.data.database import (ai, constants, difficulty_modes, equations, factions,
                      items, klass, levels, lore, mcost, minimap, overworld,
                      overworld_node, parties, raw_data, skills, stats, varslot,
                      supports, tags, terrain, translations, units, weapons)
from app.events import event_prefab


class Database(object):
    save_data_types = ("constants", "stats", "equations", "mcost", "terrain", "weapon_ranks",
                       "weapons", "factions", "items", "skills", "tags", "game_var_slots", "classes",
                       "support_constants", "support_ranks", "affinities", "units", "support_pairs",
                       "ai", "parties", "difficulty_modes",
                       "translations", "lore", "levels", "events", "overworlds", "raw_data")
    save_as_chunks = ("events", 'items', 'skills', 'units', 'classes', 'levels')

    def __init__(self):
        self.current_proj_dir = None

        self.constants = constants.constants
        self.teams = ["player", "enemy", "enemy2", "other"]  # Order determine phase order
        self.stats = stats.StatCatalog()
        self.equations = equations.EquationCatalog()
        self.mcost = mcost.McostGrid()
        self.terrain = terrain.TerrainCatalog()
        self.minimap = minimap.MinimapCatalog()
        self.weapon_ranks = weapons.RankCatalog()
        self.weapons = weapons.WeaponCatalog()
        self.factions = factions.FactionCatalog()
        self.items = items.ItemCatalog()
        self.skills = skills.SkillCatalog()
        self.tags = tags.TagCatalog(['Lord', 'Boss', 'Armor', 'Horse', 'Mounted', 'Dragon', 'ZeroMove', 'AutoPromote', 'NoAutoPromote'])
        self.game_var_slots = varslot.VarSlotCatalog([])
        self.classes = klass.ClassCatalog()

        self.support_constants = supports.constants
        self.support_ranks = supports.SupportRankCatalog(['C', 'B', 'A'])
        self.affinities = supports.AffinityCatalog()

        self.units = units.UnitCatalog()

        self.support_pairs = supports.SupportPairCatalog()

        self.parties = parties.PartyCatalog()
        self.ai = ai.AICatalog()
        self.difficulty_modes = difficulty_modes.DifficultyModeCatalog()

        self.overworlds = overworld.OverworldCatalog()

        self.levels = levels.LevelCatalog()
        self.events = event_prefab.EventCatalog()

        self.translations = translations.TranslationCatalog()
        self.lore = lore.LoreCatalog()

        self.raw_data = raw_data.RawDataCatalog()

    # Disk Interaction Functions
    def json_save(self, save_loc: str, value: Any):
        temp_save_loc = save_loc + ".tmp"
        with open(temp_save_loc, 'w') as serialize_file:
            json.dump(value, serialize_file, indent=4)
        os.replace(temp_save_loc, save_loc)

    def jsonsort(self, jsonobj):
        try:
            if isinstance(jsonobj, list):
                if all(['_orderkey' in obj.keys() for obj in jsonobj]):
                    return sorted(jsonobj, key=lambda obj: obj['_orderkey'])
            return jsonobj
        except:
            return jsonobj

    def json_load(self, data_dir: str, key: str) -> Dict | List:
        if os.path.exists(os.path.join(data_dir, key)): # data type is a directory, browse within
            data_fnames = os.listdir(os.path.join(data_dir, key))
            save_data = []
            for fname in data_fnames:
                if not fname.endswith('.json'): # ignore other files
                    continue
                save_loc = os.path.join(data_dir, key, fname)
                logging.info("Deserializing %s from %s" % (key, save_loc))
                with open(save_loc) as load_file:
                    for data in json.load(load_file):
                        data['fname'] = os.path.basename(fname)
                        save_data.append(data)
            if '.orderkeys' in data_fnames: # using order key file
                with open(os.path.join(data_dir, key, '.orderkeys')) as load_file:
                    orderkeys = json.load(load_file)
                    return sorted(save_data, key=lambda data: orderkeys.get(data['fname'], 999999))
            else: # using order keys per object, or no order keys at all
                return self.jsonsort(save_data)
        else:
            save_loc = os.path.join(data_dir, key + '.json')
            if os.path.exists(save_loc):
                logging.info("Deserializing %s from %s" % (key, save_loc))
                with open(save_loc) as load_file:
                    try:
                        return json.load(load_file)
                    except Exception as e:
                        logging.error("failed file load at %s" % load_file)
                        raise e
            else:
                logging.warning("%s does not exist!" % save_loc)
                return []

    # === Saving and loading important data functions ===
    def restore(self, save_obj):
        for data_type in self.save_data_types:
            logging.info("Database: Restoring %s..." % (data_type))
            getattr(self, data_type).restore(save_obj[data_type])

    def save(self):
        # import time
        to_save = {}
        for data_type in self.save_data_types:
            # logging.info("Saving %s..." % data_type)
            # time1 = time.time_ns()/1e6
            to_save[data_type] = getattr(self, data_type).save()
            # time2 = time.time_ns()/1e6 - time1
            # logging.info("Time taken: %s ms" % time2)
        return to_save

    def serialize(self, proj_dir):
        data_dir = os.path.join(proj_dir, 'game_data')
        if not os.path.exists(data_dir):
            os.mkdir(data_dir)
        logging.warning("Serializing data in %s..." % data_dir)

        import time
        start = time.perf_counter() * 1000

        to_save = self.save()
        # This section is what takes so long!
        for key, value in to_save.items():
            if key not in self.save_as_chunks:
                save_loc = os.path.join(data_dir, key + '.json')
                logging.info("Serializing %s to %s" % (key, save_loc))
                self.json_save(save_loc, value)
            else: # divide save data into chunks based on key value
                save_dir = os.path.join(data_dir, key)
                if os.path.exists(save_dir):
                    shutil.rmtree(save_dir)
                os.mkdir(save_dir)
                orderkeys: Dict[str, int] = {}
                for idx, subvalue in enumerate(value):
                    # ordering
                    if 'nid' in subvalue:
                        name = subvalue['nid']
                    elif 'name' in subvalue:
                        if 'level_nid' in subvalue.keys(): # to handle the wonky event nid property
                            name = (subvalue['level_nid'] if subvalue['level_nid'] else 'global') + "_" + subvalue['name']
                        else:
                            name = subvalue['name']
                    else:
                        name = str(idx).zfill(6)
                    name = re.sub(r'[\\/*?:"<>|]', "", name)
                    name = name.replace(' ', '_')
                    fname = name + '.json'
                    orderkeys[fname] = idx
                    save_loc = os.path.join(save_dir, name + '.json')
                    logging.info("Serializing %s to %s" % ('%s/%s.json' % (key, name), save_loc))
                    self.json_save(save_loc, [subvalue])
                self.json_save(os.path.join(save_dir, '.orderkeys'), orderkeys)

        end = time.perf_counter() * 1000
        logging.warning("Total Time Taken for Database: %s ms" % (end - start))
        logging.warning("Done serializing!")

    def load(self, proj_dir):
        self.current_proj_dir = proj_dir
        data_dir = os.path.join(proj_dir, 'game_data')
        logging.warning("Deserializing data from %s..." % data_dir)

        import time
        start = time.perf_counter() * 1000

        save_obj = {}
        for key in self.save_data_types:
            save_obj[key] = self.json_load(data_dir, key)

        self.restore(save_obj)

        end = time.perf_counter() * 1000

        logging.warning("Total Time Taken for Database: %s ms" % (end - start))
        logging.warning("Done deserializing!")

DB = Database()

# Testing
# Run "python -m app.data.database.database" from main directory
