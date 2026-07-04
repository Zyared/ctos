"""Заглушка модуля в стиле CtOS (учебная симуляция)."""

from __future__ import annotations

import tkinter as tk

from ctos.ui import theme as T
from ctos.ui.viewport import Viewport


class PlaceholderModule:
    """Экран с заголовком, текстом и BACK — для модулей в разработке."""

    def __init__(
        self,
        canvas: tk.Canvas,
        root: tk.Tk,
        on_exit,
        title: str,
        body: str,
    ):
        self.canvas = canvas
        self.root = root
        self.on_exit = on_exit
        self.title = title
        self.body = body

    def start(self) -> None:
        self._draw()

    def _draw(self) -> None:
        self.canvas.delete("all")
        vp = Viewport.from_canvas(self.canvas, self.root)
        w, h = vp.w, vp.h

        self.canvas.create_rectangle(0, 0, w, h, fill="#000000", outline="")

        self.canvas.create_text(
            w // 2,
            vp.px(48),
            text=f"CtOS  //  {self.title}",
            fill=T.HUD_TITLE,
            font=vp.consolas(20, bold=True),
        )

        self.canvas.create_text(
            w // 2,
            h // 2 - vp.px(20),
            text=self.body,
            fill="#aee6ff",
            font=vp.consolas(12),
            width=min(vp.px(760), w - vp.px(120)),
            justify="center",
        )

        self.canvas.create_text(
            w // 2,
            h // 2 + vp.px(120),
            text="[ SIMULATION ONLY — NO REAL ATTACK ]",
            fill="#557788",
            font=vp.consolas(10),
        )

        bx, by = vp.px(30), vp.px(20)
        rect = self.canvas.create_rectangle(
            bx, by, bx + vp.px(120), by + vp.px(44), outline=T.MENU_NODE_OUTLINE, width=vp.wid(2), fill="#050d14"
        )
        lab = self.canvas.create_text(
            bx + vp.px(60), by + vp.px(22), text="BACK", fill=T.MENU_NODE_OUTLINE, font=vp.consolas(12, bold=True)
        )
        for item in (rect, lab):
            self.canvas.tag_bind(item, "<Enter>", lambda e: self.canvas.itemconfig(rect, fill="#0a1a22"))
            self.canvas.tag_bind(item, "<Leave>", lambda e: self.canvas.itemconfig(rect, fill="#050d14"))
            self.canvas.tag_bind(item, "<Button-1>", lambda e: self._exit())

        # delete("all") выше стирает водяной знак МИВЛГУ, который рисует
        # application.py перед запуском модуля — перерисовываем его здесь же,
        # иначе он пропадает на весь показ заглушки.
        self.canvas.create_text(
            w - vp.px(20),
            h - vp.px(20),
            anchor="se",
            text="МИВЛГУ",
            fill=T.HUD_MIVLGU,
            font=vp.arial_black(22),
            tags=("mivlgu",),
        )

    def _exit(self) -> None:
        self.canvas.delete("all")
        self.on_exit()
