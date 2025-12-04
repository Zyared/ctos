import tkinter as tk
import math
import os
try:
    import winsound
except ImportError:
    winsound = None
# --------- Типы узлов --------- #
TYPE_NORMAL = "normal"   # обычный узел
TYPE_GATE = "gate"       # ворота (замок)
TYPE_START = "start"     # старт
TYPE_EXIT = "exit"       # финиш
class GraphNode:
    """
    Узел графа в стиле Watch Dogs.
    direction: 0=UP, 1=RIGHT, 2=DOWN, 3=LEFT
    """
    def __init__(self, node_id, col, row, ntype=TYPE_NORMAL, direction=0, gate_required=1):
        self.id = node_id
        self.col = col
        self.row = row
        self.ntype = ntype
        self.direction = direction % 4
        self.gate_required = gate_required  # сколько входов нужно, чтобы ворота считались запитанными
        self.powered = False
class ZeroDownModule:
    """
    Шаблон мини-игры Zero-Day в стиле Watch Dogs.
    Главное:
      • узлы — чёрные круги с пунктирной окружностью и белым указателем направления;
        при активации указатель светится синим;
      • связи — серые линии между узлами, при активном обоих концах становятся синими;
      • START — чёрный ромб с 4 маленькими белыми ромбами;
      • GATE — чёрный ромб с белым замком;
      • EXIT — чёрный ромб, по контуру пульсация белым, при достижении мигает зелёным;
      • логика питания по направлению: из START сигнал идёт по графу
        только по рёбрам, куда «смотрит» указатель.
    """
    def __init__(self, canvas: tk.Canvas, root: tk.Tk, on_exit):
        self.canvas = canvas
        self.root = root
        self.on_exit = on_exit
        # Рендер-параметры
        self.layer_tag = "zero_down_layer"
        self.bg_color = "black"
        self.grid_spacing_x = 160
        self.grid_spacing_y = 160
        self.origin_x = 200
        self.origin_y = 220
        # Граф
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[tuple[str, str]] = []
        self.adj: dict[str, list[str]] = {}
        self.start_id = None
        self.exit_id = None
        # Анимация
        self.running = True
        self.ticks = 0
        # Звуки (опционально)
        self.sounds = {
            "click": os.path.join("sound", "click.wav"),
            "success": os.path.join("sound", "lock_open.wav"),
        }
        # Сборка уровня (демо) — ИМЕННО ЭТУ ЧАСТЬ ТЫ БУДЕШЬ МЕНЯТЬ ПОД СВОИ ПАТТЕРНЫ
        self.build_demo_level()
        # Привязка событий
        self.canvas.bind("<Button-1>", self.on_click)
        self.root.bind("<Escape>", self.handle_escape)
        # Первый пересчёт и отрисовка
        self.recalculate_power()
        self.redraw()
        # Запуск анимации
        self.animate()
    # ======================== УРОВЕНЬ / ШАБЛОН ======================== #
    def clear_graph(self):
        self.nodes.clear()
        self.edges.clear()
        self.adj.clear()
        self.start_id = None
        self.exit_id = None
    def add_node(self, node_id, col, row, ntype=TYPE_NORMAL, direction=0, gate_required=1):
        """
        Добавить узел в сетке (col, row).
        Узлы автоматически переводятся в координаты пикселей.
        """
        node = GraphNode(node_id, col, row, ntype, direction, gate_required)
        self.nodes[node_id] = node
        self.adj.setdefault(node_id, [])
        if ntype == TYPE_START:
            self.start_id = node_id
        if ntype == TYPE_EXIT:
            self.exit_id = node_id
    def add_edge(self, a_id, b_id):
        """Добавить неориентированное ребро между двумя узлами."""
        if a_id not in self.nodes or b_id not in self.nodes:
            return
        self.edges.append((a_id, b_id))
        self.adj.setdefault(a_id, []).append(b_id)
        self.adj.setdefault(b_id, []).append(a_id)
    def build_demo_level(self):
        """
        ДЕМОНСТРАЦИОННЫЙ ПАТТЕРН:
        ОДНА ЛИНИЯ ВИДОВ УЗЛОВ:
            START -> N1 -> GATE -> N2 -> EXIT
        • Узлы стоят на одной строке row=2 (для примера).
        • Ты можешь полностью переписать эту функцию под свою карту:
            - добавлять узлы self.add_node(...)
            - добавлять рёбра self.add_edge(...)
        """
        self.clear_graph()

        self.add_node("start", 0, 2, TYPE_START)
        self.add_node("n1", 1, 2, TYPE_NORMAL, direction=1)
        self.add_node("e2", 1, 1, TYPE_NORMAL, direction=1)
        self.add_node("n3", 2, 1, TYPE_NORMAL, direction=1)
        self.add_node("n4", 3, 1, TYPE_NORMAL, direction=1)
        self.add_node("n5", 2, 2, TYPE_NORMAL, direction=1)
        # Ворота: пока сделаем, что им достаточно 1 входа (gate_required=1)
        self.add_node("gate", 3, 2, TYPE_GATE, gate_required=0)
        self.add_node("n7", 4, 2, TYPE_NORMAL, direction=1)
        self.add_node("exit", 5, 2, TYPE_EXIT)
        # Связи по прямой
        self.add_edge("start", "n1")
        self.add_edge("n1", "e2")
        self.add_edge("e2", "n3")
        self.add_edge("n3", "n4")
        self.add_edge("n4", "gate")
        self.add_edge("n1", "n5")
        self.add_edge("n5", "gate")
        self.add_edge("gate", "n7")
        self.add_edge("n7", "exit")
    # ======================== ЛОГИКА ПИТАНИЯ ======================== #
    def node_coords(self, node: GraphNode):
        """Перевод (col,row) в пиксели."""
        x = self.origin_x + node.col * self.grid_spacing_x
        y = self.origin_y + node.row * self.grid_spacing_y
        return x, y
    @staticmethod
    def dir_from_to(a: GraphNode, b: GraphNode):
        """
        Геометрическое направление из A к B по сетке (4 направления).
        Если не по прямой — возвращает None.
        """
        dc = b.col - a.col
        dr = b.row - a.row
        if dc == 0 and dr < 0:
            return 0  # UP
        if dc > 0 and dr == 0:
            return 1  # RIGHT
        if dc == 0 and dr > 0:
            return 2  # DOWN
        if dc < 0 and dr == 0:
            return 3  # LEFT
        return None
    def recalculate_power(self):
        """
        Питание распространяется так:
        • START всегда запитан.
        • Из узла сигнал идёт только по тем рёбрам, куда смотрит указатель (direction).
        • GATE запитывается, когда к нему пришло нужное количество сигналов (gate_required).
        • EXIT считается достигнутым, если запитан.
        """
        # сброс
        for node in self.nodes.values():
            node.powered = False
        if not self.start_id or self.start_id not in self.nodes:
            return
        # START запитан по умолчанию
        self.nodes[self.start_id].powered = True
        # для ворот — учёт количества входов
        gate_inputs: dict[str, int] = {}
        queue = [self.start_id]
        visited = set()
        while queue:
            nid = queue.pop(0)
            if nid in visited:
                continue
            visited.add(nid)
            node = self.nodes[nid]
            for nb_id in self.adj.get(nid, []):
                nb = self.nodes[nb_id]
                # направление от node к nb
                d = self.dir_from_to(node, nb)
                if d is None:
                    continue
                # node может давать питание только в сторону direction
                if node.direction != d and node.ntype != TYPE_START:
                    # START не имеет направления — условно «раздаёт» всем соседям
                    continue
                if nb.ntype == TYPE_GATE:
                    # увеличиваем число входов
                    gate_inputs[nb_id] = gate_inputs.get(nb_id, 0) + 1
                    if gate_inputs[nb_id] >= max(1, nb.gate_required) and not nb.powered:
                        nb.powered = True
                        queue.append(nb_id)
                else:
                    if not nb.powered:
                        nb.powered = True
                        queue.append(nb_id)
    def is_exit_powered(self):
        return self.exit_id in self.nodes and self.nodes[self.exit_id].powered
    # ======================== ОТРИСОВКА ======================== #
    def redraw(self):
        self.canvas.delete(self.layer_tag)
        w = int(self.canvas["width"])
        h = int(self.canvas["height"])
        # фон
        self.canvas.create_rectangle(
            0, 0, w, h,
            fill=self.bg_color,
            outline="",
            tags=self.layer_tag
        )
        # лёгкая рамка панели
        panel_margin = 80
        self.canvas.create_rectangle(
            panel_margin, panel_margin,
            w - panel_margin, h - panel_margin,
            outline="#1b2835",
            width=3,
            tags=self.layer_tag
        )
        # заголовок
        self.canvas.create_text(
            w // 2, panel_margin - 30,
            text="CtOS  //  ZERO-DAY NODE GRID (TEMPLATE)",
            fill="#7de4ff",
            font=("Consolas", 16, "bold"),
            tags=self.layer_tag
        )
        # подсказка
        self.canvas.create_text(
            w // 2, panel_margin - 10,
            text="Rotate nodes to route the signal from START -> GATE -> EXIT",
            fill="#496a7f",
            font=("Consolas", 10),
            tags=self.layer_tag
        )
        # кнопка EXIT в правом верхнем углу
        bx1, by1, bx2, by2 = w - 160, panel_margin - 40, w - 60, panel_margin - 10
        self.exit_btn_bbox = (bx1, by1, bx2, by2)
        self.canvas.create_rectangle(
            bx1, by1, bx2, by2,
            outline="#ff4444", width=2,
            tags=self.layer_tag
        )
        self.canvas.create_text(
            (bx1 + bx2) // 2, (by1 + by2) // 2,
            text="EXIT",
            fill="#ff4444",
            font=("Consolas", 11, "bold"),
            tags=self.layer_tag
        )
        # сначала рёбра
        for a_id, b_id in self.edges:
            a = self.nodes[a_id]
            b = self.nodes[b_id]
            self.draw_edge(a, b)
        # потом узлы
        for node in self.nodes.values():
            self.draw_node(node)
    def draw_edge(self, a: GraphNode, b: GraphNode):
        ax, ay = self.node_coords(a)
        bx, by = self.node_coords(b)
        active = a.powered and b.powered
        color = "#55caff" if active else "#2a3b47"
        width = 4 if active else 2
        self.canvas.create_line(
            ax, ay, bx, by,
            fill=color,
            width=width,
            capstyle="round",
            tags=self.layer_tag
        )
    def draw_node(self, node: GraphNode):
        x, y = self.node_coords(node)
        if node.ntype == TYPE_NORMAL:
            self.draw_normal_node(node, x, y)
        elif node.ntype == TYPE_GATE:
            self.draw_gate(node, x, y)
        elif node.ntype == TYPE_START:
            self.draw_start(node, x, y)
        elif node.ntype == TYPE_EXIT:
            self.draw_exit(node, x, y)
    # --------- Обычный узел (круг с пунктиром и стрелкой) --------- #
    def draw_normal_node(self, node: GraphNode, x, y):
        outer_r = 20
        inner_r = 14
        # внешняя пунктирная окружность
        self.canvas.create_oval(
            x - outer_r, y - outer_r,
            x + outer_r, y + outer_r,
            outline="#233746",
            width=2,
            dash=(3, 3),
            tags=self.layer_tag
        )
        # внутренняя заливка
        self.canvas.create_oval(
            x - inner_r, y - inner_r,
            x + inner_r, y + inner_r,
            outline="#000000",
            fill="#000000",
            width=2,
            tags=self.layer_tag
        )
        # указатель направления
        color = "#6fd6ff" if node.powered else "#ffffff"
        self.draw_direction_marker(node.direction, x, y, color)
    def draw_direction_marker(self, direction, x, y, color):
        l = 11
        if direction == 0:  # up
            self.canvas.create_line(x, y, x, y - l, fill=color, width=3, tags=self.layer_tag)
        elif direction == 1:  # right
            self.canvas.create_line(x, y, x + l, y, fill=color, width=3, tags=self.layer_tag)
        elif direction == 2:  # down
            self.canvas.create_line(x, y, x, y + l, fill=color, width=3, tags=self.layer_tag)
        elif direction == 3:  # left
            self.canvas.create_line(x, y, x - l, y, fill=color, width=3, tags=self.layer_tag)
    # --------- GATE: ромб с замком --------- #
    def draw_gate(self, node: GraphNode, x, y):
        size = 24
        col = "#6fd6ff" if node.powered else "#ffffff"
        self.canvas.create_polygon(
            x, y - size,
            x + size, y,
            x, y + size,
            x - size, y,
            outline=col,
            fill="#000000",
            width=3,
            tags=self.layer_tag
        )
        self.canvas.create_text(
            x, y,
            text="🔒",
            fill=col,
            font=("Consolas", 18),
            tags=self.layer_tag
        )
    # --------- START: ромб с 4 маленькими ромбами --------- #
    def draw_start(self, node: GraphNode, x, y):
        size = 24
        col = "#ffffff"
        # большой ромб
        self.canvas.create_polygon(
            x, y - size,
            x + size, y,
            x, y + size,
            x - size, y,
            outline=col,
            fill="#000000",
            width=3,
            tags=self.layer_tag
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
                tags=self.layer_tag
            )
    # --------- EXIT: пульсирующий ромб --------- #
    def draw_exit(self, node: GraphNode, x, y):
        size = 24
        # пульсация по ticks
        phase = (self.ticks // 4) % 10
        pulse = 0.3 + 0.7 * abs(math.sin(self.ticks / 10.0))
        if node.powered:
            base_col = (0, int(255 * pulse), 100)  # зелёный
        else:
            base_col = (int(255 * pulse), int(255 * pulse), int(255 * pulse))
        outline = "#%02x%02x%02x" % base_col
        self.canvas.create_polygon(
            x, y - size,
            x + size, y,
            x, y + size,
            x - size, y,
            outline=outline,
            fill="#000000",
            width=3,
            tags=self.layer_tag
        )
        self.canvas.create_text(
            x, y,
            text="EXIT",
            fill=outline,
            font=("Consolas", 10, "bold"),
            tags=self.layer_tag
        )
    # ======================== ВЗАИМОДЕЙСТВИЕ ======================== #
    def find_node_by_point(self, x, y, radius=25):
        """Найти ближайший узел по клику мыши."""
        best_id = None
        best_d2 = radius * radius
        for nid, node in self.nodes.items():
            nx, ny = self.node_coords(node)
            dx = nx - x
            dy = ny - y
            d2 = dx * dx + dy * dy
            if d2 <= best_d2:
                best_d2 = d2
                best_id = nid
        return best_id
    def on_click(self, event):
        if not self.running:
            return
        # клик по кнопке EXIT
        if hasattr(self, "exit_btn_bbox") and self.exit_btn_bbox is not None:
            x1, y1, x2, y2 = self.exit_btn_bbox
            if x1 <= event.x <= x2 and y1 <= event.y <= y2:
                self.cleanup()
                self.on_exit()
                return
        nid = self.find_node_by_point(event.x, event.y)
        if not nid:
            return
        node = self.nodes[nid]
        # START / GATE / EXIT не вращаем — это только шаблон,
        # но можно разрешить, если захочешь.
        if node.ntype in (TYPE_START, TYPE_GATE, TYPE_EXIT):
            return
        node.direction = (node.direction + 1) % 4
        self.play_sound("click")
        self.recalculate_power()
        self.redraw()
    def handle_escape(self, event=None):
        self.cleanup()
        self.on_exit()
    # ======================== АНИМАЦИЯ ======================== #
    def animate(self):
        if not self.running:
            return
        self.ticks += 1
        # Для EXIT нужна пульсация => просто перерисовываем
        self.redraw()
        self.root.after(80, self.animate)
    # ======================== СЕРВИС ======================== #
    def play_sound(self, name):
        path = self.sounds.get(name)
        if not path or winsound is None or not os.path.exists(path):
            return
        try:
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass
    def cleanup(self):
        self.running = False
        self.canvas.unbind("<Button-1>")
        self.root.unbind("<Escape>")
        self.canvas.delete(self.layer_tag)
# ------------------------- ЛОКАЛЬНЫЙ ТЕСТ ------------------------- #
if __name__ == "__main__":
    root = tk.Tk()
    root.title("Zero-Day WD Template")
    root.geometry("1280x720")
    canvas = tk.Canvas(root, bg="black", width=1280, height=720)
    canvas.pack(fill="both", expand=True)
    def back():
        root.destroy()
    game = ZeroDownModule(canvas, root, back)
    root.mainloop()
