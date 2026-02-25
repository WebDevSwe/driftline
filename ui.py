from __future__ import annotations

import json
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from models import WorldConfig
from world import World, SIZE_MAP, REGIONS

WINDOW_SIZE = 900
GRID_PADDING = 16
BASE_TICK_MS = 1000

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Driftline – Simulering")
        self.geometry(f"{WINDOW_SIZE}x{WINDOW_SIZE}")
        self.minsize(700, 650)

        self.world = None
        self.running = False
        self.speed_multiplier = 1

        self.statusbar = ctk.CTkFrame(self, height=40, fg_color="#131720")
        self.statusbar.pack(fill=tk.X, side=tk.TOP)
        self.statusbar.grid_columnconfigure(0, weight=0)
        self.statusbar.grid_columnconfigure(1, weight=0)
        self.statusbar.grid_columnconfigure(2, weight=0)
        self.statusbar.grid_columnconfigure(3, weight=1)

        self.status_left = ctk.CTkLabel(self.statusbar, text="Driftline", anchor="w")
        self.status_left.grid(row=0, column=0, sticky="w", padx=(12, 8), pady=8)

        controls = ctk.CTkFrame(self.statusbar, fg_color="transparent")
        controls.grid(row=0, column=1, sticky="w", padx=8, pady=6)

        self.play_button = ctk.CTkButton(controls, text="▶", width=36, command=self._toggle_play)
        self.play_button.grid(row=0, column=0, padx=(0, 8))

        self.speed_var = tk.StringVar(value="Normal")
        self.speed_menu = ctk.CTkOptionMenu(
            controls,
            variable=self.speed_var,
            values=["Normal", "+1", "+2"],
            command=self._set_speed,
            width=90,
        )
        self.speed_menu.grid(row=0, column=1)

        food_frame = ctk.CTkFrame(self.statusbar, fg_color="transparent")
        food_frame.grid(row=0, column=2, sticky="w", padx=8, pady=6)
        ctk.CTkLabel(food_frame, text="Mat", anchor="w").grid(row=0, column=0, padx=(0, 6))
        self.food_bar = ctk.CTkProgressBar(food_frame, width=120)
        self.food_bar.grid(row=0, column=1)
        self.food_bar.set(1.0)

        self.status_right = ctk.CTkLabel(self.statusbar, text="Resurser: - | Population: - | Stabilitet: -", anchor="e")
        self.status_right.grid(row=0, column=3, sticky="e", padx=(8, 12), pady=8)

        self.canvas = tk.Canvas(self, bg="#0f1115", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.stats_window = None
        self.stats_metric = tk.StringVar(value="Invånare")
        self.stats_per_year = tk.BooleanVar(value=False)
        self.budget_window = None
        self._updating_budget = False

        self._build_menus()
        self.bind("<Configure>", lambda _event: self._render_world())
        self.after(50, self._open_start_dialog)

    def _build_menus(self):
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Spara...", command=self._save_world)
        file_menu.add_command(label="Öppna...", command=self._load_world)
        file_menu.add_separator()
        file_menu.add_command(label="Avsluta", command=self.destroy)

        services_menu = tk.Menu(menubar, tearoff=0)
        services_menu.add_command(label="Socialservice...", command=self._open_services_settings)

        budget_menu = tk.Menu(menubar, tearoff=0)
        budget_menu.add_command(label="Budget...", command=self._open_budget_window)

        stats_menu = tk.Menu(menubar, tearoff=0)
        stats_menu.add_command(label="Statistik...", command=self._open_stats_window)

        menubar.add_cascade(label="Arkiv", menu=file_menu)
        menubar.add_cascade(label="Socialservice", menu=services_menu)
        menubar.add_cascade(label="Budget", menu=budget_menu)
        menubar.add_cascade(label="Statistik", menu=stats_menu)

        self.config(menu=menubar)

    def _open_start_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Skapa ny värld")
        dialog.geometry("420x320")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Namn på världen:").pack(anchor="w", padx=16, pady=(16, 4))
        name_var = tk.StringVar(value="Ny värld")
        name_entry = ctk.CTkEntry(dialog, textvariable=name_var)
        name_entry.pack(fill=tk.X, padx=16)

        ctk.CTkLabel(dialog, text="Ytans storlek:").pack(anchor="w", padx=16, pady=(12, 4))
        size_var = tk.StringVar(value="Medium")
        size_combo = ctk.CTkOptionMenu(dialog, variable=size_var, values=list(SIZE_MAP.keys()))
        size_combo.pack(fill=tk.X, padx=16)

        ctk.CTkLabel(dialog, text="Plats:").pack(anchor="w", padx=16, pady=(12, 4))
        region_var = tk.StringVar(value=REGIONS[1])
        region_combo = ctk.CTkOptionMenu(dialog, variable=region_var, values=REGIONS)
        region_combo.pack(fill=tk.X, padx=16)

        btns = ctk.CTkFrame(dialog, fg_color="transparent")
        btns.pack(fill=tk.X, padx=16, pady=16)
        btns.grid_columnconfigure(0, weight=1)
        btns.grid_columnconfigure(1, weight=1)

        def create_world():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Saknar namn", "Ange ett namn på världen.")
                return
            config = WorldConfig(name=name, size_label=size_var.get(), region=region_var.get())
            self.world = World(config)
            self.running = True
            self.play_button.configure(text="❚❚")
            self._render_world()
            self._update_status()
            self._tick()
            dialog.destroy()

        def cancel():
            self.destroy()

        ctk.CTkButton(btns, text="Skapa", command=create_world).grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ctk.CTkButton(btns, text="Avbryt", command=cancel, fg_color="#2b2f38").grid(row=0, column=1, sticky="ew")

        name_entry.focus_set()

    def _toggle_play(self):
        if not self.world:
            return
        self.running = not self.running
        self.play_button.configure(text="❚❚" if self.running else "▶")
        if self.running:
            self._tick()

    def _set_speed(self, value):
        if value == "Normal":
            self.speed_multiplier = 1
        elif value == "+1":
            self.speed_multiplier = 2
        else:
            self.speed_multiplier = 3

    def _tick(self):
        if not self.running or not self.world:
            return
        self.world.advance_month()
        self._update_status()
        self._update_stats_window()
        self._update_budget_window()
        tick_ms = max(200, int(BASE_TICK_MS / self.speed_multiplier))
        self.after(tick_ms, self._tick)

    def _update_status(self):
        if not self.world:
            return
        employed = self.world._employed_count()
        tax_month = (self.world.month % 12 == 0)
        if self.world.population > 0:
            food_ratio = max(0.0, 1.0 - (self.world.last_hungry / self.world.population))
        else:
            food_ratio = 1.0
        self.food_bar.set(food_ratio)
        facts = (
            f"Pengar: {self.world.money} | "
            f"Population: {self.world.population} | "
            f"Sysselsättning: {employed} | "
            f"Sjuka: {self.world.last_sick} | "
            f"Stabilitet: {self.world.stability} | "
            f"Skatt: {'NU' if tax_month else 'senare'} | "
            f"Tid: {self.world.formatted_time()}"
        )
        self.status_right.configure(text=facts)

    def _save_world(self):
        if not self.world:
            messagebox.showinfo("Ingen värld", "Skapa en värld innan du sparar.")
            return
        path = filedialog.asksaveasfilename(
            title="Spara simulering",
            defaultextension=".json",
            filetypes=[("Driftline JSON", "*.json")],
        )
        if not path:
            return
        data = self.world.to_dict()
        with open(path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def _load_world(self):
        path = filedialog.askopenfilename(
            title="Öppna simulering",
            filetypes=[("Driftline JSON", "*.json")],
        )
        if not path:
            return
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)
        self.world = World.from_dict(data)
        self.running = True
        self.play_button.configure(text="❚❚")
        self._render_world()
        self._update_status()
        self._update_stats_window()
        self._tick()

    def _open_tax_settings(self):
        if not self.world:
            messagebox.showinfo("Ingen värld", "Skapa eller ladda en värld först.")
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title("Skatter")
        dialog.geometry("360x220")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Skattesats:").pack(anchor="w", padx=16, pady=(16, 4))
        value_label = ctk.CTkLabel(dialog, text=f"{int(self.world.tax_rate * 100)}%")
        value_label.pack(anchor="w", padx=16)

        def update_tax(value):
            self.world.tax_rate = value / 100.0
            value_label.configure(text=f"{int(value)}%")

        slider = ctk.CTkSlider(dialog, from_=0, to=70, number_of_steps=70, command=update_tax)
        slider.set(self.world.tax_rate * 100)
        slider.pack(fill=tk.X, padx=16, pady=(8, 16))

        ctk.CTkButton(dialog, text="Klar", command=dialog.destroy).pack(padx=16, pady=(0, 16))

    def _open_services_settings(self):
        if not self.world:
            messagebox.showinfo("Ingen värld", "Skapa eller ladda en värld först.")
            return
        dialog = ctk.CTkToplevel(self)
        dialog.title("Socialservice")
        dialog.geometry("360x300")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        vars_map = {}
        for name, enabled in self.world.services.items():
            var = tk.BooleanVar(value=enabled)
            cb = ctk.CTkCheckBox(dialog, text=name, variable=var)
            cb.pack(anchor="w", padx=16, pady=6)
            vars_map[name] = var

        def apply_services():
            for name, var in vars_map.items():
                self.world.services[name] = bool(var.get())
            dialog.destroy()

        ctk.CTkButton(dialog, text="Spara", command=apply_services).pack(padx=16, pady=16)

    def _open_stats_window(self):
        if not self.world:
            messagebox.showinfo("Ingen värld", "Skapa eller ladda en värld först.")
            return
        if self.stats_window and self.stats_window.winfo_exists():
            self.stats_window.lift()
            return
        window = ctk.CTkToplevel(self)
        window.title("Statistik")
        window.geometry("520x380")
        window.transient(self)
        self.stats_window = window

        top = ctk.CTkFrame(window, fg_color="transparent")
        top.pack(fill=tk.X, padx=16, pady=(16, 8))

        ctk.CTkLabel(top, text="Visa:").pack(side=tk.LEFT)
        metric_menu = ctk.CTkOptionMenu(
            top,
            variable=self.stats_metric,
            values=["Invånare", "Pengar", "Utgifter", "Byggnader", "Total ekonomi"],
            command=lambda _value: self._update_stats_window(),
            width=160,
        )
        metric_menu.pack(side=tk.LEFT, padx=(8, 0))
        per_year = ctk.CTkCheckBox(
            top,
            text="Per år",
            variable=self.stats_per_year,
            command=self._update_stats_window,
        )
        per_year.pack(side=tk.LEFT, padx=12)

        self.stats_label = ctk.CTkLabel(window, text="")
        self.stats_label.pack(anchor="w", padx=16, pady=(0, 8))

        self.stats_canvas = tk.Canvas(window, bg="#0f1115", height=220, highlightthickness=0)
        self.stats_canvas.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

        self._update_stats_window()

    def _update_stats_window(self):
        if not self.world or not self.stats_window or not self.stats_window.winfo_exists():
            return
        metric = self.stats_metric.get()
        key_map = {
            "Invånare": "population",
            "Pengar": "money",
            "Utgifter": "expenses",
            "Byggnader": "buildings",
            "Total ekonomi": "economy",
        }
        key = key_map.get(metric, "population")
        source = self.world.history_year if self.stats_per_year.get() else self.world.history
        data = source.get(key, [])
        if metric == "Byggnader":
            current = len(self.world.buildings)
            if not data:
                data = [current]
            elif max(data) == 0 and current > 0:
                data = [current] * len(data)
            counts = {}
            for b in self.world.buildings:
                counts[b.kind] = counts.get(b.kind, 0) + 1
            breakdown = " | ".join(f"{k}: {v}" for k, v in sorted(counts.items()))
            self.stats_label.configure(
                text=f"{metric}: {current}  |  {breakdown}  |  Tid: {self.world.formatted_time()}"
            )
            self._draw_chart(data)
            return
        else:
            current = data[-1] if data else 0
        self.stats_label.configure(text=f"{metric}: {current}  |  Tid: {self.world.formatted_time()}")
        self._draw_chart(data)

    def _open_budget_window(self):
        if not self.world:
            messagebox.showinfo("Ingen värld", "Skapa eller ladda en värld först.")
            return
        if self.budget_window and self.budget_window.winfo_exists():
            self.budget_window.lift()
            self._update_budget_window()
            return
        window = ctk.CTkToplevel(self)
        window.title("Budget")
        window.geometry("520x540")
        window.transient(self)
        self.budget_window = window

        self.budget_labels = {}
        header = ctk.CTkLabel(window, text="Budget (per år)", font=ctk.CTkFont(size=16, weight="bold"))
        header.pack(anchor="w", padx=16, pady=(16, 8))

        content = ctk.CTkScrollableFrame(window, fg_color="transparent")
        content.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

        for key in ["Intäkter", "Utgifter", "Basutgifter", "Service", "Säsong", "Netto"]:
            label = ctk.CTkLabel(content, text="")
            label.pack(anchor="w", pady=4)
            self.budget_labels[key] = label

        ctk.CTkLabel(content, text="Budget-allokering (%):").pack(anchor="w", pady=(8, 4))
        self.budget_sliders = {}
        for name in ["Basutgifter", "Service", "Säsong"]:
            row = ctk.CTkFrame(content, fg_color="transparent")
            row.pack(fill=tk.X, pady=2)
            ctk.CTkLabel(row, text=name, width=90, anchor="w").pack(side=tk.LEFT)
            slider = ctk.CTkSlider(
                row,
                from_=0,
                to=100,
                number_of_steps=100,
                command=lambda value, n=name: self._set_budget_allocation(n, value),
            )
            slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
            value_label = ctk.CTkLabel(row, text="0%")
            value_label.pack(side=tk.RIGHT)
            self.budget_sliders[name] = (slider, value_label)
            slider.set(self.world.budget_allocations.get(name, 100))

        ctk.CTkLabel(content, text="Skatt (%):").pack(anchor="w", pady=(8, 4))
        tax_row = ctk.CTkFrame(content, fg_color="transparent")
        tax_row.pack(fill=tk.X, pady=2)
        self.tax_slider = ctk.CTkSlider(
            tax_row,
            from_=0,
            to=70,
            number_of_steps=70,
            command=self._set_tax_rate,
        )
        self.tax_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.tax_label = ctk.CTkLabel(tax_row, text="0%")
        self.tax_label.pack(side=tk.RIGHT)
        self.tax_slider.set(self.world.tax_rate * 100)

        ctk.CTkLabel(content, text="Service-budget (%):").pack(anchor="w", pady=(8, 4))
        self.service_sliders = {}
        for name in ["Polis", "Brandkår", "Sjukvård", "Skola", "Barnomsorg", "A-kassa"]:
            row = ctk.CTkFrame(content, fg_color="transparent")
            row.pack(fill=tk.X, pady=2)
            ctk.CTkLabel(row, text=name, width=90, anchor="w").pack(side=tk.LEFT)
            slider = ctk.CTkSlider(
                row,
                from_=0,
                to=100,
                number_of_steps=100,
                command=lambda value, n=name: self._set_service_budget(n, value),
            )
            slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=6)
            value_label = ctk.CTkLabel(row, text="0%")
            value_label.pack(side=tk.RIGHT)
            self.service_sliders[name] = (slider, value_label)
            slider.set(self.world.service_funding.get(name, 0))

        self._update_budget_window()

    def _update_budget_window(self):
        if not self.world or not self.budget_window or not self.budget_window.winfo_exists():
            return
        self._updating_budget = True
        revenue = self.world.last_year_revenue
        total_expenses = self.world.last_year_expenses
        breakdown = self.world.last_expenses
        net = revenue - total_expenses
        year = max(1, (self.world.month // 12))
        self.budget_labels["Intäkter"].configure(text=f"Intäkter (år {year}): {revenue}")
        self.budget_labels["Utgifter"].configure(text=f"Utgifter totalt (år {year}): {total_expenses}")
        self.budget_labels["Basutgifter"].configure(text=f"Basutgifter (senaste månad): {breakdown.get('Basutgifter', 0)}")
        self.budget_labels["Service"].configure(text=f"Service (senaste månad): {breakdown.get('Service', 0)}")
        self.budget_labels["Säsong"].configure(text=f"Säsong (senaste månad): {breakdown.get('Säsong', 0)}")
        self.budget_labels["Netto"].configure(text=f"Netto (år {year}): {net}")
        for name, (slider, value_label) in self.budget_sliders.items():
            value = self.world.budget_allocations.get(name, 100)
            value_label.configure(text=f"{int(value)}%")
        if hasattr(self, "tax_slider"):
            self.tax_slider.set(self.world.tax_rate * 100)
            self.tax_label.configure(text=f"{int(self.world.tax_rate * 100)}%")
        for name, (slider, value_label) in self.service_sliders.items():
            value = self.world.service_funding.get(name, 0)
            value_label.configure(text=f"{int(value)}%")
        self._updating_budget = False

    def _set_service_budget(self, name, value):
        if not self.world:
            return
        if self._updating_budget:
            return
        self.world.service_funding[name] = int(value)
        self._update_budget_window()

    def _set_budget_allocation(self, name, value):
        if not self.world:
            return
        if self._updating_budget:
            return
        self.world.budget_allocations[name] = int(value)
        self._update_budget_window()

    def _set_tax_rate(self, value):
        if not self.world:
            return
        if self._updating_budget:
            return
        self.world.tax_rate = int(value) / 100.0
        if hasattr(self, "tax_label"):
            self.tax_label.configure(text=f"{int(value)}%")

    def _draw_chart(self, data):
        canvas = self.stats_canvas
        canvas.delete("all")
        if not data:
            return
        width = canvas.winfo_width()
        height = canvas.winfo_height()
        if width < 10 or height < 10:
            return
        padding = 20
        values = data[-50:]
        max_val = max(values)
        min_val = min(values)
        span = max(1, max_val - min_val)
        step = (width - 2 * padding) / max(1, len(values) - 1)
        points = []
        for i, value in enumerate(values):
            x = padding + i * step
            y = height - padding - ((value - min_val) / span) * (height - 2 * padding)
            points.extend([x, y])
        canvas.create_line(points, fill="#62b1ff", width=2, smooth=True)
        canvas.create_rectangle(padding, padding, width - padding, height - padding, outline="#1f232b")

    def _render_world(self):
        self.canvas.delete("all")
        if not self.world:
            return

        grid_size = self.world.grid_size
        available = min(self.winfo_width(), self.winfo_height() - self.statusbar.winfo_height()) - 2 * GRID_PADDING
        cell = max(4, available // grid_size)
        grid_px = cell * grid_size
        start_x = (self.winfo_width() - grid_px) // 2
        start_y = self.statusbar.winfo_height() + (self.winfo_height() - self.statusbar.winfo_height() - grid_px) // 2

        for i in range(grid_size + 1):
            x = start_x + i * cell
            y = start_y + i * cell
            self.canvas.create_line(start_x, y, start_x + grid_px, y, fill="#1f232b")
            self.canvas.create_line(x, start_y, x, start_y + grid_px, fill="#1f232b")

        road_color = "#2b2f38"
        road_width = max(2, cell // 2)
        center = grid_size // 2
        x = start_x + center * cell
        y = start_y + center * cell
        self.canvas.create_line(x, start_y, x, start_y + grid_px, fill=road_color, width=road_width)
        self.canvas.create_line(start_x, y, start_x + grid_px, y, fill=road_color, width=road_width)

        interval = max(6, grid_size // 10)
        for i in range(interval, grid_size, interval):
            if i == center:
                continue
            xi = start_x + i * cell
            yi = start_y + i * cell
            self.canvas.create_line(xi, start_y, xi, start_y + grid_px, fill=road_color, width=max(1, road_width - 2))
            self.canvas.create_line(start_x, yi, start_x + grid_px, yi, fill=road_color, width=max(1, road_width - 2))

        pad = max(1, cell // 10)
        for building in self.world.buildings:
            x1 = start_x + building.x * cell + pad
            y1 = start_y + building.y * cell + pad
            x2 = x1 + cell - 2 * pad
            y2 = y1 + cell - 2 * pad
            color = building.color
            if not building.active:
                color = "#6b6f7a"
            self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = App()
    app.mainloop()
