from app.engine.sprites import SPRITES

from app.engine import engine, image_mods
from app.engine.state import State
from app.engine.game_state import game

transition_speed = 1
transition_max = 8

class TransitionInState(State):
    name = 'transition_in'
    transparent = True

    def start(self):
        self.bg = SPRITES.get('bg_black')
        self.counter = 0
        self.transition_speed = game.memory.get('transition_speed', transition_speed)

    def draw(self, surf):
        self.bg = image_mods.make_translucent(self.bg, self.counter * .125)
        engine.blit_center(surf, self.bg)

        self.counter += self.transition_speed
        if self.counter >= transition_max:
            game.state.back()
        return surf

    def finish(self):
        game.memory['transition_speed'] = None

class TransitionOutState(State):
    name = 'transition_out'
    transparent = True

    def start(self):
        self.bg = SPRITES.get('bg_black')
        self.transition_speed = game.memory.get('transition_speed', transition_speed)
        self.counter = transition_max

    def draw(self, surf):
        self.bg = image_mods.make_translucent(self.bg, self.counter * .125)
        engine.blit_center(surf, self.bg)

        self.counter -= self.transition_speed
        if self.counter <= 0:
            game.state.back()
        return surf

    def finish(self):
        game.memory['transition_speed'] = None

class TransitionPopState(TransitionOutState):
    name = 'transition_pop'

    def draw(self, surf):
        self.bg = image_mods.make_translucent(self.bg, self.counter * .125)
        engine.blit_center(surf, self.bg)

        self.counter -= self.transition_speed
        if self.counter <= 0:
            game.state.back()
            game.state.back()
        return surf

class TransitionDoublePopState(TransitionPopState):
    name = 'transition_double_pop'

    def draw(self, surf):
        self.bg = image_mods.make_translucent(self.bg, self.counter * .125)
        engine.blit_center(surf, self.bg)

        self.counter -= self.transition_speed
        if self.counter <= 0:
            game.state.back()
            game.state.back()
            game.state.back()
        return surf
