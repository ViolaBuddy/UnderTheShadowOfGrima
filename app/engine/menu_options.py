import math

from app.data.database import DB

from app.engine.sprites import SPRITES
from app.engine.fonts import FONT
from app.engine import engine, image_mods, icons, help_menu, text_funcs, item_system
from app.engine.game_state import game

class EmptyOption():
    def __init__(self, idx):
        self.idx = idx
        self.help_box = None
        self.color = None
        self.ignore = False

    def get(self):
        return None

    def set_text(self):
        pass

    def width(self):
        return 104

    def height(self):
        return 16

    def draw(self, surf, x, y):
        pass

    def draw_highlight(self, surf, x, y, menu_width):
        highlight_surf = SPRITES.get('menu_highlight')
        width = highlight_surf.get_width()
        for slot in range((menu_width - 10)//width):
            left = x + 5 + slot*width
            top = y + 9
            surf.blit(highlight_surf, (left, top))
        return surf

class BasicOption():
    def __init__(self, idx, text):
        self.idx = idx
        self.text = text
        self.display_text = text_funcs.translate(text)
        self.help_box = None
        self.color = 'text-white'
        self.ignore = False

    def get(self):
        return self.text

    def set_text(self, text):
        self.text = text
        self.display_text = text_funcs.translate(text)

    def width(self):
        return FONT[self.color].width(self.display_text) + 24

    def height(self):
        return 16

    def draw(self, surf, x, y):
        font = FONT[self.color]
        font.blit(self.display_text, surf, (x + 6, y))

    def draw_highlight(self, surf, x, y, menu_width):
        highlight_surf = SPRITES.get('menu_highlight')
        width = highlight_surf.get_width()
        for slot in range((menu_width - 10)//width):
            left = x + 5 + slot*width
            top = y + 9
            surf.blit(highlight_surf, (left, top))
        return surf

class HorizOption(BasicOption):
    def width(self):
        return FONT[self.color].width(self.display_text)

class TitleOption():
    def __init__(self, idx, text, option_bg_name):
        self.idx = idx
        self.text = text
        self.display_text = text_funcs.translate(text)
        self.option_bg_name = option_bg_name

        self.color = 'chapter-grey'

    def get(self):
        return self.text

    def set_text(self, text):
        self.text = text
        self.display_text = text_funcs.translate(text)

    def width(self):
        return SPRITES.get(self.option_bg_name).get_width()

    def height(self):
        return SPRITES.get(self.option_bg_name).get_height()

    def draw_text(self, surf, x, y):
        font = FONT[self.color]

        text = self.display_text
        text_size = font.size(text)
        position = (x - text_size[0]//2, y - text_size[1]//2)

        # Handle outline
        t = math.sin(math.radians((engine.get_time()//10) % 180))
        color_transition = image_mods.blend_colors((192, 248, 248), (56, 48, 40), t)
        outline_surf = engine.create_surface((text_size[0] + 4, text_size[1] + 2), transparent=True)
        font.blit(text, outline_surf, (1, 0))
        font.blit(text, outline_surf, (0, 1))
        font.blit(text, outline_surf, (1, 2))
        font.blit(text, outline_surf, (2, 1))
        outline_surf = image_mods.change_color(outline_surf, color_transition)

        surf.blit(outline_surf, (position[0] - 1, position[1] - 1))
        font.blit(text, surf, position)

    def draw(self, surf, x, y):
        left = x - self.width()//2
        surf.blit(SPRITES.get(self.option_bg_name), (left, y))

        self.draw_text(surf, left + self.width()//2, y + self.height()//2 + 1)

    def draw_highlight(self, surf, x, y):
        left = x - self.width()//2
        surf.blit(SPRITES.get(self.option_bg_name + '_highlight'), (left, y))

        self.draw_text(surf, left + self.width()//2, y + self.height()//2 + 1)

class ChapterSelectOption(TitleOption):
    def __init__(self, idx, text, option_bg_name, bg_color):
        self.idx = idx
        self.text = text
        self.display_text = text_funcs.translate(text)
        self.bg_color = bg_color
        self.option_bg_name = option_bg_name + '_' + bg_color

        self.color = 'chapter-grey'

    def draw_flicker(self, surf, x, y):
        left = x - self.width()//2
        surf.blit(SPRITES.get(self.option_bg_name + '_flicker'), (left, y))

        self.draw_text(surf, left + self.width()//2, y + self.height()//2 + 1)

class ItemOption(BasicOption):
    def __init__(self, idx, item):
        self.idx = idx
        self.item = item
        self.help_box = None
        self.color = None
        self.ignore = False

    def get(self):
        return self.item

    def set_text(self, text):
        pass

    def set_item(self, item):
        self.item = item

    def width(self):
        return 104

    def height(self):
        return 16

    def get_color(self):
        owner = game.get_unit(self.item.owner_nid)
        main_font = 'text_grey'
        uses_font = 'text_grey'
        if self.color:
            main_font = self.color
            uses_font = self.color
            if main_font == 'text-white':
                uses_font = 'text-blue'
        elif owner and item_system.available(owner, self.item):
            main_font = 'text-white'
            uses_font = 'text-blue'
        return main_font, uses_font

    def get_help_box(self):
        owner = game.get_unit(self.item.owner_nid)
        if item_system.is_weapon(owner, self.item) or item_system.is_spell(owner, self.item):
            return help_menu.ItemHelpDialog(self.item)
        else:
            return help_menu.HelpDialog(self.item.desc)

    def draw(self, surf, x, y):
        main_font = 'text_grey'
        uses_font = 'text_grey'
        icon = icons.get_item_icon(self.item)
        if icon:
            surf.blit(icon, (x + 2, y))
        main_font, uses_font = self.get_color()
        FONT[main_font].blit(self.item.name, surf, (x + 20, y))
        uses_string = '--'
        if self.item.uses:
            uses_string = str(self.item.uses.value)
        elif self.item.c_uses:
            uses_string = str(self.item.c_uses.value)
        left = x + self.width() - 4 - FONT[uses_font].size(uses_string)[0] - 5
        FONT[uses_font].blit(uses_string, surf, (left, y))

class FullItemOption(ItemOption):
    def width(self):
        return 120

    def draw(self, surf, x, y):
        main_font = 'text-grey'
        uses_font = 'text-grey'
        icon = icons.get_item_icon(self.item)
        if icon:
            surf.blit(icon, (x + 2, y))
        main_font, uses_font = self.get_color()
        FONT[main_font].blit(self.item.name, surf, (x + 20, y))

        uses_string_a = '--'
        uses_string_b = '--'
        if self.item.data.get('uses') is not None:
            uses_string_a = str(self.item.data['uses'])
            uses_string_b = str(self.item.data['starting_uses'])
        elif self.item.get('c_uses') is not None:
            uses_string_a = str(self.item.data['c_uses'])
            uses_string_b = str(self.item.data['starting_c_uses'])
        FONT[uses_font].blit_right(uses_string_a, surf, (x + 96, y))
        FONT['text-white'].blit("/", surf, (x + 98, y))
        FONT[uses_font].blit_right(uses_string_b, surf, (x + 120, y))