from app.data.constants import WINWIDTH, WINHEIGHT, TILEWIDTH, TILEHEIGHT, TILEX, TILEY, FRAMERATE
from app import utilities
from app.data import unit_object
from app.engine.sprites import SPRITES
from app.engine.fonts import FONT
from app.engine import engine, combat_calcs, icons
from app.engine.game_state import game

team_dict = {'player': 'blue',
             'enemy': 'red',
             'other': 'green',
             'enemy2': 'purple'}

class HealthBar():
    display_numbers = True

    def __init__(self, unit):
        self.unit = unit

        self.displayed_hp = self.unit.get_hp()
        self.old_hp = self.displayed_hp
        self.total_hp = game.equations.hitpoints(self.unit)

        self.transition_flag = False
        self.time_for_change = 200
        self.last_update = 0

    def set_hp(self, val):
        self.displayed_hp = val

    def update(self):
        # print(self.displayed_hp, self.unit.get_hp(), self.transition_flag)
        # Check to see if we should begin showing transition
        if self.displayed_hp != self.unit.get_hp() and not self.transition_flag:
            self.transition_flag = True
            self.time_for_change = max(200, abs(self.displayed_hp - self.unit.get_hp()) * 2 * FRAMERATE)  # 2 frames an hp point
            self.last_update = engine.get_time()

        # Check to see if we should update
        if self.transition_flag:
            time = (engine.get_time() - self.last_update) / self.time_for_change
            new_val = self.old_hp + int(utilities.lerp(self.old_hp, self.unit.get_hp(), time))
            self.set_hp(new_val)
            if time >= 1:
                self.set_hp(self.unit.get_hp())
                self.old_hp = self.displayed_hp
                self.transition_flag = False

    def draw(self, surf):
        fraction_hp = self.displayed_hp / self.total_hp
        index_pixel = int(50 * fraction_hp)
        position = 25, 22
        surf.blit(engine.subsurface(SPRITES.get('health_bar'), (0, 0, index_pixel, 2)), position)

        # Blit HP number
        if self.display_numbers:
            font = FONT['number_small2']
            if self.transition_flag:
                font = FONT['number_big2']
            s = str(self.displayed_hp)
            position = 22 - font.size(s)[0], 15
            font.blit(s, surf, position)

        return surf

