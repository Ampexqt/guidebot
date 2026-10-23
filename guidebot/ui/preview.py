"""Clickable logical 240x320 LCD layout. This is a desktop Canvas, not SPI output."""

import tkinter as tk

from ..controller import Page
from .face import BG, INK, MUTED, TEAL, draw_robot


class LCDPreview(tk.Canvas):
    WIDTH = 240
    HEIGHT = 320

    def __init__(self, master, controller, dispatch, **kwargs):
        super().__init__(master, width=self.WIDTH, height=self.HEIGHT,
                         bg=BG, highlightthickness=0, **kwargs)
        self.controller = controller
        self.dispatch = dispatch
        self._hits = []
        self._menu_offset = 0
        self.bind("<Button-1>", self._click)

    def _click(self, event):
        for x1, y1, x2, y2, action in reversed(self._hits):
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.dispatch(action)
                break

    def _button(self, x, y, width, height, text, action, *, primary=False):
        self.create_rectangle(x, y, x+width, y+height,
                              fill=TEAL if primary else "#203b54", outline="")
        self.create_text(x+width/2, y+height/2, text=text, fill="#08251e" if primary else INK,
                         font=("Segoe UI", 9, "bold"), width=width-10)
        self._hits.append((x, y, x+width, y+height, action))

    def _scroll_menu(self, amount):
        self._menu_offset = max(0, self._menu_offset + amount)

    def render(self):
        c = self.controller
        self.delete("all")
        self._hits.clear()
        self.create_rectangle(0, 0, 240, 29, fill="#1d354c", outline="")
        self.create_text(12, 14, text="GUIDEBOT", anchor="w", fill=INK, font=("Segoe UI", 10, "bold"))
        self.create_text(229, 14, text="SIM", anchor="e", fill=TEAL, font=("Segoe UI", 9, "bold"))
        self.create_rectangle(0, 29, 240, 47, fill="#4a3b23", outline="")
        self.create_text(120, 38, text="PLACEHOLDER ROUTES" if c.database.is_placeholder else "LOCAL CAMPUS DATA",
                         fill="#ffdc96", font=("Segoe UI", 8, "bold"))
        if c.page == Page.WELCOME:
            draw_robot(self, 20, 54, 200, 128, c.expression, c.elapsed, c.servos.angles, body=False)
            self.create_text(120, 195, text="Hello! I'm GuideBot!", fill=INK, font=("Segoe UI", 14, "bold"))
            self.create_text(120, 225, text="Where would you like to go?", fill=MUTED, font=("Segoe UI", 9))
            self._button(16, 252, 208, 39, "Find a destination", c.show_menu, primary=True)
        elif c.page == Page.MENU:
            self.create_text(12, 62, text="Campus destinations", anchor="w", fill=INK, font=("Segoe UI", 12, "bold"))
            self.create_text(12, 84, text="Search using desktop controls", anchor="w", fill=MUTED, font=("Segoe UI", 8))
            items = c.results
            self._menu_offset = min(self._menu_offset, max(0, len(items)-4))
            for index, item in enumerate(items[self._menu_offset:self._menu_offset+4]):
                self._button(12, 100+index*39, 216, 34, item.name, lambda item=item: c.select(item.id))
            if not items:
                self.create_text(120, 150, text="No matching destinations", fill=MUTED, font=("Segoe UI", 10))
            if len(items) > 4:
                self._button(12, 259, 103, 22, "Earlier", lambda: self._scroll_menu(-4))
                self._button(125, 259, 103, 22, "More", lambda: self._scroll_menu(4))
        elif c.destination:
            self.create_text(12, 62, text=c.destination.name, anchor="w", fill=INK,
                             width=216, font=("Segoe UI", 11, "bold"))
            self.create_text(12, 98, text=f"STEP {c.step_index+1} OF {len(c.destination.steps)}",
                             anchor="w", fill=TEAL, font=("Segoe UI", 9, "bold"))
            self.create_text(12, 120, text=c.destination.steps[c.step_index], anchor="nw",
                             width=212, fill=INK, font=("Segoe UI", 10))
            if c.step_index > 0:
                self._button(12, 244, 102, 34, "Previous", lambda: c.change_step(-1))
            if c.step_index < len(c.destination.steps)-1:
                self._button(126, 244, 102, 34, "Next", lambda: c.change_step(1), primary=True)
            else:
                self.create_text(174, 261, text="Route complete", fill=TEAL, font=("Segoe UI", 9))
        if c.page != Page.WELCOME:
            self._button(12, 286, 103, 28, "Back", c.back)
            self._button(125, 286, 103, 28, "Home", c.home)
