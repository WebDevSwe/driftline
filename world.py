from __future__ import annotations

import random
from bisect import bisect_right

from models import Building, Human, Workplace, WorldConfig

SIZE_MAP = {
    "Liten": 30,
    "Medium": 60,
    "Stor": 100,
}

REGIONS = ["Norra", "Medel", "Syd"]
SEASONS = ["Vinter", "Vår", "Sommar", "Höst"]

BLOCK_COST_MIN = 1
FOOD_MAX = 100
FOOD_BUY_THRESHOLD = 30
FOOD_MONTHLY_NEED = 2
FOOD_FARM_PER_EMPLOYEE_MONTH = 16
RENT_COST = 6
FOOD_PRICE = 2
STORE_BUY_PRICE = 0.5
TENT_CAPACITY = 4

WORKPLACE_RULES = {
    "Jordbruk": {
        "blocks": 4,
        "block_cost_multiplier": 0,
        "capacity_min": 1,
        "capacity_max": 10,
        "wage": 20,
        "strain": 1,
        "status_req": 0,
        "color": "#6ed26a",
    },
    "Mataffär": {
        "blocks_min": 1,
        "blocks_max": 2,
        "block_cost_multiplier": 2,
        "capacity_min": 2,
        "capacity_max": 20,
        "wage": 80,
        "strain": 1,
        "status_req": 1,
        "color": "#2eb6a8",
    },
    "Basjobb": {
        "blocks_min": 1,
        "blocks_max": 2,
        "block_cost_multiplier": 2,
        "capacity_min": 1,
        "capacity_max": 20,
        "wage": 60,
        "strain": 1,
        "status_req": 1,
        "color": "#7cc4ff",
    },
    "Service": {
        "blocks_min": 2,
        "blocks_max": 6,
        "block_cost_multiplier": 10,
        "capacity_min": 1,
        "capacity_max": 100,
        "wage": 140,
        "strain": 2,
        "status_req": 2,
        "color": "#ffd166",
    },
    "Industri": {
        "blocks_choices": [4, 6, 8, 16],
        "block_cost_multiplier": 100,
        "capacity_min": 100,
        "capacity_max": 10000,
        "wage": 300,
        "strain": 3,
        "status_req": 10,
        "color": "#f0b34f",
    },
}

