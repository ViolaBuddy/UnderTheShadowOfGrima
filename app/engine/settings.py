from app.resources.resources import RESOURCES

from app.data.constants import WINWIDTH, WINHEIGHT

from app.engine import config as cf
from app.engine.sprites import SPRITES
from app.engine.fonts import FONT
from app.engine.sound import SOUNDTHREAD
from app.engine.state import State
from app.engine import engine, background, banner, settings_menu, base_surf, text_funcs
from app.engine.game_state import game

controls = {'key_SELECT': engine.subsurface(SPRITES.get('buttons'), (0, 66, 14, 13)),
            'key_BACK': engine.subsurface(SPRITES.get('buttons'), (0, 82, 14, 13)),
            'key_INFO': engine.subsurface(SPRITES.get('buttons'), (1, 149, 16, 9)),
            'key_AUX': engine.subsurface(SPRITES.get('buttons'), (1, 133, 16, 9)),
            'key_START': engine.subsurface(SPRITES.get('buttons'), (0, 165, 33, 9)),
            'key_LEFT': engine.subsurface(SPRITES.get('buttons'), (1, 4, 13, 12)),
            'key_RIGHT': engine.subsurface(SPRITES.get('buttons'), (1, 19, 13, 12)),
            'key_DOWN': engine.subsurface(SPRITES.get('buttons'), (1, 34, 12, 13)),
            'key_UP': engine.subsurface(SPRITES.get('buttons'), (1, 50, 12, 13))}
control_order = ('key_SELECT', 'key_BACK', 'key_INFO', 'key_AUX', 'key_LEFT', 'key_RIGHT', 'key_UP', 'key_DOWN', 'key_START')

config = [('animation', ['Always', 'Your Turn', 'Combat Only', 'Never'], 0),
          ('temp_screen_size', ['1', '2', '3', '4', '5'], 18),
          ('unit_speed', list(reversed(range(15, 180, 15))), 1),
          ('text_speed', cf.text_speed_options, 2),
          ('cursor_speed', list(reversed(range(32, 160, 16))), 8),
          ('show_terrain', bool, 7),
          ('show_objective', bool, 6),
          ('autocursor', bool, 13),
          ('hp_map_team', ['All', 'Ally', 'Enemy'], 10),
          ('hp_map_cull', ['None', 'Wounded', 'All'], 10),
          ('music_volume', [x/10.0 for x in range(0, 11, 1)], 15),
          ('sound_volume', [x/10.0 for x in range(0, 11, 1)], 16),
          ('autoend_turn', bool, 14),
          ('confirm_end', bool, 14),
          ('display_hints', bool, 3)]

config_icons = [engine.subsurface(SPRITES.get('settings_icons'), (0, c[2] * 16, 16, 16)) for c in config]

