from __future__ import annotations

import json
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

from models import WorldConfig
from sprites import SpriteLibrary
from world import (
    APARTMENT_RENT,
    HOME_RUNNING_COSTS,
    HOTEL_RENT,
    REGIONS,
    RENT_COST,
    SIZE_MAP,
    TRANSPORT_MODES,
    World,
)

WINDOW_SIZE = 900
GRID_PADDING = 16
BASE_TICK_MS = 1000
PANEL = "#121a25"
PANEL_RAISED = "#182535"
INK = "#e8eef7"
MUTED = "#8fa4bb"
ACCENT = "#e6a84a"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Driftline – Simulering")
        self.geometry(f"{WINDOW_SIZE}x{WINDOW_SIZE}")
        self.minsize(700, 650)

        self.world = None
        self.running = False
        self.speed_multiplier = 1
        self.sprites = SpriteLibrary()

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
        self.canvas.bind("<Button-1>", self._inspect_map_block)

        self.stats_window = None
        self.stats_metric = tk.StringVar(value="Invånare")
        self.stats_per_year = tk.BooleanVar(value=False)
        self.stats_overview = None
        self.budget_window = None
        self.budget_service_overview = None
        self._updating_budget = False
        self.citizens_window = None
        self.citizens_frame = None
        self.citizen_detail = None
        self.citizen_portrait = None
        self.citizen_name_label = None
        self.citizen_context = None
        self.citizen_transport = None
        self.pin_button = None
        self.selected_human_id = None
        self.block_window = None
        self.block_content = None
        self.selected_block = None
        self.citizens_page = 0
        self._citizens_tick_counter = 0

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

        citizens_menu = tk.Menu(menubar, tearoff=0)
        citizens_menu.add_command(label="Invånare...", command=self._open_citizens_window)

        menubar.add_cascade(label="Arkiv", menu=file_menu)
        menubar.add_cascade(label="Socialservice", menu=services_menu)
        menubar.add_cascade(label="Budget", menu=budget_menu)
        menubar.add_cascade(label="Statistik", menu=stats_menu)
        menubar.add_cascade(label="Invånare", menu=citizens_menu)

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
            self.running = False
            self.play_button.configure(text="▶")
            self._render_world()
            self._update_status()
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
        self._render_world()
        self._update_status()
        self._update_stats_window()
        self._update_budget_window()
        self._update_block_window()
        self._citizens_tick_counter += 1
        has_pinned = any(h.pinned for h in self.world.humans)
        if has_pinned or self._citizens_tick_counter >= 24:
            self._citizens_tick_counter = 0
            self._update_citizens_window()
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
            f"Arbetslösa: {self.world.unemployed} | "
            f"Sjuka: {self.world.last_sick} | "
            f"Stabilitet: {self.world.stability} | "
            f"Dragningskraft: {self.world.attractiveness:.0f} | "
            f"Kriminalitet: {self.world.crime_rate:.0f} | "
            f"Flytt: +{self.world.last_arrivals}/-{self.world.last_departures} | "
            f"Bankränta: {self.world.last_bank_rate:.2%} | "
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
        self.running = False
        self.play_button.configure(text="▶")
        self._render_world()
        self._update_status()
        self._update_stats_window()

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
            self._update_budget_window()
            dialog.destroy()

        ctk.CTkButton(dialog, text="Spara", command=apply_services).pack(padx=16, pady=16)

    def _open_stats_window(self):
        if not self.world:
            messagebox.showinfo("Ingen värld", "Skapa eller ladda en värld först.")
            return
        if self.stats_window and self.stats_window.winfo_exists():
            self.stats_window.lift()
            self._update_stats_window()
            return
        window = ctk.CTkToplevel(self)
        window.title("Statistik")
        window.geometry("880x700")
        window.minsize(720, 580)
        window.transient(self)
        self.stats_window = window

        top = ctk.CTkFrame(window, fg_color="transparent")
        top.pack(fill=tk.X, padx=16, pady=(16, 8))

        ctk.CTkLabel(top, text="Visa:").pack(side=tk.LEFT)
        metric_menu = ctk.CTkOptionMenu(
            top,
            variable=self.stats_metric,
            values=[
                "Invånare", "Inflyttade", "Utflyttade", "Sysselsatta", "Arbetslösa",
                "Hungriga", "Sjuka", "Mat tillgänglig", "Matlager", "Bostadskapacitet",
                "Boende i bostad", "Arbetsplatser", "Jordbruk", "Byggnader",
                "Hotellgäster", "Hotellplatser", "Cyklar", "Bussresenärer", "Bilar",
                "Pensionärer", "Dödsfall", "Pensionskapital",
                "Vårdade", "Brottsutsatta", "Bränder", "Studerande", "Barnomsorg",
                "Centrumyta", "Dragningskraft", "Kriminalitet", "Kommunens pengar",
                "Utgifter", "A-kassa", "Total ekonomi", "Penningmängd",
                "Servicetäckning", "Serviceeffekt", "Extern balans", "Bokföringsavvikelse",
            ],
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

        self.stats_canvas = tk.Canvas(window, bg="#0f1115", height=240, highlightthickness=0)
        self.stats_canvas.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 8))

        self.stats_overview = ctk.CTkTextbox(window, height=250, font=("Consolas", 12))
        self.stats_overview.pack(fill=tk.X, padx=16, pady=(0, 16))
        self.stats_overview.configure(state="disabled")

        self._update_stats_window()

    def _open_citizens_window(self):
        if not self.world:
            messagebox.showinfo("Ingen värld", "Skapa eller ladda en värld först.")
            return
        if self.citizens_window and self.citizens_window.winfo_exists():
            self.citizens_window.lift()
            self._update_citizens_window()
            return
        window = ctk.CTkToplevel(self)
        window.title("Invånare")
        window.geometry("1040x680")
        window.minsize(900, 600)
        window.transient(self)
        self.citizens_window = window

        layout = ctk.CTkFrame(window, fg_color="transparent")
        layout.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)
        layout.grid_columnconfigure(0, weight=2)
        layout.grid_columnconfigure(1, weight=3)
        layout.grid_rowconfigure(0, weight=1)

        self.citizens_frame = ctk.CTkScrollableFrame(layout, fg_color="transparent")
        self.citizens_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        detail_frame = ctk.CTkFrame(layout, fg_color=PANEL, corner_radius=12)
        detail_frame.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        hero = ctk.CTkFrame(detail_frame, fg_color=PANEL_RAISED, corner_radius=10)
        hero.pack(fill=tk.X, padx=12, pady=12)
        self.citizen_portrait = ctk.CTkLabel(hero, text="", width=190, height=190)
        self.citizen_portrait.pack(side=tk.LEFT, padx=10, pady=10)
        hero_text = ctk.CTkFrame(hero, fg_color="transparent")
        hero_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4, 12), pady=12)
        self.citizen_name_label = ctk.CTkLabel(
            hero_text, text="", anchor="w", font=ctk.CTkFont(size=22, weight="bold"), text_color=INK
        )
        self.citizen_name_label.pack(fill=tk.X)
        self.citizen_context = ctk.CTkLabel(hero_text, text="", anchor="w", justify="left", text_color=MUTED)
        self.citizen_context.pack(fill=tk.X, pady=(6, 0))
        self.citizen_transport = ctk.CTkLabel(hero, text="", width=90, height=70)
        self.citizen_transport.pack(side=tk.RIGHT, padx=(0, 12), pady=10)
        self.citizen_detail = ctk.CTkTextbox(detail_frame, font=("Consolas", 13), fg_color="#0d141d")
        self.citizen_detail.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 8))
        self.citizen_detail.configure(state="disabled")
        self.pin_button = ctk.CTkButton(detail_frame, text="Nåla fast", command=self._toggle_pin_selected)
        self.pin_button.pack(fill=tk.X, padx=12, pady=(0, 12))

        controls = ctk.CTkFrame(window, fg_color="transparent")
        controls.pack(fill=tk.X, padx=16, pady=(0, 12))
        ctk.CTkButton(controls, text="◀", width=40, command=self._prev_citizens_page).pack(side=tk.LEFT)
        ctk.CTkButton(controls, text="▶", width=40, command=self._next_citizens_page).pack(side=tk.LEFT, padx=(8, 0))

        self._update_citizens_window()

    def _energy_color(self, energy):
        ratio = max(0.0, min(1.0, energy / 100))
        red = int(255 * (1 - ratio))
        green = int(255 * ratio)
        return f"#{red:02x}{green:02x}00"

    def _select_citizen(self, human_id):
        self.selected_human_id = human_id
        self._update_citizens_window()

    def _toggle_pin_selected(self):
        if not self.world or self.selected_human_id is None: return
        human = next((h for h in self.world.humans if h.id == self.selected_human_id), None)
        if human is None: return
        human.pinned = not human.pinned
        if human.pinned and not human.personal_history:
            workplace = next((w for w in self.world.workplaces if w.id == human.job_id), None)
            human.personal_history.append({
                "month": self.world.month, "money": human.money, "food": human.food,
                "health": human.health, "energy": human.energy,
                "job": workplace.kind if workplace else None,
                "home": human.home_kind, "hungry": human.hungry,
            })
        self._update_citizens_window()

    def _prev_citizens_page(self):
        if self.citizens_page > 0:
            self.citizens_page -= 1
            self._update_citizens_window()

    def _next_citizens_page(self):
        if not self.world:
            return
        max_page = max(0, (len(self.world.humans) - 1) // 10)
        if self.citizens_page < max_page:
            self.citizens_page += 1
            self._update_citizens_window()

    def _update_citizens_window(self):
        if not self.world or not self.citizens_window or not self.citizens_window.winfo_exists():
            return
        if not self.citizens_frame or not self.citizen_detail:
            return

        for child in self.citizens_frame.winfo_children():
            child.destroy()

        selected = None
        start = self.citizens_page * 10
        end = start + 10
        pinned = [h for h in self.world.humans if h.pinned]
        page = [h for h in self.world.humans[start:end] if not h.pinned]
        for h in pinned + page:
            row = ctk.CTkFrame(self.citizens_frame, fg_color="transparent")
            row.pack(fill=tk.X, pady=2)

            dot = tk.Canvas(row, width=12, height=12, highlightthickness=0, bg="#0f1115")
            dot.pack(side=tk.LEFT, padx=(0, 6))
            color = self._energy_color(h.energy)
            dot.create_oval(2, 2, 10, 10, fill=color, outline="")

            name_btn = ctk.CTkButton(
                row,
                text=f"★ {h.name}" if h.pinned else h.name,
                width=140,
                command=lambda hid=h.id: self._select_citizen(hid),
            )
            name_btn.pack(side=tk.LEFT, padx=(0, 6))

            status = "Sjuk" if h.sick else "Hungrig" if h.hungry else "Ok"
            row_job = next((w for w in self.world.workplaces if w.id == h.job_id), None)
            ctk.CTkLabel(
                row, text=f"{status} | {(row_job.service_name or row_job.kind) if row_job else ('Pensionär' if h.retired else 'Arbetslös')} | {h.money} SM"
            ).pack(side=tk.LEFT)

            if self.selected_human_id == h.id:
                selected = h

        if selected is None and self.world.humans:
            selected = self.world.humans[0]
            self.selected_human_id = selected.id

        if selected:
            workplace = next((w for w in self.world.workplaces if w.id == selected.job_id), None)
            job_status = ((workplace.service_name or workplace.kind) if workplace else
                          ("Pensionär" if selected.retired else "Arbetslös"))
            wage = self.world._wage_for(selected, workplace) if workplace else 0
            if workplace and workplace.blocks and selected.home_x is not None:
                commute = min(abs(selected.home_x-x)+abs(selected.home_y-y) for x, y in workplace.blocks)
            else:
                commute = None
            address = (f"Block ({selected.home_x}, {selected.home_y})"
                       if selected.home_x is not None else "Ingen fast adress")
            owned_housing = sum(
                1 for b in self.world.buildings
                if b.active and b.kind == "Bostad" and b.owner_id == selected.id
            )
            owned_housing_capacity = sum(
                self.world._private_home_capacity(b) for b in self.world.buildings
                if b.active and b.kind == "Bostad" and b.owner_id == selected.id
            )
            owned_businesses = sum(1 for w in self.world.workplaces if w.owner_id == selected.id)
            employees = sum(w.employed for w in self.world.workplaces if w.owner_id == selected.id)
            tenants = sum(
                1
                for h in self.world.humans
                if h.home_owner_id == selected.id and h.id != selected.id
            )
            renting = (
                selected.home_kind not in ("Tält", "Bostadslös")
                and selected.home_owner_id is not None
                and selected.home_owner_id != selected.id
            )
            interests = {
                "företagare": "företagande och lokala affärer", "lantbruk": "odling och matförsörjning",
                "tältliv": "enkelt boende och frihet", "status": "bekvämlighet och status",
                "risk": "nya möjligheter och risktagande", "sparsam": "sparande och trygghet",
            }.get(selected.drive, selected.drive)
            self.citizen_portrait.configure(image=self.sprites.portrait(selected), text="")
            self.citizen_name_label.configure(text=selected.name)
            self.citizen_context.configure(
                text=f"{selected.age} år  •  {job_status}\nIntresse: {interests}\n{address}"
            )
            mode = self.world._transport_mode(selected)
            self.citizen_transport.configure(image=self.sprites.transport(mode), text="")
            lines = ["VÄLMÅENDE OCH EKONOMI",
                     f"Pengar                 {selected.money:>6} SM",
                     f"Inkomst denna månad    {selected.last_income:>6} SM",
                     f"Levnadskostnad         {selected.last_living_cost:>6} SM",
                     f"Mat / energi / hälsa   {selected.food} / {selected.energy} / {selected.health}",
                     f"Kompetens              {selected.education_level:>6.1f}/100",
                     f"Missnöje                {selected.dissatisfaction:>6.0f}/100"]
            if selected.sick: lines.append("Status: Sjuk")
            if selected.hungry: lines.append("Status: Hungrig")
            if selected.retired: lines.append("Status: Pensionär")
            if selected.dependents: lines.append(f"Omsorgsansvar: {selected.dependents} barn")
            if selected.loan_balance: lines.append(f"Lån: {selected.loan_balance} SM")
            lines += ["", "BOENDE OCH ÄGANDE", f"Boende: {selected.home_kind}", f"Adress: {address}"]
            if selected.home_owner_id == selected.id and selected.home_kind in HOME_RUNNING_COSTS:
                lines.append(f"Boendedrift: {HOME_RUNNING_COSTS[selected.home_kind]} SM/mån")
            if renting:
                rent = HOTEL_RENT if selected.home_kind == "Hotell" else (
                    APARTMENT_RENT if selected.home_kind == "Lägenhet" else RENT_COST
                )
                lines.append(f"Hyra: {rent} SM/mån")
            if owned_housing:
                lines += [f"Ägda bostäder: {owned_housing}",
                          f"Platser i egna hus: {owned_housing_capacity}"]
            if tenants: lines.append(f"Hyresgäster nu: {tenants}")
            if owned_businesses:
                lines += [f"Ägda företag: {owned_businesses}", f"Anställda: {employees}"]
            lines += ["", "ARBETE OCH RESA", f"Arbete: {job_status}"]
            if workplace:
                lines += [f"Lön: {wage} SM/mån", f"Arbetsplats-ID: {selected.job_id}",
                          f"Arbetsadress: Block {workplace.blocks[0] if workplace.blocks else '-'}",
                          f"Resväg: {commute if commute is not None else '-'} block"]
            lines.append(f"Transportsätt: {mode} ({TRANSPORT_MODES[mode]['monthly']} SM/mån)")
            lines += ["", "INKÖP OCH SPARANDE",
                      f"Mat i skafferiet: {selected.food}",
                      f"Pensionskapital: {selected.pension_balance} SM",
                      f"Statusinköp: {selected.status_items}",
                      f"Fritidsköp: {selected.leisure_items}"]
            if selected.healthcare_visits:
                lines.append(f"Vårdtillfällen: {selected.healthcare_visits}")
            if selected.crime_victimizations:
                lines.append(f"Brottsutsatt: {selected.crime_victimizations} gånger")
            if selected.school_months:
                lines.append(f"Utbildningsmånader: {selected.school_months}")
            if selected.childcare_months:
                lines.append(f"Barnomsorgsmånader: {selected.childcare_months}")
            if selected.recent_purchases:
                lines.append("Senaste transaktioner:")
                lines.extend(
                    f"  M{purchase['month']}: {purchase['item']}  −{purchase['amount']} SM"
                    for purchase in selected.recent_purchases[-6:]
                )
            influences = []
            if selected.hungry: influences.append("− Hunger pressar hälsa och missnöje")
            if selected.unemployed_months: influences.append(f"− Arbetslös i {selected.unemployed_months} månader")
            if selected.financial_stress_months: influences.append(
                f"− Utgifterna har pressat ekonomin i {selected.financial_stress_months} månader")
            if selected.home_kind in ("Tält", "Bostadslös"): influences.append("− Osäkert boende påverkar hälsa och trivsel")
            if selected.job_id is not None: influences.append("+ Arbete ger lön och pensionsavsättning")
            if selected.home_kind not in ("Tält", "Bostadslös"): influences.append("+ Fast boende ger trygghet")
            if not influences: influences.append("• Inga starka individuella påverkansfaktorer just nu")
            if selected.last_events:
                influences.extend(f"• Denna månad: {event}" for event in selected.last_events)
            lines += ["", "VARFÖR MÅR PERSONEN SÅ HÄR?", *influences]
            detail = "\n".join(lines)+"\n"
            if selected.personal_history:
                first = selected.personal_history[0]
                detail += (
                    f"\nFöljs sedan månad {first['month']} ({len(selected.personal_history)} mätpunkter)\n"
                    f"Pengar: {first['money']} → {selected.money} SM\n"
                    f"Hälsa: {first['health']} → {selected.health}\n"
                    f"Mat: {first['food']} → {selected.food}\n"
                )
            self.citizen_detail.configure(state="normal")
            self.citizen_detail.delete("1.0", tk.END)
            self.citizen_detail.insert("1.0", detail)
            self.citizen_detail.configure(state="disabled")
            if self.pin_button:
                self.pin_button.configure(text="Ta bort nål" if selected.pinned else "Nåla fast")

    def _update_stats_window(self):
        if not self.world or not self.stats_window or not self.stats_window.winfo_exists():
            return
        metric = self.stats_metric.get()
        key_map = {
            "Invånare": "population",
            "Inflyttade": "arrivals", "Utflyttade": "departures",
            "Sysselsatta": "employed", "Arbetslösa": "unemployed",
            "Hungriga": "hungry", "Sjuka": "sick",
            "Mat tillgänglig": "food_supply", "Matlager": "food_stored",
            "Bostadskapacitet": "housing_capacity", "Boende i bostad": "housed",
            "Arbetsplatser": "workplaces", "Jordbruk": "farms",
            "Hotellgäster": "hotel_guests", "Hotellplatser": "hotel_rooms",
            "Cyklar": "bikes", "Bussresenärer": "bus_users", "Bilar": "cars",
            "Pensionärer": "retired", "Dödsfall": "deaths", "Pensionskapital": "pension_assets",
            "Vårdade": "healthcare_treated", "Brottsutsatta": "crime_victims",
            "Bränder": "fire_incidents", "Studerande": "students_supported",
            "Barnomsorg": "childcare_supported",
            "Centrumyta": "central_area", "Dragningskraft": "attractiveness",
            "Kriminalitet": "crime", "Kommunens pengar": "money",
            "Utgifter": "expenses",
            "A-kassa": "unemployment_support",
            "Byggnader": "buildings",
            "Total ekonomi": "economy",
            "Penningmängd": "money_supply", "Extern balans": "external_balance",
            "Servicetäckning": "service_coverage", "Serviceeffekt": "service_effectiveness",
            "Bokföringsavvikelse": "money_discrepancy",
        }
        key = key_map.get(metric, "population")
        source = self.world.history_year if self.stats_per_year.get() else self.world.history
        data = source.get(key, [])
        if not data:
            snapshot = self.world.statistics_snapshot()
            fallback = {
                "population": self.world.population, "money": self.world.money,
                "expenses": self.world.expenses, "buildings": snapshot["active_buildings"],
                "economy": self.world.money-self.world.expenses,
                "hungry": self.world.last_hungry, "sick": self.world.last_sick,
                "unemployed": self.world.unemployed, "employed": self.world._employed_count(),
                "food_supply": self.world.last_food_supply, "food_stored": snapshot["food_stored"],
                "housing_capacity": snapshot["housing_capacity"], "housed": snapshot["housed"],
                "workplaces": len(self.world.workplaces), "farms": snapshot["farms"],
                "attractiveness": self.world.attractiveness, "crime": self.world.crime_rate,
                "arrivals": self.world.last_arrivals, "departures": self.world.last_departures,
                "central_area": snapshot["central_area"],
                "unemployment_support": self.world.last_unemployment_support,
                "hotel_guests": snapshot["hotel_guests"], "hotel_rooms": snapshot["hotel_rooms"],
                "cars": snapshot["cars"],
                "bikes": snapshot["transport_modes"].get("Cykel", 0),
                "bus_users": snapshot["transport_modes"].get("Buss", 0),
                "retired": snapshot["retired"], "deaths": self.world.last_deaths,
                "pension_assets": self.world.central_bank.pension_assets,
                "healthcare_treated": self.world.last_healthcare_treated,
                "crime_victims": self.world.last_crime_victims,
                "fire_incidents": self.world.last_fire_incidents,
                "students_supported": self.world.last_students_supported,
                "childcare_supported": self.world.last_childcare_supported,
                "money_supply": self.world.last_money_supply,
                "external_balance": self.world.last_external_inflow-self.world.last_external_outflow,
                "money_discrepancy": self.world.last_money_discrepancy,
                "service_coverage": (round(100*sum(s.coverage for n, s in self.world.service_states.items()
                                                    if self.world.services.get(n))
                                           /max(1, sum(self.world.services.values())), 1)),
                "service_effectiveness": (round(100*sum(s.effectiveness for n, s in self.world.service_states.items()
                                                         if self.world.services.get(n))
                                                /max(1, sum(self.world.services.values())), 1)),
            }
            data = [fallback.get(key, 0)]
        current = data[-1] if data else 0
        self.stats_label.configure(
            text=f"{metric}: {current}  |  Senaste {len(data)} "
                 f"{'år' if self.stats_per_year.get() else 'månader'}  |  Tid: {self.world.formatted_time()}"
        )
        self._draw_chart(data)
        self._update_stats_overview()

    def _update_stats_overview(self):
        if not self.world or self.stats_overview is None: return
        stats = self.world.statistics_snapshot()
        businesses = "  ".join(
            f"{kind}: {count} ({stats['employees_by_kind'].get(kind, 0)} anst.)"
            for kind, count in sorted(stats["workplace_counts"].items())
        ) or "Inga"
        buildings = "  ".join(
            f"{kind}: {count}" for kind, count in sorted(stats["building_counts"].items())
        ) or "Inga"
        services = "  ".join(
            f"{name}: {count}" for name, count in stats["service_buildings"].items() if count
        ) or "Inga fysiska servicebyggnader"
        service_capacity = "  ".join(
            f"{name}: {state['staffed']}/{state['target']} bem, "
            f"{round(state['coverage']*100)}% täckning, {round(state['effectiveness']*100)}% effekt"
            for name, state in stats["service_states"].items()
            if self.world.services.get(name)
        ) or "Ingen aktiv service"
        home_types = "  ".join(
            f"{kind}: {count}" for kind, count in sorted(stats["home_types"].items())
        )
        text = (
            "BEFOLKNING OCH VÄLFÄRD\n"
            f"Invånare: {self.world.population:<6} Sysselsatta: {self.world._employed_count():<6} "
            f"Arbetslösa: {self.world.unemployed:<6} Hungriga: {self.world.last_hungry:<6} Sjuka: {self.world.last_sick}\n"
            f"Flytt denna månad: +{self.world.last_arrivals}/-{self.world.last_departures}    "
            f"Pensionärer: {stats['retired']}    Dödsfall: {self.world.last_deaths}\n"
            f"Dragningskraft: {self.world.attractiveness:.0f}    Kriminalitet: {self.world.crime_rate:.0f}\n\n"
            "SERVICEUTFALL DENNA MÅNAD\n"
            f"Vårdade: {self.world.last_healthcare_treated}    "
            f"Brottsutsatta: {self.world.last_crime_victims}    "
            f"Bränder: {self.world.last_fire_incidents}    "
            f"Utbildning: {self.world.last_students_supported}    "
            f"Barnomsorg: {self.world.last_childcare_supported}\n"
            f"Genomsnittlig kompetens: {stats['average_education']}    "
            f"Barn i hushållen: {stats['dependents']}\n\n"
            "MAT OCH ARBETE\n"
            f"Mat tillgänglig: {self.world.last_food_supply:<7} Mat såld: {self.world.last_food_sold:<7} "
            f"Mat i gårdslager: {stats['food_stored']}\n"
            f"Jordbruk: {stats['farms']}    Bönder: {stats['farm_workers']}    Företag: {len(self.world.workplaces)}\n"
            f"Verksamheter: {businesses}\n\n"
            "BOSTÄDER OCH CENTRUM\n"
            f"Boende i bostad: {stats['housed']}/{stats['housing_capacity']}    "
            f"Lediga platser: {stats['housing_vacancies']}\n"
            f"Privata hus: {stats['private_houses']}    Utbyggda hus: {stats['expanded_houses']}    "
            f"Flerfamiljshus: {stats['apartment_buildings']}    Centrumyta: {stats['central_area']}\n"
            f"Hotellgäster: {stats['hotel_guests']}/{stats['hotel_rooms']}    "
            f"Transport: gå {stats['transport_modes']['Gå']}, cykel {stats['transport_modes']['Cykel']}, "
            f"buss {stats['transport_modes']['Buss']}, bil {stats['transport_modes']['Bil']}\n"
            f"Boendeformer: {home_types}\n"
            f"Servicebyggnader: {services}\n"
            f"Servicekapacitet: {service_capacity}\n\n"
            "EKONOMI OCH SKAPAT INNEHÅLL\n"
            f"Kommunens pengar: {self.world.money} SM    Utgifter: {self.world.expenses} SM    "
            f"A-kassa utbetald: {self.world.last_unemployment_support} SM\n"
            f"Genomsnittliga invånarpengar: {stats['average_money']} SM\n"
            f"Centralbank: {self.world.central_bank.reserves} SM i reserv, "
            f"{self.world.central_bank.pension_assets} SM pensionskapital, "
            f"{self.world.central_bank.outstanding_loans} SM utlånat, "
            f"ränta {self.world.central_bank.policy_rate*100:.1f}%\n"
            f"Penningmängd: {self.world.last_money_supply} SM    "
            f"Externt flöde: +{self.world.last_external_inflow}/-{self.world.last_external_outflow} SM    "
            f"Avvikelse: {self.world.last_money_discrepancy:+} SM\n"
            f"Aktiva byggnader ({stats['active_buildings']}): {buildings}"
        )
        self.stats_overview.configure(state="normal")
        self.stats_overview.delete("1.0", tk.END)
        self.stats_overview.insert("1.0", text)
        self.stats_overview.configure(state="disabled")

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
        window.geometry("760x760")
        window.minsize(680, 620)
        window.transient(self)
        self.budget_window = window

        self.budget_labels = {}
        header = ctk.CTkLabel(window, text="Kommunens budget och prognos", font=ctk.CTkFont(size=16, weight="bold"))
        header.pack(anchor="w", padx=16, pady=(16, 8))

        content = ctk.CTkScrollableFrame(window, fg_color="transparent")
        content.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 16))

        for key in [
            "Kassa", "Prognos", "Nollskatt", "Uthållighet", "Intäkter", "Utgifter",
            "Skatteintäkter", "Markintäkter", "Investeringar", "Basutgifter",
            "Service", "Kommunala löner", "A-kassa", "Säsong", "Netto",
            "Penningmängd", "Extern ekonomi", "Avstämning", "Transaktioner",
        ]:
            label = ctk.CTkLabel(content, text="")
            label.pack(anchor="w", pady=4)
            self.budget_labels[key] = label

        ctk.CTkLabel(
            content,
            text="Prognosen använder dagens befolkning, jobb och servicenivå. "
                 "Full A-kassa ingår; framtida bygginvesteringar går inte att förutsäga.",
            text_color="#8f9bab", wraplength=680, justify="left",
        ).pack(anchor="w", pady=(2, 8))

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

        ctk.CTkLabel(content, text="Blockkostnad (min 1):").pack(anchor="w", pady=(8, 4))
        block_row = ctk.CTkFrame(content, fg_color="transparent")
        block_row.pack(fill=tk.X, pady=2)
        self.block_slider = ctk.CTkSlider(
            block_row,
            from_=1,
            to=1000,
            number_of_steps=999,
            command=self._set_block_cost,
        )
        self.block_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        self.block_label = ctk.CTkLabel(block_row, text="100")
        self.block_label.pack(side=tk.RIGHT)
        self.block_slider.set(self.world.block_cost)

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

        ctk.CTkLabel(content, text="Servicekapacitet och beräknad kostnad:").pack(anchor="w", pady=(12, 4))
        self.budget_service_overview = ctk.CTkLabel(
            content, text="", anchor="w", justify="left", font=("Consolas", 12)
        )
        self.budget_service_overview.pack(fill=tk.X, anchor="w", pady=(0, 8))

        self._update_budget_window()

    def _update_budget_window(self):
        if not self.world or not self.budget_window or not self.budget_window.winfo_exists():
            return
        for name, funding in self.world.service_funding.items():
            if funding > 0: self.world.services[name] = True
        self._updating_budget = True
        revenue = self.world.last_year_revenue
        total_expenses = self.world.last_year_expenses
        breakdown = self.world.last_expenses
        net = revenue - total_expenses
        forecast = self.world.budget_snapshot()
        year = max(1, (self.world.month // 12))
        projected = forecast["projected_net"]
        forecast_color = "#62d890" if projected >= 0 else "#ff7272"
        self.budget_labels["Kassa"].configure(
            text=f"Pengar i kassan nu: {forecast['treasury']} SM",
            text_color="#62d890" if forecast["treasury"] > 0 else "#ff7272",
        )
        self.budget_labels["Prognos"].configure(
            text=f"Prognos nästa 12 månader: {projected:+} SM  "
                 f"(intäkter {forecast['annual_income']} / drift {forecast['annual_cost']})",
            text_color=forecast_color,
        )
        break_even = forecast["break_even_tax"]
        break_even_text = "saknar löneunderlag" if break_even is None else f"cirka {break_even:.1%}"
        self.budget_labels["Nollskatt"].configure(
            text=f"Skatt för ungefär nollresultat: {break_even_text}"
        )
        runway = forecast["runway_months"]
        runway_text = "kassan växer" if runway is None else f"cirka {runway:.1f} månader"
        self.budget_labels["Uthållighet"].configure(text=f"Uthållighet med nuvarande prognos: {runway_text}")
        self.budget_labels["Intäkter"].configure(text=f"Intäkter (år {year}): {revenue}")
        self.budget_labels["Utgifter"].configure(text=f"Utgifter totalt (år {year}): {total_expenses}")
        self.budget_labels["Skatteintäkter"].configure(
            text=f"Senaste skatteintäkt: {forecast['last_tax_revenue']} SM"
        )
        self.budget_labels["Markintäkter"].configure(
            text=f"Bygg- och markintäkter denna månad: {forecast['last_development_revenue']} SM"
        )
        self.budget_labels["Investeringar"].configure(
            text=f"Kommunala bygginvesteringar denna månad: {breakdown.get('Investeringar', 0)} SM"
        )
        self.budget_labels["Basutgifter"].configure(text=f"Basutgifter (senaste månad): {breakdown.get('Basutgifter', 0)}")
        self.budget_labels["Service"].configure(text=f"Service (senaste månad): {breakdown.get('Service', 0)}")
        self.budget_labels["Kommunala löner"].configure(
            text=f"Kommunala löner (senaste månad): {breakdown.get('Kommunala löner', 0)}"
        )
        self.budget_labels["A-kassa"].configure(
            text=f"A-kassa till invånare (senaste månad): {breakdown.get('A-kassa utbetalningar', 0)}"
        )
        self.budget_labels["Säsong"].configure(text=f"Säsong (senaste månad): {breakdown.get('Säsong', 0)}")
        self.budget_labels["Netto"].configure(text=f"Netto (år {year}): {net}")
        flow_summary = self.world.transaction_summary()
        largest_flows = sorted(flow_summary.items(), key=lambda row: row[1], reverse=True)[:6]
        self.budget_labels["Penningmängd"].configure(
            text=f"Total penningmängd: {self.world.last_money_supply} SM"
        )
        self.budget_labels["Extern ekonomi"].configure(
            text=f"Externt denna månad: +{self.world.last_external_inflow} / "
                 f"-{self.world.last_external_outflow} SM"
        )
        discrepancy = self.world.last_money_discrepancy
        self.budget_labels["Avstämning"].configure(
            text=f"Bokföringsavvikelse: {discrepancy:+} SM",
            text_color="#62d890" if discrepancy == 0 else "#ff7272",
        )
        self.budget_labels["Transaktioner"].configure(
            text="Största månadsflöden: "+(", ".join(f"{name} {amount} SM" for name, amount in largest_flows)
                                           if largest_flows else "inga")
        )
        if self.budget_service_overview is not None:
            rows = []
            for name, item in forecast["service_items"].items():
                status = "PÅ " if item["enabled"] else "AV "
                coverage = round(item["coverage"]*100)
                effect = round(item["effectiveness"]*100)
                load = f"{item['workload']:.1f}x" if item["staffed"] else "—"
                detail = (f"mål {item['jobs']:>3}  lokal {item['facility_positions']:>3}  "
                          f"bem {item['staffed']:>3}  täck {coverage:>3}%  effekt {effect:>3}%  "
                          f"bel {load:>4}  drift {item['administration']:>3}")
                if item["transfer"]:
                    detail += f" + stöd {item['transfer']:>5} SM/mån"
                rows.append(
                    f"{name:<12} {status} {item['funding']:>3}%   {detail}  "
                    f"{item['monthly']*12:>7} SM/år"
                )
            self.budget_service_overview.configure(text="\n".join(rows))
        for name, (slider, value_label) in self.budget_sliders.items():
            value = self.world.budget_allocations.get(name, 100)
            value_label.configure(text=f"{int(value)}%")
        if hasattr(self, "tax_slider"):
            self.tax_slider.set(self.world.tax_rate * 100)
            self.tax_label.configure(text=f"{int(self.world.tax_rate * 100)}%")
        if hasattr(self, "block_slider"):
            self.block_slider.set(self.world.block_cost)
            self.block_label.configure(text=f"{int(self.world.block_cost)}")
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
        self.world.services[name] = int(value) > 0
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
        self._update_budget_window()

    def _set_block_cost(self, value):
        if not self.world:
            return
        if self._updating_budget:
            return
        self.world.block_cost = max(1, int(value))
        if hasattr(self, "block_label"):
            self.block_label.configure(text=f"{int(self.world.block_cost)}")

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
        canvas.create_rectangle(padding, padding, width - padding, height - padding, outline="#1f232b")
        canvas.create_text(padding+4, padding+4, text=f"max {max_val:g}", fill="#8f9bab", anchor="nw")
        canvas.create_text(padding+4, height-padding-4, text=f"min {min_val:g}", fill="#8f9bab", anchor="sw")
        if len(values) == 1:
            x, y = points
            canvas.create_oval(x-3, y-3, x+3, y+3, fill="#62b1ff", outline="")
        else:
            canvas.create_line(points, fill="#62b1ff", width=2, smooth=True)

    def _inspect_map_block(self, event):
        if not self.world or not hasattr(self, "_grid_geometry"): return
        start_x, start_y, cell, grid_size = self._grid_geometry
        x = int((event.x-start_x)//cell)
        y = int((event.y-start_y)//cell)
        if not (0 <= x < grid_size and 0 <= y < grid_size): return
        self.selected_block = (x, y)
        self._open_block_window()

    def _open_block_window(self):
        if not self.world or self.selected_block is None: return
        if self.block_window and self.block_window.winfo_exists():
            self.block_window.lift()
            self._update_block_window()
            return
        window = ctk.CTkToplevel(self)
        window.title("Kvartersvy")
        window.geometry("1000x700")
        window.minsize(840, 600)
        window.transient(self)
        self.block_window = window
        self.block_content = ctk.CTkFrame(window, fg_color="transparent")
        self.block_content.pack(fill=tk.BOTH, expand=True, padx=16, pady=16)
        self._update_block_window()

    def _show_citizen(self, human_id):
        if not self.world: return
        self.selected_human_id = human_id
        resident = next((h for h in self.world.humans if h.id == human_id), None)
        if resident and not resident.pinned:
            unpinned = [h for h in self.world.humans if not h.pinned]
            if resident in unpinned: self.citizens_page = unpinned.index(resident)//10
        self._open_citizens_window()

    def _update_block_window(self):
        if (not self.world or self.selected_block is None or not self.block_window
                or not self.block_window.winfo_exists() or self.block_content is None): return
        for child in self.block_content.winfo_children(): child.destroy()
        x, y = self.selected_block
        buildings = [b for b in self.world.buildings if b.active and b.x == x and b.y == y]
        residents = [h for h in self.world.humans if h.home_x == x and h.home_y == y]
        workplaces = [w for w in self.world.workplaces if (x, y) in w.blocks]
        workers = [h for h in self.world.humans if any(h.job_id == w.id for w in workplaces)]
        people = {h.id: h for h in self.world.humans}
        building = buildings[0] if buildings else None
        display_kind = (self.world._home_type(building) if building and building.kind == "Bostad"
                        else building.kind if building else "Obebyggd mark")
        self.block_window.title(f"Block ({x}, {y}) · {display_kind}")
        self.block_content.grid_columnconfigure(0, weight=2)
        self.block_content.grid_columnconfigure(1, weight=3)
        self.block_content.grid_rowconfigure(0, weight=1)

        overview = ctk.CTkFrame(self.block_content, fg_color=PANEL, corner_radius=12)
        overview.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(overview, text=display_kind.upper(), text_color=ACCENT,
                     font=ctk.CTkFont(size=22, weight="bold")).pack(padx=14, pady=(14, 4))
        ctk.CTkLabel(overview, text=f"BLOCK {x}, {y}", text_color=MUTED).pack()
        if building:
            image = self.sprites.building(display_kind, (340, 250))
            ctk.CTkLabel(overview, text="", image=image).pack(fill=tk.X, padx=12, pady=10)
        else:
            ctk.CTkLabel(overview, text="Tom mark", height=180, text_color=MUTED).pack(fill=tk.X)

        facts = []
        if building:
            owner = people.get(building.owner_id)
            facts += [f"Ägare: {owner.name if owner else 'Kommunen / ingen'}",
                      f"Nivå: {building.level}    Centralitet: {building.centrality:.1f}"]
            if building.kind == "Bostad":
                capacity = self.world._private_home_capacity(building)
                facts.append(f"Boende: {len(residents)}/{capacity} platser")
            elif building.kind in ("Flerfamiljshus", "Hotell"):
                facts.append(f"Boende: {len(residents)}/{building.housing_units} platser")
        for workplace in workplaces:
            owner = people.get(workplace.owner_id)
            facts += ["", f"{workplace.service_name or workplace.kind} · verksamhet {workplace.id}",
                      f"Ägare: {owner.name if owner else 'Kommunen'}",
                      f"Jobb: {workplace.employed}/{workplace.capacity}",
                      f"Kassa: {workplace.money} SM    Resultat: {workplace.monthly_profit:+} SM"]
        ctk.CTkLabel(overview, text="\n".join(facts) or "Ingen verksamhet på platsen",
                     anchor="w", justify="left", text_color=INK).pack(fill=tk.X, padx=18, pady=(0, 14))

        right = ctk.CTkScrollableFrame(self.block_content, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self._block_impact_panel(right, building, workplaces, residents, workers)
        self._people_panel(right, "BOR HÄR", residents)
        workplace_residents = [h for h in workers if h not in residents]
        self._people_panel(right, "ARBETAR HÄR", workplace_residents)

    def _block_impact_panel(self, parent, building, workplaces, residents, workers):
        card = ctk.CTkFrame(parent, fg_color=PANEL_RAISED, corner_radius=10)
        card.pack(fill=tk.X, pady=(0, 10))
        ctk.CTkLabel(card, text="VARFÖR SPELAR BLOCKET ROLL?", text_color=ACCENT,
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=14, pady=(12, 5))
        impacts = []
        if building:
            kind = building.kind
            if kind in ("Bostad", "Flerfamiljshus"): impacts.append(f"+ Ger hem åt {len(residents)} invånare och minskar hemlöshet")
            if kind == "Hotell": impacts.append("+ Tar emot nyinflyttade innan de får permanent bostad")
            if kind == "Jordbruk": impacts.append("+ Producerar lokal mat och gör fortsatt inflyttning möjlig")
            if kind in ("Centrum", "Torg"): impacts.append("+ Höjer områdets centralitet och drar service närmare")
            if kind in self.world.services:
                state = self.world.service_states[kind]
                impacts.append(
                    f"+ {state.staffed}/{state.target_positions} tjänster bemannade, "
                    f"{round(state.coverage*100)}% täckning och "
                    f"{round(state.effectiveness*100)}% faktisk effekt"
                )
                if state.workload > 1:
                    impacts.append(f"− Belastningen är {state.workload:.1f} gånger tillgänglig kapacitet")
            if kind == "Industri": impacts.append("+ Många jobb och högre löner, men dyr placering nära bostäder")
        if workplaces:
            impacts.append(f"+ {sum(w.employed for w in workplaces)} löner förs ut i hushållsekonomin varje månad")
            profit = sum(w.monthly_profit for w in workplaces)
            impacts.append(f"{'+' if profit >= 0 else '−'} Verksamheternas senaste netto är {profit:+} SM")
        impacts.append(f"• {len(residents)} boende och {len(workers)} arbetande är direkt knutna hit")
        ctk.CTkLabel(card, text="\n".join(impacts), anchor="w", justify="left",
                     wraplength=500, text_color=INK).pack(fill=tk.X, padx=14, pady=(0, 12))

    def _people_panel(self, parent, title, humans):
        card = ctk.CTkFrame(parent, fg_color=PANEL, corner_radius=10)
        card.pack(fill=tk.X, pady=(0, 10))
        ctk.CTkLabel(card, text=f"{title} · {len(humans)}", text_color=MUTED,
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=14, pady=(10, 5))
        if not humans:
            ctk.CTkLabel(card, text="Ingen", text_color=MUTED).pack(anchor="w", padx=14, pady=(0, 10))
            return
        for human in humans[:30]:
            workplace = next((w for w in self.world.workplaces if w.id == human.job_id), None)
            role = (workplace.service_name or workplace.kind) if workplace else ("Pensionär" if human.retired else "Arbetslös")
            row = ctk.CTkButton(card, height=38, fg_color=PANEL_RAISED, hover_color="#263b53",
                                anchor="w", text=f"{human.name}   ·   {role}   ·   {human.money} SM",
                                command=lambda hid=human.id: self._show_citizen(hid))
            row.pack(fill=tk.X, padx=10, pady=3)
        if len(humans) > 30:
            ctk.CTkLabel(card, text=f"… och {len(humans)-30} till", text_color=MUTED).pack(pady=6)

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
        self._grid_geometry = (start_x, start_y, cell, grid_size)

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
            if building.kind == "Tält":
                self.canvas.create_oval(x1, y1, x2, y2, fill=color, outline="")
            elif building.kind == "Jordbruk":
                self.canvas.create_rectangle(x1, y1, x2, y2, fill="#8b5a2b", outline="")
                dot_color = "#c7a17a"
                dot_radius = max(1, cell // 8)
                spacing = max(dot_radius + 1, cell // 3)
                for dx in range(0, int(cell), spacing):
                    for dy in range(0, int(cell), spacing):
                        cx = x1 + dx + dot_radius
                        cy = y1 + dy + dot_radius
                        self.canvas.create_oval(
                            cx - dot_radius,
                            cy - dot_radius,
                            cx + dot_radius,
                            cy + dot_radius,
                            fill=dot_color,
                            outline="",
                        )
            elif building.kind == "Flerfamiljshus":
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#d8cae8")
                window_color = "#f3d98b"
                window_size = max(1, cell // 5)
                for wx in (x1 + cell * .25, x1 + cell * .65):
                    for wy in (y1 + cell * .25, y1 + cell * .6):
                        self.canvas.create_rectangle(
                            wx, wy, wx + window_size, wy + window_size,
                            fill=window_color, outline="",
                        )
            elif building.kind == "Bostad":
                width = max(1, min(3, building.level))
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="#c8e4ff", width=width)
            else:
                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="")
            if building.active and cell >= 14:
                display_kind = self.world._home_type(building) if building.kind == "Bostad" else building.kind
                sprite = self.sprites.canvas_building(display_kind, max(10, cell-2))
                if sprite:
                    self.canvas.create_image((x1+x2)/2, (y1+y2)/2, image=sprite)
            if self.selected_block == (building.x, building.y):
                self.canvas.create_rectangle(
                    start_x+building.x*cell, start_y+building.y*cell,
                    start_x+(building.x+1)*cell, start_y+(building.y+1)*cell,
                    outline=ACCENT, width=max(2, cell//7),
                )

        self.canvas.create_text(
            start_x+8, start_y+grid_px-8,
            text="Klicka på ett block för kvartersvy",
            fill=MUTED, anchor="sw", font=("Consolas", 10),
        )

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    app = App()
    app.mainloop()