class World:
    def __init__(self, config: WorldConfig):
        self.name = config.name
        self.size_label = config.size_label
        self.region = config.region
        self.grid_size = SIZE_MAP[config.size_label]
        self.buildings: list[Building] = []
        self.money = 120
        self.population = 10
        self.stability = 78
        self.expenses = 25
        self.tax_rate = 0.01
        self.services = {
            "Polis": False,
            "Brandkår": False,
            "Sjukvård": False,
            "Skola": False,
            "Barnomsorg": False,
            "A-kassa": False,
        }
        self.service_funding = {
            "Polis": 0,
            "Brandkår": 0,
            "Sjukvård": 0,
            "Skola": 0,
            "Barnomsorg": 0,
            "A-kassa": 0,
        }
        self.budget_allocations = {
            "Basutgifter": 100,
            "Service": 100,
            "Säsong": 100,
        }
        self.service_costs = {
            "Polis": 6,
            "Brandkår": 5,
            "Sjukvård": 7,
            "Skola": 6,
            "Barnomsorg": 4,
            "A-kassa": 3,
        }
        self.healthcare_extra_per_sick = 2
        self.region_profile = {
            "Norra": {
                "season_multiplier": {
                    "Vinter": 1.45,
                    "Vår": 1.15,
                    "Sommar": 1.05,
                    "Höst": 1.25,
                },
                "winter_stability_penalty": 2,
            },
            "Medel": {
                "season_multiplier": {
                    "Vinter": 1.2,
                    "Vår": 1.05,
                    "Sommar": 1.0,
                    "Höst": 1.1,
                },
                "winter_stability_penalty": 1,
            },
            "Syd": {
                "season_multiplier": {
                    "Vinter": 1.05,
                    "Vår": 1.0,
                    "Sommar": 0.95,
                    "Höst": 1.05,
                },
                "winter_stability_penalty": 0,
            },
        }
        self.month = 0
        self.unemployed = 6
        self.block_cost = 1
        self.block_restore_cost = 100
        self.food_price = 2
        self.next_human_id = 1
        self.next_workplace_id = 1
        self.humans: list[Human] = []
        self.workplaces: list[Workplace] = []
        self.history = {
            "population": [],
            "money": [],
            "expenses": [],
            "buildings": [],
            "economy": [],
        }
        self.history_year = {
            "population": [],
            "money": [],
            "expenses": [],
            "buildings": [],
            "economy": [],
        }
        self.last_revenue = 0
        self.last_expenses = {
            "Basutgifter": 0,
            "Service": 0,
            "Säsong": 0,
        }
        self.last_hungry = 0
        self.last_sick = 0
        self.last_unemployed = 0
        self.last_food_supply = 0
        self.last_food_sold = 0
        self.last_bank_rate = 0.01
        self.year_revenue = 0
        self.year_expenses = 0
        self.last_year_revenue = 0
        self.last_year_expenses = 0
        self._first_names = [
            "Alex", "Erik", "Sara", "Lina", "Oskar", "Nora", "Emil", "Maja",
            "Karl", "Vera", "Anton", "Elsa", "Leo", "Sofia", "Johan", "Ida",
        ]
        self._last_names = [
            "Andersson", "Johansson", "Karlsson", "Nilsson", "Larsson",
            "Olsson", "Persson", "Svensson", "Gustafsson", "Pettersson",
        ]
        self._drives = [
            ("företagare", 0.18),
            ("lantbruk", 0.12),
            ("tältliv", 0.08),
            ("status", 0.18),
            ("risk", 0.14),
            ("sparsam", 0.30),
        ]

        self._seed_world()
        self._seed_population()
        self._record_history()

    def _seed_world(self):
        random.seed(42)
        center = self.grid_size // 2
        size = 6
        start = center - (size // 2)
        for dx in range(size):
            for dy in range(size):
                self.buildings.append(Building(start + dx, start + dy, "#d9534f", "Torg"))

    def _seed_population(self):
        for _ in range(self.population):
            self.humans.append(
                Human(
                    id=self.next_human_id,
                    money=self._starting_capital(),
                    food=40,
                    name=self._random_name(),
                    age=random.randint(18, 35),
                    drive=self._random_drive(),
                )
            )
            self.next_human_id += 1

    def advance_month(self):
        self.month += 1
        self._apply_economy()
        self._record_history()

    def formatted_time(self):
        year = (self.month // 12) + 1
        month = (self.month % 12) + 1
        return f"År {year}, Månad {month} ({self.season()})"

    def season(self):
        return SEASONS[(self.month % 12) // 3]

    def _record_history(self):
        self.history["population"].append(self.population)
        self.history["money"].append(self.money)
        self.history["expenses"].append(self.expenses)
        self.history["buildings"].append(len(self.buildings))
        self.history["economy"].append(self.money - self.expenses)
        if self.month % 12 == 0:
            self.history_year["population"].append(self.population)
            self.history_year["money"].append(self.money)
            self.history_year["expenses"].append(self.expenses)
            self.history_year["buildings"].append(len(self.buildings))
            self.history_year["economy"].append(self.money - self.expenses)

    def _apply_economy(self):
        self._sync_population()
        self._age_population()
        self._maybe_upgrade_housing()
        self._assign_housing()
        self._sync_tents()
        self._spawn_new_businesses()
        self._assign_jobs_and_pay_wages()
        self._expand_workplaces()
        hungry = self._apply_food()
        self._apply_bankruptcy()
        self._update_building_activity()
        sick = self._update_health(hungry)
        self._apply_status_purchases()
        self._apply_unemployment_support()
        self._apply_bank_interest_and_loans()
        self._clamp_balances()

        season = self.season()
        service_cost = self._calc_service_cost(sick)
        base_expenses, seasonal_expenses, total_expenses = self._calc_expenses(season, service_cost)
        revenue, tax_month = self._calc_revenue()
        net = self._apply_budget(revenue, total_expenses, base_expenses, service_cost, seasonal_expenses, tax_month)

        self.last_hungry = hungry
        self.last_sick = sick
        self.last_unemployed = self.unemployed

        self._update_stability(season, net, hungry, sick)
        self._update_population(season, net, hungry)
        self._cleanup_abandoned_workplaces()

    def _calc_service_cost(self, sick):
        active_service_cost = sum(
            cost for name, cost in self.service_costs.items() if self.services.get(name, False)
        )
        if sick > 0 and self.services.get("Sjukvård", False):
            active_service_cost += min(30, sick) * self.healthcare_extra_per_sick
        funding_scale = 0.0
        if self.services:
            active = [name for name, enabled in self.services.items() if enabled]
            if active:
                funding_scale = sum(self.service_funding.get(name, 0) for name in active) / (100 * len(active))
        service_scale = max(0.6, self.population / 10)
        if active_service_cost == 0:
            return 0
        return int(active_service_cost * service_scale * max(0.2, funding_scale))

    def _calc_expenses(self, season, service_cost):
        profile = self.region_profile.get(self.region, self.region_profile["Medel"])
        season_multiplier = profile["season_multiplier"].get(season, 1.0)
        base_expenses = int(self.population * 0.6)
        seasonal_expenses = int(base_expenses * (season_multiplier - 1.0))
        base_expenses = int(base_expenses * (self.budget_allocations.get("Basutgifter", 100) / 100))
        service_cost = int(service_cost * (self.budget_allocations.get("Service", 100) / 100))
        seasonal_expenses = int(seasonal_expenses * (self.budget_allocations.get("Säsong", 100) / 100))
        total_expenses = base_expenses + service_cost + seasonal_expenses
        return base_expenses, seasonal_expenses, total_expenses

    def _calc_revenue(self):
        employed = self._employed_count()
        tax_month = (self.month % 12 == 0)
        revenue = int(employed * (2 + 6 * self.tax_rate) * (12 if tax_month else 0))
        return revenue, tax_month

    def _apply_budget(self, revenue, total_expenses, base_expenses, service_cost, seasonal_expenses, tax_month):
        net = revenue - total_expenses
        self.money = max(0, self.money + net)
        self.expenses = total_expenses
        self.last_revenue = revenue
        self.year_revenue += revenue
        self.year_expenses += total_expenses
        self.last_expenses = {
            "Basutgifter": base_expenses,
            "Service": service_cost,
            "Säsong": seasonal_expenses,
        }
        if tax_month:
            self.last_year_revenue = self.year_revenue
            self.last_year_expenses = self.year_expenses
            self.year_revenue = 0
            self.year_expenses = 0
        return net

    def _update_stability(self, season, net, hungry, sick):
        profile = self.region_profile.get(self.region, self.region_profile["Medel"])
        stability_drift = 0
        if self.region == "Norra" and season == "Vinter":
            stability_drift -= profile["winter_stability_penalty"]
        if self.tax_rate > 0.5:
            stability_drift -= int((self.tax_rate - 0.5) * 10)
        if self.services.get("Sjukvård", False):
            stability_drift += 1
        if self.services.get("Polis", False):
            stability_drift += 1
        if self.services.get("Skola", False):
            stability_drift += 1
        if self.budget_allocations.get("Basutgifter", 100) < 70:
            stability_drift -= 1
        if self.budget_allocations.get("Service", 100) < 60 and any(self.services.values()):
            stability_drift -= 1
        if self.service_funding.get("Polis", 0) >= 60:
            stability_drift += 1
        if self.service_funding.get("Brandkår", 0) >= 60:
            stability_drift += 1
        if net < 0 and (self.month % 12 == 0):
            stability_drift -= 1
        if self.unemployed > max(2, self.population // 3):
            stability_drift -= 2
        if hungry > 0:
            stability_drift -= min(5, hungry)
        if sick > 0:
            stability_drift -= min(4, sick // 3)
        if self.stability >= 70 and net >= 0:
            stability_drift += 1
        self.stability = max(0, min(100, self.stability + stability_drift))

    def _update_population(self, season, net, hungry):
        pop_change = 0
        if self.stability >= 70 and net >= 0:
            pop_change += 1
        if self.money >= 20:
            pop_change += 1
        if self.stability >= 55:
            pop_change += 1
        if self.stability <= 35 or self.money == 0:
            pop_change -= 1
        if self.stability <= 25:
            pop_change -= 1
        if season == "Vinter" and self.region == "Norra":
            pop_change -= 1
        if hungry == 0:
            pop_change += 1
        if self.unemployed > max(3, self.population // 2):
            pop_change -= 1
        if self.population <= 5 and pop_change < 0:
            pop_change += 1
        self.population = max(0, self.population + pop_change)

    def _sync_population(self):
        if self.population > len(self.humans):
            for _ in range(self.population - len(self.humans)):
                self.humans.append(
                    Human(
                        id=self.next_human_id,
                        money=self._starting_capital(),
                        food=30,
                        name=self._random_name(),
                        age=random.randint(18, 35),
                        drive=self._random_drive(),
                    )
                )
                self.next_human_id += 1
        elif self.population < len(self.humans):
            self.humans = self.humans[: self.population]

    def _random_name(self):
        return f"{random.choice(self._first_names)} {random.choice(self._last_names)}"

    def _random_drive(self):
        roll = random.random()
        acc = 0.0
        for name, weight in self._drives:
            acc += weight
            if roll <= acc:
                return name
        return "sparsam"

    def _starting_capital(self):
        base_wage = WORKPLACE_RULES["Basjobb"]["wage"]
        return random.randint(base_wage // 2, base_wage * 3)

    def _age_population(self):
        if self.month % 12 != 0:
            return
        for h in self.humans:
            h.age = min(120, h.age + 1)

    def _assign_housing(self):
        season = self.season()
        housing_blocks = [b for b in self.buildings if b.kind == "Bostad" and b.active]
        humans_by_id = {h.id: h for h in self.humans}
        slots = []
        for b in housing_blocks:
            if b.owner_id is None:
                continue
            slots.extend([b.owner_id] * 2)
        random.shuffle(slots)

        for h in self.humans:
            if h.home_kind == "Bostadslös" and h.home_owner_id is not None:
                h.home_owner_id = None

        owners = {b.owner_id for b in housing_blocks if b.owner_id is not None}
        for h in self.humans:
            if h.id in owners:
                h.home_kind = "Bostad"
                h.home_owner_id = h.id
                if h.id in slots:
                    slots.remove(h.id)

        candidates = [h for h in self.humans if h.home_kind != "Bostad"]
        random.shuffle(candidates)
        for h in candidates:
            if not slots:
                break
            owner_id = slots.pop()
            h.home_kind = "Bostad"
            h.home_owner_id = owner_id

        if season == "Vinter":
            for h in self.humans:
                if h.home_kind == "Tält":
                    h.home_kind = "Bostadslös"
                    h.home_owner_id = None
                    h.homeless_months = 0

        for h in self.humans:
            if h.home_kind == "Bostad" and h.home_owner_id is not None and h.home_owner_id != h.id:
                if h.money >= RENT_COST:
                    h.money -= RENT_COST
                    owner = humans_by_id.get(h.home_owner_id)
                    if owner is not None:
                        owner.money += RENT_COST
                else:
                    h.home_kind = "Bostadslös"
                    h.home_owner_id = None
                    h.homeless_months = 0

        if season != "Vinter":
            for h in self.humans:
                if h.money <= 0 and h.home_kind != "Bostad":
                    h.home_kind = "Tält"
                    h.home_owner_id = None
                    h.homeless_months = 0

    def _sync_tents(self):
        season = self.season()
        for h in self.humans:
            if season != "Vinter" and h.home_kind == "Bostadslös" and random.random() < 0.1:
                h.home_kind = "Tält"
                h.home_owner_id = None
                h.homeless_months = 0
        if season == "Vinter":
            target = 0
        else:
            tents_needed = sum(1 for h in self.humans if h.home_kind == "Tält")
            target = (tents_needed + TENT_CAPACITY - 1) // TENT_CAPACITY
        active_tents = [b for b in self.buildings if b.kind == "Tält" and b.active]
        if len(active_tents) > target:
            for b in active_tents[target:]:
                b.active = False
                b.owner_id = None
                b.kind = "Övergiven"
                b.color = "#6b6f7a"
            return
        needed = target - len(active_tents)
        if needed <= 0:
            return
        inactive = [b for b in self.buildings if not b.active]
        random.shuffle(inactive)
        while needed > 0 and inactive:
            b = inactive.pop()
            b.kind = "Tält"
            b.color = "#4caf50"
            b.active = True
            b.owner_id = None
            needed -= 1
        if needed <= 0:
            return
        free = self._available_blocks()
        while needed > 0 and free:
            x, y = free.pop()
            self.buildings.append(Building(x, y, "#4caf50", "Tält", active=True, owner_id=None))
            needed -= 1

    def _mark_homeless(self, count):
        if count <= 0:
            return
        candidates = [h for h in self.humans if h.home_kind == "Tält"]
        random.shuffle(candidates)
        for h in candidates[:count]:
            h.home_kind = "Bostadslös"
            h.home_owner_id = None
            h.homeless_months = 0

    def _employed_count(self):
        return sum(1 for h in self.humans if h.job_id is not None)

    def _available_blocks(self):
        used = {(b.x, b.y) for b in self.buildings if b.active}
        free = []
        for x in range(2, self.grid_size - 2):
            for y in range(2, self.grid_size - 2):
                if (x, y) in used:
                    continue
                free.append((x, y))
        random.shuffle(free)
        return free

    def _inactive_blocks(self):
        inactive = [b for b in self.buildings if not b.active]
        random.shuffle(inactive)
        return inactive

    def _claim_block(self, kind, color, owner_id, cost_multiplier):
        if cost_multiplier == 0:
            cost = 0
        else:
            cost = max(BLOCK_COST_MIN, self.block_cost) * cost_multiplier
        tents = [b for b in self.buildings if b.kind == "Tält" and b.active]
        if tents:
            block = tents[0]
            block.kind = kind
            block.color = color
            block.active = True
            block.owner_id = owner_id
            self._mark_homeless(TENT_CAPACITY)
            return block, cost
        inactive = self._inactive_blocks()
        if inactive:
            block = inactive[0]
            block.kind = kind
            block.color = color
            block.active = True
            block.owner_id = owner_id
            if cost_multiplier == 0:
                restore_cost = self.block_restore_cost
            else:
                restore_cost = min(
                    self.block_restore_cost,
                    int(max(BLOCK_COST_MIN, self.block_cost) * cost_multiplier * 0.5),
                )
            return block, restore_cost
        free = self._available_blocks()
        if not free:
            return None, None
        x, y = free[0]
        building = Building(x, y, color, kind, active=True, owner_id=owner_id)
        self.buildings.append(building)
        return building, cost

    def _claim_blocks(self, kind, color, owner_id, cost_multiplier, blocks_needed):
        blocks, total_cost = self._claim_blocks_rectangle(kind, color, owner_id, cost_multiplier, blocks_needed)
        if blocks:
            return blocks, total_cost
        blocks = []
        total_cost = 0
        for _ in range(blocks_needed):
            building, cost = self._claim_block(kind, color, owner_id, cost_multiplier)
            if building is None:
                break
            blocks.append((building.x, building.y))
            if cost is not None:
                total_cost += cost
        if len(blocks) < blocks_needed:
            for b in self.buildings:
                if (b.x, b.y) in blocks:
                    b.active = False
                    b.owner_id = None
                    b.kind = "Övergiven"
                    b.color = "#6b6f7a"
            return [], 0
        return blocks, total_cost

    def _claim_blocks_rectangle(self, kind, color, owner_id, cost_multiplier, blocks_needed):
        used = {(b.x, b.y): b for b in self.buildings if b.active}
        inactive = {(b.x, b.y): b for b in self.buildings if not b.active}
        dims = [(w, blocks_needed // w) for w in range(1, blocks_needed + 1) if blocks_needed % w == 0]
        random.shuffle(dims)
        for width, height in dims:
            max_x = self.grid_size - 2 - width
            max_y = self.grid_size - 2 - height
            if max_x < 2 or max_y < 2:
                continue
            xs = list(range(2, max_x + 1))
            ys = list(range(2, max_y + 1))
            random.shuffle(xs)
            random.shuffle(ys)
            for x in xs:
                for y in ys:
                    cells = [(x + dx, y + dy) for dx in range(width) for dy in range(height)]
                    blocked = False
                    for cell in cells:
                        b = used.get(cell)
                        if b is not None and b.kind != "Tält":
                            blocked = True
                            break
                    if blocked:
                        continue
                    total_cost = 0
                    for cell in cells:
                        if cell in used:
                            block = used[cell]
                            if block.kind == "Tält":
                                self._mark_homeless(TENT_CAPACITY)
                            block.kind = kind
                            block.color = color
                            block.active = True
                            block.owner_id = owner_id
                            if cost_multiplier != 0:
                                total_cost += max(BLOCK_COST_MIN, self.block_cost) * cost_multiplier
                            continue
                        if cell in inactive:
                            block = inactive[cell]
                            block.kind = kind
                            block.color = color
                            block.active = True
                            block.owner_id = owner_id
                            if cost_multiplier == 0:
                                total_cost += self.block_restore_cost
                            else:
                                total_cost += min(
                                    self.block_restore_cost,
                                    int(max(BLOCK_COST_MIN, self.block_cost) * cost_multiplier * 0.5),
                                )
                            continue
                        cx, cy = cell
                        self.buildings.append(Building(cx, cy, color, kind, active=True, owner_id=owner_id))
                        if cost_multiplier != 0:
                            total_cost += max(BLOCK_COST_MIN, self.block_cost) * cost_multiplier
                    return cells, total_cost
        return [], 0

    def _find_farm_blocks(self):
        used = {(b.x, b.y): b for b in self.buildings if b.active}
        inactive = {(b.x, b.y): b for b in self.buildings if not b.active}
        candidates = []
        for x in range(2, self.grid_size - 3):
            for y in range(2, self.grid_size - 3):
                cells = [(x, y), (x + 1, y), (x, y + 1), (x + 1, y + 1)]
                if any(c in used and used[c].kind not in ("Tält",) for c in cells):
                    continue
                if any(c in inactive or c in used for c in cells):
                    pass
                adj = False
                for cx, cy in cells:
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nx, ny = cx + dx, cy + dy
                        b = used.get((nx, ny))
                        if b and b.kind in ("Tält", "Bostad"):
                            adj = True
                            break
                    if adj:
                        break
                if adj:
                    candidates.append(cells)
        random.shuffle(candidates)
        return candidates, used, inactive

    def _claim_farm_blocks(self, owner_id):
        candidates, used, inactive = self._find_farm_blocks()
        if not candidates:
            return [], 0
        cells = candidates[0]
        total_cost = 0
        for cell in cells:
            if cell in used:
                block = used[cell]
                if block.kind == "Tält":
                    self._mark_homeless(TENT_CAPACITY)
                block.kind = "Jordbruk"
                block.color = WORKPLACE_RULES["Jordbruk"]["color"]
                block.active = True
                block.owner_id = owner_id
                continue
            if cell in inactive:
                block = inactive[cell]
                block.kind = "Jordbruk"
                block.color = WORKPLACE_RULES["Jordbruk"]["color"]
                block.active = True
                block.owner_id = owner_id
                total_cost += self.block_restore_cost
                continue
            x, y = cell
            self.buildings.append(Building(x, y, WORKPLACE_RULES["Jordbruk"]["color"], "Jordbruk", True, owner_id))
        return cells, total_cost

    def _adjacent_free_block(self, blocks):
        used = {(b.x, b.y) for b in self.buildings if b.active}
        inactive = {(b.x, b.y): b for b in self.buildings if not b.active}
        for x, y in blocks:
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if nx < 2 or ny < 2 or nx >= self.grid_size - 2 or ny >= self.grid_size - 2:
                    continue
                if (nx, ny) in used:
                    continue
                if (nx, ny) in inactive:
                    return (nx, ny), inactive[(nx, ny)]
                return (nx, ny), None
        return None, None

    def _expand_workplaces(self):
        for w in self.workplaces:
            if w.kind not in WORKPLACE_RULES or w.kind == "Jordbruk":
                continue
            if w.money < max(BLOCK_COST_MIN, self.block_cost):
                continue
            if random.random() > 0.05:
                continue
            target, inactive = self._adjacent_free_block(w.blocks)
            if not target:
                continue
            rules = WORKPLACE_RULES[w.kind]
            cost_multiplier = rules["block_cost_multiplier"]
            cost = max(BLOCK_COST_MIN, self.block_cost) * cost_multiplier
            if inactive is not None:
                cost = min(self.block_restore_cost, int(cost * 0.5))
                if w.money < cost:
                    continue
                inactive.kind = w.kind
                inactive.color = rules["color"]
                inactive.active = True
                inactive.owner_id = w.owner_id
            else:
                if w.money < cost:
                    continue
                x, y = target
                self.buildings.append(Building(x, y, rules["color"], w.kind, active=True, owner_id=w.owner_id))
            w.money -= cost
            self.money += cost
            w.blocks.append(target)

    def _maybe_upgrade_housing(self):
        for h in self.humans:
            if h.home_kind != "Tält":
                continue
            if h.drive == "tältliv":
                continue
            if h.money < max(BLOCK_COST_MIN, self.block_cost):
                continue
            if random.random() > 0.05:
                continue
            building, cost = self._claim_block("Bostad", "#4aa3ff", h.id, 1)
            if building is None:
                continue
            if h.money < cost:
                continue
            h.money -= cost
            self.money += cost
            h.home_kind = "Hydda"
            h.home_owner_id = h.id

    def _spawn_new_businesses(self):
        hungry_count = sum(1 for h in self.humans if h.hungry)
        for h in self.humans:
            if h.sick:
                continue
            if h.hungry and h.money >= self.food_price * 5:
                if self._create_workplace(h, "Mataffär"):
                    continue
            roll = random.random()
            base_chance = 0.08
            if h.drive == "företagare":
                base_chance = 0.16
            elif h.drive == "risk":
                base_chance = 0.13
            elif h.drive == "lantbruk":
                base_chance = 0.12
            elif h.drive == "status":
                base_chance = 0.09
            elif h.drive == "sparsam":
                base_chance = 0.04
            if hungry_count > 0:
                base_chance *= 1.5
            if h.job_id is not None and h.drive not in ("företagare", "risk", "lantbruk"):
                continue
            if roll > base_chance:
                continue
            if h.status_items >= WORKPLACE_RULES["Industri"]["status_req"]:
                kind = "Industri"
            elif h.status_items >= WORKPLACE_RULES["Service"]["status_req"]:
                kind = "Service"
            elif h.status_items >= WORKPLACE_RULES["Basjobb"]["status_req"]:
                kind = "Mataffär" if random.random() < 0.35 else "Basjobb"
            else:
                kind = "Jordbruk"
            if h.drive == "lantbruk":
                kind = "Jordbruk"
            if kind == "Jordbruk" and h.home_kind not in ("Tält", "Hydda"):
                continue
            self._create_workplace(h, kind)

    def _create_workplace(self, owner: Human, kind: str):
        rules = WORKPLACE_RULES[kind]
        if kind == "Jordbruk":
            blocks, total_cost = self._claim_farm_blocks(owner.id)
            if not blocks:
                return False
        elif kind == "Industri":
            blocks_needed = random.choice(rules["blocks_choices"])
        else:
            blocks_needed = random.randint(rules["blocks_min"], rules["blocks_max"])
        capacity = random.randint(rules["capacity_min"], rules["capacity_max"])
        if kind != "Jordbruk":
            blocks, total_cost = self._claim_blocks(
                kind, rules["color"], owner.id, rules["block_cost_multiplier"], blocks_needed
            )
            if not blocks:
                return False
        if total_cost > 0:
            if owner.money < total_cost:
                needed = total_cost - owner.money
                if not self._take_loan(owner, needed):
                    for b in self.buildings:
                        if (b.x, b.y) in blocks:
                            b.active = False
                            b.owner_id = None
                    return False
            owner.money -= total_cost
            self.money += total_cost
        workplace = Workplace(
            id=self.next_workplace_id,
            kind=kind,
            wage=rules["wage"],
            capacity=capacity,
            strain=rules["strain"],
            owner_id=owner.id,
            money=0,
            blocks=blocks,
        )
        self.next_workplace_id += 1
        if owner.money > 0:
            seed = min(owner.money, max(rules["wage"], rules["wage"] * max(1, capacity // 2)))
            owner.money -= seed
            workplace.money += seed
        self.workplaces.append(workplace)
        return True

    def _assign_jobs_and_pay_wages(self):
        for w in self.workplaces:
            w.employed = 0
        for h in self.humans:
            h.job_id = None
        humans_by_id = {h.id: h for h in self.humans}
        owners = {}
        for w in self.workplaces:
            if w.owner_id is None:
                continue
            owners.setdefault(w.owner_id, []).append(w)
        for h in self.humans:
            if h.id in owners and not h.sick:
                owned = owners[h.id]
                if len(owned) > 1:
                    owned = sorted(owned, key=lambda w: w.wage, reverse=True)
                w = owned[0]
                h.job_id = w.id
                w.employed += 1

        unemployed = [h for h in self.humans if h.job_id is None]
        remaining_workplaces = []
        remaining_caps = []
        for w in self.workplaces:
            remaining = max(0, w.capacity - w.employed)
            if remaining > 0:
                remaining_workplaces.append(w)
                remaining_caps.append(remaining)
        total_capacity = sum(remaining_caps)
        if total_capacity > 0 and unemployed:
            need = min(len(unemployed), total_capacity)
            slots = random.sample(range(total_capacity), need)
            job_slots = []
            if len(remaining_workplaces) == 1:
                job_slots = [remaining_workplaces[0]] * need
            else:
                cumulative = []
                running = 0
                for cap in remaining_caps:
                    running += cap
                    cumulative.append(running)
                for slot in slots:
                    idx = bisect_right(cumulative, slot)
                    job_slots.append(remaining_workplaces[idx])
            random.shuffle(job_slots)
            for h, w in zip(unemployed, job_slots):
                if h.sick:
                    continue
                h.job_id = w.id
                w.employed += 1

        employees_by_workplace = {}
        for h in self.humans:
            if h.job_id is None:
                continue
            employees_by_workplace.setdefault(h.job_id, []).append(h)

        for w in self.workplaces:
            if w.employed == 0:
                w.idle_months += 1
            else:
                w.idle_months = 0
            employees = employees_by_workplace.get(w.id, [])
            random.shuffle(employees)
            wages_paid = 0
            paid_count = 0
            for h in employees:
                wage = self._wage_for(h, w)
                if w.money < wage:
                    h.job_id = None
                    continue
                w.money -= wage
                h.money += wage
                wages_paid += wage
                paid_count += 1
            w.employed = paid_count
            if w.kind in ("Basjobb", "Service", "Industri"):
                w.money += wages_paid * 4
                owner = humans_by_id.get(w.owner_id)
                if owner and wages_paid > 0:
                    owner_share = max(10, int(wages_paid * 0.1))
                    w.money = max(0, w.money - owner_share)
                    owner.money += owner_share
            elif w.kind == "Mataffär":
                owner = humans_by_id.get(w.owner_id)
                if owner and wages_paid > 0:
                    owner_share = max(10, int(wages_paid * 0.1))
                    w.money = max(0, w.money - owner_share)
                    owner.money += owner_share
            else:
                pass

        self.unemployed = sum(1 for h in self.humans if h.job_id is None)

    def _wage_for(self, human: Human, workplace: Workplace):
        base = workplace.wage
        bonus = min(300, human.status_items * 2)
        wage = base + bonus
        return max(20, min(1000, wage))

    def _apply_food(self):
        for h in self.humans:
            h.hungry = False
            if h.food >= FOOD_MONTHLY_NEED:
                h.food -= FOOD_MONTHLY_NEED
            else:
                h.food = 0
                h.hungry = True

        humans_by_id = {h.id: h for h in self.humans}
        farms = [w for w in self.workplaces if w.kind == "Jordbruk"]
        stores = [w for w in self.workplaces if w.kind == "Mataffär"]
        total_farm_employed = sum(w.employed for w in farms)
        food_supply = total_farm_employed * FOOD_FARM_PER_EMPLOYEE_MONTH
        self.last_food_supply = food_supply
        sold = 0

        for store in stores:
            if food_supply <= 0:
                break
            capacity = max(0, store.capacity - store.stock_food)
            if capacity <= 0:
                continue
            buy_amount = min(capacity, food_supply)
            cost = max(1, int(buy_amount * STORE_BUY_PRICE + 0.5))
            if store.money < cost:
                owner = humans_by_id.get(store.owner_id)
                if owner is not None and owner.money > 0:
                    top_up = min(owner.money, cost - store.money)
                    owner.money -= top_up
                    store.money += top_up
            if store.money < cost:
                buy_amount = min(buy_amount, int(store.money // STORE_BUY_PRICE))
                cost = max(1, int(buy_amount * STORE_BUY_PRICE + 0.5))
            if buy_amount <= 0:
                continue
            store.money -= cost
            store.stock_food += buy_amount
            food_supply -= buy_amount
            if farms and cost > 0 and total_farm_employed > 0:
                for w in farms:
                    share = w.employed / total_farm_employed
                    w.money += int(cost * share)

        for store in stores:
            if store.stock_food >= store.capacity:
                continue
            needed = store.capacity - store.stock_food
            cost = max(1, int(needed * STORE_BUY_PRICE + 0.5))
            if store.money < cost:
                owner = humans_by_id.get(store.owner_id)
                if owner is not None and owner.money > 0:
                    top_up = min(owner.money, cost - store.money)
                    owner.money -= top_up
                    store.money += top_up
            if store.money < cost:
                affordable = int(store.money // STORE_BUY_PRICE)
                if affordable <= 0:
                    continue
                needed = affordable
                cost = max(1, int(needed * STORE_BUY_PRICE + 0.5))
            store.money -= cost
            store.stock_food += needed

        for h in self.humans:
            if h.food >= FOOD_BUY_THRESHOLD:
                continue
            if h.money < self.food_price:
                if self._take_loan(h, self.food_price * 5):
                    h.money += self.food_price * 5
                else:
                    continue
            buy_amount = min(10, FOOD_MAX - h.food)
            if buy_amount <= 0:
                continue
            purchase = buy_amount
            if food_supply > 0:
                take = min(purchase, food_supply)
                cost = take * self.food_price
                if h.money < cost:
                    take = h.money // self.food_price
                    cost = take * self.food_price
                if take > 0:
                    h.money -= cost
                    h.food += take
                    food_supply -= take
                    sold += take
                    purchase -= take
                    if farms and cost > 0 and total_farm_employed > 0:
                        for w in farms:
                            share = w.employed / total_farm_employed
                            w.money += int(cost * share)
            for store in stores:
                if purchase <= 0:
                    break
                if store.stock_food <= 0:
                    continue
                take = min(purchase, store.stock_food)
                cost = take * self.food_price
                if h.money < cost:
                    take = h.money // self.food_price
                    cost = take * self.food_price
                if take <= 0:
                    continue
                h.money -= cost
                h.food += take
                store.stock_food -= take
                store.money += cost
                sold += take
                purchase -= take

        self.last_food_sold = sold

        for h in self.humans:
            if h.food == 0 and h.sick:
                h.food = min(FOOD_MAX, h.food + 10)

        return sum(1 for h in self.humans if h.hungry)

    def _apply_status_purchases(self):
        for h in self.humans:
            if h.home_kind == "Tält":
                continue
            if h.hungry:
                continue
            if h.status_items >= 100:
                continue
            if h.money < 10:
                continue
            chance = 0.2
            if h.drive == "status":
                chance = 0.5
            elif h.drive == "sparsam":
                chance = 0.05
            elif h.drive == "tältliv":
                chance = 0.1
            if random.random() > chance:
                continue
            h.money -= 10
            h.status_items += 1

    def _apply_unemployment_support(self):
        if not self.services.get("A-kassa", False):
            return
        level = self.service_funding.get("A-kassa", 0) / 100.0
        if level <= 0:
            return
        base_wage = WORKPLACE_RULES["Basjobb"]["wage"]
        payout = int(base_wage * level)
        if payout <= 0:
            return
        for h in self.humans:
            if h.job_id is None:
                h.money += payout

    def _apply_bankruptcy(self):
        season = self.season()
        block_value = max(BLOCK_COST_MIN, self.block_cost)
        for h in self.humans:
            if h.money > 0:
                continue
            total_sale = 0
            for b in self.buildings:
                if b.kind != "Bostad" or b.owner_id != h.id:
                    continue
                total_sale += max(1, int(block_value * 0.5))
                b.active = False
                b.owner_id = None
                b.kind = "Övergiven"
                b.color = "#6b6f7a"
            if total_sale > 0:
                h.money += total_sale
            h.job_id = None
            if season != "Vinter":
                h.home_kind = "Tält" if random.random() < 0.7 else "Bostadslös"
            else:
                h.home_kind = "Bostadslös"
            h.home_owner_id = None
            h.homeless_months = 0

    def _clamp_balances(self):
        for h in self.humans:
            if h.money < 0:
                h.money = 0
        for w in self.workplaces:
            if w.money < 0:
                w.money = 0

    def _update_health(self, hungry):
        season = self.season()
        workplace_by_id = {w.id: w for w in self.workplaces}
        for h in self.humans:
            if h.home_kind == "Bostadslös":
                h.homeless_months += 1
                if h.homeless_months >= 12:
                    h.status_items = 0
            energy_loss = 1
            if h.hungry:
                energy_loss += 3
            if season == "Vinter":
                energy_loss += 1
            if h.job_id is not None:
                job = workplace_by_id.get(h.job_id)
                if job:
                    energy_loss += max(1, job.strain - 1)
            status_buffer = min(3, h.status_items // 10)
            energy_loss = max(0, energy_loss - status_buffer)
            energy_gain = 0
            if not h.hungry:
                energy_gain += 2
            if h.energy < 40 and not h.hungry:
                energy_gain += 1
            h.energy = min(100, max(0, h.energy - energy_loss + energy_gain))

            if h.energy < 30:
                h.health = max(0, h.health - 2)
            elif h.energy > 60 and not h.hungry:
                h.health = min(100, h.health + 1)
            if h.status_items >= 5 and h.health < 100:
                h.health = min(100, h.health + 1)

            if self.services.get("Sjukvård", False) and self.service_funding.get("Sjukvård", 0) >= 50:
                if h.health < 85:
                    h.health = min(100, h.health + 2)

            if h.health >= 60 and h.energy >= 40:
                h.sick = False
            else:
                h.sick = h.health < 40 or h.energy < 20
        return sum(1 for h in self.humans if h.sick)

    def _update_building_activity(self):
        buildings_by_owner_kind = {}
        for b in self.buildings:
            key = (b.owner_id, b.kind)
            buildings_by_owner_kind.setdefault(key, []).append(b)
        for w in self.workplaces:
            key = (w.owner_id, w.kind)
            targets = buildings_by_owner_kind.get(key, [])
            if not targets:
                continue
            active = w.employed > 0
            for b in targets:
                b.active = active

    def _cleanup_abandoned_workplaces(self):
        buildings_by_coord = {(b.x, b.y): b for b in self.buildings}
        active_industry = [b for b in self.buildings if b.kind == "Industri" and b.active]
        active = []
        for w in self.workplaces:
            if w.kind == "Jordbruk":
                for b in active_industry:
                    for fx, fy in w.blocks:
                        if abs(b.x - fx) + abs(b.y - fy) <= 4:
                            w.idle_months = 6
                            break
                    if w.idle_months >= 6:
                        break
            if w.idle_months < 6:
                active.append(w)
                continue
            for coord in w.blocks:
                b = buildings_by_coord.get(coord)
                if b is None:
                    continue
                b.active = False
                b.owner_id = None
                b.kind = "Övergiven"
                b.color = "#6b6f7a"
        self.workplaces = active

    def _bank_base_rate(self):
        rate = 0.01 + (1 - self.stability / 100) * 0.09
        rate = max(0.01, min(0.10, rate))
        self.last_bank_rate = rate
        return rate

    def _bank_deposits(self):
        deposits = sum(h.money for h in self.humans) + sum(w.money for w in self.workplaces)
        return max(0, deposits)

    def _bank_total_loans(self):
        loans = sum(h.loan_balance for h in self.humans) + sum(w.loan_balance for w in self.workplaces)
        return max(0, loans)

    def _take_loan(self, target, amount):
        if amount <= 0:
            return False
        deposits = self._bank_deposits()
        max_loans = deposits * 0.5
        if self._bank_total_loans() + amount > max_loans:
            return False
        limit = 0
        if isinstance(target, Human):
            limit = target.money * 10
        elif isinstance(target, Workplace):
            limit = max(1, target.money) * 10
        if amount > max(limit, 0):
            return False
        target.loan_balance += amount
        return True

    def _apply_bank_interest_and_loans(self):
        if self.month % 12 != 0:
            return
        buildings_by_coord = {(b.x, b.y): b for b in self.buildings}
        base_rate = self._bank_base_rate()
        for h in self.humans:
            if h.money > 0:
                h.money += int(h.money * base_rate)
        for h in self.humans:
            if h.loan_balance <= 0:
                continue
            rate = max(0.0, base_rate * 2 - (h.status_items * 0.0001))
            interest = int(h.loan_balance * rate)
            amort = max(1, int(h.loan_balance * 0.1))
            payment = interest + amort
            if h.money >= payment:
                h.money -= payment
                h.loan_balance = max(0, h.loan_balance - amort)
                h.loan_years_missed = 0
            else:
                h.loan_years_missed += 1
                h.health = max(0, h.health - 5)
        survivors = []
        for w in self.workplaces:
            if w.loan_balance <= 0:
                survivors.append(w)
                continue
            rate = base_rate * 2
            interest = int(w.loan_balance * rate)
            amort = max(1, int(w.loan_balance * 0.1))
            payment = interest + amort
            if w.money >= payment:
                w.money -= payment
                w.loan_balance = max(0, w.loan_balance - amort)
                w.loan_years_missed = 0
                survivors.append(w)
            else:
                w.loan_years_missed += 1
                if w.loan_years_missed >= 3:
                    for coord in w.blocks:
                        b = buildings_by_coord.get(coord)
                        if b is None:
                            continue
                        b.active = False
                        b.owner_id = None
                else:
                    survivors.append(w)
        self.workplaces = survivors

        for h in self.humans:
            if h.loan_years_missed >= 3:
                h.job_id = None
                h.status_items = 0
                h.loan_balance = 0
                h.loan_years_missed = 0
                for w in list(self.workplaces):
                    if w.owner_id == h.id:
                        for coord in w.blocks:
                            b = buildings_by_coord.get(coord)
                            if b is None:
                                continue
                            b.active = False
                            b.owner_id = None
                        self.workplaces.remove(w)

    def _calc_food_status(self):
        if self.population <= 0:
            return 1.0
        return max(0.0, 1.0 - (self.last_hungry / self.population))

    def to_dict(self):
        return {
            "name": self.name,
            "size_label": self.size_label,
            "region": self.region,
            "money": self.money,
            "population": self.population,
            "stability": self.stability,
            "expenses": self.expenses,
            "tax_rate": self.tax_rate,
            "services": self.services,
            "service_costs": self.service_costs,
            "service_funding": self.service_funding,
            "budget_allocations": self.budget_allocations,
            "block_cost": self.block_cost,
            "block_restore_cost": self.block_restore_cost,
            "food_price": self.food_price,
            "unemployed": self.unemployed,
            "month": self.month,
            "history": self.history,
            "history_year": self.history_year,
            "buildings": [b.__dict__ for b in self.buildings],
            "last_revenue": self.last_revenue,
            "last_expenses": self.last_expenses,
            "last_hungry": self.last_hungry,
            "last_sick": self.last_sick,
            "last_unemployed": self.last_unemployed,
            "last_food_supply": self.last_food_supply,
            "last_food_sold": self.last_food_sold,
            "last_bank_rate": self.last_bank_rate,
            "year_revenue": self.year_revenue,
            "year_expenses": self.year_expenses,
            "last_year_revenue": self.last_year_revenue,
            "last_year_expenses": self.last_year_expenses,
            "humans": [h.__dict__ for h in self.humans],
            "workplaces": [w.__dict__ for w in self.workplaces],
            "next_human_id": self.next_human_id,
            "next_workplace_id": self.next_workplace_id,
        }

    @staticmethod
    def from_dict(data):
        config = WorldConfig(
            name=data.get("name", "Ny värld"),
            size_label=data.get("size_label", "Medium"),
            region=data.get("region", REGIONS[1]),
        )
        world = World(config)
        world.money = data.get("money", data.get("resources", world.money))
        world.population = data.get("population", world.population)
        world.stability = data.get("stability", world.stability)
        world.expenses = data.get("expenses", world.expenses)
        world.tax_rate = data.get("tax_rate", world.tax_rate)
        world.services = data.get("services", world.services)
        world.service_costs = data.get("service_costs", world.service_costs)
        world.service_funding = data.get("service_funding", world.service_funding)
        world.budget_allocations = data.get("budget_allocations", world.budget_allocations)
        world.block_cost = data.get("block_cost", world.block_cost)
        world.block_restore_cost = data.get("block_restore_cost", world.block_restore_cost)
        world.food_price = data.get("food_price", world.food_price)
        world.unemployed = data.get("unemployed", world.unemployed)
        world.last_revenue = data.get("last_revenue", world.last_revenue)
        world.last_expenses = data.get("last_expenses", world.last_expenses)
        world.last_hungry = data.get("last_hungry", world.last_hungry)
        world.last_sick = data.get("last_sick", world.last_sick)
        world.last_unemployed = data.get("last_unemployed", world.last_unemployed)
        world.last_food_supply = data.get("last_food_supply", world.last_food_supply)
        world.last_food_sold = data.get("last_food_sold", world.last_food_sold)
        world.last_bank_rate = data.get("last_bank_rate", world.last_bank_rate)
        world.year_revenue = data.get("year_revenue", world.year_revenue)
        world.year_expenses = data.get("year_expenses", world.year_expenses)
        world.last_year_revenue = data.get("last_year_revenue", world.last_year_revenue)
        world.last_year_expenses = data.get("last_year_expenses", world.last_year_expenses)
        humans = []
        for item in data.get("humans", world.humans):
            if isinstance(item, Human):
                humans.append(item)
                continue
            if "name" not in item:
                item["name"] = world._random_name()
            if "age" not in item:
                item["age"] = random.randint(18, 35)
            if "drive" not in item:
                item["drive"] = world._random_drive()
            humans.append(Human(**item))
        world.humans = humans
        world.workplaces = [Workplace(**item) for item in data.get("workplaces", world.workplaces)]
        world.next_human_id = data.get("next_human_id", world.next_human_id)
        world.next_workplace_id = data.get("next_workplace_id", world.next_workplace_id)
        world.month = data.get("month", world.month)
        world.history = data.get("history", world.history)
        world.history_year = data.get("history_year", world.history_year)
        buildings = []
        for item in data.get("buildings", []):
            buildings.append(Building(**item))
        if buildings:
            world.buildings = buildings
        return world
