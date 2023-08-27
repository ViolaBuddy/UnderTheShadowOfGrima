from enum import Enum
from typing import List

from app.engine import engine
from app.events import speak_style, event_commands
from app.events.event import Event
from app.engine.sprites import SPRITES
from app.engine.text_evaluator import TextEvaluator
from app.events.event_parser import EventParser

from app.utilities.typing import NID

class IfStatementStrategy(Enum):
    ALWAYS_TRUE = 1
    ALWAYS_FALSE = 2

class MockGame():
    """
    Mock game object that stores the speak styles, so they work even though the rest of the game isn't present
    """
    def __init__(self):
        self.speak_styles = speak_style.SpeakStyleLibrary()
        self.movement = None

class MockEvent(Event):
    # These are the only commands that will be processed by this event
    available = {"finish", "wait", "end_skip", "music", "music_clear", 
                 "sound", "add_portrait", "multi_add_portrait", 
                 "remove_portrait", "multi_remove_portrait", 
                 "move_portrait", "mirror_portrait", "bop_portrait", 
                 "expression", "speak_style", "speak", "unhold", 
                 "transition", "change_background", "table", 
                 "remove_table", "draw_overlay_sprite", 
                 "remove_overlay_sprite", "location_card", "credits", 
                 "ending", "pop_dialog", "unpause"}

    loop_commands = {'for', 'endf'}

    def __init__(self, nid, commands, command_idx=0, if_statement_strategy=IfStatementStrategy.ALWAYS_TRUE):
        self._transition_speed = 250
        self._transition_color = (0, 0, 0)
        
        self.nid = nid
        self.command_queue: List[event_commands.EventCommand] = []

        self.background = None
        self.bg_black = SPRITES.get('bg_black').copy()
        self.game = MockGame()

        self._generic_setup()

        self.text_evaluator = TextEvaluator(self.logger, None)
        self.parser = MockEventParser('Mock', commands.copy(), self.text_evaluator, if_statement_strategy)

    def update(self):
        # update all internal updates, remove the ones that are finished
        self.should_update = {name: to_update for name, to_update in self.should_update.items() if not to_update(self.do_skip)}

        self._update_state(dialog_log=False)
        self._update_transition()

    def draw(self, surf):
        # Necessary to clear out content from the previous frame
        if not self.background:
            engine.blit_center(surf, self.bg_black)
        surf = super().draw(surf)
        return surf

    def run_command(self, command: event_commands.EventCommand):
        # Only certain commands will be processed
        if command.nid in self.available:
            super().run_command(command)

    def _get_unit(self, text):
        return None

class MockEventParser(EventParser):
    def __init__(self, nid: NID, commands: List[event_commands.EventCommand],
                 text_evaluator: TextEvaluator, if_statement_strategy=IfStatementStrategy.ALWAYS_TRUE):
        self.if_statement_strategy = if_statement_strategy
        super().__init__(nid, commands, text_evaluator)

    def _get_truth(self, command: event_commands.EventCommand) -> bool:
        if self.if_statement_strategy == IfStatementStrategy.ALWAYS_TRUE:
            truth = True
        else:
            truth = False
        self.logger.info("Result: %s" % truth)
        return truth
