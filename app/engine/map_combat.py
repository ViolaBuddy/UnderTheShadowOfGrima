from app.data.constants import TILEWIDTH, TILEHEIGHT
from app.resources.resources import RESOURCES

from app.engine.solver import CombatPhaseSolver

from app.engine.sound import SOUNDTHREAD
from app.engine import engine, combat_calcs, gui, action
from app.engine.health_bar import MapCombatInfo
from app.engine.animations import MapAnimation
from app.engine.game_state import game

class MapCombat():
    def __init__(self, attacker, item, position, main_target, splash):
        self.target_position = position
        self.attacker = attacker
        self.defender = main_target
        self.splash = splash

        self.item = item
        self.def_item = self.defender.get_equipped_weapon() if self.defender else None

        self.state_machine = CombatPhaseSolver(attacker, main_target, splash, item)

        self.last_update = engine.get_time()
        self.state = 'begin_phase'
        self.hp_bar_time = 400

        self._skip = False
        self.playback = []
        self.actions = []

        self.animations = []
        self.damage_numbers = []
        self.health_bars = {}

    def skip(self):
        self._skip = True
        self.attacker.sprite.reset()
        if self.defender:
            self.defender.sprite.reset()

    def get_from_playback(self, s):
        return [brush for brush in self.playback if brush[0] == s]

    def update(self) -> bool:
        current_time = engine.get_time() - self.last_update

        if self.state == 'begin_phase':
            # Get playback
            if not self.state_machine.get_state():
                return True
            self.actions, self.playback = self.state_machine.do()
            self._build_health_bars()

            # Camera
            if self.get_from_playback('defender_phase'):
                game.cursor.set_pos(self.attacker.position)
            else:
                if self.defender:
                    game.cursor.set_pos(self.defender.position)
                else:
                    game.cursor.set_pos(self.target_position)
            if not self._skip:
                game.state.change('move_camera')

            # Sprites
            if self.get_from_playback('defender_phase'):
                self.defender.sprite.change_state('combat_attacker')
                self.attacker.sprite.change_state('combat_defender')
            else:
                self.attacker.sprite.change_state('combat_attacker')
                if self.defender:
                    self.defender.sprite.change_state('combat_defender')
            # for unit in self.splash:
            #     unit.sprite.change_state('combat_defender')
            self.state = 'red_cursor'

        elif self.state == 'red_cursor':
            if self.defender:
                game.cursor.combat_show()
            elif any(unit.position == self.target_position for unit in self.splash):
                game.cursor.combat_show()
            else:
                game.cursor.hide()
            self.state = 'start_anim'
            self.last_update = engine.get_time()

        elif self.state == 'start_anim':
            if self._skip or current_time > 400:
                game.cursor.hide()
                game.highlight.remove_highlights()
                animation_brushes = self.playback.get_from_playback('cast_anim')
                for brush in animation_brushes:
                    anim = RESOURCES.animations.get(brush[1])
                    pos = game.cursor.position
                    if anim:
                        anim = MapAnimation(anim, pos)
                        self.animations.append(anim)
                self.state = 'sound'
                self.last_update = engine.get_time()

        elif self.state == 'sound':
            if self._skip or current_time > 400:
                if self.defender and self.defender.sprite.state == 'combat_attacker':
                    self.defender.sprite.change_state('combat_anim')
                else:
                    self.attacker.sprite.change_state('combat_anim')
                sound_brushes = self.playback.get_from_playback('cast_sound')
                for brush in sound_brushes:
                    SOUNDTHREAD.play_sfx(brush[1])

                self.state = 'anim'
                self.last_update = engine.get_time()

        elif self.state == 'anim':
            if self._skip or current_time > 400:
                if self.defender and self.defender.sprite.state == 'combat_anim':
                    self.defender.sprite.change_state('combat_attacker')
                else:
                    self.attacker.sprite.change_state('combat_attacker')

                self._handle_playback()
                self._apply_actions()

                # Force update hp bars so we can get timing info
                for hp_bar in self.health_bars.value():
                    hp_bar.update()
                if self.health_bars:
                    self.hp_bar_time = max(hp_bar.get_time_for_change() for hp_bar in self.hp_bars.values())
                else:
                    self.hp_bar_time = 400
                self.state = 'hp_bar_wait'
                self.last_update = engine.get_time()

        elif self.state == 'hp_bar_wait':
            if self._skip or current_time > self.hp_bar_time:
                self.state = 'end_phase'
                self.last_update = engine.get_time()

        elif self.state == 'wait':
            if self._skip or current_time > 400:
                self._end_phase()
                self.state = 'begin_phase'

        if self.state not in ('begin_phase', 'red_cursor'):
            for hp_bar in self.health_bars.values():
                hp_bar.update()

        return False

    def _build_health_bars(self):
        if (self.defender and self.splash) or len(self.splash) > 1:
            # Many splash attacks
            # No health bars!!
            self.health_bars.clear()

        else:
            # P1 on P1
            if self.defender and self.attacker is self.defender:
                hit = combat_calcs.compute_hit(self.attacker, self.defender, self.item, 'Attack')
                mt = combat_calcs.compute_damage(self.attacker, self.defender, self.item, 'Attack')
                if self.attacker not in self.health_bars:
                    attacker_health = MapCombatInfo('p1', self.attacker, self.item, self.defender, (hit, mt))
                    self.health_bars[self.attacker] = attacker_health

            # P1 on P2
            elif self.defender:
                hit = combat_calcs.compute_hit(self.attacker, self.defender, self.item, 'Attack')
                mt = combat_calcs.compute_damage(self.attacker, self.defender, self.item, 'Attack')
                if self.attacker not in self.health_bars:
                    attacker_health = MapCombatInfo('p1', self.attacker, self.item, self.defender, (hit, mt))
                    self.health_bars[self.attacker] = attacker_health

                if self.get_from_playback('defender_phase'):
                    hit = combat_calcs.compute_hit(self.defender, self.attacker, self.def_item, 'Defense')
                    mt = combat_calcs.compute_damage(self.defender, self.attacker, self.def_item, 'Defense')
                else:
                    hit, mt = None, None
                if self.defender not in self.health_bars:
                    defender_health = MapCombatInfo('p2', self.defender, self.def_item, self.attacker, (hit, mt))
                    self.health_bars[self.defender] = defender_health

            # P1 on single splash
            elif len(self.splash) == 1:
                hit = combat_calcs.compute_hit(self.attacker, self.defender, self.item, 'Attack')
                mt = combat_calcs.compute_damage(self.attacker, self.defender, self.item, 'Attack')
                if self.attacker not in self.health_bars:
                    attacker_health = MapCombatInfo('p1', self.attacker, self.item, self.defender, (hit, mt))
                    self.health_bars[self.attacker] = attacker_health
                if self.defender not in self.health_bars:
                    splash_health = MapCombatInfo('splash', self.defender, None, self.attacker, (None, None))
                    self.health_bars[self.defender] = splash_health

    def _handle_playback(self):
        for brush in self.playback:
            if brush[0] == 'unit_tint':
                color = brush[2]
                brush[1].sprite.begin_flicker(400, color)
            elif brush[0] == 'hit_sound':
                sound = brush[1]
                SOUNDTHREAD.play_sfx(sound)
            elif brush[0] == 'shake':
                shake = brush[1]
                for health_bar in self.health_bars.values():
                    health_bar.shake(shake)
            elif brush[0] == 'hit_anim':
                anim = RESOURCES.animations.get(brush[1])
                pos = brush[2].position
                if anim and pos:
                    anim = MapAnimation(anim, pos)
                    self.animations.append(anim)
            elif brush[0] == 'damage_hit':
                damage = brush[4]
                if damage <= 0:
                    continue
                str_damage = str(damage)
                left = brush[3].position
                for idx, num in enumerate(str_damage):
                    d = gui.DamageNumber(int(num), idx, len(str_damage), left, 'small_red')
                    self.damage_numbers.append(d)
            elif brush[0] == 'damage_crit':
                damage = brush[4]
                if damage <= 0:
                    continue
                str_damage = str(damage)
                left = brush[3].position
                for idx, num in enumerate(str_damage):
                    d = gui.DamageNumber(int(num), idx, len(str_damage), left, 'small_yellow')
                    self.damage_numbers.append(d)
            elif brush[0] == 'heal_hit':
                damage = brush[4]
                if damage <= 0:
                    continue
                str_damage = str(damage)
                left = brush[3].position
                for idx, num in enumerate(str_damage):
                    d = gui.DamageNumber(int(num), idx, len(str_damage), left, 'small_cyan')
                    self.damage_numbers.append(d)

    def _apply_actions(self):
        """
        Actually commit the actions that we had stored!
        """
        for act in self.actions:
            action.do(act)

    def _end_phase(self):
        pass

    def draw(self, surf):
        for hp_bar in self.health_bars.values():
            hp_bar.draw(surf)

        # Animations
        self.animations = [anim for anim in self.animations if not anim.update()]
        for anim in self.animations:
            anim.draw(surf)

        # Damage Nums
        for damage_num in self.damage_numbers:
            damage_num.update()
            position = damage_num.left
            c_pos = game.camera.get_xy()
            rel_x = position[0] - c_pos[0]
            rel_y = position[1] - c_pos[1]
            damage_num.draw(surf, (rel_x * TILEWIDTH + 4, rel_y * TILEHEIGHT))
        self.damage_numbers = [d for d in self.damage_numbers if not d.done]

        return surf