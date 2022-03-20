from enum import Enum
from app.data.components import Component

class SkillTags(Enum):
    ATTRIBUTE = 'attribute'
    BASE = 'base'
    MOVEMENT = 'movement'
    COMBAT = 'combat'
    COMBAT2 = 'combat2'
    DYNAMIC = 'dynamic'
    FORMULA = 'formula'
    STATUS = 'status'
    TIME = 'time'
    CHARGE = 'charge'
    AESTHETIC = 'aesthetic'
    ADVANCED = 'advanced'
    EXTRA = 'extra'

    HIDDEN = 'hidden'

class SkillComponent(Component):
    skill = None
    ignore_conditional = False
