from __future__ import annotations

import random

from models import Building, FoodStore, Human, Workplace, WorldConfig

SIZE_MAP = {
    "Liten": 30,
    "Medium": 60,
    "Stor": 100,
}

REGIONS = ["Norra", "Medel", "Syd"]
SEASONS = ["Vinter", "Vår", "Sommar", "Höst"]

class World:
    def __init__(self, config: WorldConfig):
        self.name = config.name
        self.size_label = config.size_label
        self.region = config.region
        self.grid_size = SIZE_MAP[config.size_label]
        self.buildings = []
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
        self.housing_units = {
            "Tält": 10,
            "Hydda": 4,
            "Lägenhet": 2,
            "Villa": 0,
        }
        self.housing_capacity = {
            "Tält": 1,
            "Hydda": 2,
            "Lägenhet": 4,
            "Villa": 5,
        }
        self.housing_cost = {
            "Tält": 0,
            "Hydda": 3,
            "Lägenhet": 6,
            "Villa": 9,
        }
        self.housing_allowed_seasons = {
            "Tält": {"Vår", "Sommar", "Höst"},
            "Hydda": set(SEASONS),
            "Lägenhet": set(SEASONS),
            "Villa": set(SEASONS),
        }
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
        self.jobs = {
            "Basjobb": 8,
            "Service": 4,
            "Industri": 2,
        }
        self.has_megafactory = False
        self.immigration_buffer = 0
        self.next_human_id = 1
        self.next_workplace_id = 1
        self.next_store_id = 1
        self.humans: list[Human] = []
        self.workplaces: list[Workplace] = []
        self.food_stores: list[FoodStore] = []
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
        self.last_homeless = 0
        self.last_unpaid_rent = 0
        self.last_sick = 0
        self.year_revenue = 0
        self.year_expenses = 0
        self.last_year_revenue = 0
        self.last_year_expenses = 0
        self._seed_world()
        self._seed_population()
        self._seed_economy_buildings()
        self._record_history()

    def _seed_world(self):
        random.seed(42)
        center = self.grid_size // 2
        size = 6
        start = center - (size // 2)
        for dx in range(size):
            for dy in range(size):
                self.buildings.append(Building(start + dx, start + dy, "#d9534f", "Torg"))
        self._seed_zone(
            x_start=2,
            x_end=center - 6,
            y_start=center + 6,
            y_end=self.grid_size - 3,
            density=0.08,
            color="#4aa3ff",
            kind="Bostad",
        )
        self._seed_zone(
            x_start=center + 6,
            x_end=self.grid_size - 3,
            y_start=2,
            y_end=center - 6,
            density=0.1,
            color="#f0b34f",
            kind="Industri",
        )

    def _seed_zone(self, x_start, x_end, y_start, y_end, density, color, kind):
        for x in range(x_start, x_end):
            for y in range(y_start, y_end):
                if random.random() < density:
                    self.buildings.append(Building(x, y, color, kind))

    def _seed_population(self):
        for _ in range(self.population):
            self.humans.append(Human(id=self.next_human_id, money=10))
            self.next_human_id += 1

    def _seed_economy_buildings(self):
        self._add_workplace(kind="Basjobb", wage=6, capacity=6, strain=1)
        self._add_workplace(kind="Service", wage=7, capacity=4, strain=2)
        self._add_workplace(kind="Industri", wage=9, capacity=3, strain=3)
        self._add_food_store(kind="Mataffär", price=2, capacity=8)

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
        self._update_jobs()
        self._apply_jobs()
        self._apply_wages()
        hungry = self._apply_food()
        self._update_building_activity()
        homeless, unpaid_rent = self._apply_housing()
        sick = self._update_health(hungry, homeless, unpaid_rent)

        season = self.season()
        service_cost = self._calc_service_cost(sick)
        base_expenses, seasonal_expenses, total_expenses = self._calc_expenses(season, service_cost)
        revenue, tax_month = self._calc_revenue()
        net = self._apply_budget(revenue, total_expenses, base_expenses, service_cost, seasonal_expenses, tax_month)

        self.last_hungry = hungry
        self.last_homeless = homeless
        self.last_unpaid_rent = unpaid_rent
        self.last_sick = sick

        self._update_stability(season, net, hungry, homeless, unpaid_rent, sick, tax_month)
        self._update_population(season, net, hungry, homeless, unpaid_rent)
        self._update_buildings()
        self._sync_workforce()

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

    def _update_stability(self, season, net, hungry, homeless, unpaid_rent, sick, tax_month):
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
        if net < 0 and tax_month:
            stability_drift -= 1
        if not self._has_winter_safe_housing() and season == "Vinter":
            stability_drift -= 6
        if self.unemployed > max(2, self.population // 3):
            stability_drift -= 2
        if hungry > 0:
            stability_drift -= min(5, hungry)
        if homeless > 0:
            stability_drift -= min(6, homeless)
        if unpaid_rent > 0:
            stability_drift -= min(4, unpaid_rent // 2)
        if sick > 0:
            stability_drift -= min(4, sick // 3)
        if self.stability >= 70 and net >= 0:
            stability_drift += 1
        self.stability = max(0, min(100, self.stability + stability_drift))

    def _update_population(self, season, net, hungry, homeless, unpaid_rent):
        pop_change = 0
        if self.stability >= 70 and net >= 0:
            pop_change += 1
        if self.money >= 20 and self._has_housing_capacity(season):
            pop_change += 1
        if self.stability >= 55 and self._has_housing_capacity(season):
            pop_change += 1
        if self.stability <= 35 or self.money == 0:
            pop_change -= 1
        if self.stability <= 25:
            pop_change -= 1
        if not self._has_housing_capacity(season):
            pop_change -= 1
        if season == "Vinter" and not self._has_winter_safe_housing():
            pop_change -= 2
        immigrants = self._immigration_flow(season)
        if self.population <= 2 and self.money >= 10 and self._has_housing_capacity(season):
            immigrants += 1
        if self.population <= 3 and self.stability >= 40 and self._has_housing_capacity(season):
            immigrants += 2
        if hungry == 0 and homeless == 0 and unpaid_rent == 0:
            pop_change += 1
        if self.population <= 5 and pop_change < 0:
            pop_change += 1
        self.population = max(0, self.population + pop_change + immigrants)

    def _apply_jobs(self):
        available_jobs = sum(self.jobs.values())
        if self.population == 0:
            self.unemployed = 0
            return
        employed = min(self.population, available_jobs)
        self.unemployed = max(0, self.population - employed)

    def _employed_count(self):
        return max(0, self.population - self.unemployed)

    def _sync_workforce(self):
        available_jobs = sum(self.jobs.values())
        if self.population == 0:
            self.unemployed = 0
            return
        employed = min(self.population, available_jobs)
        self.unemployed = max(0, self.population - employed)

    def _sync_population(self):
        if self.population > len(self.humans):
            for _ in range(self.population - len(self.humans)):
                self.humans.append(Human(id=self.next_human_id, money=8))
                self.next_human_id += 1
        elif self.population < len(self.humans):
            self.humans = self.humans[: self.population]
        self.housing_units["Tält"] = max(self.population, self.housing_units.get("Tält", 0))

    def _update_jobs(self):
        if self.population == 0:
            return
        if not self.has_megafactory and self.population >= 15:
            self._add_workplace(kind="Industri", wage=9, capacity=1000, strain=3)
            self.jobs["Industri"] += 1000
            self.has_megafactory = True
            for _ in range(3):
                self._spawn_building(kind="Industri", color="#f0b34f")
        growth_factor = 1.0
        if self.tax_rate <= 0.1:
            growth_factor *= 1.15
        if self.month >= 6:
            if (
                not self.services.get("Polis", False)
                or not self.services.get("Brandkår", False)
                or self.service_funding.get("Polis", 0) < 40
                or self.service_funding.get("Brandkår", 0) < 40
            ):
                growth_factor = 0.7
        if self.stability < 45:
            growth_factor *= 0.7
        elif self.stability > 75:
            growth_factor *= 1.1
        target_jobs = max(6, int(self.population * 1.25 * growth_factor))
        current_jobs = sum(self.jobs.values())
        if current_jobs >= target_jobs:
            return
        needed = target_jobs - current_jobs
        base_add = max(1, needed // 2)
        service_add = max(0, needed // 3)
        industry_add = max(0, needed - base_add - service_add)
        self.jobs["Basjobb"] += base_add
        self.jobs["Service"] += service_add
        self.jobs["Industri"] += industry_add
        if base_add > 0:
            self._add_workplace(kind="Basjobb", wage=6, capacity=base_add, strain=1)
            for _ in range(max(1, base_add // 3)):
                self._spawn_building(kind="Basjobb", color="#7cc4ff")
        if service_add > 0:
            self._add_workplace(kind="Service", wage=7, capacity=service_add, strain=2)
            for _ in range(max(1, service_add // 2)):
                self._spawn_building(kind="Service", color="#ffd166")
        if industry_add > 0:
            self._add_workplace(kind="Industri", wage=9, capacity=industry_add, strain=3)
            for _ in range(max(1, industry_add // 2)):
                self._spawn_building(kind="Industri", color="#f0b34f")
        if sum(store.capacity for store in self.food_stores) < max(12, int(self.population * 1.2)):
            self._add_food_store(kind="Mataffär", price=2, capacity=8)
            self._spawn_building(kind="Mataffär", color="#6ed26a")

    def _apply_wages(self):
        for w in self.workplaces:
            w.employed = 0
        for h in self.humans:
            h.job_id = None
        available = []
        for w in self.workplaces:
            available.extend([w] * w.capacity)
        random.shuffle(available)
        for h, w in zip(self.humans, available):
            if h.sick:
                continue
            h.job_id = w.id
            h.money += w.wage
            w.employed += 1

    def _apply_food(self):
        for store in self.food_stores:
            store.sold = 0
        hungry = 0
        price = min((s.price for s in self.food_stores), default=3)
        available_food = sum(store.capacity for store in self.food_stores)
        for h in self.humans:
            if available_food <= 0:
                h.hungry = True
                hungry += 1
                continue
            if h.money >= price:
                h.money -= price
                available_food -= 1
                self._consume_store_unit()
                h.hungry = False
            else:
                h.hungry = True
                hungry += 1
        if hungry > 0 or available_food < self.population:
            self._add_food_store(kind="Mataffär", price=2, capacity=8)
            self._spawn_building(kind="Mataffär", color="#6ed26a")
        return hungry

    def _consume_store_unit(self):
        for store in self.food_stores:
            if store.sold < store.capacity:
                store.sold += 1
                return

    def _update_health(self, hungry, homeless, unpaid_rent):
        season = self.season()
        homeless_ratio = homeless / self.population if self.population > 0 else 0
        unpaid_ratio = unpaid_rent / self.population if self.population > 0 else 0
        for h in self.humans:
            energy_loss = 1
            if h.hungry:
                energy_loss += 3
            energy_loss += int(2 * homeless_ratio + 0.5)
            energy_loss += int(1 * unpaid_ratio + 0.5)
            if season == "Vinter":
                energy_loss += 1
            if h.job_id is not None:
                job = next((w for w in self.workplaces if w.id == h.job_id), None)
                if job:
                    energy_loss += max(1, job.strain - 1)
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

            if self.services.get("Sjukvård", False) and self.service_funding.get("Sjukvård", 0) >= 50:
                if h.health < 85:
                    h.health = min(100, h.health + 2)

            if h.health >= 60 and h.energy >= 40:
                h.sick = False
            else:
                h.sick = h.health < 40 or h.energy < 20
        return sum(1 for h in self.humans if h.sick)

    def _update_building_activity(self):
        kind_to_buildings = {}
        for b in self.buildings:
            kind_to_buildings.setdefault(b.kind, []).append(b)

        workplace_kinds = {
            "Basjobb": self.jobs.get("Basjobb", 0),
            "Service": self.jobs.get("Service", 0),
            "Industri": self.jobs.get("Industri", 0),
        }
        for kind, total_jobs in workplace_kinds.items():
            buildings = kind_to_buildings.get(kind, [])
            if not buildings:
                continue
            employed = 0
            for w in self.workplaces:
                if w.kind == kind:
                    employed += w.employed
            target_active = max(0, min(len(buildings), employed // 2))
            self._set_active_buildings(buildings, target_active)

        store_buildings = kind_to_buildings.get("Mataffär", [])
        if store_buildings:
            sold = sum(s.sold for s in self.food_stores)
            target_active = max(0, min(len(store_buildings), sold // 4))
            self._set_active_buildings(store_buildings, target_active)

    def _set_active_buildings(self, buildings, target_active):
        active = [b for b in buildings if b.active]
        if len(active) > target_active:
            random.shuffle(active)
            for b in active[target_active:]:
                b.active = False
        elif len(active) < target_active:
            inactive = [b for b in buildings if not b.active]
            random.shuffle(inactive)
            for b in inactive[: target_active - len(active)]:
                b.active = True

    def _apply_housing(self):
        season = self.season()
        slots = []
        for name, units in self.housing_units.items():
            if season not in self.housing_allowed_seasons.get(name, set()):
                continue
            cap = self.housing_capacity.get(name, 0)
            cost = self.housing_cost.get(name, 0)
            slots.extend([cost] * (units * cap))
        slots.sort()
        homeless = 0
        unpaid = 0
        for h in self.humans:
            if not slots:
                homeless += 1
                continue
            cost = slots.pop(0)
            if cost == 0:
                continue
            if h.money >= cost:
                h.money -= cost
            else:
                unpaid += 1
        return homeless, unpaid

    def _immigration_flow(self, season):
        if not self._has_housing_capacity(season):
            return 0
        score = 0
        if self.stability >= 60:
            score += 1
        if self.stability >= 75:
            score += 1
        if self.stability <= 35:
            score -= 1
        if self.money >= 30:
            score += 1
        if self._employed_count() < sum(self.jobs.values()):
            score += 1
        if self.tax_rate <= 0.1:
            score += 1
        if season == "Vinter" and self.region == "Norra":
            score -= 1
        return max(0, score // 2)

    def _update_buildings(self):
        total_capacity = sum(
            units * self.housing_capacity.get(name, 0)
            for name, units in self.housing_units.items()
        )
        permanent_capacity = sum(
            units * self.housing_capacity.get(name, 0)
            for name, units in self.housing_units.items()
            if "Vinter" in self.housing_allowed_seasons.get(name, set())
        )
        target_capacity = max(self.population + 2, int(self.population * 1.1))
        if self.population <= total_capacity:
            self._update_abandoned_buildings()
            if permanent_capacity < target_capacity:
                self.housing_units["Hydda"] += 1
                self._spawn_building(kind="Bostad", color="#4aa3ff")
            return
        needed = max(1, (self.population - total_capacity + 2) // 2)
        self.housing_units["Hydda"] += needed
        for _ in range(needed):
            self._spawn_building(kind="Bostad", color="#4aa3ff")
        self._update_abandoned_buildings()

    def _update_abandoned_buildings(self):
        housing_buildings = [b for b in self.buildings if b.kind == "Bostad"]
        if not housing_buildings:
            return
        target_active = max(1, min(len(housing_buildings), (self.population // 2) + 1))
        active_buildings = [b for b in housing_buildings if b.active]
        if len(active_buildings) > target_active:
            random.shuffle(active_buildings)
            for b in active_buildings[target_active:]:
                b.active = False
        elif len(active_buildings) < target_active:
            inactive = [b for b in housing_buildings if not b.active]
            random.shuffle(inactive)
            for b in inactive[: target_active - len(active_buildings)]:
                b.active = True

    def _spawn_building(self, kind, color):
        for b in self.buildings:
            if b.kind == kind and not b.active:
                b.active = True
                return
        center = self.grid_size // 2
        for _ in range(50):
            x = random.randint(2, self.grid_size - 3)
            y = random.randint(2, self.grid_size - 3)
            if abs(x - center) <= 3 and abs(y - center) <= 3:
                continue
            if any(b.x == x and b.y == y for b in self.buildings):
                continue
            self.buildings.append(Building(x, y, color, kind))
            return

    def _add_workplace(self, kind, wage, capacity, strain=1):
        self.workplaces.append(
            Workplace(id=self.next_workplace_id, kind=kind, wage=wage, capacity=capacity, strain=strain)
        )
        self.next_workplace_id += 1

    def _add_food_store(self, kind, price, capacity):
        self.food_stores.append(
            FoodStore(id=self.next_store_id, kind=kind, price=price, capacity=capacity)
        )
        self.next_store_id += 1

    def _housing_monthly_cost(self):
        return sum(
            units * self.housing_cost[name]
            for name, units in self.housing_units.items()
        )

    def _has_housing_capacity(self, season):
        capacity = 0
        for name, units in self.housing_units.items():
            if season in self.housing_allowed_seasons.get(name, set()):
                capacity += units * self.housing_capacity.get(name, 0)
        return capacity >= self.population

    def _has_winter_safe_housing(self):
        capacity = 0
        for name, units in self.housing_units.items():
            if "Vinter" in self.housing_allowed_seasons.get(name, set()):
                capacity += units * self.housing_capacity.get(name, 0)
        return capacity >= self.population

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
            "housing_units": self.housing_units,
            "housing_capacity": self.housing_capacity,
            "housing_cost": self.housing_cost,
            "housing_allowed_seasons": {
                name: sorted(list(seasons))
                for name, seasons in self.housing_allowed_seasons.items()
            },
            "jobs": self.jobs,
            "unemployed": self.unemployed,
            "immigration_buffer": self.immigration_buffer,
            "has_megafactory": self.has_megafactory,
            "month": self.month,
            "history": self.history,
            "history_year": self.history_year,
            "buildings": [b.__dict__ for b in self.buildings],
            "last_revenue": self.last_revenue,
            "last_expenses": self.last_expenses,
            "last_hungry": self.last_hungry,
            "last_homeless": self.last_homeless,
            "last_unpaid_rent": self.last_unpaid_rent,
            "last_sick": self.last_sick,
            "year_revenue": self.year_revenue,
            "year_expenses": self.year_expenses,
            "last_year_revenue": self.last_year_revenue,
            "last_year_expenses": self.last_year_expenses,
            "humans": [h.__dict__ for h in self.humans],
            "workplaces": [w.__dict__ for w in self.workplaces],
            "food_stores": [s.__dict__ for s in self.food_stores],
            "next_human_id": self.next_human_id,
            "next_workplace_id": self.next_workplace_id,
            "next_store_id": self.next_store_id,
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
        world.housing_units = data.get("housing_units", world.housing_units)
        world.housing_capacity = data.get("housing_capacity", world.housing_capacity)
        world.housing_cost = data.get("housing_cost", world.housing_cost)
        allowed = data.get("housing_allowed_seasons")
        if allowed:
            world.housing_allowed_seasons = {
                name: set(seasons) for name, seasons in allowed.items()
            }
        world.jobs = data.get("jobs", world.jobs)
        world.unemployed = data.get("unemployed", world.unemployed)
        world.immigration_buffer = data.get("immigration_buffer", world.immigration_buffer)
        world.has_megafactory = data.get("has_megafactory", world.has_megafactory)
        world.last_revenue = data.get("last_revenue", world.last_revenue)
        world.last_expenses = data.get("last_expenses", world.last_expenses)
        world.last_hungry = data.get("last_hungry", world.last_hungry)
        world.last_homeless = data.get("last_homeless", world.last_homeless)
        world.last_unpaid_rent = data.get("last_unpaid_rent", world.last_unpaid_rent)
        world.last_sick = data.get("last_sick", world.last_sick)
        world.year_revenue = data.get("year_revenue", world.year_revenue)
        world.year_expenses = data.get("year_expenses", world.year_expenses)
        world.last_year_revenue = data.get("last_year_revenue", world.last_year_revenue)
        world.last_year_expenses = data.get("last_year_expenses", world.last_year_expenses)
        world.humans = [Human(**item) for item in data.get("humans", world.humans)]
        world.workplaces = [Workplace(**item) for item in data.get("workplaces", world.workplaces)]
        world.food_stores = [FoodStore(**item) for item in data.get("food_stores", world.food_stores)]
        world.next_human_id = data.get("next_human_id", world.next_human_id)
        world.next_workplace_id = data.get("next_workplace_id", world.next_workplace_id)
        world.next_store_id = data.get("next_store_id", world.next_store_id)
        world.month = data.get("month", world.month)
        world.history = data.get("history", world.history)
        world.history_year = data.get("history_year", world.history_year)
        buildings = []
        for item in data.get("buildings", []):
            buildings.append(Building(**item))
        if buildings:
            world.buildings = buildings
        return world

