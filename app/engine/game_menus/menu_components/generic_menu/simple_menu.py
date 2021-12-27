from __future__ import annotations
import math
from app.engine.graphics.ui_framework.premade_animations.animation_templates import component_scroll_anim
from app.engine.graphics.ui_framework.premade_components.plain_text_component import PlainTextLine

from app.engine.base_surf import create_base_surf, create_highlight_surf

from typing import List, TYPE_CHECKING, Tuple

from app.engine.graphics.ui_framework import (HeaderList, IconRow,
                                            ListLayoutStyle, UIComponent,
                                            UILayoutType )
from app.engine import engine
from app.engine.graphics.ui_framework.ui_framework_layout import HAlignment
from app.engine.gui import ScrollArrow, ScrollBar
from app.sprites import SPRITES
from app.utilities.enums import Orientation
from app.utilities.utils import tuple_add

class SimpleIconTable(UIComponent):
    def __init__(self, name: str, parent: UIComponent = None,
                 initial_data: List[str] | List[Tuple[engine.Surface, str, str]] = [],
                 num_columns: int = 1, num_rows: int = 0, row_width: int = -1,
                 background = 'menu_bg_base', title: str = None, orientation: Orientation = Orientation.VERTICAL,
                 option_text_align: HAlignment = HAlignment.LEFT):
        super().__init__(name=name, parent=parent)

        self.num_display_columns = max(num_columns, 1)
        self.num_rows = num_rows
        self._row_width = row_width
        self._data = []
        self._title = None
        self._background = background
        self.orientation = orientation
        self.text_align = option_text_align
        self.column_data: List[List[IconRow]] = []

        self.row_height = 16 # default icon. will be resized if any rows are larger.

        # subcomponents and layout
        self.props.layout = UILayoutType.LIST
        self.props.list_style = ListLayoutStyle.COLUMN
        self.overflow = (20, 20, 12, 12)

        if not title:
            self.header: PlainTextLine = None
        else:
            self.header: PlainTextLine = PlainTextLine('header', self, title)
            self.add_child(self.header)

        self.table_container = UIComponent("table_container", self)
        self.table_container.props.layout = UILayoutType.LIST
        self.table_container.props.list_style = ListLayoutStyle.ROW
        self.table_container.overflow = (20, 20, 12, 12)
        num_columns = self.calculate_num_cols(self.num_rows, self.num_display_columns, len(self._data), self.orientation)
        self.column_components: List[HeaderList] = []
        self._reconstruct_table_cols(num_columns)

        self.add_child(self.table_container)

        self.set_title(title)
        self.set_data(initial_data)

        self._reset('init')

    def calculate_num_cols(self, display_rows: int, display_cols: int, num_data: int, orientation: Orientation):
        """because rows are easily added, but cols are not, we have to precalculate number of cols needed
        """
        if orientation == Orientation.VERTICAL:
            return display_cols
        else:
            return math.ceil(num_data / display_rows)

    def _reconstruct_table_cols(self, num_cols):
        if num_cols == len(self.table_container.children):
            return
        self.column_components: List[HeaderList] = [HeaderList('', self, None, []) for _ in range(num_cols)]
        self.table_container.children.clear()
        for col in self.column_components:
            col.overflow = (20, 20, 0, 0)
            self.table_container.add_child(col)

    def construct_row(self, datum: str | Tuple[engine.Surface | UIComponent, str]
                                       | Tuple[engine.Surface | UIComponent, str, str]) -> IconRow:
        if isinstance(datum, tuple):
            icon = datum[0]
            text = datum[1]
            if len(datum) == 3: # includes nid
                nid = datum[2]
            else:
                nid = datum[1]
            row = IconRow(text, text=text, icon=icon, data=nid, text_align=self.text_align)
        else:
            row =  IconRow(datum, text=datum, data=datum)
        row.overflow = (15, 0, 15, 0)
        return row

    def table_scroll(self):
        if self.row_width():
            return self.table_container.scroll[0] / self.row_width()
        return 0

    def row_width(self):
        return self._autosize(self._row_width, self.num_rows)[0]

    def scroll_right(self):
        scroll_right_anim = component_scroll_anim(self.table_container.scroll,
                                                 (self.table_container.scroll[0] + self.row_width(), self.table_container.scroll[1]))
        self.table_container.queue_animation(animations=[scroll_right_anim])

    def scroll_left(self):
        scroll_left_anim = component_scroll_anim(self.table_container.scroll,
                                                 (self.table_container.scroll[0] - self.row_width(), self.table_container.scroll[1]))
        self.table_container.queue_animation(animations=[scroll_left_anim])

    def set_title(self, title: str):
        if title == self._title:
            return
        self._title = title
        if self.header:
            self.header.set_text(self._title)

    def set_data(self, data: List):
        if data == self._data:
            return
        self._data = data
        num_columns = self.calculate_num_cols(self.num_rows, self.num_display_columns, len(data), self.orientation)
        self._reconstruct_table_cols(num_columns)
        self.column_data = [list() for _ in range(num_columns)]
        for idx, item in enumerate(data):
            row_item = self.construct_row(item)
            self.row_height = max(self.row_height, row_item.height)
            self.column_data[idx % num_columns].append(row_item)
        self._reset('set_data')
        for idx, col in enumerate(self.column_components):
            col.set_data_rows(self.column_data[idx])

    def _reset(self, reason: str):
        """Pre-draw, basically; take all known props, and recalculate one last time."""
        row_width, table_height = self._autosize(self._row_width, self.num_rows)
        for column in self.column_components:
            column.width = row_width

        self.table_container.size = (len(self.column_components) * row_width, table_height)

        # toggle cols for visibility
        left_visible = self.table_scroll() - 0.25
        right_visible = self.table_scroll() - 0.75 + self.num_display_columns
        for idx, col in enumerate(self.table_container.children):
            if idx < left_visible or idx > right_visible:
                col.disable()
            else:
                col.enable()
        total_height = table_height
        if self.header:
            total_height += self.header.height
        self.size = (self.num_display_columns * row_width, total_height)
        # regenerate bg
        if self._background:
            if 'menu_bg' in self._background:
                menu_bg = create_base_surf(self.tsize[0] + 10, self.tsize[1] + 10, self._background)
                self.set_background(menu_bg)
            else: # not actually a tileable base bg
                menu_bg = SPRITES.get(self._background)
                self.set_background(menu_bg)

    def _autosize(self, force_row_width = 0, force_num_rows = 0) -> Tuple[int, int]:
        max_row_width = 0
        if not force_row_width > 0:
            for col in self.column_data:
                for row in col:
                    max_row_width = max(row.text.twidth + row.icon.twidth, max_row_width)
            if self.header:
                max_row_width = max(self.header.twidth / self.num_display_columns, max_row_width)
        else:
            max_row_width = force_row_width

        table_height = 0
        if force_num_rows > 0:
            table_height = self.num_rows * self.row_height
        else:
            table_height = self.max_rows_in_cols * self.row_height

        return max_row_width, table_height

    @property
    def max_rows_in_cols(self):
        max_rows_in_col = 0
        for col in self.column_data:
            max_rows_in_col = max(len(col), max_rows_in_col)
        return max_rows_in_col