class MapCombatInfo():
    blind_speed = 1/8.  # 8 frames to fade in

    def __init__(self, draw_method, unit, item, target, stats):
        self.skill_icons = []
        self.ordering = None

        self.reset()
        self.change_unit(unit, item, target, stats, draw_method)
        # self.fade_in()

    def change_unit(self, unit, item, target=None, stats=None, draw_method=None):
        if draw_method:
            self.draw_method = draw_method
            self.true_position = None

        if unit != self.unit or target != self.target:
            self.fade_in()
        else:
            self.blinds = 1

        self.hp_bar = HealthBar(unit)
        self.unit = unit
        self.item = item
        if target:
            self.target = target
        if stats:
            self.hit = stats[0]
            self.mt = stats[1]

        self.skill_icons.clear()

        # Handle surfaces
        team = 'enemy' if not isinstance(unit, unit_object.UnitObject) else unit.team

        self.stats_surf = None
        self.bg_surf = SPRITES.get('health_' + team_dict[team]).convert_alpha()
        self.c_surf = SPRITES.get('combat_stats_' + team_dict[team]).convert_alpha()
        self.gem = SPRITES.get('combat_gem_' + team_dict[team]).convert_alpha()

    def reset(self):
        self.draw_method = None
        self.true_position = None

        self.hp_bar = None
        self.unit = None
        self.item = None
        self.target = None
        self.hit = None
        self.mt = None

        self.blinds = 1
        self.reset_shake()

        self.stats_surf = None
        self.bg_surf = None
        self.c_surf = None
        self.gem = None

        self.skill_icons.clear()

    def fade_in(self):
        self.blinds = 0

    def fade_out(self):
        pass

    def shake(self, num):
        self.current_shake_idx = 1
        if num == 1:  # Normal hit
            self.shake_set = [(-3, -3), (0, 0), (3, 3), (0, 0)]
        elif num == 2:  # Kill
            self.shake_set = [(3, 3), (0, 0), (0, 0), (3, 3), (-3, -3), (3, 3), (-3, -3), (0, 0)]
        elif num == 3:  # Crit
            self.shake_set = [(3, 3), (0, 0), (0, 0), (-3, -3), (0, 0), (0, 0), (3, 3), (0, 0), (-3, -3), (0, 0), (3, 3), (0, 0), (-3, -3), (3, 3), (0, 0)]

    def reset_shake(self):
        self.shake_set = [(0, 0)]  # How the hp bar will shake
        self.shake_offset = (0, 0)  # How it is currently shaking
        self.current_shake_idx = 0

    def handle_shake(self):
        if self.current_shake_idx:
            self.shake_offset = self.shake_set[self.current_shake_idx - 1]
            self.current_shake_idx += 1
            if self.current_shake_idx > len(self.shake_set):
                self.current_shake_idx = 0

    def build_stat_surf(self):
        stat_surf = self.c_surf.copy()
        # Blit hit
        if self.hit is not None:
            hit = str(self.hit)
        else:
            hit = '--'
        position = stat_surf.get_width() // 2 - FONT['number_small2'].size(hit)[0] - 1, -2
        FONT['number_small2'].blit(hit, stat_surf, position)
        # Blit damage
        if self.mt is not None:
            damage = str(self.mt)
        else:
            damage = '--'
        position = stat_surf.get_width() - FONT['number_small2'].size(damage)[0] - 2, -2
        FONT['number_small2'].blit(damage, stat_surf, position)
        return stat_surf

    def get_time_for_change(self):
        return self.hp_bar.time_for_change

    def force_position_update(self):
        if self.unit:
            width, height = self.bg_surf.get_width(), self.bg_surf.get_height()
            self.determine_position(width, height)

    def determine_position(self, width, height):
        self.true_position = self.draw_method
        if self.draw_method in ('p1', 'p2'):
            pos1 = self.unit.position
            pos2 = self.target.position
            camera_pos = game.camera.get_xy()
            if self.draw_method == 'p1':
                left = True if pos1[0] <= pos2[0] else False
            else:
                left = True if pos1[0] < pos2[0] else False
            self.ordering = 'left' if left else 'right'

            x_pos = WINWIDTH//2 - width if left else WINWIDTH//2
            rel_1 = pos1[1] - camera_pos[1]
            rel_2 = pos2[1] - camera_pos[1]

            # If both are on top of screen
            if rel_1 < TILEY//2 and rel_2 < TILEY//2:
                rel = max(rel_1, rel_2)
                y_pos = (rel + 1) * TILEHEIGHT + 12
            # If both are on bottom of screen
            elif rel_1 >= TILEY//2 and rel_2 >= TILEY//2:
                rel = min(rel_1, rel_2)
                y_pos = rel * TILEHEIGHT - 12 - height - 13  # Stat surf
            # Find largest gap and place it in the middle
            else:
                top_gap = min(rel_1, rel_2)
                bottom_gap = TILEY - 1 - max(rel_1, rel_2)
                middle_gap = abs(rel_1 - rel_2)
                if top_gap > bottom_gap and top_gap > middle_gap:
                    y_pos = top_gap * TILEHEIGHT - 12 - height - 13  # Stat surf
                elif bottom_gap > top_gap and bottom_gap > middle_gap:
                    y_pos = (bottom_gap + 1) * TILEHEIGHT + 12
                else:
                    y_pos = WINHEIGHT//4 - height//2 - 13//2 if rel_1 < TILEY//2 else 3*WINHEIGHT//4 - height//2 - 13//2
                    x_pos = WINWIDTH//4 - width//2 if pos1[0] - camera_pos[0] > TILEX//2 else 3*WINWIDTH//4 - width//2
                    self.ordering = 'middle'
            self.true_position = (x_pos, y_pos)

        elif self.draw_method == 'splash':
            x_pos = self.unit.position[0] - game.camera.get_x()
            x_pos = utilities.clamp(x_pos, 3, TILEX - 2)
            if self.unit.position[1] - game.camera.get_y() < TILEY//2:
                y_pos = self.unit.position[1] - game.camera.get_y() + 2
            else:
                y_pos = self.unit.position[1] - game.camera.get_y() - 3
            self.true_position = x_pos * TILEWIDTH - width//2, y_pos * TILEHEIGHT - 8
            self.ordering = 'middle'

    def update(self):
        # Make blinds wider
        self.blinds = utilities.clamp(self.blinds, self.blinds + self.blind_speed, 1)

        if self.unit and self.blinds >= 1:
            self.handle_shake()
            self.hp_bar.update()

    def draw(self, surf):
        # Create background surface
        width, height = self.bg_surf.get_width(), self.bg_surf.get_height()
        true_height = height + self.c_surf.get_height()
        if self.hit or self.mt:
            bg_surf = engine.create_surface((width, true_height))
        else:
            bg_surf = engine.create_surface((width, height))
        bg_surf.blit(self.bg_surf, (0, 0))

        # Name
        name_width = FONT['text_numbers'].size(self.unit.name)[0]
        position = width - name_width - 4, 3
        FONT['text_numbers'].blit(self.unit.name, bg_surf, position)

        # Item
        if self.item:
            # Determine effectiveness
            if self.target:
                if isinstance(self.target, unit_object.UnitObject) and game.targets.check_enemy(self.unit, self.target):
                    white = combat_calcs.get_effective(self.item, self.target)
                else:
                    white = True if self.item.extra_tile_damage else False
            else:
                white = False
            icons.draw_item(bg_surf, self.item, (2, 3), white)

            # Blit advantage
            if isinstance(self.target, unit_object.UnitObject) and game.targets.check_enemy(self.unit, self.target):
                adv = combat_calcs.compute_advantage(self.unit, self.item, self.target.get_weapon())
                disadv = combat_calcs.compute_advantage(self.unit, self.item, self.target.get_weapon(), False)
                if adv:
                    up_arrow = engine.subsurface(SPRITES.get('arrow_advantage'), (game.map_view.arrow_counter.count * 7, 0, 7, 10))
                    bg_surf.blit(up_arrow, (11, 7))
                elif disadv:
                    down_arrow = engine.subsurface(SPRITES.get('arrow_advantage'), (game.map_view.arrow_counter.count * 7, 10, 7, 10))
                    bg_surf.blit(down_arrow, (11, 7))
        # End item

        bg_surf = self.hp_bar.draw(bg_surf)

        # Blit stat surf
        if self.hit is not None or self.mt is not None:
            if not self.stats_surf:
                self.stats_surf = self.build_stat_surf()
            bg_surf.blit(self.stats_surf, (0, height))

        if not self.true_position:
            self.determine_position(width, height)

        if self.hit is not None or self.mt is not None:
            blit_surf = engine.subsurface(bg_surf, (0, true_height//2 - int(true_height * self.blinds // 2), width, int(true_height * self.blinds)))
            y_pos = self.true_position[1] + true_height//2 - int(true_height * self.blinds // 2)
        else:
            blit_surf = engine.subsurface(bg_surf, (0, height//2 - int(height * self.blinds // 2), width, int(height * self.blinds)))
            y_pos = self.true_position[1] + height//2 - int(height * self.blinds // 2)
        x, y = (self.true_position[0] + self.shake_offset[0], y_pos + self.shake_offset[1])
        surf.blit(blit_surf, (x, y))

        # Gem
        if self.blinds >= 1 and self.gem and self.ordering:
            if self.ordering == 'left':
                position = (x + 2, y - 3)
            elif self.ordering == 'right':
                position = (x + 56, y - 3)
            elif self.ordering == 'middle':
                position = (x + 27, y - 3)
            surf.blit(self.gem, position)

        # Draw skill icons
        for idx, skill_icon in enumerate(self.skill_icons):
            skill_icon.update()
            x, y = self.true_position + width // 2, self.true_position[1] - 16 * idx * 16
            skill_icon.draw(surf, (x, y))
        self.skill_icons = [s for s in self.skill_icons if not s.done]

        return surf
