import tkinter as tk
import random
import os

# Для звуков (Windows). На других системах просто игнорируем.
try:
    import winsound
except ImportError:
    winsound = None


class ZeroDownNode:
    """
    Узел сетки.
    Порты: 0=UP, 1=RIGHT, 2=DOWN, 3=LEFT
    """
    def __init__(self, row, col, node_type,
                 rotation=0,
                 is_source=False,
                 is_target=False,
                 is_gate=False,
                 gate_required=2):
        self.row = row
        self.col = col
        self.node_type = node_type   # line, corner, tee, cross, block
        self.rotation = rotation

        self.is_source = is_source
        self.is_target = is_target
        self.is_gate = is_gate
        self.gate_required = gate_required
        self.gate_unlocked = False

        self.powered = False

    @property
    def base_ports(self):
        if self.is_source:
            # источник бьёт вверх
            return {0}
        if self.is_target:
            # финальный замок принимает со всех сторон
            return {0, 1, 2, 3}
        if self.is_gate:
            # ворота теоретически могут принимать с любых сторон
            return {0, 1, 2, 3}

        if self.node_type == "line":
            # базовая линия — вертикальная
            return {0, 2}
        if self.node_type == "corner":
            # угол: вверх-вправо
            return {0, 1}
        if self.node_type == "tee":
            # Т-образный без низа
            return {0, 1, 3}
        if self.node_type == "cross":
            return {0, 1, 2, 3}
        # block / прочее — глухой
        return set()

    @property
    def ports(self):
        return {(p + self.rotation) % 4 for p in self.base_ports}