class SettingsMenuState(State):
    name = 'settings_menu'
    in_level = False
    show_map = False

    def create_background(self):
        panorama = RESOURCES.panoramas.get('settings_background')
        if not panorama:
            panorama = RESOURCES.panoramas.get('default_background')
        if panorama:
            if panorama.num_frames > 1:
                self.bg = background.PanoramaBackground(panorama)
            else:
                self.bg = background.ScrollingBackground(panorama)
        else:
            self.bg = None

    def start(self):
        self.create_background()
        # top_menu_left, top_menu_right, config, controls, get_input
        self.state = 'top_menu_left'

        control_options = control_order
        control_icons = [controls[c] for c in control_options]
        self.controls_menu = settings_menu.Controls(None, control_options, 'menu_bg_base', control_icons)

        config_options = [(c[0], c[1]) for c in config]
        self.config_menu = settings_menu.Config(None, config_options, 'menu_bg_base', config_icons)

        game.state.change('transition_in')
        return 'repeat'

    @property
    def current_menu(self):
        if self.state in ('top_menu_left', 'config'):
            return self.config_menu
        else:
            return self.controls_menu

    def take_input(self, event):
        if self.state == 'get_input':
            if event == 'BACK':
                SOUNDTHREAD.play_sfx('Select 4')
                self.state = 'controls'
                game.input_manager.set_change_keymap(False)
            elif event == 'NEW':
                SOUNDTHREAD.play_sfx('Select 1')
                self.state = 'controls'
                selection = self.current_menu.get_current()
                cf.SETTINGS[selection] = game.input_manager.unavailable_button
                game.input_manager.set_change_keymap(False)
                game.input_manager.update_key_map()
            elif event:
                SOUNDTHREAD.play_sfx('Select 4')
                self.state = 'invalid'
                game.input_manager.set_change_keymap(False)
                text = 'Invalid Choice!'
                game.alerts.append(banner.Custom(text))
                game.state.change('alert')
        elif self.state in ('top_menu_left', 'top_menu_right'):
            if event == 'DOWN':
                SOUNDTHREAD.play_sfx('Select 6')
                if self.state == 'top_menu_left':
                    self.state = 'config'
                else:
                    self.state = 'controls'
            elif event == 'LEFT':
                if self.state == 'top_menu_right':
                    SOUNDTHREAD.play_sfx('Select 6')
                    self.state = 'top_menu_left'
            elif event == 'RIGHT':
                if self.state == 'top_menu_left':
                    SOUNDTHREAD.play_sfx('Select 6')
                    self.state = 'top_menu_right'
            elif event == 'BACK':
                self.back()
        else:
            self.current_menu.handle_mouse()
            if event == 'DOWN':
                SOUNDTHREAD.play_sfx('Select 6')
                self.current_menu.move_down()
            elif event == 'UP':
                SOUNDTHREAD.play_sfx('Select 6')
                if self.current_menu.get_current_index() <= 0:
                    if self.state == 'config':
                        self.state = 'top_menu_left'
                    else:
                        self.state = 'top_menu_right'
                else:
                    self.current_menu.move_up()
            elif event == 'LEFT':
                SOUNDTHREAD.play_sfx('Select 6')
                self.current_menu.move_left()
            elif event == 'RIGHT':
                SOUNDTHREAD.play_sfx('Select 6')
                self.current_menu.move_right()

            elif event == 'BACK':
                self.back()

            elif event == 'SELECT':
                selection = self.current_menu.get_current()
                if self.current_menu is self.top_menu:
                    SOUNDTHREAD.play_sfx('Select 1')
                    if selection == 'config':
                        # Transition to config menu state
                        self.state = 'config'
                    elif selection == 'controls':
                        self.state = 'controls'
                elif self.state == 'controls':
                    self.state = 'get_input'
                    game.input_manager.set_change_keymap(True)

    def back(self):
        SOUNDTHREAD.play_sfx('Select 4')
        cf.save_settings()
        game.state.change('transition_pop')

    def update(self):
        self.current_menu.update()

    def draw_top_menu(self, surf):
        bg = base_surf.create_base_surf(112, 24, 'menu_bg_clear')
        surf.blit(bg, (4, 4))
        surf.blit(bg, (WINWIDTH//2 + 4, 4))
        if self.current_menu is self.config_menu:
            FONT['text_yellow'].blit_center('Config', surf, (4 + 112/2, 8))
            FONT['text_grey'].blit_center('Controls', surf, (WINWIDTH//2 + 4 + 112/2, 8))
        else:
            FONT['text_grey'].blit_center('Config', surf, (4 + 112/2, 8))
            FONT['text_yellow'].blit_center('Controls', surf, (WINWIDTH//2 + 4 + 112/2, 8))

    def draw_info_banner(self, surf):
        height = 16
        bg = base_surf.create_base_surf(WINWIDTH + 16, height, 'menu_bg_clear')
        surf.blit(bg, (-8, WINHEIGHT - height))
        if self.state == 'top_menu_left':
            text = 'config_desc'
        elif self.state == 'top_menu_left':
            text = 'controls_desc'
        elif self.state == 'config':
            idx = self.config_menu.get_current_index()
            text = config[idx][0] + '_desc'
        else:
            text = 'keymap_desc'
        text = text_funcs.translate(text)
        FONT['text_white'].blit_center(text, surf, (WINWIDTH//2, WINHEIGHT - height))
    
    def draw(self, surf):
        if self.bg:
            self.bg.draw(surf)

        self.draw_top_menu(surf)
        self.current_menu.draw(surf)
        self.draw_info_banner(surf)

        return surf

    def finish(self):
        # Just to make sure!
        game.input_manager.set_change_keymap(False)
