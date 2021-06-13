from app.data.skill_components import SkillComponent
from app.data.components import Type

from app.engine import action

class BuildCharge(SkillComponent):
    nid = 'build_charge'
    desc = "Skill gains charges until full"
    tag = "charge"

    expose = Type.Int
    value = 10

    ignore_conditional = True

    def init(self, skill):
        self.skill.data['charge'] = 0
        self.skill.data['total_charge'] = self.value

    def condition(self, unit):
        return self.skill.data['charge'] >= self.skill.data['total_charge']

    def on_end_chapter(self, unit, skill):
        self.skill.data['charge'] = 0

    def trigger_charge(self, unit, skill):
        action.do(action.SetObjData(self.skill, 'charge', 0))

    def text(self) -> str:
        return str(self.skill.data['charge'])

    def cooldown(self):
        return self.skill.data['charge'] / self.skill.data['total_charge']

class DrainCharge(SkillComponent):
    nid = 'drain_charge'
    desc = "Skill will have a number of charges that are drained by 1 when activated"
    tag = "charge"

    expose = Type.Int
    value = 1

    ignore_conditional = True

    def init(self, skill):
        self.skill.data['charge'] = self.value
        self.skill.data['total_charge'] = self.value

    def condition(self, unit):
        return self.skill.data['charge'] > 0

    def on_end_chapter(self, unit, skill):
        self.skill.data['charge'] = self.skill.data['total_charge']

    def trigger_charge(self, unit, skill):
        new_value = self.skill.data['charge'] - 1
        action.do(action.SetObjData(self.skill, 'charge', new_value))

    def text(self) -> str:
        return str(self.skill.data['charge'])

    def cooldown(self):
        return self.skill.data['charge'] / self.skill.data['total_charge']

def get_marks(playback, unit, item):
    from app.data.database import DB
    marks = [mark for mark in playback if mark[0] == 'mark_hit']
    marks += [mark for mark in playback if mark[0] == 'mark_crit']
    if DB.constants.value('miss_wexp'):
        marks += [mark for mark in playback if mark[0] == 'mark_miss']
    marks = [mark for mark in marks if mark[1] == unit and mark[2] != unit and mark[4] == item]
    return marks

class CombatChargeIncrease(SkillComponent):
    nid = 'combat_charge_increase'
    desc = "Increases charge of skill each combat"
    tag = "charge"

    expose = Type.Int
    value = 5

    ignore_conditional = True

    def end_combat(self, playback, unit, item, target, mode):
        marks = get_marks(playback, unit, item)
        if not self.skill.data.get('active') and marks:
            new_value = self.skill.data['charge'] + self.value
            new_value = min(new_value, self.skill.data['total_charge'])
            action.do(action.SetObjData(self.skill, 'charge', new_value))

class CombatChargeIncreaseByStat(SkillComponent):
    nid = 'combat_charge_increase_by_stat'
    desc = "Increases charge of skill each combat"
    tag = "charge"

    expose = Type.Stat
    value = 'SKL'

    ignore_conditional = True

    def end_combat(self, playback, unit, item, target, mode):
        marks = get_marks(playback, unit, item)
        if not self.skill.data.get('active') and marks:
            new_value = self.skill.data['charge'] + unit.stats[self.value] + unit.stat_bonus(self.value)
            new_value = min(new_value, self.skill.data['total_charge'])
            action.do(action.SetObjData(self.skill, 'charge', new_value))

class GainSP(SkillComponent):
    nid = 'gain_sp'
    desc = "Gain X SP on use"
    # paired_with = ('effective_tag',)
    tag = "charge"
    author = 'KD'

    expose = Type.Int
    value = 2

    ignore_conditional = True

    def start_combat(self, playback, unit, item, target, mode):
        if self.skill.data.get('active'):
            action.do(action.ChangeSP(unit, self.value))

class CostSP(SkillComponent):
    nid = 'cost_sp'
    desc = "Skill reduces SP with each use. Unit must have >=X SP to use the skill."
    tag = "charge"
    author = 'KD'

    expose = Type.Int
    value = 2

    ignore_conditional = True

    def condition(self, unit):
        return unit.current_sp >= self.value

    def start_combat(self, playback, unit, item, target, mode):
        if self.skill.data.get('active'):
            action.do(action.ChangeSP(unit, -self.value))

    # def text(self) -> str:
    #     return 'Reduces SP by ' + str(self.value)

class CheckSP(SkillComponent):
    nid = 'check_sp'
    desc = "Unit must have more than X SP to use this skill. Does not subtract SP on use."
    tag = "charge"
    author = 'KD'

    expose = Type.Int
    value = 2

    ignore_conditional = True

    def condition(self, unit):
        return unit.current_sp >= self.value