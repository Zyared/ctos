import tkinter as tk
import random
import os

# Для звука на Windows. На других системах просто игнорируется.
try:
    import winsound
except ImportError:
    winsound = None


class ZeroDownNode:
    """
    Узел сетки.
    Порты: 0 = UP, 1 = RIGHT, 2 = DOWN, 3 = LEFT
    """
    def __init__(self, row, col, node_type,
                 rotation=0,
                 is_source=False,
                 is_target=False,
                 is_gate=False,
                 gate_required=2):
        self.row = row
        self.col = col
        self.node_type = node_type  # "line", "corner", "tee", "cross", "empty"
        self.rotation = rotation    # 0..3

        self.is_source = is_source
        self.is_target = is_target
        self.is_gate = is_gate
        self.gate_required = gate_required
        self.gate_unlocked = False

        self.powered = False

    @property
    def base_ports(self):
        """
        Порты при rotation = 0.
        """
        if self.node_type == "empty":
            return set()

        if self.is_source:
            # Источник — бьёт вверх.
            return {0}
        if self.is_target:
            # целевой замок принимает питание с ЛЮБОЙ стороны
            return {0, 1, 2, 3}

        if self.is_gate:
            # Ворота могут принимать питание с любых сторон.
            return {0, 1, 2, 3}

        if self.node_type == "line":
            # Базовая линия — вертикальная (UP-DOWN).
            return {0, 2}
        if self.node_type == "corner":
            # Базовый угол — UP-RIGHT.
            return {0, 1}
        if self.node_type == "tee":
            # Базовый T — UP-RIGHT-LEFT (без низа).
            return {0, 1, 3}
        if self.node_type == "cross":
            return {0, 1, 2, 3}

        return set()

    @property
    def ports(self):
        """
        Порты с учётом поворота.
        """
        return {(p + self.rotation) % 4 for p in self.base_ports}