class ChoiceTable(SimpleIconTable):
    def __init__(self, name: str, parent: UIComponent = None,
                 initial_data: List[str] | List[Tuple[engine.Surface, str, str]] = [],
                 num_columns: int = 1, num_rows: int = -1, row_width: int = -1,
                 background='menu_bg_base', title: str = None, orientation: Orientation = Orientation.VERTICAL,
                 option_text_align: HAlignment = HAlignment.LEFT):
        super().__init__(name, parent=parent, initial_data=initial_data,
                         num_columns=num_columns, num_rows=num_rows, row_width=row_width,
                         background=background, title=title, orientation=orientation,
                         option_text_align=option_text_align)
        self.cursor_sprite = SPRITES.get('menu_hand')
        self.cursor_offsets = [0, 0, 0, 0, 0, 0, 0, 1, 1, 2, 2, 2, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 4, 3, 3, 2, 2, 2, 1, 1, 1, 1]
        self.cursor_offset_index = 0
        self.selected_index = (0, 0)
        self.cursor_mode = 1 # 0 is no cursor, 1 is yes, 2 is yes but no move
        self.arrow_mode = 0 # 0 is no arrow, 1 is yes
        self.scroll_bar_mode = 0 #0 is no scrollbar, 1 is yes

        # UIF X GUI crossover pog
        # we have to adjust for the uif internal overflow
        header_height = 0
        if self.header:
            header_height = self.header.height
        lscroll_topleft = tuple_add((-8, header_height + (self.height - header_height)/2 - 5), self.overflow[::2])
        rscroll_topleft = tuple_add((self.width, header_height + (self.height - header_height)/2 - 5), self.overflow[::2])
        self.lscroll_arrow = ScrollArrow('left', lscroll_topleft)
        self.rscroll_arrow = ScrollArrow('right', rscroll_topleft)

        self.scroll_bar = ScrollBar()
        self.scroll_bar_topright = tuple_add((self.width + 4, header_height-4), self.overflow[::2])

    def should_redraw(self) -> bool:
        return True

    def update_cursor_and_highlight(self):
        x, y = self.selected_index
        cy = (y - self.column_components[x].scrolled_index) * self.column_components[x].row_height + 3
        self.cursor_offset_index = (self.cursor_offset_index + 1) % len(self.cursor_offsets)
        if self.cursor_mode == 1:
            cx = -15 + self.cursor_offsets[self.cursor_offset_index]
        else:
            cx = -11
        self.column_components[x].add_surf(self.cursor_sprite, (cx, cy), 1)
        highlight_surf = create_highlight_surf(self.column_components[x].width)
        self.column_components[x].add_surf(highlight_surf, (0, cy + 3), -1)

    def move_down(self):
        if self.any_children_animating():
            return
        x, y = self.selected_index
        self.selected_index = (x, min(y + 1, len(self.column_data[x]) - 1))
        if self.selected_index[1] > self.column_components[x].max_visible_rows + self.column_components[x].scrolled_index - 1:
            for hl in self.column_components:
                hl.scroll_down()

    def move_up(self):
        if self.any_children_animating():
            return
        x, y = self.selected_index
        self.selected_index = (x, max(y - 1, 0))
        if self.selected_index[1] < self.column_components[x].scrolled_index:
            for hl in self.column_components:
                hl.scroll_up()

    def move_left(self):
        if self.any_children_animating():
            return
        self.lscroll_arrow.pulse()
        x, y = self.selected_index
        new_col = max(x - 1, 0)
        self.selected_index = (new_col, min(y, len(self.column_data[new_col]) - 1))
        if self.selected_index[0] < self.table_scroll():
            self.scroll_left()

    def move_right(self):
        if self.any_children_animating():
            return
        self.rscroll_arrow.pulse()
        x, y = self.selected_index
        new_col = min(x + 1, len(self.column_data) - 1)
        self.selected_index = (new_col, min(y, len(self.column_data[new_col]) - 1))
        if self.selected_index[0] > self.table_scroll() + self.num_display_columns - 1:
            self.scroll_right()

    def get_selected(self):
        x, y = self.selected_index
        return self.column_data[x][y].data

    def set_cursor_mode(self, cursor_mode):
        self.cursor_mode = cursor_mode

    def set_scrollbar_mode(self, scroll_bar_mode):
        self.scroll_bar_mode = scroll_bar_mode

    def set_arrow_mode(self, arrow_mode):
        self.arrow_mode = arrow_mode

    def to_surf(self, no_cull=False, should_not_cull_on_redraw=True) -> engine.Surface:
        if self.cursor_mode != 0:
            for hl in self.column_components:
                if hl.manual_surfaces:
                    hl.manual_surfaces.clear()
            self.update_cursor_and_highlight()
        surf = super().to_surf(no_cull, should_not_cull_on_redraw)
        if self.arrow_mode != 0:
            # draw scroll bars
            self.lscroll_arrow.draw(surf)
            self.rscroll_arrow.draw(surf)
        if self.scroll_bar_mode != 0:
            total_rows = math.ceil(len(self._data) / self.num_display_columns)
            if total_rows > self.num_rows and self.table_container.children and self.table_container.children[0]:
                self.scroll_bar.draw(surf, self.scroll_bar_topright, self.table_container.children[0].scrolled_index, self.num_rows, total_rows)
        return surf
