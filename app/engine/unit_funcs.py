def get_next_level_up(self, unit):
    # TODO Implement support for negative growths
    if unit.team == 'player':
        mode = DB.constants.get('player_leveling').value
    else:
        mode = DB.constants.get('enemy_leveling').value
        if mode == 'Match':
            mode = DB.constants.get('player_leveling').value

    r = static_random.get_levelup(unit.nid, unit.get_internal_level * 100)

    stat_changes = {nid: 0 for nid in DB.stats.keys()}
    klass = DB.classes.get(unit.klass)
    if mode in ("Fixed", "Random", "Dynamic"):
        for nid in DB.stats.keys():
            growth = unit.growths[nid]
            if mode == 'Fixed':
                stat_changes[nid] = unit.growth_points[nid] + growth // 100
                stat_changes[nid] = min(stat_changes, klass.max_stats[nid] - unit.stats[nid])
                unit.growth_points[nid] = (unit.growth_points[nid] + growth) % 100
            elif mode == 'Random':
                while growth > 0:
                    stat_changes[nid] += 1 if r.randint(0, 99) < growth else 0
                    growth -= 100
                stat_changes[nid] = min(stat_changes, klass.max_stats[nid] - unit.stats[nid])
            elif mode == 'Dynamic':
                # Growth points used to modify growth 
                start_growth = growth + unit.growth_points[nid]
                while start_growth > 0:
                    if r.randint(0, 99) < int(start_growth):
                        stat_changes[nid] += 1
                        unit.growth_points[nid] -= (100 - growth)/5.
                        start_growth -= 100
                    else:
                        unit.growth_points[nid] += growth/5.
                stat_changes[nid] = min(stat_changes, klass.max_stats[nid] - unit.stats[nid])

