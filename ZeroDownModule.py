import tkinter as tk
import math
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
        self.rotation = rotation % 4
        self.visual_angle: float = self.rotation * 90.0
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
        return { (p + self.rotation) % 4 for p in self.base_ports }
class ZeroDownModule:
    """
    Шаблон мини-игры Zero-Day в стиле Watch Dogs.
    ✔ Полноценная портовая логика.
    ✔ Плавный поворот узлов (Rotation: A).
    ✔ Пульсирующий луч по активным линиям (Beam: 1).
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
        # визуал
        self.spacing = 160
        self.origin_x = 200
        self.origin_y = 250
        self.layer_tag = "wd_layer"
        # UI EXIT
        self.ui_exit_bbox = None
        # анимация
        self.ticks = 0
        self.anim_loop_running = True
        # демо-уровень
        self.build_demo()
        # логика + отрисовка
        self.recalculate_power()
        self.redraw()
        # управление
        self.canvas.bind("<Button-1>", self.on_click)
        root.bind("<Escape>", self._on_escape)
        # запуск анимации
        self.animate()
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
        ntype: str = TYPE_NORMAL,
        rotation: int = 0,
        gate_required: int | None = None,
    ):
        """
        Добавить узел.
        col, row — позиция в условной сетке (не пиксели).
        rotation — поворот 0..3 (на 90°) для логики портов.
        ntype — один из:
            TYPE_LINE, TYPE_CORNER, TYPE_CROSS, TYPE_GATE, TYPE_START, TYPE_EXIT.
        gate_required — для GATE: минимальное число разных направлений входа.
        """
        if gate_required is None:
            gate_required = 2
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
        self.adj.setdefault(a_id, []).append(b_id)
        self.adj.setdefault(b_id, []).append(a_id)
    def build_demo(self):
        """
        ДЕМО-шаблон:
            START – LINE – CORNER – CROSS – GATE – EXIT
        Ворота здесь gate_required=1, чтобы демка проходилась одной линией.
        В своих уровнях ставь gate_required=2.
        """
        self.clear_graph()
        r = 2
        self.add_node("start", 0, 2, TYPE_START)
        self.add_node("line", 1, 2, TYPE_LINE, rotation=1)        # горизонтальная линия
        self.add_node("corner", 2, 2, TYPE_CORNER, rotation=1)    # угол
        self.add_node("corner2", 2, 1, TYPE_CORNER, rotation=1)  # угол
        self.add_node("cross", 3, 1, TYPE_CROSS)                  # крест
        self.add_node("corner3", 3, 0, TYPE_CORNER, rotation=1)  # угол
        self.add_node("corner4", 3, 2, TYPE_CORNER, rotation=1)  # угол
        self.add_node("line2", 4, 0, TYPE_LINE, rotation=1)        # горизонтальная линия
        self.add_node("line3", 4, 2, TYPE_LINE, rotation=1)        # горизонтальная линия
        self.add_node("corner5", 5, 0, TYPE_CORNER, rotation=1)  # угол
        self.add_node("corner6", 5, 2, TYPE_CORNER, rotation=1)  # угол
        self.add_node("gate", 5, 1, TYPE_GATE, gate_required=2)   # ворота, для демо 1
        self.add_node("exit", 6, 1, TYPE_EXIT)

        self.add_edge("start",  "line")
        self.add_edge("line",  "corner")
        self.add_edge("corner",  "corner2")
        self.add_edge("corner2",  "cross")
        self.add_edge("cross", "corner3")
        self.add_edge("cross",  "corner4")
        self.add_edge("corner3", "line2")
        self.add_edge("corner4",  "line3")
        self.add_edge("line2", "corner5")
        self.add_edge("line3", "corner6")
        self.add_edge("corner5",  "gate")
        self.add_edge("corner6",  "gate")
        self.add_edge("gate", "exit")
    # =================== ГЕОМЕТРИЯ И НАПРАВЛЕНИЯ =================== #
    def node_xy(self, node: WDNode) -> tuple[int, int]:
        x = self.origin_x + node.col * self.spacing
        y = self.origin_y + node.row * self.spacing
        return x, y
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
                    # Запоминаем направление
                    nb.gate_input_dirs.add(d_ba)
                    if not nb.powered and len(nb.gate_input_dirs) >= max(1, nb.gate_required):
                        nb.powered = True
                        queue.append(nb_id)
                elif nb.type == TYPE_EXIT:
                    nb.powered = True
                else:
                    if not nb.powered:
                        nb.powered = True
                        queue.append(nb_id)
    # ========================= АНИМАЦИЯ ========================= #
    def animate(self):
        if not self.anim_loop_running:
            return
        self.ticks += 1
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
        w = int(self.canvas["width"])
        h = int(self.canvas["height"])
        # фон
        self.canvas.create_rectangle(
            0, 0, w, h,
            fill="black",
            outline="",
            tags=self.layer_tag,
        )
        margin = 70
        self.canvas.create_rectangle(
            margin, margin,
            w - margin, h - margin,
            outline="#1b2835",
            width=3,
            tags=self.layer_tag,
        )
        # заголовок
        self.canvas.create_text(
            w // 2, margin - 25,
            text="CtOS  //  ZERO-DAY NODE GRID (TEMPLATE)",
            fill="#7de4ff",
            font=("Consolas", 16, "bold"),
            tags=self.layer_tag,
        )
        self.canvas.create_text(
            w // 2, margin - 8,
            text="Rotate nodes to route power from START through GATE to EXIT",
            fill="#4b6c7f",
            font=("Consolas", 10),
            tags=self.layer_tag,
        )
        # UI-EXIT
        btn_w, btn_h = 90, 28
        bx2 = w - margin
        bx1 = bx2 - btn_w
        by1 = margin - 40
        by2 = by1 + btn_h
        self.ui_exit_bbox = (bx1, by1, bx2, by2)
        self.canvas.create_rectangle(
            bx1, by1, bx2, by2,
            outline="#ff4444", width=2,
            tags=self.layer_tag,
        )
        self.canvas.create_text(
            (bx1 + bx2) // 2,
            (by1 + by2) // 2,
            text="EXIT",
            fill="#ff4444",
            font=("Consolas", 11, "bold"),
            tags=self.layer_tag,
        )
        # рёбра
        for a_id, b_id in self.edges:
            self.draw_edge(self.nodes[a_id], self.nodes[b_id])
        # узлы
        for node in self.nodes.values():
            self.draw_node(node)
    def draw_edge(self, a: WDNode, b: WDNode):
        x1, y1 = self.node_xy(a)
        x2, y2 = self.node_xy(b)
        active = a.powered and b.powered
        color = "#55caff" if active else "#2a3b47"
        width = 4 if active else 2
        # основная линия
        self.canvas.create_line(
            x1, y1, x2, y2,
            fill=color,
            width=width,
            capstyle="round",
            tags=self.layer_tag,
        )
        # бегущий луч по активной линии (Beam: 1)
        if active:
            # t бежит от 0 до 1
            base_t = (self.ticks * 0.03) % 1.0
            for phase in (0.0, 0.5):
                t = (base_t + phase) % 1.0
                px = x1 + (x2 - x1) * t
                py = y1 + (y2 - y1) * t
                r = 4
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
        outer_r = 22
        inner_r = 15
        # внешний пунктир
        self.canvas.create_oval(
            x - outer_r, y - outer_r,
            x + outer_r, y + outer_r,
            outline="#233746",
            width=2,
            dash=(3, 3),
            tags=self.layer_tag,
        )
        # внутренний чёрный круг
        self.canvas.create_oval(
            x - inner_r, y - inner_r,
            x + inner_r, y + inner_r,
            outline="#000000",
            fill="#000000",
            width=2,
            tags=self.layer_tag,
        )
        # шаблон (line / corner / cross)
        shape_color = "#55caff" if node.powered else "#233746"
        if node.type == TYPE_LINE:
            self.draw_line_template(node, x, y, shape_color)
        elif node.type == TYPE_CORNER:
            self.draw_corner_template(node, x, y, shape_color)
        elif node.type == TYPE_CROSS:
            self.draw_cross_template(node, x, y, shape_color)
        # стрелка-направление: просто короткий сегмент вверх, повернутый на visual_angle
        dir_color = "#6fd6ff" if node.powered else "#ffffff"
        self.draw_direction_marker(node, x, y, dir_color)
    @staticmethod
    def _rot(dx: float, dy: float, angle_deg: float) -> tuple[float, float]:
        a = math.radians(angle_deg)
        ca, sa = math.cos(a), math.sin(a)
        return dx * ca - dy * sa, dx * sa + dy * ca
    def draw_direction_marker(self, node: WDNode, x: int, y: int, color: str):
        L = 11
        # базовый вектор (0, -L), вращаем на visual_angle
        dx, dy = self._rot(0, -L, node.visual_angle)
        self.canvas.create_line(
            x, y, x + dx, y + dy,
            fill=color,
            width=3,
            tags=self.layer_tag,
        )
    # --------- внутренний шаблон для LINE --------- #
    def draw_line_template(self, node: WDNode, x: int, y: int, color: str):
        L = 13
        # базовая вертикальная линия от (0,-L) до (0,L)
        dx1, dy1 = self._rot(0, -L, node.visual_angle)
        dx2, dy2 = self._rot(0, L, node.visual_angle)
        self.canvas.create_line(
            x + dx1, y + dy1, x + dx2, y + dy2,
            fill=color,
            width=2,
            tags=self.layer_tag,
        )
    # --------- внутренний шаблон для CORNER --------- #
    def draw_corner_template(self, node: WDNode, x: int, y: int, color: str):
        L = 11
        # база (rotation=0): угол UP+RIGHT => сегменты (0,-L) и (L,0) от центра
        # просто вращаем оба сегмента на visual_angle
        dx1, dy1 = self._rot(0, -L, node.visual_angle)
        dx2, dy2 = self._rot(L, 0, node.visual_angle)
        self.canvas.create_line(
            x, y, x + dx1, y + dy1,
            fill=color,
            width=2,
            tags=self.layer_tag,
        )
        self.canvas.create_line(
            x, y, x + dx2, y + dy2,
            fill=color,
            width=2,
            tags=self.layer_tag,
        )
    # --------- внутренний шаблон для CROSS --------- #
    def draw_cross_template(self, node: WDNode, x: int, y: int, color: str):
        L = 10
        # базовый крест: горизонталь (±L, 0), вертикаль (0, ±L)
        # весь крест вращаем на visual_angle (на практике для крестов разницы почти не видно,
        # но так всё честно)
        dx1, dy1 = self._rot(-L, 0, node.visual_angle)
        dx2, dy2 = self._rot(L, 0, node.visual_angle)
        dx3, dy3 = self._rot(0, -L, node.visual_angle)
        dx4, dy4 = self._rot(0, L, node.visual_angle)
        self.canvas.create_line(
            x + dx1, y + dy1, x + dx2, y + dy2,
            fill=color,
            width=2,
            tags=self.layer_tag,
        )
        self.canvas.create_line(
            x + dx3, y + dy3, x + dx4, y + dy4,
            fill=color,
            width=2,
            tags=self.layer_tag,
        )
    # ---------------- GATE ---------------- #
    def draw_gate_node(self, node: WDNode, x: int, y: int):
        size = 26
        col = "#6fd6ff" if node.powered else "#ffffff"
        self.canvas.create_polygon(
            x, y - size,
            x + size, y,
            x, y + size,
            x - size, y,
            outline=col,
            fill="#000000",
            width=3,
            tags=self.layer_tag,
        )
        self.canvas.create_text(
            x, y,
            text="🔒",
            fill=col,
            font=("Consolas", 18),
            tags=self.layer_tag,
        )
    # ---------------- START ---------------- #
    def draw_start_node(self, node: WDNode, x: int, y: int):
        size = 26
        col = "#ffffff"
        self.canvas.create_polygon(
            x, y - size,
            x + size, y,
            x, y + size,
            x - size, y,
            outline=col,
            fill="#000000",
            width=3,
            tags=self.layer_tag,
        )
        mini = 8
        offsets = [(-10, 0), (10, 0), (0, -10), (0, 10)]
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
                width=2,
                tags=self.layer_tag,
            )
    # ---------------- EXIT ---------------- #
    def draw_exit_node(self, node: WDNode, x: int, y: int):
        size = 26
        if node.powered:
            # лёгкая пульсация по ticks
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
            width=3,
            tags=self.layer_tag,
        )
        self.canvas.create_text(
            x, y,
            text="EXIT",
            fill=outline,
            font=("Consolas", 11, "bold"),
            tags=self.layer_tag,
        )
    # ====================== ВЗАИМОДЕЙСТВИЕ ====================== #
    def _on_escape(self, event=None):
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
    def find_node_by_point(self, x: int, y: int, radius: int = 26) -> WDNode | None:
        r2 = radius * radius
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
            # пока анимация не закончилась, игнорируем новые клики по этому узлу
            return
        # запускаем плавный поворот на 90°
        node.animating = True
        node.anim_from_angle = node.visual_angle
        node.anim_to_angle = node.visual_angle + 90.0
        node.anim_step = 0
        node.anim_steps = 10  # ~10 кадров на поворот (≈0.4 сек)
# ========================= ЛОКАЛЬНЫЙ ТЕСТ ========================= #
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1280x720")
    root.title("Zero-Day WD Ports Template")
    canvas = tk.Canvas(root, bg="black", width=1280, height=720)
    canvas.pack(fill="both", expand=True)
    def back():
        root.destroy()
    ZeroDownModule(canvas, root, back)
    root.mainloop()