class ZeroDownModule:
    """
    Мини-игра Zero-Day в стиле взлома сети из Watch Dogs.
    """

    def __init__(self, canvas: tk.Canvas, root: tk.Tk, on_exit):
        self.canvas = canvas
        self.root = root
        self.on_exit = on_exit

        # Размер сетки
        self.size = 8
        self.grid = []

        # Геометрия отрисовки
        self.margin = 80
        self.cell_size = 70
        self.layer_tag = "zero_down_layer"

        # Таймер
        self.total_time = 40
        self.time_left = self.total_time
        self.timer_id = None
        self.game_over = False

        # Флаг, чтобы различать успех/фейл
        self.success_shown = False

        # Звуки
        self.sounds = {
            "click": os.path.join("sound", "click.mp3"),
            "lock_open": os.path.join("sound", "lock_open.mp3"),
            "fail": os.path.join("sound", "fail.mp3"),
        }

        # Кнопка EXIT
        self.exit_btn_bbox = None

        # События
        self.canvas.bind("<Button-1>", self.on_click)
        self.root.bind("<Escape>", self.handle_escape)

        # Генерация уровня
        self.generate_level()
        # Перемешиваем повороты, чтобы уровень не был решён сразу
        self.randomize_rotations()
        # Пересчитываем питание (после перемешивания всё будет обесточено)
        self.recalculate_power()
        self.redraw()
        self.start_timer()

    # ---------------------- ЗВУК ---------------------- #
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
        """
        Удобный сеттер, чтобы не писать одно и то же.
        """
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
        Фиксированный, но красивый и извилистый лабиринт 8x8.

        Структура:
        - Источник (S) внизу.
        - Вертикальный подъём к центральному Tee.
        - От Tee уходят две ветки (A и B) к воротам Gate с разных сторон.
        - Gate после 2-х входов даёт питание на путь к Target.
        - В нескольких местах есть тупики.
        - Всё остальное — пустота (никаких лишних кружков).
        """
        # Сначала — пустая сетка: все клетки "empty"
        self.grid = [[ZeroDownNode(r, c, "empty") for c in range(self.size)]
                     for r in range(self.size)]

        # === Ключевые узлы ===
        src_r, src_c = 7, 3           # источник внизу по центру
        mid_r1, mid_c1 = 6, 3         # переход вверх
        tee_r, tee_c = 5, 3           # центральный Tee (разветвитель)

        gate_r, gate_c = 3, 5         # ворота
        target_r, target_c = 2, 7     # финальный замок (справа сверху)

        # --- Вертикаль: Source -> Mid -> Tee ---
        # Источник: вертикальная линия вверх (питание вверх)
        self.set_node(
            src_r, src_c,
            "line",
            rotation=0,
            is_source=True
        )

        # Средний сегмент над источником — тоже вертикаль
        self.set_node(mid_r1, mid_c1, "line", rotation=0)

        # Tee: принимаем поток снизу и даём влево+вправо (ветки A и B)
        # Нужно UP-LEFT-RIGHT? Нет, мы хотим: снизу входит (2),
        # а выходы идут влево (3) и вправо (1).
        # Базовый tee: {0,1,3}, rotation=2 -> {2,3,1} = {DOWN,LEFT,RIGHT}
        self.set_node(tee_r, tee_c, "tee", rotation=2)

        # === ВЕТКА A: Tee -> слева к Gate ===
        # Путь A: Tee(5,3) → A1(5,2) → A2(4,2) → A3(4,3) → A4(3,3) → A5(3,4) → Gate(3,5)

        a1 = (5, 2)
        a2 = (4, 2)
        a3 = (4, 3)
        a4 = (3, 3)
        a5 = (3, 4)

        # A1: Tee справа (1) -> A2 вверх (0). Нужен угол RIGHT-UP.
        # Базовый угол {0,1} (UP-RIGHT). Нам нужен {RIGHT,UP} = то же самое.
        self.set_node(a1[0], a1[1], "corner", rotation=0)

        # A2: A1 снизу (2), A3 вправо (1), + тупик влево (3).
        # Порты {1,2,3} -> tee rotation=2 (даёт {1,2,3}).
        self.set_node(a2[0], a2[1], "tee", rotation=2)

        # A3: A2 слева (3), A4 вверх (0) -> угол LEFT-UP.
        # Базовый {0,1} -> rotation=3 => {3,0}.
        self.set_node(a3[0], a3[1], "corner", rotation=3)

        # A4: A3 снизу (2), A5 вправо (1) -> угол DOWN-RIGHT.
        # Базовый {0,1} -> rotation=1 => {1,2}.
        self.set_node(a4[0], a4[1], "corner", rotation=1)

        # A5: A4 слева (3), Gate справа (1) -> линия LEFT-RIGHT.
        # line {0,2}, rotation=1 => {1,3}.
        self.set_node(a5[0], a5[1], "line", rotation=1)

        # Тупик возле A2 слева: D2(4,1): соединён только с A2 справа.
        d2_r, d2_c = 4, 1
        self.set_node(d2_r, d2_c, "line", rotation=1)

        # === ВЕТКА B: Tee -> через низ и правый лабиринт к Gate ===
        # B-путь: Tee(5,3) → B1(5,4) → B2(5,5) → B3(6,5) → B4(6,6)
        #        → B5(5,6) → B6(4,6) → B7(4,5) → Gate(3,5)

        b1 = (5, 4)
        b2 = (5, 5)
        b3 = (6, 5)
        b4 = (6, 6)
        b5 = (5, 6)
        b6 = (4, 6)
        b7 = (4, 5)

        # B1: Tee слева (3) -> B2 справа (1) -> линия LEFT-RIGHT.
        self.set_node(b1[0], b1[1], "line", rotation=1)

        # B2: B1 слева (3) -> B3 вниз (2) -> угол LEFT-DOWN.
        # Базовый {0,1} -> rotation=2 => {2,3}.
        self.set_node(b2[0], b2[1], "corner", rotation=2)

        # B3: B2 сверху (0) -> B4 справа (1) -> угол UP-RIGHT.
        self.set_node(b3[0], b3[1], "corner", rotation=0)

        # B4: B3 слева (3), B5 вверх (0) + тупик вниз (2).
        # Нужны {0,2,3}. tee {0,1,3} -> rotation=3 => {3,0,2}.
        self.set_node(b4[0], b4[1], "tee", rotation=3)

        # B5: B4 снизу (2) -> B6 вверх (0) -> вертикальная линия.
        self.set_node(b5[0], b5[1], "line", rotation=0)

        # B6: B5 снизу (2) -> B7 слева (3) -> угол DOWN-LEFT.
        # базовый {0,1} -> rotation=2 => {2,3}
        self.set_node(b6[0], b6[1], "corner", rotation=2)

        # B7: B6 справа (1) -> Gate сверху (0) -> угол RIGHT-UP.
        # базовый {0,1} уже {UP,RIGHT}, но нам {RIGHT,UP} — rotation=0 подходит.
        self.set_node(b7[0], b7[1], "corner", rotation=0)

        # Тупик D1(7,6) от B4 вниз
        d1_r, d1_c = 7, 6
        self.set_node(d1_r, d1_c, "line", rotation=0)

        # === ВОРОТА (Gate) и путь к Target ===
        # Gate принимают минимум 2 входа (слева и снизу)
        self.set_node(
            gate_r, gate_c,
            "cross",
            rotation=0,
            is_gate=True,
            gate_required=2
        )

        # От Gate вправо и вверх к Target:
        # Gate(3,5) → C1(3,6) → C2(3,7) → Target(2,7)

        c1 = (3, 6)
        c2 = (3, 7)

        # C1: Gate слева (3), C2 справа (1), тупик вверх (0)
        # Нужны {0,1,3} -> tee rotation=0.
        self.set_node(c1[0], c1[1], "tee", rotation=0)

        # C2: C1 слева (3), Target сверху (0) -> угол LEFT-UP.
        # базовый угол {0,1} -> rotation=3 => {3,0}.
        self.set_node(c2[0], c2[1], "corner", rotation=3)

        # Target — финальный замок
        self.set_node(
            target_r, target_c,
            "cross",
            rotation=0,
            is_target=True
        )

        # Тупик D3(2,6) сверху от C1
        d3_r, d3_c = 2, 6
        self.set_node(d3_r, d3_c, "line", rotation=0)

        # Больше НИКАКИХ декоративных узлов — остальные клетки остаются "empty".

    def randomize_rotations(self):
        """
        Случайно поворачиваем все узлы, кроме источника и финальной цели.
        Благодаря этому уровень никогда не стартует в решённом состоянии.
        Решение уникально, но фигуры изначально стоят случайно.
        """
        for row in self.grid:
            for n in row:
                if n.node_type == "empty":
                    continue
                if n.is_source or n.is_target:
                    continue
                # все остальные можно крутить
                n.rotation = random.randint(0, 3)

    # ---------------------- ЭНЕРГИЯ ---------------------- #
    def neighbors_for(self, r, c):
        """
        Соседи: (nr, nc, dir_from_here, dir_in_neighbor)
        """
        dirs = [(-1, 0), (0, 1), (1, 0), (0, -1)]
        for d, (dr, dc) in enumerate(dirs):
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.size and 0 <= nc < self.size:
                yield nr, nc, d, (d + 2) % 4

    def recalculate_power(self):
        """
        Пересчёт питания:
        1) Сбрасываем всё.
        2) Первый проход BFS: питание доходит до всех узлов, КРОМЕ цели (target),
           но может доходить до ворот (gate).
        3) Считаем, сколько направлений входит в gate. Если >= gate_required,
           считаем ворота открытыми.
        4) Второй проход BFS — теперь питание может идти через открытые ворота
           и доходить до target.
        """
        # Сброс
        source = None
        for row in self.grid:
            for n in row:
                n.powered = False
                if n.is_gate:
                    n.gate_unlocked = False
                if n.is_source:
                    source = n

        if not source:
            return

        # Первый проход: target ещё нельзя питать
        self._bfs_power(source, allow_target=False)

        # Подсчёт входов в gate
        for row in self.grid:
            for n in row:
                if n.is_gate:
                    cnt = self._count_gate_inputs(n)
                    if cnt >= n.gate_required:
                        n.gate_unlocked = True

        # Второй проход: всё заново, но теперь открытые ворота проводят питание,
        # и можно запитать target.
        for row in self.grid:
            for n in row:
                if not n.is_source:
                    n.powered = False
        self._bfs_power(source, allow_target=True)

    def _bfs_power(self, start: ZeroDownNode, allow_target: bool):
        """
        BFS: распространяем питание по соединённым портам.
        Если allow_target = False, цель не будет запитываться.
        Закрытые ворота не пропускают питание дальше.
        """
        queue = [start]
        start.powered = True

        while queue:
            node = queue.pop(0)
            r, c = node.row, node.col

            # Закрытые ворота не проводят дальше (но сами могут быть запитаны)
            if node.is_gate and not node.gate_unlocked and not node.is_source:
                continue

            for nr, nc, d_here, d_neigh in self.neighbors_for(r, c):
                neigh = self.grid[nr][nc]

                if neigh.node_type == "empty":
                    continue

                # Пока не разрешено — не запитываем target
                if neigh.is_target and not allow_target:
                    continue

                if d_here in node.ports and d_neigh in neigh.ports:
                    if not neigh.powered:
                        neigh.powered = True
                        queue.append(neigh)

    def _count_gate_inputs(self, gate: ZeroDownNode) -> int:
        """
        Считаем, с каких сторон уже приходит реальное питание в ворота.
        """
        r, c = gate.row, gate.col
        count = 0
        for nr, nc, d_here, d_neigh in self.neighbors_for(r, c):
            neigh = self.grid[nr][nc]
            if neigh.powered and d_neigh in neigh.ports and d_here in gate.ports:
                count += 1
        return count

    def is_target_powered(self) -> bool:
        for row in self.grid:
            for n in row:
                if n.is_target and n.powered:
                    return True
        return False

    # ---------------------- ОТРИСОВКА ---------------------- #
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

        # Таймер
        timer_color = "#7ee8ff" if self.time_left > 12 else "#ff6666"
        self.canvas.create_text(
            x0, y0 - 25,
            anchor="w",
            text=f"{self.time_left}s",
            fill=timer_color,
            font=("Consolas", 16, "bold"),
            tags=self.layer_tag
        )

        # Кнопка EXIT
        bx1 = x0 + panel_w
        by1 = y0 - 30
        bx0 = bx1 - 80
        by0 = by1 - 26
        self.exit_btn_bbox = (bx0, by0, bx1, by1)

        self.canvas.create_rectangle(
            bx0, by0, bx1, by1,
            outline="#ff4444",
            width=2,
            tags=self.layer_tag
        )
        self.canvas.create_text(
            (bx0 + bx1) / 2,
            (by0 + by1) / 2,
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
                if n.node_type == "empty":
                    # пустая клетка — ничего не рисуем
                    continue

                cx = grid_x0 + c * self.cell_size + self.cell_size // 2
                cy = grid_y0 + r * self.cell_size + self.cell_size // 2
                col = active_color if n.powered else base_color

                # Линии от центра к портам
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

                # Источник — ромб
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

                # Target — ромб с замком
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
                        outline=c2,
                        width=2,
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

                # Ворота — кольцо с сегментами
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

                # Обычный узел-кружок (включая тупики)
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
                # вверх
                self.canvas.create_line(
                    cx, cy - rad - 4,
                    cx, cy - rad - 4 - t,
                    fill=tick, width=2,
                    tags=self.layer_tag
                )
                # вниз
                self.canvas.create_line(
                    cx, cy + rad + 4,
                    cx, cy + rad + 4 + t,
                    fill=tick, width=2,
                    tags=self.layer_tag
                )
                # вправо
                self.canvas.create_line(
                    cx + rad + 4, cy,
                    cx + rad + 4 + t, cy,
                    fill=tick, width=2,
                    tags=self.layer_tag
                )
                # влево
                self.canvas.create_line(
                    cx - rad - 4, cy,
                    cx - rad - 4 - t, cy,
                    fill=tick, width=2,
                    tags=self.layer_tag
                )

    # ---------------------- ВЗАИМОДЕЙСТВИЕ ---------------------- #
    def canvas_to_cell(self, x, y):
        """
        Перевод координат клика в (row, col) узла.
        """
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

        # Проверка на клик по EXIT
        if self.exit_btn_bbox is not None:
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

        if node.node_type == "empty":
            return
        # Нельзя крутить источник и финальную цель (их положение фиксировано)
        if node.is_source or node.is_target:
            return

        node.rotation = (node.rotation + 1) % 4
        self.play_sound("click")

        self.recalculate_power()
        self.redraw()

        if self.is_target_powered():
            self.handle_success()

    def handle_escape(self, event=None):
        """
        Esc — выход в меню CtOS.
        """
        self.cleanup()
        self.on_exit()

    # ---------------------- ТАЙМЕР ---------------------- #
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

    # ---------------------- КОНЕЦ ИГРЫ ---------------------- #
    def handle_success(self):
        if self.game_over:
            return
        self.game_over = True
        self.success_shown = True
        self.play_sound("lock_open")
        if self.timer_id is not None:
            try:
                self.root.after_cancel(self.timer_id)
            except Exception:
                pass
        self.show_success_popup()

    def handle_fail(self):
        if self.game_over:
            return
        self.game_over = True
        self.success_shown = False
        self.play_sound("fail")
        if self.timer_id is not None:
            try:
                self.root.after_cancel(self.timer_id)
            except Exception:
                pass
        self.show_fail_popup()

    # ---------------------- ПОПАПЫ ---------------------- #
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
            "Ты запитал обе ветки и открыл ворота, а затем довёл сигнал до выхода.\n\n"
            "Zero-Day — это уязвимость, о которой производитель ПО ещё не знает.\n"
            "Пока нет патча и сигнатур, такие дыры позволяют обходить аутентификацию,\n"
            "повышать привилегии и выполнять код на удалённых системах незаметно\n"
            "для стандартных средств защиты."
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
            text="Нажми ESC, чтобы вернуться в центральное меню CtOS.",
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
            text="Временное окно для эксплуатации уязвимости закрылось.\n"
                 "Перезапусти Zero-Day и попробуй ещё раз.",
            fill="#ffcccc",
            font=("Consolas", 11),
            justify="center",
            tags=self.layer_tag
        )

        self.canvas.create_text(
            (x0 + x1) / 2, y1 - 35,
            text="Нажми ESC, чтобы выйти в меню CtOS.",
            fill="#ff8888",
            font=("Consolas", 11),
            tags=self.layer_tag
        )

    # ---------------------- ОЧИСТКА ---------------------- #
    def cleanup(self):
        if self.timer_id is not None:
            try:
                self.root.after_cancel(self.timer_id)
            except Exception:
                pass
            self.timer_id = None

        self.canvas.unbind("<Button-1>")
        self.root.unbind("<Escape>")
        self.canvas.delete(self.layer_tag)
