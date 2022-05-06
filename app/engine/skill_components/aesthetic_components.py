from app.data.skill_components import SkillComponent, SkillTags
from app.data.components import Type

from app.engine import equations, action, item_system, item_funcs
from app.engine.game_state import game
from app.engine.combat import playback as pb

class UnitAnim(SkillComponent):
    nid = 'unit_anim'
    desc = "Displays MapAnimation over unit"
    tag = SkillTags.AESTHETIC

    expose = Type.MapAnimation

    def on_add(self, unit, skill):
        unit.sprite.add_animation(self.value)

    def re_add(self, unit, skill):
        unit.sprite.add_animation(self.value)

    def on_remove(self, unit, skill):
        unit.sprite.remove_animation(self.value)

class UnitFlickeringTint(SkillComponent):
    nid = 'unit_flickering_tint'
    desc = "Displays a flickering tint on the unit"
    tag = SkillTags.AESTHETIC

    expose = Type.Color3

    def unit_sprite_flicker_tint(self, unit, skill) -> tuple:
        return (self.value, 900, 300)

class UpkeepAnimation(SkillComponent):
    nid = 'upkeep_animation'
    desc = "Displays map animation at beginning of turn"
    tag = SkillTags.AESTHETIC

    expose = Type.MapAnimation

    def on_upkeep(self, actions, playback, unit):
        playback.append(pb.CastAnim(self.value, unit))

# Get proc skills working before bothering with this one
class DisplaySkillIconInCombat(SkillComponent):
    nid = 'display_skill_icon_in_combat'
    desc = "Displays the skill's icon in combat"
    tag = SkillTags.AESTHETIC

    def display_skill_icon(self, unit) -> bool:
        return True

# Show steal icon
class StealIcon(SkillComponent):
    nid = 'steal_icon'
    desc = "Displays icon above units with stealable items"
    tag = SkillTags.AESTHETIC

    def steal_icon(self, unit, target) -> bool:
        # Unit has item that can be stolen
        attack = equations.parser.steal_atk(unit)
        defense = equations.parser.steal_def(target)
        if attack >= defense:
            for def_item in target.items:
                if self._item_restrict(unit, target, def_item):
                    return True
        return False

    def _item_restrict(self, unit, defender, def_item) -> bool:
        if item_system.unstealable(defender, def_item):
            return False
        if item_funcs.inventory_full(unit, def_item):
            return False
        if def_item is defender.get_weapon():
            return False
        return True

class GBAStealIcon(StealIcon, SkillComponent):
    nid = 'gba_steal_icon'

    def _item_restrict(self, unit, defender, def_item) -> bool:
        if item_system.unstealable(defender, def_item):
            return False
        if item_funcs.inventory_full(unit, def_item):
            return False
        if item_system.is_weapon(defender, def_item) or item_system.is_spell(defender, def_item):
            return False
        return True

class AlternateBattleAnim(SkillComponent):
    nid = 'alternate_battle_anim'
    desc = "Use a specific pose when attacking in an animation combat (except on miss)"
    tag = SkillTags.AESTHETIC

    expose = Type.String
    value = 'Critical'

    def after_hit(self, actions, playback, unit, item, target, mode, attack_info):
        marks = [mark.nid for mark in playback]
        if 'mark_hit' in marks or 'mark_crit' in marks:
            playback.append(pb.AlternateBattlePose(self.value))

class ChangeVariant(SkillComponent):
    nid = 'change_variant'
    desc = "Change the unit's variant"
    tag = SkillTags.AESTHETIC

    expose = Type.String
    value = ''

    def change_variant(self, unit):
        return self.value

class ChangeAnimation(SkillComponent):
    nid = 'change_animation'
    desc = "Change the unit's animation"
    tag = SkillTags.AESTHETIC

    expose = Type.String
    value = ''

    def change_animation(self, unit):
        return self.value

class MapCastAnim(SkillComponent):
    nid = 'map_cast_anim'
    desc = "Adds a map animation on cast"
    tag = SkillTags.AESTHETIC

    expose = Type.MapAnimation

    def start_combat(self, playback, unit, item, target, mode):
        playback.append(pb.CastAnim(self.value))