class ZeroDownModule:
    """
    Zero-Day мини-игра в стиле сетевого взлома Watch Dogs.
    """

    def __init__(self, canvas: tk.Canvas, root: tk.Tk, on_exit):
        self.canvas = canvas
        self.root = root
        self.on_exit = on_exit

        self.size = 8  # 8×8 — большой лабиринт
        self.grid = []

        self.margin = 80
        self.cell_size = 70
        self.layer_tag = "zero_down_ui"

        self.total_time = 40
        self.time_left = self.total_time
        self.game_over = False
        self.success_shown = False
        self.timer_id = None

        self.sounds = {
            "click": os.path.join("sound", "click.mp3"),
            "lock_open": os.path.join("sound", "lock_open.mp3"),
            "fail": os.path.join("sound", "fail.mp3")
        }

        self.exit_btn_bbox = None

        self.canvas.bind("<Button-1>", self.on_click)
        self.root.bind("<Escape>", self.handle_escape)

        self.generate_level()
        self.recalculate_power()
        self.redraw()
        self.start_timer()

    # --------------------- ЗВУК --------------------- #
    def play_sound(self, name):
        path = self.sounds.get(name)
        if not path or not os.path.exists(path) or winsound is None:
            return
        try:
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            pass

    # ------------------ ГЕНЕРАЦИЯ УРОВНЯ ------------------ #
    def set_node(self, r, c, node_type, rotation=0,
                 is_source=False, is_target=False,
                 is_gate=False, gate_required=2):
        self.grid[r][c] = ZeroDownNode(
            r, c, node_type,
            rotation=rotation,
            is_source=is_source,
            is_target=is_target,
            is_gate=is_gate,
            gate_required=gate_required
        )

    def generate_level(self):
        """
        Фиксированный, но сложный лабиринт 8×8:

        S (внизу по центру) → длинный извилистый путь → Tee
        Tee даёт:
          ├─ Путь A (через левую часть) → в Gate слева
          └─ Путь B (через низ и правый лабиринт) → в Gate снизу
        Gate после двух питаний → путь вправо и вверх → Target.
        По пути есть тупики и декоративные узлы.
        """
        # сначала все клетки — глухие декоративные круги
        self.grid = [[ZeroDownNode(r, c, "block") for c in range(self.size)]
                     for r in range(self.size)]

        # координаты важных узлов
        src_r, src_c = 7, 3              # источник
        mid_r1, mid_c1 = 6, 3           # промежуточный вертикальный сегмент
        tee_r, tee_c = 5, 3             # центральный Tee/разветвитель

        gate_r, gate_c = 3, 5           # ворота
        target_r, target_c = 2, 7       # финальный замок (почти верхний правый угол)

        # ===== ОСНОВНОЙ ВЕРТИКАЛЬНЫЙ УЧАСТОК: source → mid → tee =====
        # источник — вертикальная линия вверх
        self.set_node(src_r, src_c, "line",
                      rotation=0,
                      is_source=True)

        # узел над источником — просто вертикальный отрезок
        self.set_node(mid_r1, mid_c1, "line", rotation=0)

        # Tee: соединён с mid снизу, левым путём A и правым путём B
        # нужны порты {LEFT, RIGHT, DOWN} = {3,1,2}
        # базовый tee {0,1,3} -> rotation=2 => {2,3,1} = {1,2,3}
        self.set_node(tee_r, tee_c, "tee", rotation=2)

        # ===== ПУТЬ A: от Tee через левую часть сетки к Gate слева =====
        # координаты пути A (без tee и gate):
        # Tee (5,3) -> (5,2) -> (4,2) -> (4,3) -> (3,3) -> (3,4) -> Gate(3,5)
        a1 = (5, 2)
        a2 = (4, 2)
        a3 = (4, 3)
        a4 = (3, 3)
        a5 = (3, 4)

        # A1: от Tee справа (1) к A2 вверх (0) => порты {RIGHT, UP} = {1,0} -> corner rot=0
        self.set_node(a1[0], a1[1], "corner", rotation=0)

        # A2: от A1 снизу (2), к A3 вправо (1), плюс ветка-тупик влево (3)
        # порты {1,2,3} -> tee rotation=2 (даёт {1,2,3})
        self.set_node(a2[0], a2[1], "tee", rotation=2)

        # A3: от A2 слева (3), к A4 вверх (0) -> {0,3} -> corner rotation=3
        self.set_node(a3[0], a3[1], "corner", rotation=3)

        # A4: от A3 снизу (2), к A5 вправо (1) -> {1,2} -> corner rotation=1
        self.set_node(a4[0], a4[1], "corner", rotation=1)

        # A5: горизонтальный сегмент к Gate справа -> {LEFT, RIGHT}={3,1}
        # line {0,2} rotation=1 => {1,3}
        self.set_node(a5[0], a5[1], "line", rotation=1)

        # Тупик к A2 слева: D2 (4,1)
        d2_r, d2_c = 4, 1
        # соединён только с A2 справа (1) -> можно line {LEFT,RIGHT} rotation=1
        self.set_node(d2_r, d2_c, "line", rotation=1)

        # ===== ПУТЬ B: от Tee через низ и правую часть к Gate снизу =====
        # Tee(5,3) -> B1(5,4) -> B2(5,5) -> B3(6,5) -> B4(6,6)
        #         -> B5(5,6) -> B6(4,6) -> B7(4,5) -> Gate(3,5)
        b1 = (5, 4)
        b2 = (5, 5)
        b3 = (6, 5)
        b4 = (6, 6)
        b5 = (5, 6)
        b6 = (4, 6)
        b7 = (4, 5)

        # B1: Tee слева (3), B2 справа (1) -> {1,3} line rotation=1
        self.set_node(b1[0], b1[1], "line", rotation=1)

        # B2: B1 слева (3), B3 снизу (2) -> {2,3} corner rotation=2
        self.set_node(b2[0], b2[1], "corner", rotation=2)

        # B3: B2 сверху (0), B4 справа (1) -> {0,1} corner rotation=0
        self.set_node(b3[0], b3[1], "corner", rotation=0)

        # B4: B3 слева (3), B5 сверху (0) и D1 (7,6) снизу (2) -> {0,2,3}
        # tee {0,1,3} rotation=3 => {3,0,2}
        self.set_node(b4[0], b4[1], "tee", rotation=3)

        # B5: B4 снизу (2), B6 сверху (0) -> {0,2} line rotation=0
        self.set_node(b5[0], b5[1], "line", rotation=0)

        # B6: B5 снизу (2), B7 слева (3) -> {2,3} corner rotation=2
        self.set_node(b6[0], b6[1], "corner", rotation=2)

        # B7: B6 справа (1), Gate сверху (0) -> {0,1} corner rotation=0
        self.set_node(b7[0], b7[1], "corner", rotation=0)

        # Тупик от B4 вниз: D1 (7,6)
        d1_r, d1_c = 7, 6
        # соединён только с B4 сверху (0) -> line вертикальная rotation=0
        self.set_node(d1_r, d1_c, "line", rotation=0)

        # ===== ВОРОТА (Gate) и путь к TARGET =====
        # Gate принимает минимум с двух сторон (слева и снизу)
        self.set_node(gate_r, gate_c, "cross",
                      rotation=0,
                      is_gate=True,
                      gate_required=2)

        # C1(3,6): от Gate слева (3), к C2(3,7) справа (1), плюс тупик вверх -> tee {0,1,3}
        c1 = (3, 6)
        self.set_node(c1[0], c1[1], "tee", rotation=0)

        # C2(3,7): от C1 слева (3), к Target сверху (0) -> {0,3} corner rotation=3
        c2 = (3, 7)
        self.set_node(c2[0], c2[1], "corner", rotation=3)

        # Target (2,7): финальный замок
        self.set_node(target_r, target_c, "cross",
                      rotation=0,
                      is_target=True)

        # Тупик от C1 вверх: D3(2,6)
        d3_r, d3_c = 2, 6
        # соединён только с C1 снизу (2) -> line вертикальная rotation=0
        self.set_node(d3_r, d3_c, "line", rotation=0)

        # ===== Дополнительные декоративные “ложные” сегменты (не связаны с путями) =====
        # Пара уголков и линий в левом верхнем углу
        decor = [
            (0, 1, "corner", random.randint(0, 3)),
            (1, 0, "line", random.randint(0, 3)),
            (1, 1, "tee", random.randint(0, 3)),
            (2, 0, "corner", random.randint(0, 3)),
        ]
        for r, c, t, rot in decor:
            # не перезаписываем важные клетки
            if isinstance(self.grid[r][c], ZeroDownNode) and self.grid[r][c].node_type == "block":
                self.set_node(r, c, t, rotation=rot)

    # --------------------- ЭНЕРГИЯ --------------------- #
    def neighbors_for(self, r, c):
        dirs = [(-1, 0), (0, 1), (1, 0), (0, -1)]
        for d, (dr, dc) in enumerate(dirs):
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.size and 0 <= nc < self.size:
                yield nr, nc, d, (d + 2) % 4

    def recalculate_power(self):
        for row in self.grid:
            for n in row:
                n.powered = False
                if n.is_gate:
                    n.gate_unlocked = False

        # источник
        source = None
        for row in self.grid:
            for n in row:
                if n.is_source:
                    source = n
        if not source:
            return

        # несколько итераций: сначала распространяем питание,
        # затем открываем ворота (если два входа), затем ещё раз.
        for _ in range(3):
            self._bfs_power(source)

            updated = False
            for row in self.grid:
                for n in row:
                    if n.is_gate:
                        cnt = self._count_gate_inputs(n)
                        if cnt >= n.gate_required and not n.gate_unlocked:
                            n.gate_unlocked = True
                            updated = True
            if not updated:
                break

    def _bfs_power(self, start: ZeroDownNode):
        for row in self.grid:
            for n in row:
                if not n.is_source:
                    n.powered = False

        queue = [start]
        start.powered = True

        while queue:
            node = queue.pop(0)
            r, c = node.row, node.col

            # закрытые ворота не пропускают питание дальше
            if node.is_gate and not node.gate_unlocked and not node.is_source:
                continue

            for nr, nc, d_here, d_neigh in self.neighbors_for(r, c):
                neigh = self.grid[nr][nc]
                if d_here in node.ports and d_neigh in neigh.ports:
                    if not neigh.powered:
                        neigh.powered = True
                        queue.append(neigh)

    def _count_gate_inputs(self, gate: ZeroDownNode):
        r, c = gate.row, gate.col
        count = 0
        for nr, nc, d_here, d_neigh in self.neighbors_for(r, c):
            neigh = self.grid[nr][nc]
            if neigh.powered and d_neigh in neigh.ports and d_here in gate.ports:
                count += 1
        return count

    def is_target_powered(self):
        for row in self.grid:
            for n in row:
                if n.is_target and n.powered:
                    return True
        return False

    # --------------------- ОТРИСОВКА --------------------- #
    def redraw(self):
        self.canvas.delete(self.layer_tag)

        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 1 or h <= 1:
            w = self.root.winfo_screenwidth()
            h = self.root.winfo_screenheight()

        panel_w = self.size * self.cell_size + self.margin * 2
        panel_h = self.size * self.cell_size + self.margin * 2
        x0 = (w - panel_w) // 2
        y0 = (h - panel_h) // 2

        grid_x0 = x0 + self.margin
        grid_y0 = y0 + self.margin

        # TIMER
        timer_color = "#7ee8ff" if self.time_left > 12 else "#ff6666"
        self.canvas.create_text(
            x0, y0 - 25, anchor="w",
            text=f"{self.time_left}s",
            fill=timer_color, font=("Consolas", 16, "bold"),
            tags=self.layer_tag
        )

        # EXIT
        bx1 = x0 + panel_w
        by1 = y0 - 30
        bx0 = bx1 - 80
        by0 = by1 - 26
        self.exit_btn_bbox = (bx0, by0, bx1, by1)

        self.canvas.create_rectangle(
            bx0, by0, bx1, by1,
            outline="#ff4444", width=2,
            tags=self.layer_tag
        )
        self.canvas.create_text(
            (bx0 + bx1) / 2, (by0 + by1) / 2,
            text="EXIT",
            fill="#ff4444",
            font=("Consolas", 12, "bold"),
            tags=self.layer_tag
        )

        base_color = "#31424f"
        active_color = "#4fd6ff"

        for r in range(self.size):
            for c in range(self.size):
                n = self.grid[r][c]
                cx = grid_x0 + c * self.cell_size + self.cell_size // 2
                cy = grid_y0 + r * self.cell_size + self.cell_size // 2

                col = active_color if n.powered else base_color

                # линии-сегменты от центра к портам
                port_len = self.cell_size / 2 - 10
                for p in n.ports:
                    if p == 0:
                        x2, y2 = cx, cy - port_len
                    elif p == 1:
                        x2, y2 = cx + port_len, cy
                    elif p == 2:
                        x2, y2 = cx, cy + port_len
                    else:
                        x2, y2 = cx - port_len, cy

                    self.canvas.create_line(
                        cx, cy, x2, y2,
                        fill=col,
                        width=4 if n.powered else 2,
                        capstyle=tk.ROUND,
                        tags=self.layer_tag
                    )

                # SOURCE (ромб)
                if n.is_source:
                    d = 18
                    self.canvas.create_polygon(
                        cx, cy - d,
                        cx + d, cy,
                        cx, cy + d,
                        cx - d, cy,
                        outline=active_color,
                        width=3,
                        fill="",
                        tags=self.layer_tag
                    )
                    continue

                # TARGET (замок)
                if n.is_target:
                    d = 22
                    c2 = active_color if n.powered else "#ffffff"
                    self.canvas.create_polygon(
                        cx, cy - d,
                        cx + d, cy,
                        cx, cy + d,
                        cx - d, cy,
                        outline=c2,
                        width=3,
                        fill="",
                        tags=self.layer_tag
                    )
                    body_w, body_h = 14, 10
                    self.canvas.create_rectangle(
                        cx - body_w / 2, cy + 3,
                        cx + body_w / 2, cy + 3 + body_h,
                        outline=c2, width=2,
                        tags=self.layer_tag
                    )
                    arc_r = body_w / 2
                    self.canvas.create_arc(
                        cx - arc_r, cy - arc_r,
                        cx + arc_r, cy + arc_r,
                        start=200, extent=140,
                        style="arc",
                        outline=c2,
                        width=2,
                        tags=self.layer_tag
                    )
                    continue

                # GATE (ворота)
                if n.is_gate:
                    ring = 22
                    c2 = active_color if n.gate_unlocked else "#ffffff"
                    self.canvas.create_oval(
                        cx - ring, cy - ring,
                        cx + ring, cy + ring,
                        outline=c2,
                        width=3,
                        tags=self.layer_tag
                    )
                    # сегменты по кругу
                    for start in (10, 100, 190, 280):
                        self.canvas.create_arc(
                            cx - ring, cy - ring,
                            cx + ring, cy + ring,
                            start=start, extent=40,
                            style="arc",
                            outline=c2,
                            width=3,
                            tags=self.layer_tag
                        )
                    continue

                # обычный круглый узел (в т.ч. декоративные block)
                rad = 14
                self.canvas.create_oval(
                    cx - rad, cy - rad,
                    cx + rad, cy + rad,
                    outline=col,
                    width=2,
                    tags=self.layer_tag
                )
                tick = "#ffffff" if n.powered else "#8fa1ac"
                t = 8
                # up
                self.canvas.create_line(
                    cx, cy - rad - 4,
                    cx, cy - rad - 4 - t,
                    fill=tick, width=2,
                    tags=self.layer_tag
                )
                # down
                self.canvas.create_line(
                    cx, cy + rad + 4,
                    cx, cy + rad + 4 + t,
                    fill=tick, width=2,
                    tags=self.layer_tag
                )
                # right
                self.canvas.create_line(
                    cx + rad + 4, cy,
                    cx + rad + 4 + t, cy,
                    fill=tick, width=2,
                    tags=self.layer_tag
                )
                # left
                self.canvas.create_line(
                    cx - rad - 4, cy,
                    cx - rad - 4 - t, cy,
                    fill=tick, width=2,
                    tags=self.layer_tag
                )

    # --------------------- ВЗАИМОДЕЙСТВИЕ --------------------- #
    def canvas_to_cell(self, x, y):
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 1 or h <= 1:
            w = self.root.winfo_screenwidth()
            h = self.root.winfo_screenheight()

        panel_w = self.size * self.cell_size + self.margin * 2
        panel_h = self.size * self.cell_size + self.margin * 2
        x0 = (w - panel_w) // 2
        y0 = (h - panel_h) // 2

        gx = x - (x0 + self.margin)
        gy = y - (y0 + self.margin)
        if gx < 0 or gy < 0:
            return None

        c = int(gx // self.cell_size)
        r = int(gy // self.cell_size)

        if 0 <= r < self.size and 0 <= c < self.size:
            return r, c
        return None

    def on_click(self, event):
        if self.game_over:
            return

        # клик по EXIT
        if self.exit_btn_bbox:
            x0, y0, x1, y1 = self.exit_btn_bbox
            if x0 <= event.x <= x1 and y0 <= event.y <= y1:
                self.cleanup()
                self.on_exit()
                return

        cell = self.canvas_to_cell(event.x, event.y)
        if not cell:
            return

        r, c = cell
        node = self.grid[r][c]

        if node.is_source or node.is_target or node.is_gate:
            return

        node.rotation = (node.rotation + 1) % 4
        self.play_sound("click")

        self.recalculate_power()
        self.redraw()

        if self.is_target_powered():
            self.handle_success()

    # --------------------- ESC / ВЫХОД --------------------- #
    def handle_escape(self, event=None):
        self.cleanup()
        self.on_exit()

    # --------------------- ТАЙМЕР --------------------- #
    def start_timer(self):
        self.update_timer()

    def update_timer(self):
        if self.game_over:
            return
        self.time_left -= 1
        if self.time_left < 0:
            self.handle_fail()
            return
        self.redraw()
        self.timer_id = self.root.after(1000, self.update_timer)

    # --------------------- КОНЕЦ ИГРЫ --------------------- #
    def handle_success(self):
        if self.game_over:
            return
        self.game_over = True
        self.play_sound("lock_open")
        if self.timer_id:
            try:
                self.root.after_cancel(self.timer_id)
            except Exception:
                pass
        self.show_success_popup()

    def handle_fail(self):
        if self.game_over:
            return
        self.game_over = True
        self.play_sound("fail")
        self.show_fail_popup()

    # --------------------- ПОПАПЫ --------------------- #
    def show_success_popup(self):
        self.canvas.delete(self.layer_tag)
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        bw, bh = 600, 260
        x0 = (w - bw) // 2
        y0 = (h - bh) // 2
        x1 = x0 + bw
        y1 = y0 + bh

        self.canvas.create_rectangle(
            x0, y0, x1, y1,
            fill="#020910",
            outline="#82e4ff",
            width=3,
            tags=self.layer_tag
        )

        self.canvas.create_text(
            (x0 + x1) / 2, y0 + 35,
            text="ZERO-DAY VULNERABILITY FOUND",
            fill="#82e4ff",
            font=("Consolas", 18, "bold"),
            tags=self.layer_tag
        )

        explanation = (
            "Ты активировал обе ветки питания и открыл ворота.\n\n"
            "Zero-Day — это уязвимость, о которой ещё не знают разработчики,\n"
            "поэтому она не закрыта патчами и не отслеживается защитой.\n"
            "Через такие дыры можно обойти аутентификацию, повысить привилегии\n"
            "или выполнить код на удалённой системе."
        )

        self.canvas.create_text(
            (x0 + x1) / 2, (y0 + y1) / 2,
            text=explanation,
            fill="#d0f6ff",
            font=("Consolas", 11),
            justify="center",
            tags=self.layer_tag
        )

        self.canvas.create_text(
            (x0 + x1) / 2, y1 - 35,
            text="Нажми ESC для возврата в меню CtOS.",
            fill="#82e4ff",
            font=("Consolas", 11),
            tags=self.layer_tag
        )

    def show_fail_popup(self):
        self.canvas.delete(self.layer_tag)
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()

        bw, bh = 450, 180
        x0 = (w - bw) // 2
        y0 = (h - bh) // 2
        x1 = x0 + bw
        y1 = y0 + bh

        self.canvas.create_rectangle(
            x0, y0, x1, y1,
            fill="#120207",
            outline="#ff4444",
            width=3,
            tags=self.layer_tag
        )

        self.canvas.create_text(
            (x0 + x1) / 2, y0 + 35,
            text="FIREWALL LOCKED",
            fill="#ff5555",
            font=("Consolas", 18, "bold"),
            tags=self.layer_tag
        )

        self.canvas.create_text(
            (x0 + x1) / 2, (y0 + y1) / 2,
            text="Окно эксплуатации закрылось.\nПопробуй снова запустить Zero-Day.",
            fill="#ffcccc",
            font=("Consolas", 11),
            justify="center",
            tags=self.layer_tag
        )

        self.canvas.create_text(
            (x0 + x1) / 2, y1 - 35,
            text="Нажми ESC для выхода в меню CtOS.",
            fill="#ff8888",
            font=("Consolas", 11),
            tags=self.layer_tag
        )

    # --------------------- ОЧИСТКА --------------------- #
    def cleanup(self):
        if self.timer_id:
            try:
                self.root.after_cancel(self.timer_id)
            except Exception:
                pass
            self.timer_id = None

        self.canvas.unbind("<Button-1>")
        self.root.unbind("<Escape>")
        self.canvas.delete(self.layer_tag)
