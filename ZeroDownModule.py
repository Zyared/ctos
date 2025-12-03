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
    Узел в сетке Zero-Day мини-игры.
    Стороны кодируются: 0=UP, 1=RIGHT, 2=DOWN, 3=LEFT
    """
    def __init__(self, row, col, node_type, rotation=0, is_source=False, is_target=False):
        self.row = row
        self.col = col
        self.node_type = node_type
        self.rotation = rotation  # 0..3
        self.is_source = is_source
        self.is_target = is_target
        self.powered = False

    @property
    def base_ports(self):
        """Базовые порты для rotation=0."""
        if self.is_source:
            # Источник бьёт вверх
            return {0}
        if self.is_target:
            # Цель принимает с любой стороны
            return {0, 1, 2, 3}

        if self.node_type == "line":
            return {0, 2}          # вертикаль
        elif self.node_type == "corner":
            return {0, 1}          # угол вверх-вправо
        elif self.node_type == "tee":
            return {0, 1, 3}       # Т без низа
        elif self.node_type == "cross":
            return {0, 1, 2, 3}
        elif self.node_type == "block":
            return set()
        else:
            return set()

    @property
    def ports(self):
        """Порты с учётом поворота."""
        res = set()
        for p in self.base_ports:
            res.add((p + self.rotation) % 4)
        return res


class ZeroDownModule:
    """
    Интерактивная мини-игра Zero-Day в стиле взлома сети из Watch Dogs.
    Использование:
        module = ZeroDownModule(canvas, root, on_exit_callback)
    """

    def __init__(self, canvas: tk.Canvas, root: tk.Tk, on_exit):
        self.canvas = canvas
        self.root = root
        self.on_exit = on_exit

        # Параметры сетки
        self.size = random.randint(3, 6)  # динамическая сложность
        self.grid = []                   # 2D list[ZeroDownNode]

        # Размеры отрисовки
        self.margin = 80
        self.cell_size = 70
        self.layer_tag = "zero_down_layer"

        # Таймер
        # Чем больше сетка, тем сложнее -> меньше времени
        self.total_time = max(12, 40 - self.size * 4)
        self.time_left = self.total_time
        self.timer_id = None
        self.game_over = False
        self.success_shown = False

        # Звуки
        self.sounds = {
            "click": os.path.join("sound", "click.mp3"),
            "pulse": os.path.join("sound", "pulse.mp3"),
            "lock_open": os.path.join("sound", "lock_open.mp3"),
            "fail": os.path.join("sound", "fail.mp3"),
        }

        # Координаты кнопки EXIT внутри модуля
        self.exit_btn_bbox = None

        # Привязка событий
        self.canvas.bind("<Button-1>", self.on_click)
        self.root.bind("<Escape>", self.handle_escape)

        # Сгенерировать уровень и запустить
        self.generate_level()
        self.recalculate_power()
        self.redraw()
        self.start_timer()

    # -------------------- ЗВУК -------------------- #

    def play_sound(self, name):
        path = self.sounds.get(name)
        if not path or not os.path.exists(path) or winsound is None:
            return
        try:
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        except Exception:
            # Игнорируем ошибки воспроизведения
            pass

    # -------------------- ЛОГИКА УРОВНЯ -------------------- #

    def generate_level(self):
        """
        Генерация сетки с гарантированным путём от источника к целевому замку.
        """
        self.grid = []

        # Позиции источника и цели
        source_row = self.size - 1
        source_col = self.size // 2
        target_row = 0
        target_col = random.randint(0, self.size - 1)

        # Пустая сетка (пока блоки)
        for r in range(self.size):
            row = []
            for c in range(self.size):
                row.append(ZeroDownNode(r, c, "block"))
            self.grid.append(row)

        # Построение пути от источника до цели
        path = [(source_row, source_col)]
        cur_r, cur_c = source_row, source_col

        while (cur_r, cur_c) != (target_row, target_col):
            options = []
            if cur_r > target_row:
                options.append((-1, 0))  # вверх
            if cur_c < target_col:
                options.append((0, 1))   # вправо
            if cur_c > target_col:
                options.append((0, -1))  # влево

            # Добавим немного рандома, чтобы путь не был слишком прямым
            if random.random() < 0.3:
                if cur_r > 0:
                    options.append((-1, 0))
                if cur_c > 0:
                    options.append((0, -1))
                if cur_c < self.size - 1:
                    options.append((0, 1))

            if not options:
                # На всякий случай, если нет ходов, выходим вверх
                options = [(-1, 0)]

            dr, dc = random.choice(options)
            nr, nc = cur_r + dr, cur_c + dc

            # Гарантируем, что не выходим за границы
            nr = max(0, min(self.size - 1, nr))
            nc = max(0, min(self.size - 1, nc))

            if (nr, nc) not in path:
                path.append((nr, nc))
                cur_r, cur_c = nr, nc
            else:
                # Если зациклились — небольшой сдвиг по вертикали
                if cur_r > 0:
                    cur_r -= 1
                else:
                    break

        # Настроить типы узлов вдоль пути
        for i, (r, c) in enumerate(path):
            if i == 0:
                # Источник
                node = ZeroDownNode(r, c, "line", is_source=True)
            elif i == len(path) - 1:
                # Цель
                node = ZeroDownNode(r, c, "cross", is_target=True)
            else:
                prev_r, prev_c = path[i - 1]
                next_r, next_c = path[i + 1]

                dr1, dc1 = r - prev_r, c - prev_c
                dr2, dc2 = next_r - r, next_c - c

                # Определим направления (0=up,1=right,2=down,3=left)
                def vec_to_dir(dr, dc):
                    if dr == -1 and dc == 0:
                        return 0
                    if dr == 0 and dc == 1:
                        return 1
                    if dr == 1 and dc == 0:
                        return 2
                    if dr == 0 and dc == -1:
                        return 3
                    return None

                d1 = vec_to_dir(dr1, dc1)
                d2 = vec_to_dir(dr2, dc2)

                if d1 is None or d2 is None:
                    node = ZeroDownNode(r, c, "block")
                else:
                    # Если направление одно и то же по вертикали или горизонтали -> line
                    if (d1 + 2) % 4 == d2:
                        # прямая
                        node = ZeroDownNode(r, c, "line")
                        # базовый line - up/down -> если нужна горизонталь, повернём
                        if (d1 in (1, 3)) or (d2 in (1, 3)):
                            # горизонтальная линия -> повернуть на 1
                            node.rotation = 1
                    else:
                        # угол
                        node = ZeroDownNode(r, c, "corner")
                        # базовый corner: up-right (0,1)
                        # нам нужны d1 и d2, независимо от порядка
                        dirs = {d1, d2}

                        # подберём поворот так, чтобы порты совпали с dirs
                        # переберём rotation 0..3 и оставим подходящий
                        for rot in range(4):
                            ports = set(((p + rot) % 4) for p in {0, 1})
                            if ports == dirs:
                                node.rotation = rot
                                break

            self.grid[r][c] = node

        # Остальные клетки заполним случайным мусором
        types = ["line", "corner", "tee", "cross", "block"]
        for r in range(self.size):
            for c in range(self.size):
                node = self.grid[r][c]
                if not node.is_source and not node.is_target and node.node_type == "block":
                    t = random.choice(types)
                    rot = random.randint(0, 3)
                    self.grid[r][c] = ZeroDownNode(r, c, t, rot)

    # -------------------- ЛОГИКА ЭНЕРГИИ -------------------- #

    def neighbors_for(self, r, c):
        """Соседи (r, c, dir_from_here, dir_in_neighbor)."""
        dirs = [(-1, 0), (0, 1), (1, 0), (0, -1)]
        for d, (dr, dc) in enumerate(dirs):
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.size and 0 <= nc < self.size:
                opposite = (d + 2) % 4
                yield nr, nc, d, opposite

    def recalculate_power(self):
        """Пересчитать, какие узлы запитаны от источника."""
        for row in self.grid:
            for node in row:
                node.powered = False

        # Найдём источник
        source_node = None
        for row in self.grid:
            for node in row:
                if node.is_source:
                    source_node = node
                    break
            if source_node:
                break

        if not source_node:
            return

        queue = [source_node]
        source_node.powered = True

        while queue:
            node = queue.pop(0)
            r, c = node.row, node.col

            for nr, nc, d_here, d_neigh in self.neighbors_for(r, c):
                n = self.grid[nr][nc]
                if d_here in node.ports and d_neigh in n.ports:
                    if not n.powered:
                        n.powered = True
                        queue.append(n)

    def is_target_powered(self):
        for row in self.grid:
            for node in row:
                if node.is_target and node.powered:
                    return True
        return False

    # -------------------- ОТРИСОВКА -------------------- #

    def redraw(self):
        """Полностью перерисовать мини-игру."""
        self.canvas.delete(self.layer_tag)

        # ✅ Берём реальные размеры окна, а не canvas["width"]
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 1 or h <= 1:  # на всякий случай, если ещё не отрисовалось
            w = self.root.winfo_screenwidth()
            h = self.root.winfo_screenheight()

        # Фон под игру (полупрозрачный тёмный прямоугольник)
        panel_width = self.size * self.cell_size + self.margin * 2
        panel_height = self.size * self.cell_size + self.margin * 2

        x0 = (w - panel_width) // 2
        y0 = (h - panel_height) // 2
        x1 = x0 + panel_width
        y1 = y0 + panel_height

        self.canvas.create_rectangle(
            x0, y0, x1, y1,
            fill="#02060b",
            outline="#1c2733",
            width=2,
            tags=self.layer_tag
        )

        # Заголовок
        self.canvas.create_text(
            (x0 + x1) / 2, y0 + 25,
            text="ZERO-DAY NETWORK BREACH",
            fill="#82e4ff",
            font=("Consolas", 16, "bold"),
            tags=self.layer_tag
        )

        # Таймер
        timer_text = f"FIREWALL WINDOW: {self.time_left:02d}s"
        color = "#82e4ff" if self.time_left > self.total_time * 0.3 else "#ff5555"
        self.canvas.create_text(
            x0 + 10, y0 + 25,
            anchor="w",
            text=timer_text,
            fill=color,
            font=("Consolas", 12),
            tags=self.layer_tag
        )

        # Кнопка EXIT
        btn_w = 80
        btn_h = 28
        bx1 = x1 - 15
        by1 = y0 + 15
        bx0 = bx1 - btn_w
        by0 = by1 - btn_h
        self.exit_btn_bbox = (bx0, by0, bx1, by1)
        self.canvas.create_rectangle(
            bx0, by0, bx1, by1,
            outline="#ff4444",
            width=2,
            tags=self.layer_tag
        )
        self.canvas.create_text(
            (bx0 + bx1) / 2, (by0 + by1) / 2,
            text="EXIT",
            fill="#ff4444",
            font=("Consolas", 11, "bold"),
            tags=self.layer_tag
        )

        # Сетка
        grid_x0 = x0 + self.margin
        grid_y0 = y0 + self.margin

        for r in range(self.size):
            for c in range(self.size):
                node = self.grid[r][c]

                cx = grid_x0 + c * self.cell_size + self.cell_size / 2
                cy = grid_y0 + r * self.cell_size + self.cell_size / 2

                half = self.cell_size / 2 - 6
                base_color = "#2b3b4b"
                active_color = "#7ee8ff"

                color = active_color if node.powered else base_color

                # Квадрат
                self.canvas.create_rectangle(
                    cx - half, cy - half, cx + half, cy + half,
                    outline=color,
                    width=2,
                    tags=self.layer_tag
                )

                # Отрисовка портов (линии от центра)
                port_len = half - 8
                for p in node.ports:
                    if p == 0:  # up
                        x1p, y1p = cx, cy
                        x2p, y2p = cx, cy - port_len
                    elif p == 1:  # right
                        x1p, y1p = cx, cy
                        x2p, y2p = cx + port_len, cy
                    elif p == 2:  # down
                        x1p, y1p = cx, cy
                        x2p, y2p = cx, cy + port_len
                    else:        # left
                        x1p, y1p = cx, cy
                        x2p, y2p = cx - port_len, cy
                    self.canvas.create_line(
                        x1p, y1p, x2p, y2p,
                        fill=color,
                        width=3,
                        capstyle=tk.ROUND,
                        tags=self.layer_tag
                    )

                # Источник / цель
                if node.is_source:
                    self.canvas.create_oval(
                        cx - 10, cy - 10, cx + 10, cy + 10,
                        outline="#82e4ff",
                        width=3,
                        tags=self.layer_tag
                    )
                    self.canvas.create_text(
                        cx, cy,
                        text="S",
                        fill="#82e4ff",
                        font=("Consolas", 12, "bold"),
                        tags=self.layer_tag
                    )
                elif node.is_target:
                    # ромб-замок
                    self.canvas.create_polygon(
                        cx, cy - 13,
                        cx + 13, cy,
                        cx, cy + 13,
                        cx - 13, cy,
                        outline="#82e4ff" if node.powered else "#ffffff",
                        fill="",
                        width=3,
                        tags=self.layer_tag
                    )
                    self.canvas.create_text(
                        cx, cy,
                        text="LOCK",
                        fill="#82e4ff" if node.powered else "#ffffff",
                        font=("Consolas", 8, "bold"),
                        tags=self.layer_tag
                    )

    # -------------------- ВЗАИМОДЕЙСТВИЕ -------------------- #

    def canvas_to_cell(self, x, y):
        """Преобразовать координаты клика в (row, col) узла или None."""
        # ✅ такие же размеры, как в redraw()
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 1 or h <= 1:
            w = self.root.winfo_screenwidth()
            h = self.root.winfo_screenheight()

        panel_width = self.size * self.cell_size + self.margin * 2
        panel_height = self.size * self.cell_size + self.margin * 2

        x0 = (w - panel_width) // 2
        y0 = (h - panel_height) // 2

        grid_x0 = x0 + self.margin
        grid_y0 = y0 + self.margin

        cx = x - grid_x0
        cy = y - grid_y0

        if cx < 0 or cy < 0:
            return None

        col = int(cx // self.cell_size)
        row = int(cy // self.cell_size)

        if 0 <= row < self.size and 0 <= col < self.size:
            return row, col
        return None


    def on_click(self, event):
        if self.game_over:
            # Если уже конец игры — клики игнорируем
            return

        # Проверка на кнопку EXIT
        if self.exit_btn_bbox is not None:
            x0, y0, x1, y1 = self.exit_btn_bbox
            if x0 <= event.x <= x1 and y0 <= event.y <= y1:
                self.cleanup()
                self.on_exit()
                return

        cell = self.canvas_to_cell(event.x, event.y)
        if cell is None:
            return

        r, c = cell
        node = self.grid[r][c]

        # Нельзя крутить источник и цель
        if node.is_source or node.is_target:
            return

        # Поворот узла
        node.rotation = (node.rotation + 1) % 4
        self.play_sound("click")
        self.recalculate_power()
        self.redraw()

        # Проверка победы
        if self.is_target_powered():
            self.handle_success()

    def handle_escape(self, event=None):
        if self.game_over and self.success_shown:
            # После окна успеха Esc возвращает в меню
            self.cleanup()
            self.on_exit()
        elif not self.game_over:
            # В процессе игры Esc — просто выход
            self.cleanup()
            self.on_exit()

    # -------------------- ТАЙМЕР -------------------- #

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

    # -------------------- ОКОНЧАНИЕ ИГРЫ -------------------- #

    def handle_success(self):
        if self.game_over:
            return
        self.game_over = True
        self.play_sound("lock_open")
        if self.timer_id is not None:
            self.root.after_cancel(self.timer_id)

        self.show_success_popup()

    def handle_fail(self):
        if self.game_over:
            return
        self.game_over = True
        self.play_sound("fail")
        self.show_fail_popup()

    def show_success_popup(self):
        self.success_shown = True
        self.canvas.delete(self.layer_tag)

        w = int(self.canvas["width"])
        h = int(self.canvas["height"])

        box_w = 600
        box_h = 260
        x0 = (w - box_w) // 2
        y0 = (h - box_h) // 2
        x1 = x0 + box_w
        y1 = y0 + box_h

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
            "Вы успешно проложили скрытый маршрут обхода защиты.\n\n"
            "В реальной ситуации zero-day — это уязвимость, о которой\n"
            "производитель ПО ещё не знает, а значит нет патча и сигнатур.\n\n"
            "Чаще всего такие дыры обнаруживаются в веб-сервисах, драйверах,\n"
            "сетевых демонах и компонентах ОС. Атакующий может использовать\n"
            "их для повышения привилегий, обхода аутентификации или\n"
            "удалённого выполнения кода до того, как защита обновится."
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

        w = int(self.canvas["width"])
        h = int(self.canvas["height"])

        box_w = 450
        box_h = 180
        x0 = (w - box_w) // 2
        y0 = (h - box_h) // 2
        x1 = x0 + box_w
        y1 = y0 + box_h

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
                 "Попробуй ещё раз — уровень будет сгенерирован заново.",
            fill="#ffcccc",
            font=("Consolas", 11),
            justify="center",
            tags=self.layer_tag
        )

        self.canvas.create_text(
            (x0 + x1) / 2, y1 - 35,
            text="Нажми ESC, чтобы вернуться в центральное меню CtOS.",
            fill="#ff8888",
            font=("Consolas", 11),
            tags=self.layer_tag
        )

    def cleanup(self):
        """Очистка перед выходом в главное меню."""
        if self.timer_id is not None:
            try:
                self.root.after_cancel(self.timer_id)
            except Exception:
                pass
            self.timer_id = None

        self.canvas.unbind("<Button-1>")
        self.root.unbind("<Escape>")
        self.canvas.delete(self.layer_tag)
