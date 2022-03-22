from unittest.mock import MagicMock, Mock

from app.engine.game_state import GameState

def get_mock_game() -> GameState:
    game = Mock(wraps=GameState)

    game.movement = MagicMock()
    game.speak_styles = {}
    
    game.get_item = MagicMock()
    game.get_skill = MagicMock()
    return game
