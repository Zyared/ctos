import os
import tkinter as tk
import math
import time
import random
import pygame

from ctos.config import SOUND_DIR
from ctos.ui.viewport import Viewport
# ---------- Типы узлов ---------- #
TYPE_NORMAL = "normal"
TYPE_LINE = "line"
TYPE_CORNER = "corner"
TYPE_CROSS = "cross"
TYPE_GATE = "gate"
TYPE_START = "start"
TYPE_EXIT = "exit"
class WDNode:
    """
    Узел графа в стиле Watch Dogs.
    rotation: 0=0°, 1=90°, 2=180°, 3=270° (для логики портов).
    visual_angle: текущий визуальный угол (для плавной анимации).
    gate_required – сколько разных направлений питания нужно воротам, чтобы открыться.
    """
    def __init__(
        self,
        node_id: str,
        col: int,
        row: int,
        ntype: str = TYPE_NORMAL,
        rotation: int = 0,
        gate_required: int = 2,
    ):
        self.id = node_id
        self.col = col
        self.row = row
        self.type = ntype
        self.rotation = rotation % 4          # логический поворот
        self.visual_angle: float = self.rotation * 90.0  # визуальный угол
        self.powered = False
        self.gate_required = gate_required if ntype == TYPE_GATE else 0
        self.gate_input_dirs: set[int] = set()  # из каких направлений пришло питание
        # анимация поворота
        self.animating = False
        self.anim_from_angle = 0.0
        self.anim_to_angle = 0.0
        self.anim_step = 0
        self.anim_steps = 0
    # ---- ПОРТЫ ДЛЯ ЛОГИКИ ---- #
    @property
    def base_ports(self) -> set[int]:
        """
        Порты в положении rotation = 0
        0=UP, 1=RIGHT, 2=DOWN, 3=LEFT
        """
        if self.type in (TYPE_NORMAL, TYPE_LINE):
            # прямая: up-down
            return {0, 2}
        if self.type == TYPE_CORNER:
            # угол: up-right
            return {0, 1}
        if self.type == TYPE_CROSS:
            return {0, 1, 2, 3}
        if self.type in (TYPE_GATE, TYPE_START, TYPE_EXIT):
            # ромбы считаем 4-портовыми
            return {0, 1, 2, 3}
        return set()
    @property
    def ports(self) -> set[int]:
        """Порты с учётом rotation (для логики питания)."""
        return {(p + self.rotation) % 4 for p in self.base_ports}
class ZeroDownModule:
    """
    Полностью улучшенный модуль Zero-Day с:
    ✔ корректной логикой питания
    ✔ плавными поворотами узлов (Rotation: A)
    ✔ неоновыми эффектами WD
    ✔ бегущим лучом по активным линиям (Beam: 1)
    ✔ вращающимся пунктиром при питании
    ✔ DataExfil-style панелью завершения
    ✔ анимированным фоном (неоновая сетка + частицы)
    ✔ адаптацией под fullscreen
    """
    def __init__(self, canvas: tk.Canvas, root: tk.Tk, on_exit):
        self.canvas = canvas
        self.root = root
        self.on_exit = on_exit
        # граф
        self.nodes: dict[str, WDNode] = {}
        self.edges: list[tuple[str, str]] = []
        self.adj: dict[str, list[str]] = {}
        self.start_id: str | None = None
        self.exit_id: str | None = None
        # визуальная сетка
        self.spacing = 160
        self.layer_tag = "wd_layer"
        self.ui_exit_bbox: tuple[int, int, int, int] | None = None
        # анимация
        self.ticks = 0
        self.spin_offset = 0.0
        self.anim_loop_running = True
        # таймер
        self.timer_start = time.perf_counter()
        self.timer_running = True
        self.elapsed_final = 0.0
        self.level_completed = False
        self.success_shown = False
        self._exit_guard = False
        # фоновые частицы (x, y, dx, dy, r)
        self.bg_particles = [
            {
                "x": random.random(),
                "y": random.random(),
                "dx": (random.random() - 0.5) * 0.0015,
                "dy": (random.random() - 0.5) * 0.0015,
                "r": random.uniform(1.5, 3.5),
            }
            for _ in range(80)
        ]
        # демо-уровень
        self.build_demo()
        # логика + отрисовка
        self.recalculate_power()
        self.redraw()
        # управление
        self.canvas.bind("<Button-1>", self.on_click)
        root.bind("<Escape>", self._on_escape)
        # SOUND SYSTEM
        pygame.mixer.init()
        self.sounds = {}
        base = SOUND_DIR
        self.sounds["pulse"] = pygame.mixer.Sound(os.path.join(base, "pulse.mp3"))
        self.sounds["lock_open"] = pygame.mixer.Sound(os.path.join(base, "lock_open.mp3"))
        # громкость
        self.sounds["pulse"].set_volume(0.5)
        self.sounds["lock_open"].set_volume(0.5)
        # запуск анимации
        self.animate()

    def start(self) -> None:
        """ExploitModule: полная инициализация выполняется в __init__."""
        return

    # ================= УТИЛИТЫ ПОСТРОЕНИЯ УРОВНЯ ================= #
    def clear_graph(self):
        self.nodes.clear()
        self.edges.clear()
        self.adj.clear()
        self.start_id = None
        self.exit_id = None
    def add_node(
        self,
        node_id: str,
        col: int,
        row: int,
        ntype: str,
        rotation: int = 0,
        gate_required: int = 2,
    ):
        node = WDNode(node_id, col, row, ntype, rotation, gate_required)
        self.nodes[node_id] = node
        self.adj.setdefault(node_id, [])
        if ntype == TYPE_START:
            self.start_id = node_id
        if ntype == TYPE_EXIT:
            self.exit_id = node_id
    def add_edge(self, a_id: str, b_id: str):
        if a_id not in self.nodes or b_id not in self.nodes:
            return
        self.edges.append((a_id, b_id))
        self.adj[a_id].append(b_id)
        self.adj[b_id].append(a_id)
    def build_demo(self):
        """
        ДЕМО-шаблон:
            START – LINE – CORNER – CROSS – GATE – EXIT
        Ворота здесь gate_required=1, чтобы демо проходилась одной линией.
        В своих уровнях ставь gate_required=2.
        """
        self.clear_graph()
        r = 2
        self.add_node("start", 0, 4, TYPE_START)
        self.add_node("line1", 0, 3, TYPE_LINE, rotation=1)
        self.add_node("corner1", 0, 2, TYPE_CORNER, rotation=1)
        self.add_node("line2", 1, 2, TYPE_LINE, rotation=1)
        self.add_node("cross", 2, 2, TYPE_CROSS, rotation=1)
        self.add_node("corner2", 2, 3, TYPE_CORNER, rotation=1)
        self.add_node("corner5", 6, 1, TYPE_CORNER, rotation=1)
        self.add_node("corner3", 2, 1, TYPE_CORNER, rotation=1)
        self.add_node("line3", 3, 1, TYPE_LINE, rotation=1)
        self.add_node("line4", 4, 1, TYPE_LINE, rotation=1)
        self.add_node("line5", 5, 1, TYPE_LINE, rotation=1)
        self.add_node("corner4", 1, 3, TYPE_CORNER, rotation=1)

        self.add_node("cross2", 1, 4, TYPE_CROSS, rotation=1)
        self.add_node("line6", 1, 5, TYPE_LINE, rotation=1)
        self.add_node("corner6", 1, 6, TYPE_CORNER, rotation=1)
        self.add_node("line10", 2, 6, TYPE_LINE, rotation=1)
        self.add_node("corner14", 3, 6, TYPE_CORNER, rotation=1)
        self.add_node("cross3", 3, 5, TYPE_CROSS, rotation=1)
        self.add_node("line11", 2, 5, TYPE_LINE, rotation=1)
        self.add_node("line12", 4, 5, TYPE_LINE, rotation=1)
        self.add_node("line13", 5, 5, TYPE_LINE, rotation=2)
        self.add_node("corner15", 6, 5, TYPE_CORNER, rotation=2)
        self.add_node("line14", 6, 4, TYPE_LINE, rotation=2)
        self.add_node("line15", 6, 3, TYPE_LINE, rotation=1)
        self.add_node("corner16", 6, 6, TYPE_CORNER, rotation=3)
        self.add_node("line16", 5, 6, TYPE_LINE, rotation=1)
        self.add_node("line17", 4, 6, TYPE_LINE, rotation=1)

        self.add_node("line7", 2, 4, TYPE_LINE, rotation=1)
        self.add_node("corner7", 3, 4, TYPE_CORNER, rotation=1)
        self.add_node("corner8", 3, 3, TYPE_CORNER, rotation=2)
        self.add_node("corner9", 4, 3, TYPE_CORNER, rotation=1)
        self.add_node("corner10", 4, 4, TYPE_CORNER, rotation=3)
        self.add_node("corner11", 5, 4, TYPE_CORNER, rotation=2)
        self.add_node("corner12", 5, 2, TYPE_CORNER, rotation=2)
        self.add_node("line8", 4, 2, TYPE_LINE, rotation=1)
        self.add_node("line9", 5, 3, TYPE_LINE, rotation=1)
        self.add_node("corner13", 3, 2, TYPE_CORNER, rotation=1)


        self.add_node("gate", 6, 2, TYPE_GATE, gate_required=3)
        self.add_node("line18", 7, 2, TYPE_LINE, rotation=1)
        self.add_node("corner17", 8, 2, TYPE_CORNER, rotation=1)
        self.add_node("corner18", 8, 3, TYPE_CORNER, rotation=1)
        self.add_node("corner19", 7, 3, TYPE_CORNER, rotation=1)
        self.add_node("corner20", 7, 4, TYPE_CORNER, rotation=1)
        self.add_node("line22", 8, 4, TYPE_LINE, rotation=1)
        self.add_node("exit", 9, 4, TYPE_EXIT)

        self.add_edge("gate", "line18")
        self.add_edge("line18", "corner17")
        self.add_edge("corner17", "corner18")
        self.add_edge("corner18", "corner19")
        self.add_edge("corner19", "corner20")
        self.add_edge("corner20", "line22")
        self.add_edge("line22", "exit")

        self.add_edge("start","line1")
        self.add_edge("line1", "corner1")
        self.add_edge("corner1", "line2")
        self.add_edge("line2", "cross")
        self.add_edge("cross", "corner2")
        self.add_edge("cross", "corner3")

        self.add_edge("corner2", "corner4")
        self.add_edge("corner3", "line3")
        self.add_edge("line3", "line4")
        self.add_edge("line4", "line5")
        self.add_edge("line5", "corner5")
        self.add_edge("corner5", "gate")

        self.add_edge("corner4", "cross2")
        self.add_edge("cross2", "line6")
        self.add_edge("line6", "corner6")
        self.add_edge("corner6", "line10")
        self.add_edge("line10", "corner14")
        self.add_edge("corner14", "cross3")
        self.add_edge("cross3", "line11")
        self.add_edge("cross3", "line12")
        self.add_edge("line12", "line13")
        self.add_edge("line13", "corner15")
        self.add_edge("corner15", "line14")
        self.add_edge("corner15", "corner16")
        self.add_edge("corner16", "line16")
        self.add_edge("line16", "line17")
        self.add_edge("line14", "line15")
        self.add_edge("line15", "gate")

        self.add_edge("cross2", "line7")
        self.add_edge("line7", "corner7")
        self.add_edge("corner7", "corner8")
        self.add_edge("corner8", "corner9")
        self.add_edge("corner9", "corner10")
        self.add_edge("corner10", "corner11")
        self.add_edge("corner11", "line9")
        self.add_edge("line9", "corner12")
        self.add_edge("corner12", "gate")
        self.add_edge("corner12", "line8")
        self.add_edge("line8", "corner13")


    # =================== ГЕОМЕТРИЯ И НАПРАВЛЕНИЯ =================== #
    def compute_layout(self, w: int, h: int):
        """
        Авто-центрирование сетки по размерам окна.
        """
        self.vp = Viewport.from_canvas(self.canvas, self.root)
        vp = self.vp
        self.spacing = vp.px(160)
        self.margin = vp.px(70)
        if not self.nodes:
            self.origin_x = w // 2
            self.origin_y = h // 2
            return
        cols = [n.col for n in self.nodes.values()]
        rows = [n.row for n in self.nodes.values()]
        min_c, max_c = min(cols), max(cols)
        min_r, max_r = min(rows), max(rows)
        cx = w // 2
        cy = h // 2
        grid_cx = (min_c + max_c) / 2.0
        grid_cy = (min_r + max_r) / 2.0
        self.origin_x = cx - grid_cx * self.spacing
        self.origin_y = cy - grid_cy * self.spacing
    def node_xy(self, node: WDNode) -> tuple[int, int]:
        x = self.origin_x + node.col * self.spacing
        y = self.origin_y + node.row * self.spacing
        return int(x), int(y)
    @staticmethod
    def dir_between(a: WDNode, b: WDNode) -> int | None:
        """
        0=UP, 1=RIGHT, 2=DOWN, 3=LEFT относительно a → b.
        """
        dc = b.col - a.col
        dr = b.row - a.row
        if dc == 1 and dr == 0:
            return 1
        if dc == -1 and dr == 0:
            return 3
        if dr == -1 and dc == 0:
            return 0
        if dr == 1 and dc == 0:
            return 2
        return None
    # ======================== ЛОГИКА ПИТАНИЯ ======================== #
    def recalculate_power(self):
        # сброс
        for node in self.nodes.values():
            node.powered = False
            node.gate_input_dirs.clear()
        if not self.start_id or self.start_id not in self.nodes:
            return
        start = self.nodes[self.start_id]
        start.powered = True
        queue: list[str] = [self.start_id]
        visited: set[str] = set()
        while queue:
            nid = queue.pop(0)
            if nid in visited:
                continue
            visited.add(nid)
            node = self.nodes[nid]
            for nb_id in self.adj.get(nid, []):
                nb = self.nodes[nb_id]
                d_ab = self.dir_between(node, nb)
                if d_ab is None:
                    continue
                d_ba = (d_ab + 2) % 4
                # Порты должны смотреть друг на друга
                if d_ab not in node.ports:
                    continue
                if d_ba not in nb.ports:
                    continue
                # Узел должен быть запитан, чтобы передавать
                if not node.powered:
                    continue
                # ---- приём питания узлом nb ---- #
                if nb.type == TYPE_GATE:
                    nb.gate_input_dirs.add(d_ba)
                    if (not nb.powered) and len(nb.gate_input_dirs) >= max(1, nb.gate_required):
                        nb.powered = True
                        queue.append(nb_id)
                elif nb.type == TYPE_EXIT:
                    if not nb.powered:
                        nb.powered = True
                        # фиксируем прохождение уровня
                        if not self.level_completed:
                            self.level_completed = True
                            self.timer_running = False
                            self.elapsed_final = time.perf_counter() - self.timer_start
                            self.sounds["lock_open"].play()
                            # через 3 сек показываем плашку
                            self.root.after(3000, self.show_completion_window)
                else:
                    if not nb.powered:
                        nb.powered = True
                        queue.append(nb_id)
    # ========================= АНИМАЦИЯ ========================= #
    def animate(self):
        if not self.anim_loop_running:
            return
        self.ticks += 1
        self.spin_offset = (self.spin_offset + 1.5) % 9999  # вращение пунктира
        # двигаем фоновые частицы
        for p in self.bg_particles:
            p["x"] = (p["x"] + p["dx"]) % 1.0
            p["y"] = (p["y"] + p["dy"]) % 1.0
        any_finished = False
        # обновляем анимацию поворота узлов
        for node in self.nodes.values():
            if node.animating:
                node.anim_step += 1
                if node.anim_step >= node.anim_steps:
                    node.animating = False
                    node.rotation = (node.rotation + 1) % 4
                    node.visual_angle = node.rotation * 90.0
                    any_finished = True
                else:
                    t = node.anim_step / node.anim_steps
                    node.visual_angle = (
                        node.anim_from_angle
                        + (node.anim_to_angle - node.anim_from_angle) * t
                    )
        if any_finished:
            self.recalculate_power()
        self.redraw()
        # ~25 FPS
        self.root.after(40, self.animate)
    # ========================= ОТРИСОВКА ========================= #
    def redraw(self):
        self.canvas.delete(self.layer_tag)
        # реальные размеры canvas
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 1:
            w = int(self.canvas["width"])
        if h <= 1:
            h = int(self.canvas["height"])
        self.compute_layout(w, h)
        margin = self.margin
        vp = self.vp
        # фон
        self.draw_background(w, h)
        # рамка
        self.canvas.create_rectangle(
            margin, margin,
            w - margin, h - margin,
            outline="#1b2835",
            width=vp.wid(3),
            tags=self.layer_tag,
        )
        # заголовок
        self.canvas.create_text(
            w // 2, margin - vp.px(25),
            text="CtOS  //  ZERO-DAY NODE GRID",
            fill="#7de4ff",
            font=vp.consolas(16, bold=True),
            tags=self.layer_tag,
        )
        self.canvas.create_text(
            w // 2, margin - vp.px(8),
            text="Rotate nodes to route power from START through GATE to EXIT",
            fill="#4b6c7f",
            font=vp.consolas(10),
            tags=self.layer_tag,
        )
        # UI-EXIT
        btn_w, btn_h = vp.px(90), vp.px(28)
        bx2 = w - margin
        bx1 = bx2 - btn_w
        by1 = margin - vp.px(40)
        by2 = by1 + btn_h
        self.ui_exit_bbox = (bx1, by1, bx2, by2)
        self.canvas.create_rectangle(
            bx1, by1, bx2, by2,
            outline="#ff4444", width=vp.wid(2),
            tags=self.layer_tag,
        )
        self.canvas.create_text(
            (bx1 + bx2) // 2,
            (by1 + by2) // 2,
            text="EXIT",
            fill="#ff4444",
            font=vp.consolas(11, bold=True),
            tags=self.layer_tag,
        )
        # рёбра
        for a_id, b_id in self.edges:
            self.draw_edge(self.nodes[a_id], self.nodes[b_id])
        # узлы
        for node in self.nodes.values():
            self.draw_node(node)
        # таймер
        if self.timer_running:
            elapsed = time.perf_counter() - self.timer_start
        else:
            elapsed = self.elapsed_final
        timer_text = self.format_time(elapsed)
        self.canvas.create_text(
            w - margin - vp.px(80), margin,
            text=timer_text,
            fill="#55caff",
            font=vp.consolas(16, bold=True),
            tags=self.layer_tag,
        )
    # ---------------- Фон ---------------- #
    def draw_background(self, w: int, h: int):
        vp = self.vp
        # Тёмный фон
        self.canvas.create_rectangle(
            0, 0, w, h,
            fill="black",
            outline="",
            tags=self.layer_tag,
        )
        # Неоновая сетка
        cell = vp.px(80)
        cell = max(24, cell)
        offset = int((self.ticks * 0.5) % cell)
        for x in range(-cell, w + cell, cell):
            self.canvas.create_line(
                x + offset, 0, x + offset, h,
                fill="#08222f",
                width=vp.wid(1),
                tags=self.layer_tag,
            )
        for y in range(-cell, h + cell, cell):
            self.canvas.create_line(
                0, y + offset, w, y + offset,
                fill="#08222f",
                width=vp.wid(1),
                tags=self.layer_tag,
            )
        # Неоновые частицы
        for p in self.bg_particles:
            px = int(p["x"] * w)
            py = int(p["y"] * h)
            r = p["r"] * vp.scale
            # лёгкая пульсация яркости
            pulse = 0.5 + 0.5 * math.sin(self.ticks / 15.0 + px * 0.01)
            c = int(80 + 80 * pulse)
            color = f"#{0:02x}{c:02x}{255:02x}"
            rr = max(1.0, r)
            self.canvas.create_oval(
                px - rr, py - rr, px + rr, py + rr,
                fill=color,
                outline="",
                tags=self.layer_tag,
            )
    def draw_edge(self, a: WDNode, b: WDNode):
        x1, y1 = self.node_xy(a)
        x2, y2 = self.node_xy(b)
        active = a.powered and b.powered
        color = "#55caff" if active else "#2a3b47"
        vp = self.vp
        lw = vp.wid(4) if active else vp.wid(2)
        # основная линия
        self.canvas.create_line(
            x1, y1, x2, y2,
            fill=color,
            width=lw,
            capstyle="round",
            tags=self.layer_tag,
        )
        # бегущий луч по активной линии
        if active:
            base_t = (self.ticks * 0.03) % 1.0
            for phase in (0.0, 0.5):
                t = (base_t + phase) % 1.0
                px = x1 + (x2 - x1) * t
                py = y1 + (y2 - y1) * t
                r = vp.px(4)
                self.canvas.create_oval(
                    px - r, py - r, px + r, py + r,
                    outline="",
                    fill="#7de4ff",
                    tags=self.layer_tag,
                )
    def draw_node(self, node: WDNode):
        x, y = self.node_xy(node)
        if node.type in (TYPE_NORMAL, TYPE_LINE, TYPE_CORNER, TYPE_CROSS):
            self.draw_circle_node(node, x, y)
        elif node.type == TYPE_GATE:
            self.draw_gate_node(node, x, y)
        elif node.type == TYPE_START:
            self.draw_start_node(node, x, y)
        elif node.type == TYPE_EXIT:
            self.draw_exit_node(node, x, y)
    # ------------------- КРУГОВЫЕ УЗЛЫ ------------------- #
    def draw_circle_node(self, node: WDNode, x: int, y: int):
        vp = self.vp
        outer_r = vp.px(22)
        inner_r = vp.px(15)
        # Внешний пунктир (вращающийся при питании)
        if node.powered:
            outline = "#88caff"
            dash_offset = self.spin_offset
        else:
            outline = "#233746"
            dash_offset = 0
        self.canvas.create_oval(
            x - outer_r, y - outer_r,
            x + outer_r, y + outer_r,
            outline=outline,
            width=vp.wid(2),
            dash=vp.dash(3, 3),
            dashoffset=dash_offset,
            tags=self.layer_tag,
        )
        # Внутренний чёрный круг
        self.canvas.create_oval(
            x - inner_r, y - inner_r,
            x + inner_r, y + inner_r,
            outline="#000000",
            fill="#000000",
            width=vp.wid(2),
            tags=self.layer_tag,
        )
        # шаблон узла (линия, угол, крест)
        shape_color = "#55caff" if node.powered else "#233746"
        if node.type == TYPE_LINE:
            self.draw_line_template(node, x, y, shape_color)
        elif node.type == TYPE_CORNER:
            self.draw_corner_template(node, x, y, shape_color)
        elif node.type == TYPE_CROSS:
            self.draw_cross_template(node, x, y, shape_color)
        # стрелка-направление
        dir_color = "#6fd6ff" if node.powered else "#ffffff"
        self.draw_direction_marker(node, x, y, dir_color)
    @staticmethod
    def _rot(dx: float, dy: float, angle_deg: float) -> tuple[float, float]:
        a = math.radians(angle_deg)
        ca, sa = math.cos(a), math.sin(a)
        return dx * ca - dy * sa, dx * sa + dy * ca
    def draw_direction_marker(self, node: WDNode, x: int, y: int, color: str):
        L = self.vp.px(11)
        dx, dy = self._rot(0, -L, node.visual_angle)
        self.canvas.create_line(
            x, y, x + dx, y + dy,
            fill=color,
            width=self.vp.wid(3),
            tags=self.layer_tag,
        )
    # --------- LINE --------- #
    def draw_line_template(self, node: WDNode, x: int, y: int, color: str):
        L = self.vp.px(13)
        dx1, dy1 = self._rot(0, -L, node.visual_angle)
        dx2, dy2 = self._rot(0, L, node.visual_angle)
        self.canvas.create_line(
            x + dx1, y + dy1, x + dx2, y + dy2,
            fill=color,
            width=self.vp.wid(2),
            tags=self.layer_tag,
        )
    # --------- CORNER --------- #
    def draw_corner_template(self, node: WDNode, x: int, y: int, color: str):
        L = self.vp.px(11)
        # база: угол UP+RIGHT => (0,-L) и (L,0)
        dx1, dy1 = self._rot(0, -L, node.visual_angle)
        dx2, dy2 = self._rot(L, 0, node.visual_angle)
        self.canvas.create_line(
            x, y, x + dx1, y + dy1,
            fill=color,
            width=self.vp.wid(2),
            tags=self.layer_tag,
        )
        self.canvas.create_line(
            x, y, x + dx2, y + dy2,
            fill=color,
            width=self.vp.wid(2),
            tags=self.layer_tag,
        )
    # --------- CROSS --------- #
    def draw_cross_template(self, node: WDNode, x: int, y: int, color: str):
        L = self.vp.px(10)
        dx1, dy1 = self._rot(-L, 0, node.visual_angle)
        dx2, dy2 = self._rot(L, 0, node.visual_angle)
        dx3, dy3 = self._rot(0, -L, node.visual_angle)
        dx4, dy4 = self._rot(0, L, node.visual_angle)
        self.canvas.create_line(
            x + dx1, y + dy1, x + dx2, y + dy2,
            fill=color,
            width=self.vp.wid(2),
            tags=self.layer_tag,
        )
        self.canvas.create_line(
            x + dx3, y + dy3, x + dx4, y + dy4,
            fill=color,
            width=self.vp.wid(2),
            tags=self.layer_tag,
        )
    # ---------------- GATE ---------------- #
    def draw_gate_node(self, node: WDNode, x: int, y: int):
        size = self.vp.px(26)
        col = "#6fd6ff" if node.powered else "#ffffff"
        self.canvas.create_polygon(
            x, y - size,
            x + size, y,
            x, y + size,
            x - size, y,
            outline=col,
            fill="#000000",
            width=self.vp.wid(3),
            tags=self.layer_tag,
        )
        self.canvas.create_text(
            x, y,
            text="🔒",
            fill=col,
            font=self.vp.consolas(18),
            tags=self.layer_tag,
        )
    # ---------------- START ---------------- #
    def draw_start_node(self, node: WDNode, x: int, y: int):
        size = self.vp.px(26)
        col = "#ffffff"
        self.canvas.create_polygon(
            x, y - size,
            x + size, y,
            x, y + size,
            x - size, y,
            outline=col,
            fill="#000000",
            width=self.vp.wid(3),
            tags=self.layer_tag,
        )
        mini = self.vp.px(8)
        o = self.vp.px(10)
        offsets = [(-o, 0), (o, 0), (0, -o), (0, o)]
        for dx, dy in offsets:
            cx = x + dx
            cy = y + dy
            self.canvas.create_polygon(
                cx, cy - mini,
                cx + mini, cy,
                cx, cy + mini,
                cx - mini, cy,
                outline=col,
                fill="",
                width=self.vp.wid(2),
                tags=self.layer_tag,
            )
    # ---------------- EXIT ---------------- #
    def draw_exit_node(self, node: WDNode, x: int, y: int):
        size = self.vp.px(26)
        if node.powered:
            pulse = 0.4 + 0.6 * abs(math.sin(self.ticks / 10.0))
            g = int(255 * pulse)
            outline = f"#{0:02x}{g:02x}{80:02x}"
        else:
            outline = "#ffffff"
        self.canvas.create_polygon(
            x, y - size,
            x + size, y,
            x, y + size,
            x - size, y,
            outline=outline,
            fill="#000000",
            width=self.vp.wid(3),
            tags=self.layer_tag,
        )
        self.canvas.create_text(
            x, y,
            text="EXIT",
            fill=outline,
            font=self.vp.consolas(11, bold=True),
            tags=self.layer_tag,
        )
    # ====================== ВЗАИМОДЕЙСТВИЕ ====================== #
    def _on_escape(self, event=None):
        if self._exit_guard:
            return
        self._exit_guard = True
        self.anim_loop_running = False
        self.canvas.unbind("<Button-1>")
        self.root.unbind("<Escape>")
        self.canvas.delete(self.layer_tag)
        self.on_exit()
    def _ui_exit_click(self, x: int, y: int) -> bool:
        if not self.ui_exit_bbox:
            return False
        x1, y1, x2, y2 = self.ui_exit_bbox
        return x1 <= x <= x2 and y1 <= y <= y2
    def find_node_by_point(self, x: int, y: int, radius: int | None = None) -> WDNode | None:
        r = self.vp.px(26) if radius is None else radius
        r2 = r * r
        for node in self.nodes.values():
            nx, ny = self.node_xy(node)
            dx = nx - x
            dy = ny - y
            if dx * dx + dy * dy <= r2:
                return node
        return None
    def on_click(self, event):
        # клик по UI-EXIT
        if self._ui_exit_click(event.x, event.y):
            self._on_escape()
            return
        node = self.find_node_by_point(event.x, event.y)
        if not node:
            return
        # вращаем только круговые узлы (line/corner/cross)
        if node.type not in (TYPE_NORMAL, TYPE_LINE, TYPE_CORNER, TYPE_CROSS):
            return
        if node.animating:
            # пока анимация не закончилась, игнорируем новые клики
            return
        # запускаем плавный поворот на 90°
        self.sounds["pulse"].play()
        node.animating = True
        node.anim_from_angle = node.visual_angle
        node.anim_to_angle = node.visual_angle + 90.0
        node.anim_step = 0
        node.anim_steps = 10  # ~10 кадров на поворот
    # ====================== ТАЙМЕР И ОКНО ФИНАЛА ====================== #
    @staticmethod
    def format_time(t: float) -> str:
        ms = int((t % 1) * 1000)
        sec = int(t) % 60
        minu = int(t // 60)
        return f"{minu:02}:{sec:02}.{ms:03}"
    def show_completion_window(self):
        if self.success_shown:
            return
        self.success_shown = True
        # прекращаем дальнейшую анимацию
        self.anim_loop_running = False
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 1:
            w = int(self.canvas["width"])
        if h <= 1:
            h = int(self.canvas["height"])
        vp = getattr(self, "vp", None) or Viewport.from_canvas(self.canvas, self.root)
        # затемнение фона
        self.canvas.create_rectangle(
            0, 0, w, h,
            fill="#000000",
            stipple="gray50",
            tags=self.layer_tag,
        )
        # размеры панели (как у DataExfil-плашки)
        box_w = vp.px(700)
        box_h = vp.px(360)
        x0 = (w - box_w) // 2
        y0 = (h - box_h) // 2
        x1 = x0 + box_w
        y1 = y0 + box_h
        # панель
        self.canvas.create_rectangle(
            x0, y0, x1, y1,
            outline="#48bfff",
            width=vp.wid(2),
            fill="#020b13",
            tags=self.layer_tag,
        )
        # заголовок
        self.canvas.create_text(
            (x0 + x1) // 2, y0 + vp.px(35),
            text="ZERO-DAY VULNERABILITY DISCOVERED\n",
            fill="#48bfff",
            font=vp.consolas(18, bold=True),
            tags=self.layer_tag,
        )
        # время
        self.canvas.create_text(
            (x0 + x1) // 2, y0 + vp.px(70),
            text=f"Time: {self.format_time(self.elapsed_final)}\n",
            fill="#7de4ff",
            font=vp.consolas(14, bold=True),
            tags=self.layer_tag,
        )
        # описание
        description = (
            "\n"
            "\n"
            "\n"
            "\n"
            "\nТы успешно направил энергию через узлы сети, открыв защищённые ворота.\n"
            "\n"
            "Zero-Day — это уязвимость, о которой ещё никто не знает.\n"
            "У неё нет патчей, сигнатур и механизмов защиты.\n"
            "\n"
            "Эта мини-игра моделирует процесс эксплуатации Zero-Day:\n"
            " • поиск маршрутов внутри инфраструктуры,\n"
            " • обход защищённых сегментов сети,\n"
            " • активацию скрытых узлов,\n"
            " • получение доступа к целевой точке (EXIT).\n"
            "\n"
            "\n"
        )
        self.canvas.create_text(
            (x0 + x1) // 2, y0 + vp.px(160),
            text=description,
            fill="#cdeaff",
            font=vp.consolas(12),
            width=box_w - vp.px(80),
            justify="center",
            tags=self.layer_tag,
        )
        # кнопка CLOSE
        btn_x0 = (x0 + x1) // 2 - vp.px(90)
        btn_x1 = (x0 + x1) // 2 + vp.px(90)
        btn_y0 = y1 - vp.px(60)
        btn_y1 = y1 - vp.px(20)
        btn = self.canvas.create_rectangle(
            btn_x0, btn_y0, btn_x1, btn_y1,
            outline="#48bfff",
            width=vp.wid(2),
            fill="",
            tags=self.layer_tag,
        )
        btn_label = self.canvas.create_text(
            (btn_x0 + btn_x1) // 2,
            (btn_y0 + btn_y1) // 2,
            text="CLOSE",
            fill="#48bfff",
            font=vp.consolas(13, bold=True),
            tags=self.layer_tag,
        )
        def on_enter(event):
            self.canvas.itemconfig(btn, fill="#0a2a44")
            self.canvas.itemconfig(btn_label, fill="white")
        def on_leave(event):
            self.canvas.itemconfig(btn, fill="")
            self.canvas.itemconfig(btn_label, fill="#48bfff")
        def on_click(event):
            self._on_escape()
        for tag in (btn, btn_label):
            self.canvas.tag_bind(tag, "<Enter>", on_enter)
            self.canvas.tag_bind(tag, "<Leave>", on_leave)
            self.canvas.tag_bind(tag, "<Button-1>", on_click)
# ========================= ЛОКАЛЬНЫЙ ТЕСТ ========================= #
if __name__ == "__main__":
    root = tk.Tk()
    #root.geometry("1280x720")
    root.title("Zero-Day WD Ports Template")
    # можно включить фуллскрин:
    root.attributes("-fullscreen", True)
    canvas = tk.Canvas(root, bg="black", width=1280, height=720)
    canvas.pack(fill="both", expand=True)
    def back():
        root.destroy()
    ZeroDownModule(canvas, root, back)
    root.mainloop()
