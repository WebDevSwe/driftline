from __future__ import annotations

import math
import random

from models import Building, CentralBank, Human, MarketState, ServiceState, Transaction, Workplace, WorldConfig

SIZE_MAP = {"Liten": 30, "Medium": 60, "Stor": 100}
REGIONS = ["Norra", "Medel", "Syd"]
SEASONS = ["Vinter", "Vår", "Sommar", "Höst"]
BLOCK_COST_MIN = 1
FOOD_MAX = 100
FOOD_BUY_THRESHOLD = 24
FOOD_MONTHLY_NEED = 4
FOOD_FARM_PER_EMPLOYEE_MONTH = 9
FARM_STORAGE_MONTHS = 3
RENT_COST = 6
FOOD_PRICE = 2
TENT_CAPACITY = 4
# One owner plus at most four lodgers/tenants.
HOUSE_CAPACITY = 5
HOUSING_BUFFER = 24
HOUSE_BUILD_COST = 40
HOUSE_EXPANSION_COST = 32
HOUSE_MAX_LEVEL = 4
APARTMENT_CAPACITY = 24
APARTMENT_BUILD_COST = 140
APARTMENT_RENT = 8
HOTEL_RENT = 10
HOTEL_ROOMS_PER_BLOCK = 12
BUILD_MARGIN = 1
TRANSPORT_MODES = {
    "Gå": {"purchase": 0, "monthly": 0, "range": 5},
    "Cykel": {"purchase": 35, "monthly": 1, "range": 18},
    "Buss": {"purchase": 0, "monthly": 5, "range": 45},
    "Bil": {"purchase": 220, "monthly": 16, "range": 65},
}
# Kept as aliases for old saves and extensions importing these constants.
CAR_PRICE = TRANSPORT_MODES["Bil"]["purchase"]
CAR_MONTHLY_COST = TRANSPORT_MODES["Bil"]["monthly"]
LOCAL_COMMUTE_DISTANCE = TRANSPORT_MODES["Gå"]["range"]
CAR_COMMUTE_DISTANCE = TRANSPORT_MODES["Bil"]["range"]
CIVIC_BLOCK_COST = 18
SERVICE_BUILD_COST = 45

PERMANENT_HOME_KINDS = {"Bostad", "Hydda", "Stuga", "Villa", "Stort hus", "Gård", "Lägenhet"}
HOME_RUNNING_COSTS = {"Hydda": 1, "Stuga": 3, "Villa": 6, "Stort hus": 10, "Gård": 5}
SERVICE_STAFF_PER_RESIDENT = {
    "Polis": 1/80, "Brandkår": 1/100, "Sjukvård": 1/30,
    "Skola": 1/20, "Barnomsorg": 1/18, "A-kassa": 1/120,
}
SERVICE_STAFF_PER_BUILDING = {
    "Polis": 8, "Brandkår": 6, "Sjukvård": 10,
    "Skola": 12, "Barnomsorg": 12, "A-kassa": 6,
}

SERVICE_COLORS = {
    "Polis": "#4169a1", "Brandkår": "#d85b45", "Sjukvård": "#f2f2f2",
    "Skola": "#b58ad6", "Barnomsorg": "#ef9fbd", "A-kassa": "#7796b8",
}

WORKPLACE_RULES = {
    "Jordbruk": {"blocks": 4, "block_cost_multiplier": 0, "capacity_min": 1,
                  "capacity_max": 6, "wage": 20, "strain": 2, "status_req": 0, "color": "#6ed26a"},
    "Mataffär": {"blocks_min": 1, "blocks_max": 2, "block_cost_multiplier": 2,
                  "capacity_min": 1, "capacity_max": 6, "wage": 32, "strain": 1,
                  "status_req": 0, "color": "#2eb6a8"},
    "Basjobb": {"blocks_min": 1, "blocks_max": 2, "block_cost_multiplier": 2,
                 "capacity_min": 1, "capacity_max": 8, "wage": 36, "strain": 1,
                 "status_req": 0, "color": "#7cc4ff"},
    "Service": {"blocks_min": 1, "blocks_max": 3, "block_cost_multiplier": 5,
                 "capacity_min": 1, "capacity_max": 10, "wage": 48, "strain": 2,
                 "status_req": 1, "color": "#ffd166"},
    "Hotell": {"blocks_min": 2, "blocks_max": 3, "block_cost_multiplier": 5,
                "capacity_min": 2, "capacity_max": 12, "wage": 42, "strain": 2,
                "status_req": 1, "color": "#cf7fc2"},
    "Industri": {"blocks_choices": [4, 6, 8], "block_cost_multiplier": 12,
                  "capacity_min": 3, "capacity_max": 20, "wage": 65, "strain": 3,
                  "status_req": 3, "color": "#f0b34f"},
}


class World:
    """A need-driven local economy; chance adds texture but never creates demand."""

    def __init__(self, config: WorldConfig):
        self.name, self.size_label, self.region = config.name, config.size_label, config.region
        self.grid_size = SIZE_MAP[config.size_label]
        self.buildings: list[Building] = []
        self.humans: list[Human] = []
        self.workplaces: list[Workplace] = []
        self.money, self.population, self.stability = 120, 10, 72
        self.central_bank = CentralBank()
        self.expenses, self.tax_rate = 0, 0.01
        self.block_cost, self.block_restore_cost, self.food_price = 8, 20, FOOD_PRICE
        self.market = MarketState()
        self.month, self.unemployed = 0, self.population
        self.next_human_id = self.next_workplace_id = 1
        names = ("Polis", "Brandkår", "Sjukvård", "Skola", "Barnomsorg", "A-kassa")
        self.services = {name: False for name in names}
        self.service_funding = {name: 0 for name in names}
        self.service_costs = dict(zip(names, (6, 5, 7, 6, 4, 3)))
        self.service_states = {name: ServiceState(name) for name in names}
        self.last_service_operating_paid = {name: 0 for name in names}
        self.budget_allocations = {"Basutgifter": 100, "Service": 100, "Säsong": 100}
        self.healthcare_extra_per_sick = 2
        keys = (
            "population", "money", "expenses", "buildings", "economy",
            "hungry", "sick", "unemployed", "employed", "food_supply",
            "food_stored", "housing_capacity", "housed", "workplaces", "farms",
            "attractiveness", "crime", "arrivals", "departures", "central_area",
            "unemployment_support",
            "cars", "bikes", "bus_users", "retired", "deaths",
            "pension_assets", "hotel_guests", "hotel_rooms",
            "money_supply", "external_balance", "money_discrepancy",
            "service_coverage", "service_effectiveness",
            "healthcare_treated", "crime_victims", "fire_incidents",
            "students_supported", "childcare_supported",
            "food_price", "room_rent", "apartment_rent", "hotel_rate",
            "wage_index", "construction_index",
            "financially_secure", "average_reserve",
        )
        self.history, self.history_year = {k: [] for k in keys}, {k: [] for k in keys}
        self.last_revenue = self.last_hungry = self.last_sick = self.last_unemployed = 0
        self.last_food_supply = self.last_food_sold = 0
        self.last_unemployment_support = 0
        self.last_tax_revenue = 0
        self.last_development_revenue = 0
        self.last_tax_revenue = 0
        self.last_public_investment = 0
        self.last_public_payroll = 0
        self.last_expenses = {"Basutgifter": 0, "Service": 0, "Säsong": 0}
        self.last_bank_rate = .01
        self.year_revenue = self.year_expenses = 0
        self.last_year_revenue = self.last_year_expenses = 0
        self.attractiveness = 50.0
        self.crime_rate = 5.0
        self.last_arrivals = self.last_departures = 0
        self.last_deaths = self.last_retirements = 0
        self.population_events = []
        self.transactions: list[Transaction] = []
        self.last_external_inflow = self.last_external_outflow = 0
        self.last_money_discrepancy = 0
        self.last_money_supply = 0
        self.last_healthcare_treated = self.last_crime_victims = 0
        self.last_fire_incidents = self.last_students_supported = 0
        self.last_childcare_supported = 0
        self._month_external_inflow = self._month_external_outflow = 0
        self.centrality: dict[tuple[int, int], float] = {}
        self._rng = random.Random(42)
        self._first_names = ["Alex", "Erik", "Sara", "Lina", "Oskar", "Nora", "Emil", "Maja",
                             "Karl", "Vera", "Anton", "Elsa", "Leo", "Sofia", "Johan", "Ida"]
        self._last_names = ["Andersson", "Johansson", "Karlsson", "Nilsson", "Larsson",
                            "Olsson", "Persson", "Svensson", "Gustafsson", "Pettersson"]
        self._drives = ["företagare", "lantbruk", "tältliv", "status", "risk", "sparsam"]
        self._seed_world(); self._seed_population(); self._sync_tents()
        self.last_money_supply = self._money_supply()
        self._update_centrality(); self._update_household_plans(); self._record_history()

    def _seed_world(self):
        c = self.grid_size // 2
        for x in range(c - 2, c + 2):
            for y in range(c - 2, c + 2):
                self.buildings.append(Building(x, y, "#d9534f", "Torg"))

    def _seed_population(self):
        while len(self.humans) < self.population:
            self.humans.append(self._new_human())

    def _new_human(self):
        h = Human(self.next_human_id, self._starting_capital(), self._random_name(),
                  self._rng.randint(18, 35), self._random_drive(), food=40)
        h.housing_ambition = round(self._rng.uniform(.75, 1.25), 2)
        # Stable variation without consuming the world's random event stream.
        h.education_level = 15+(h.id*17+h.age*3)%46
        if 22 <= h.age <= 35:
            h.dependents = (h.id*7+h.age)%3 if h.id%3 else 0
        if h.drive in ("sparsam", "status"): h.housing_ambition += .2
        if h.drive == "tältliv": h.housing_ambition -= .35
        self.next_human_id += 1
        return h

    def advance_month(self):
        self.month += 1
        opening_supply = self._money_supply()
        self._month_external_inflow = self._month_external_outflow = 0
        for human in self.humans:
            human.last_income = human.last_living_cost = 0
            human.last_events = []
        self.central_bank.last_pension_contributions = 0
        self.central_bank.last_pension_payouts = 0
        self.central_bank.last_interest_income = 0
        for name, funding in self.service_funding.items():
            if funding > 0: self.services[name] = True
        self._update_market_prices()
        self._update_household_plans()
        self.last_development_revenue = 0
        self.last_public_investment = 0
        self.last_public_payroll = 0
        self._sync_population(); self._age_population(); self._develop_apartment_housing()
        self._evaluate_housing_market(); self._develop_civic_center()
        self._spawn_new_businesses(); self._sync_public_service_jobs()
        self._assign_jobs_and_pay_wages(); self._update_service_capacity(); self._apply_transport_choices()
        self._apply_unemployment_support(); self._apply_pensions()
        hungry = self._apply_food()
        self._assign_housing(); self._sync_tents(); self._apply_housing_running_costs()
        self._update_health(hungry); self._apply_status_purchases()
        self.last_hungry = hungry
        self._apply_bank_interest_and_loans(); self._apply_public_budget()
        self._update_service_capacity()
        self._apply_service_outcomes()
        self._update_dissatisfaction(); self._update_population(self.season(), self.money - self.expenses, hungry)
        self._cleanup_abandoned_workplaces(); self._update_centrality()
        self._reconcile_money(opening_supply)
        self._record_history(); self._record_pinned_humans()

    def formatted_time(self):
        return f"År {(self.month // 12) + 1}, Månad {(self.month % 12) + 1} ({self.season()})"

    def season(self):
        return SEASONS[(self.month % 12) // 3]

    def _record_history(self):
        snapshot = self.statistics_snapshot()
        active_service_states = [state for name, state in self.service_states.items()
                                 if self.services.get(name)]
        values = {
            "population": len(self.humans), "money": self.money, "expenses": self.expenses,
            "buildings": snapshot["active_buildings"], "economy": self.money-self.expenses,
            "hungry": self.last_hungry, "sick": self.last_sick,
            "unemployed": self.unemployed, "employed": self._employed_count(),
            "food_supply": self.last_food_supply, "food_stored": snapshot["food_stored"],
            "housing_capacity": snapshot["housing_capacity"], "housed": snapshot["housed"],
            "workplaces": len(self.workplaces), "farms": snapshot["farms"],
            "attractiveness": round(self.attractiveness, 1), "crime": round(self.crime_rate, 1),
            "arrivals": self.last_arrivals, "departures": self.last_departures,
            "central_area": snapshot["central_area"],
            "unemployment_support": self.last_unemployment_support,
            "cars": snapshot["cars"], "bikes": snapshot["transport_modes"].get("Cykel", 0),
            "bus_users": snapshot["transport_modes"].get("Buss", 0),
            "retired": snapshot["retired"], "deaths": self.last_deaths,
            "pension_assets": self.central_bank.pension_assets,
            "money_supply": self.last_money_supply,
            "external_balance": self.last_external_inflow-self.last_external_outflow,
            "money_discrepancy": self.last_money_discrepancy,
            "service_coverage": round(100*sum(s.coverage for s in active_service_states)
                                      /max(1, len(active_service_states)), 1),
            "service_effectiveness": round(100*sum(s.effectiveness for s in active_service_states)
                                           /max(1, len(active_service_states)), 1),
            "healthcare_treated": self.last_healthcare_treated,
            "crime_victims": self.last_crime_victims,
            "fire_incidents": self.last_fire_incidents,
            "students_supported": self.last_students_supported,
            "childcare_supported": self.last_childcare_supported,
            "food_price": self.market.food_price,
            "room_rent": self.market.room_rent,
            "apartment_rent": self.market.apartment_rent,
            "hotel_rate": self.market.hotel_rate,
            "wage_index": round(self.market.wage_index*100, 1),
            "construction_index": round(self.market.construction_index*100, 1),
            "financially_secure": sum(h.money >= h.reserve_target for h in self.humans),
            "average_reserve": round(sum(h.reserve_target for h in self.humans)
                                     /max(1, len(self.humans)), 1),
            "hotel_guests": snapshot["hotel_guests"],
            "hotel_rooms": snapshot["hotel_rooms"],
        }
        for key, value in values.items():
            self.history.setdefault(key, [])
            self.history_year.setdefault(key, [])
            self.history[key].append(value)
            if self.month > 0 and self.month % 12 == 0:
                annual_value = (sum(self.history[key][-12:]) if key in
                                {"arrivals", "departures", "deaths", "unemployment_support", "expenses",
                                 "external_balance", "money_discrepancy"}
                                else value)
                self.history_year[key].append(annual_value)

    def statistics_snapshot(self):
        active = [b for b in self.buildings if b.active]
        building_counts = {}
        for building in active:
            building_counts[building.kind] = building_counts.get(building.kind, 0)+1
        workplace_counts = {}
        employees_by_kind = {}
        for workplace in self.workplaces:
            workplace_counts[workplace.kind] = workplace_counts.get(workplace.kind, 0)+1
            employees_by_kind[workplace.kind] = employees_by_kind.get(workplace.kind, 0)+workplace.employed
        housed = sum(h.home_kind in PERMANENT_HOME_KINDS for h in self.humans)
        private_houses = [b for b in active if b.kind == "Bostad"]
        apartments = [b for b in active if b.kind == "Flerfamiljshus"]
        home_types = {}
        for human in self.humans:
            home_types[human.home_kind] = home_types.get(human.home_kind, 0)+1
        service_buildings = {name: building_counts.get(name, 0) for name in self.services}
        central_kinds = {"Torg", "Centrum", "Flerfamiljshus", *self.services.keys()}
        return {
            "active_buildings": len(active), "building_counts": building_counts,
            "workplace_counts": workplace_counts, "employees_by_kind": employees_by_kind,
            "farms": workplace_counts.get("Jordbruk", 0),
            "farm_workers": employees_by_kind.get("Jordbruk", 0),
            "food_stored": sum(w.stock_food for w in self.workplaces if w.kind == "Jordbruk"),
            "housing_capacity": self._housing_capacity(), "housed": housed,
            "housing_vacancies": max(0, self._housing_capacity()-housed),
            "private_houses": len(private_houses),
            "expanded_houses": sum(b.level > 1 for b in private_houses),
            "apartment_buildings": len(apartments),
            "service_buildings": service_buildings,
            "service_states": {
                name: {
                    "target": state.target_positions,
                    "facility": state.facility_positions,
                    "staffed": state.staffed,
                    "coverage": state.coverage,
                    "effectiveness": state.effectiveness,
                    "workload": state.workload,
                }
                for name, state in self.service_states.items()
            },
            "central_area": sum(b.kind in central_kinds for b in active),
            "average_money": round(sum(h.money for h in self.humans)/max(1, len(self.humans)), 1),
            "cars": sum(h.transport_mode == "Bil" or h.has_car for h in self.humans),
            "transport_modes": {mode: sum(self._transport_mode(h) == mode for h in self.humans)
                                for mode in TRANSPORT_MODES},
            "retired": sum(h.retired for h in self.humans),
            "hotel_guests": sum(h.home_kind == "Hotell" for h in self.humans),
            "hotel_rooms": self._temporary_housing_capacity(),
            "home_types": home_types,
            "average_education": round(sum(h.education_level for h in self.humans)
                                       /max(1, len(self.humans)), 1),
            "dependents": sum(h.dependents for h in self.humans),
            "financially_secure": sum(h.money >= h.reserve_target for h in self.humans),
            "average_reserve": round(sum(h.reserve_target for h in self.humans)
                                     /max(1, len(self.humans)), 1),
        }

    def _record_pinned_humans(self):
        workplaces = {w.id: w for w in self.workplaces}
        for human in self.humans:
            if not human.pinned: continue
            workplace = workplaces.get(human.job_id)
            human.personal_history.append({
                "month": self.month, "money": human.money, "food": human.food,
                "health": human.health, "energy": human.energy,
                "job": (workplace.service_name or workplace.kind) if workplace else None,
                "home": human.home_kind, "hungry": human.hungry,
                "education": human.education_level,
                "events": list(human.last_events),
                "decision": human.last_decision,
                "reserve": human.reserve_target,
            })
            if len(human.personal_history) > 600:
                human.personal_history = human.personal_history[-600:]

    def _starting_capital(self):
        wage = WORKPLACE_RULES["Basjobb"]["wage"]
        return self._rng.randint(wage // 2, wage * 3)

    def _money_supply(self):
        return (self.money+self.central_bank.reserves+sum(h.money for h in self.humans)
                +sum(w.money for w in self.workplaces))

    def _record_transaction(self, category, amount, source_type, source_id,
                            destination_type, destination_id, description=""):
        amount = int(amount)
        if amount <= 0: return
        self.transactions.append(Transaction(
            self.month, category, amount, source_type, source_id,
            destination_type, destination_id, description,
        ))
        if source_type == "Extern": self._month_external_inflow += amount
        if destination_type == "Extern": self._month_external_outflow += amount
        self.transactions = self.transactions[-10000:]

    def _reconcile_money(self, opening_supply, transaction_start=None):
        external_in = self._month_external_inflow
        external_out = self._month_external_outflow
        closing_supply = self._money_supply()
        self.last_external_inflow = external_in
        self.last_external_outflow = external_out
        self.last_money_supply = closing_supply
        self.last_money_discrepancy = closing_supply-opening_supply-(external_in-external_out)

    def transaction_summary(self, month=None):
        month = self.month if month is None else month
        summary = {}
        for transaction in self.transactions:
            if transaction.month != month: continue
            summary[transaction.category] = summary.get(transaction.category, 0)+transaction.amount
        return summary

    def _random_name(self):
        return f"{self._rng.choice(self._first_names)} {self._rng.choice(self._last_names)}"

    def _random_drive(self):
        return self._rng.choice(self._drives)

    def _age_population(self):
        self.last_deaths = self.last_retirements = 0
        if self.month % 12 != 0: return
        deceased = []
        for h in self.humans:
            h.age = min(120, h.age + 1)
            if h.age >= 67 and not h.retired:
                h.retired = True
                h.job_id = None
                self.last_retirements += 1
            mortality = max(0, (h.age-78)*.012)
            if h.age >= 105 or self._rng.random() < mortality:
                deceased.append(h)
        for human in deceased:
            self._remove_resident(human, "avled")
            self.last_deaths += 1

    def _remove_resident(self, human, reason):
        heirs = [h for h in self.humans if h is not human and h.age >= 18]
        heir = min(heirs, key=lambda h: h.money) if heirs else None
        if reason == "avled" and heir:
            heir.money += human.money
            self._record_transaction("Arv", human.money, "Invånare", human.id,
                                     "Invånare", heir.id, f"Arv efter {human.name}")
            for building in self.buildings:
                if building.owner_id == human.id: building.owner_id = heir.id
            for workplace in self.workplaces:
                if workplace.owner_id == human.id: workplace.owner_id = heir.id
        elif reason != "avled":
            self._record_transaction("Utflyttat kapital", human.money, "Invånare", human.id,
                                     "Extern", None, human.name)
            for building in self.buildings:
                if building.owner_id == human.id: building.owner_id = None
            for workplace in self.workplaces:
                if workplace.owner_id == human.id: workplace.owner_id = None
        elif human.money:
            self._record_transaction("Dödsbo utan arvinge", human.money, "Invånare", human.id,
                                     "Extern", None, human.name)
        self.central_bank.pension_assets = max(0, self.central_bank.pension_assets-human.pension_balance)
        self.central_bank.outstanding_loans = max(0, self.central_bank.outstanding_loans-human.loan_balance)
        if human in self.humans: self.humans.remove(human)
        self.population_events.append({"month": self.month, "name": human.name, "event": reason, "age": human.age})
        self.population_events = self.population_events[-100:]

    def _sync_population(self):
        while len(self.humans) < self.population:
            newcomer = self._new_human()
            self.humans.append(newcomer)
            self._record_transaction("Inflyttat kapital", newcomer.money, "Extern", None,
                                     "Invånare", newcomer.id, newcomer.name)
        if len(self.humans) > self.population:
            leaving = sorted(self.humans, key=lambda h: h.dissatisfaction, reverse=True)
            for human in leaving[:len(self.humans)-self.population]:
                self._remove_resident(human, "synkroniserades bort")
        self.population = len(self.humans)

    # Demand is calculated before anyone chooses a business.
    @staticmethod
    def _step_price(current, target):
        if target > current:
            return current+1
        if target < current:
            return current-1
        return current

    def _update_market_prices(self):
        if not self.humans:
            self.market.food_pressure = self.market.housing_pressure = self.market.labour_pressure = 1.0
            self.market.food_price = self._step_price(self.market.food_price, FOOD_PRICE)
            self.market.room_rent = self._step_price(self.market.room_rent, RENT_COST)
            self.market.apartment_rent = self._step_price(self.market.apartment_rent, APARTMENT_RENT)
            self.market.hotel_rate = self._step_price(self.market.hotel_rate, HOTEL_RENT)
            self.market.wage_index += (1-self.market.wage_index)*.15
            self.market.construction_index += (1-self.market.construction_index)*.12
            self.food_price = self.market.food_price
            return
        people = max(1, len(self.humans))
        farms = [w for w in self.workplaces if w.kind == "Jordbruk"]
        food_supply = (sum(w.stock_food for w in farms)
                       +sum(w.employed*FOOD_FARM_PER_EMPLOYEE_MONTH for w in farms))
        food_need = people*FOOD_MONTHLY_NEED
        food_pressure = min(3.0, food_need/max(1, food_supply))

        permanent_capacity = self._housing_capacity()
        permanent_occupants = sum(h.home_kind in PERMANENT_HOME_KINDS for h in self.humans)
        housing_seekers = sum(h.home_kind in ("Tält", "Bostadslös", "Hotell") for h in self.humans)
        housing_pressure = min(3.0, (permanent_occupants+housing_seekers)/max(1, permanent_capacity))

        labour_force = max(1, sum(not h.retired for h in self.humans))
        vacancies = max(0, sum(w.capacity for w in self.workplaces)-self._employed_count())
        unemployment = sum(not h.retired and h.job_id is None for h in self.humans)
        labour_pressure = max(.5, min(2.0, 1+(vacancies-unemployment)/labour_force))

        self.market.food_pressure = food_pressure
        self.market.housing_pressure = housing_pressure
        self.market.labour_pressure = labour_pressure
        food_target = round(FOOD_PRICE*max(.7, min(2.5, .65+.5*food_pressure)))
        room_target = round(RENT_COST*max(.7, min(1.8, .75+.35*housing_pressure)))
        apartment_target = round(APARTMENT_RENT*max(.7, min(1.7, .78+.30*housing_pressure)))
        rooms = self._temporary_housing_capacity()
        guests = sum(h.home_kind == "Hotell" for h in self.humans)
        hotel_pressure = (guests+self.last_arrivals+1)/max(1, rooms) if rooms else 1
        hotel_target = round(HOTEL_RENT*max(.75, min(1.8, .9+.35*hotel_pressure)))

        self.market.food_price = max(1, self._step_price(self.market.food_price, food_target))
        self.market.room_rent = max(1, self._step_price(self.market.room_rent, room_target))
        self.market.apartment_rent = max(1, self._step_price(self.market.apartment_rent, apartment_target))
        self.market.hotel_rate = max(1, self._step_price(self.market.hotel_rate, hotel_target))
        wage_target = max(.85, min(1.30, .85+.20*labour_pressure))
        construction_target = max(.80, min(1.55,
            .75+.28*housing_pressure+.12*labour_pressure))
        self.market.wage_index += (wage_target-self.market.wage_index)*.15
        self.market.construction_index += (construction_target-self.market.construction_index)*.12
        self.food_price = self.market.food_price  # compatibility for older UI/extensions

    def _house_build_cost(self):
        return max(1, round(HOUSE_BUILD_COST*self.market.construction_index))

    def _house_expansion_cost(self):
        return max(1, round(HOUSE_EXPANSION_COST*self.market.construction_index))

    def _update_household_plans(self):
        workplaces = {w.id: w for w in self.workplaces}
        for human in self.humans:
            workplace = workplaces.get(human.job_id)
            jobless = workplace is None and not human.retired
            food_cost = FOOD_MONTHLY_NEED*self.market.food_price
            if human.home_owner_id == human.id:
                housing_cost = HOME_RUNNING_COSTS.get(human.home_kind, 0)
            elif human.home_kind == "Lägenhet":
                housing_cost = self.market.apartment_rent
            elif human.home_kind == "Hotell":
                housing_cost = self.market.hotel_rate
            elif human.home_kind in PERMANENT_HOME_KINDS:
                housing_cost = self.market.room_rent
            else:
                housing_cost = 0
            transport_cost = TRANSPORT_MODES[self._transport_mode(human)]["monthly"]
            human.essential_monthly_cost = food_cost+housing_cost+transport_cost

            reserve_months = {
                "sparsam": 6.0, "företagare": 3.0, "lantbruk": 3.0,
                "risk": 2.0, "status": 2.0, "tältliv": 1.5,
            }.get(human.drive, 3.0)
            reserve_months += human.dependents*.5+(2 if jobless else 0)
            human.reserve_target = math.ceil(human.essential_monthly_cost*reserve_months)
            human.disposable_money = max(0, human.money-human.reserve_target)

            insecure_home = human.home_kind in ("Tält", "Bostadslös", "Hotell")
            human.housing_motivation = max(0.0,
                human.housing_ambition+(1.6 if insecure_home else 0)
                +human.dependents*.15+self.market.housing_pressure*.25
                -self.market.construction_index*.35-(.5 if jobless else 0)
            )
            human.business_motivation = max(0.0,
                {"företagare": 1.6, "risk": 1.35, "lantbruk": 1.15,
                 "sparsam": .65}.get(human.drive, .9)
                +(.35 if jobless else 0)+min(1.0, human.disposable_money/150)
                -(.5 if human.financial_stress_months else 0)
            )
            distance = self._commute_distance(human, workplace) if workplace else 0
            human.mobility_motivation = max(0.0,
                distance/max(1, TRANSPORT_MODES["Gå"]["range"])
                +(.8 if human.drive == "status" else .35 if human.drive == "risk" else 0)
                -human.essential_monthly_cost/max(1, human.money)
            )
            human.consumption_motivation = max(0.0,
                {"status": 1.5, "risk": 1.0, "sparsam": .35}.get(human.drive, .75)
                +min(1.0, human.disposable_money/max(1, human.essential_monthly_cost*4))
                -(.8 if human.hungry else 0)-(.6 if jobless else 0)
            )
            reasons = []
            if jobless: reasons.append("saknar arbetsinkomst")
            if insecure_home: reasons.append("har ett osäkert boende")
            if human.dependents: reasons.append(f"försörjer {human.dependents} barn")
            if human.money < human.reserve_target: reasons.append("har mindre än sin trygghetsbuffert")
            elif human.disposable_money: reasons.append(f"har {human.disposable_money} SM över bufferten")
            if self.market.food_pressure > 1.15: reasons.append("möter högt tryck på matmarknaden")
            if self.market.housing_pressure > 1.15: reasons.append("möter bostadsbrist")
            human.decision_reasons = reasons[:4] or ["har en stabil vardagsekonomi"]
            human.last_decision = "Prioriterar sparande och grundbehov"

    def _market_signals(self):
        people = max(1, len(self.humans))
        farms = [w for w in self.workplaces if w.kind == "Jordbruk"]
        # Vacant farm jobs count only partly: land does not feed anyone by itself.
        effective_workers = sum(w.employed+.25*max(0, w.capacity-w.employed) for w in farms)
        stored_food = sum(w.stock_food for w in farms)
        farm_output = effective_workers*FOOD_FARM_PER_EMPLOYEE_MONTH+stored_food/FARM_STORAGE_MONTHS
        need = people * FOOD_MONTHLY_NEED
        food_gap = max(0, (need * 1.35 - farm_output) / need)
        tents = sum(h.home_kind in ("Tält", "Bostadslös") for h in self.humans)
        wealth = sum(h.money for h in self.humans) / people
        jobs = sum(w.employed+.25*max(0, w.capacity-w.employed) for w in self.workplaces)
        temporary_need = sum(h.home_kind in ("Tält", "Bostadslös", "Hotell") for h in self.humans)
        hotel_rooms = sum((b.housing_units or HOTEL_ROOMS_PER_BLOCK) for b in self.buildings
                          if b.active and b.kind == "Hotell")
        desired_hotel_rooms = temporary_need+self.last_arrivals*3+people//25
        return {
            "Jordbruk": food_gap*12*math.sqrt(self.market.food_price/FOOD_PRICE),
            "Mataffär": (max(0, people / 60-sum(w.kind == "Mataffär" for w in self.workplaces))
                          *(1+wealth/100)*math.sqrt(self.market.food_price/FOOD_PRICE)),
            "Basjobb": max(0, people-jobs) / people * 3,
            "Service": max(0, people/35-sum(w.kind == "Service" for w in self.workplaces)) * wealth/45,
            "Hotell": (max(0, (desired_hotel_rooms-hotel_rooms)/max(4, people/20))
                        *(1+wealth/100)*self.market.hotel_rate/HOTEL_RENT),
            "Industri": (max(0, people/45-sum(w.kind == "Industri" for w in self.workplaces))
                          *max(0, min(2, (wealth-45)/55))) if food_gap < .15 else 0,
            "Bostad": (tents/people*wealth/30*self.market.room_rent/RENT_COST
                        /max(.75, self.market.construction_index)),
        }

    def _preference(self, h, kind):
        value = {"företagare": 1.25, "risk": 1.15, "sparsam": .85}.get(h.drive, 1)
        if h.drive == "lantbruk" and kind == "Jordbruk": value *= 2.5
        if h.drive == "status" and kind in ("Service", "Industri"): value *= 1.2
        if h.drive == "företagare" and kind == "Hotell": value *= 1.2
        if kind in ("Service", "Industri"):
            value *= .8+min(100, h.education_level)/200
        return value

    def _spawn_new_businesses(self):
        # A village can establish one firm at a time. A city has many independent
        # entrepreneurs and must be able to react in parallel to job shortages.
        attempts = min(5, 1+len(self.humans)//250)
        for _ in range(attempts):
            signals = self._market_signals()
            candidates = [h for h in self.humans if not h.sick
                          and not any(w.owner_id == h.id for w in self.workplaces)]
            choices = []
            for h in candidates:
                # A shortage of a basic necessity may not be outbid by industry.
                kinds = ("Jordbruk",) if signals["Jordbruk"] > 1 else signals.keys()
                for kind in kinds:
                    demand = signals[kind]
                    if kind == "Bostad": continue
                    profit = demand*WORKPLACE_RULES[kind]["wage"]
                    score = (demand*profit*self._preference(h, kind)
                             *max(.35, h.business_motivation)*min(1.5, .5+h.disposable_money/80))
                    if h.job_id is not None: score *= .75
                    choices.append((score, h, kind))
            created = False
            for score, owner, kind in sorted(choices, key=lambda row: row[0], reverse=True):
                if score < 8: break
                if self._create_workplace(owner, kind, signals[kind]):
                    created = True
                    break
            if not created: break

    def _create_workplace(self, owner, kind, demand_score=1):
        rules = WORKPLACE_RULES[kind]
        count = rules.get("blocks", rules.get("blocks_min", self._rng.choice(rules.get("blocks_choices", [1]))))
        cost = round(count*self.block_cost*rules["block_cost_multiplier"]
                     *self.market.construction_index)
        investable = max(0, owner.money-max(0, owner.reserve_target))
        if cost > investable and kind != "Jordbruk": return False
        blocks = (self._claim_farmland(owner.id) if kind == "Jordbruk"
                  else self._claim_near_activity(kind, rules["color"], owner.id, count))
        if not blocks: return False
        if kind == "Industri":
            # Neighbours demand mitigation, access roads and pricier land when a
            # factory is placed close to homes or farms.
            sensitive = [b for b in self.buildings if b.active and b.kind in
                         ("Bostad", "Flerfamiljshus", "Jordbruk") and (b.x, b.y) not in blocks]
            conflicts = sum(any(abs(x-b.x)+abs(y-b.y) <= 6 for b in sensitive) for x, y in blocks)
            cost += min(owner.money-cost, max(0, conflicts*self.block_cost*3))
        owner.money -= cost; self.money += cost
        self._record_transaction("Markköp", cost, "Invånare", owner.id,
                                 "Kommun", None, f"{kind}, {len(blocks)} block")
        self.last_development_revenue += cost
        divisor = 3 if kind == "Jordbruk" else 6
        capacity = min(rules["capacity_max"], max(rules["capacity_min"], math.ceil(len(self.humans)/divisor)))
        market_wage = max(1, round(rules["wage"]*self.market.wage_index))
        investable = max(0, owner.money-max(0, owner.reserve_target))
        seed = min(investable, market_wage*max(1, capacity))
        owner.money -= seed
        self._record_transaction("Företagskapital", seed, "Invånare", owner.id,
                                 "Företag", self.next_workplace_id, kind)
        workplace = Workplace(self.next_workplace_id, kind, rules["wage"], capacity,
            strain=rules["strain"], owner_id=owner.id, money=seed, blocks=blocks, demand_score=demand_score)
        self.workplaces.append(workplace)
        working_capital = market_wage*min(3, capacity)*3
        if kind != "Jordbruk" and workplace.money < working_capital:
            self._take_loan(workplace, working_capital-workplace.money)
        if kind == "Hotell":
            for coordinate in blocks:
                self._building_at(coordinate).housing_units = HOTEL_ROOMS_PER_BLOCK
        owner.last_decision = f"Startade {kind.lower()} med {cost+seed} SM"
        owner.decision_reasons = [f"såg efterfrågan {demand_score:.1f}",
                                  "bedömde risken som värd att ta"]
        self.next_workplace_id += 1
        return True

    def _claim_near_activity(self, kind, color, owner_id, count):
        used = {(b.x, b.y) for b in self.buildings if b.active}
        inactive = {(b.x, b.y): b for b in self.buildings if not b.active}
        candidates = []
        seen = set()
        satellite = ((kind == "Bostad" and self._rng.random() < .14)
                     or (kind == "Industri" and self._rng.random() < .08))
        if satellite:
            candidates = [(self._rng.random(), x, y)
                          for x in range(BUILD_MARGIN, self.grid_size-BUILD_MARGIN)
                          for y in range(BUILD_MARGIN, self.grid_size-BUILD_MARGIN)
                          if (x, y) not in used]
        # Grow from the existing urban edge. This is linear in the number of
        # occupied blocks instead of comparing every grid cell with every block.
        for distance in ([] if satellite else range(1, self.grid_size)):
            for ax, ay in used:
                for dx in range(-distance, distance+1):
                    dy = distance-abs(dx)
                    for signed_dy in ({dy, -dy} if dy else {0}):
                        x, y = ax+dx, ay+signed_dy
                        if not (BUILD_MARGIN <= x < self.grid_size-BUILD_MARGIN
                                and BUILD_MARGIN <= y < self.grid_size-BUILD_MARGIN): continue
                        if (x, y) in used or (x, y) in seen: continue
                        seen.add((x, y)); candidates.append((self._rng.random(), x, y))
            if len(candidates) >= count: break
        if kind in ("Bostad", "Industri"):
            home_sites = [(b.x, b.y) for b in self.buildings if b.active and b.kind in
                          ("Bostad", "Flerfamiljshus", "Jordbruk")]
            same_kind = [(b.x, b.y) for b in self.buildings if b.active and b.kind == kind]
            industry = [(b.x, b.y) for b in self.buildings if b.active and b.kind == "Industri"]
            def zone_score(row):
                noise, x, y = row
                nearest_home = min((abs(x-a)+abs(y-b) for a, b in home_sites), default=99)
                nearest_same = min((abs(x-a)+abs(y-b) for a, b in same_kind), default=8)
                nearest_industry = min((abs(x-a)+abs(y-b) for a, b in industry), default=99)
                local_same = sum(abs(x-a)+abs(y-b) <= 3 for a, b in same_kind)
                if kind == "Industri":
                    if satellite:
                        centre = self.grid_size//2
                        distance_from_centre = abs(x-centre)+abs(y-centre)
                        return (nearest_home < 7, abs(distance_from_centre-self.grid_size*.45), noise)
                    return (nearest_home < 7, -local_same, nearest_same, -nearest_home, noise)
                if satellite:
                    centre = self.grid_size//2
                    distance_from_centre = abs(x-centre)+abs(y-centre)
                    return (nearest_industry < 7, abs(distance_from_centre-self.grid_size*.3), noise)
                return (nearest_industry < 7, -local_same, nearest_same, noise)
            candidates.sort(key=zone_score)
        else:
            candidates.sort()
        if satellite and candidates:
            _, seed_x, seed_y = candidates[0]
            candidates.sort(key=lambda row: (abs(row[1]-seed_x)+abs(row[2]-seed_y), row[0]))
        chosen = [(x, y) for _, x, y in candidates[:count]]
        if len(chosen) < count: return []
        for x, y in chosen:
            old = inactive.get((x, y))
            if old is not None:
                old.kind, old.color, old.owner_id, old.active = kind, color, owner_id, True
            else:
                self.buildings.append(Building(x, y, color, kind, owner_id=owner_id))
        return chosen

    def _claim_farmland(self, owner_id):
        used = {(b.x, b.y) for b in self.buildings if b.active}
        inactive = {(b.x, b.y): b for b in self.buildings if not b.active}
        centres = [position for position, _ in self.central_blocks(8)]
        if not centres: centres = [(self.grid_size//2, self.grid_size//2)]
        plots = []
        farms = [(b.x, b.y) for b in self.buildings if b.active and b.kind == "Jordbruk"]
        for x in range(BUILD_MARGIN, self.grid_size-BUILD_MARGIN-1):
            for y in range(BUILD_MARGIN, self.grid_size-BUILD_MARGIN-1):
                cells = ((x, y), (x+1, y), (x, y+1), (x+1, y+1))
                if any(cell in used for cell in cells): continue
                distance = min(abs(x-cx)+abs(y-cy) for cx, cy in centres)
                nearest_farm = min((abs(x-fx)+abs(y-fy) for fx, fy in farms), default=self.grid_size)
                plots.append((distance, nearest_farm, self._rng.random(), cells))
        if not plots: return []
        # Some founders deliberately settle new land. Most extend an agricultural
        # district, but a sizeable random term prevents corner-filling geometry.
        if self._rng.random() < .20:
            viable = [row for row in plots if row[0] >= self.grid_size*.18]
            _, _, _, cells = self._rng.choice(viable or plots)
        elif farms:
            _, _, _, cells = max(plots, key=lambda row: (row[0]-row[1]*.7+row[2]*self.grid_size*.35))
        else:
            _, _, _, cells = max(plots, key=lambda row: row[0]+row[2]*self.grid_size*.45)
        for x, y in cells:
            old = inactive.get((x, y))
            if old:
                old.kind, old.color, old.owner_id, old.active = "Jordbruk", WORKPLACE_RULES["Jordbruk"]["color"], owner_id, True
            else:
                self.buildings.append(Building(x, y, WORKPLACE_RULES["Jordbruk"]["color"],
                                               "Jordbruk", owner_id=owner_id,
                                               construction_month=self.month))
        return list(cells)

    def _assign_jobs_and_pay_wages(self):
        previous_jobs = {h.id: h.job_id for h in self.humans}
        signals = self._market_signals()
        for h in self.humans: h.job_id = None
        for w in self.workplaces: w.employed = 0
        eligible = [h for h in self.humans if not h.sick and not h.retired]
        people = {h.id: h for h in eligible}
        for workplace in self.workplaces:
            if not workplace.service_name:
                workplace.demand_score = signals.get(workplace.kind, workplace.demand_score)
        workplaces = sorted(self.workplaces, key=lambda w: (
            bool(w.service_name), w.demand_score*max(1, w.wage), w.wage
        ), reverse=True)
        assignments: dict[int, int] = {}
        counts = {w.id: 0 for w in workplaces}

        def assign(human, workplace):
            assignments[human.id] = workplace.id
            counts[workplace.id] += 1

        # Owners operate their own new firms when possible. Existing staff then
        # retain their profession, which prevents random monthly reshuffling.
        for workplace in workplaces:
            owner = people.get(workplace.owner_id)
            if owner and owner.id not in assignments and self._can_commute(owner, workplace):
                assign(owner, workplace)
        for workplace in [w for w in workplaces if w.kind in ("Mataffär", "Hotell")]:
            if counts[workplace.id]: continue
            pool = [h for h in eligible if h.id not in assignments and self._can_commute(h, workplace)]
            pool.sort(key=lambda h: (previous_jobs.get(h.id) == workplace.id,
                                     self._preference(h, workplace.kind)), reverse=True)
            if pool: assign(pool[0], workplace)
        by_id = {w.id: w for w in workplaces}
        for human in eligible:
            old = by_id.get(previous_jobs.get(human.id))
            if (human.id not in assignments and old and counts[old.id] < old.capacity
                    and self._can_commute(human, old)):
                assign(human, old)

        for workplace in workplaces:
            vacancies = workplace.capacity-counts[workplace.id]
            if vacancies <= 0: continue
            pool = [h for h in eligible if h.id not in assignments and self._can_commute(h, workplace)]
            pool.sort(key=lambda h: (
                self._preference(h, workplace.kind),
                -self._commute_distance(h, workplace), h.money
            ), reverse=True)
            for human in pool[:vacancies]: assign(human, workplace)

        # A completely locked labour market kills every new firm. Vacant,
        # better-paid workplaces may therefore recruit a few workers per month.
        for workplace in workplaces:
            vacancies = workplace.capacity-counts[workplace.id]
            if vacancies <= 0: continue
            candidates = []
            for human in eligible:
                old = by_id.get(assignments.get(human.id))
                if not old or old.id == workplace.id or not self._can_commute(human, workplace): continue
                if old.kind == workplace.kind: continue
                if old.kind in ("Mataffär", "Hotell") and counts[old.id] <= 1: continue
                gain = self._wage_for(human, workplace)-self._wage_for(human, old)
                essential_reopening = (counts[workplace.id] == 0 and workplace.kind in ("Mataffär", "Hotell"))
                if gain < 8 and not essential_reopening: continue
                if old.kind == "Jordbruk" and signals.get("Jordbruk", 0) > .5: continue
                essential_bonus = 80 if essential_reopening and old.kind != "Jordbruk" else 0
                candidates.append((gain+essential_bonus+self._preference(human, workplace.kind)*3, human, old))
            for _, human, old in sorted(candidates, key=lambda row: row[0], reverse=True)[:min(vacancies, max(1, workplace.capacity//3))]:
                counts[old.id] -= 1
                assignments[human.id] = workplace.id
                counts[workplace.id] += 1

        for w in workplaces:
            payroll = 0
            staff = [people[human_id] for human_id, workplace_id in assignments.items()
                     if workplace_id == w.id]
            for h in staff:
                wage = self._wage_for(h, w)
                if w.service_name and w.money < wage and self.money >= wage:
                    self.money -= wage
                    self.last_public_payroll += wage
                    w.money += wage
                    self._record_transaction("Kommunal finansiering", wage, "Kommun", None,
                                             "Företag", w.id, w.service_name)
                if w.money < wage and w.kind in ("Jordbruk", "Mataffär", "Hotell"):
                    self._take_loan(w, wage-w.money)
                if w.money < wage: continue
                contribution = max(1, int(wage*.08))
                tax = int(max(0, wage-contribution)*self.tax_rate)
                net_wage = wage-contribution-tax
                w.money -= wage; h.money += net_wage; self.money += tax; h.job_id = w.id
                h.last_income += net_wage
                if previous_jobs.get(h.id) != w.id:
                    h.last_decision = f"Tog arbete inom {w.service_name or w.kind}"
                    h.decision_reasons = [f"lönen är {wage} SM per månad",
                                          f"resvägen är {self._commute_distance(h, w)} block"]
                h.pension_balance += contribution
                self.central_bank.reserves += contribution
                self.central_bank.pension_assets += contribution
                self.central_bank.last_pension_contributions += contribution
                self.last_tax_revenue += tax
                self._record_transaction("Nettolön", net_wage, "Företag", w.id,
                                         "Invånare", h.id, w.service_name or w.kind)
                self._record_transaction("Inkomstskatt", tax, "Företag", w.id,
                                         "Kommun", None, h.name)
                self._record_transaction("Pensionsavsättning", contribution, "Företag", w.id,
                                         "Centralbank", None, h.name)
                payroll += wage; w.employed += 1
            factor = (0 if w.service_name else
                      {"Basjobb": 1.35, "Service": 1.25, "Industri": 1.45}.get(w.kind, 0))
            revenue = int(payroll * factor * min(1.5, max(.8, w.demand_score)))
            w.money += revenue; w.monthly_profit = revenue-payroll
            self._record_transaction("Extern försäljning", revenue, "Extern", None,
                                     "Företag", w.id, w.kind)
        employed = {h.id for h in self.humans if h.job_id is not None}
        self.unemployed = sum(not h.retired and h.id not in employed for h in self.humans)
        for human in self.humans:
            if not human.retired and human.id not in employed and human.last_decision.startswith("Prioriterar"):
                human.last_decision = "Söker ett arbete som går att nå och försörja sig på"

    def _wage_for(self, human, workplace):
        base_wage = max(1, round(workplace.wage*self.market.wage_index))
        if workplace.service_name:
            return base_wage+min(5, int(human.education_level//20))
        skill_bonus = min(5, int(human.education_level//20)) if workplace.kind in ("Service", "Industri") else 0
        return max(20, min(1000, base_wage+skill_bonus+min(100, human.status_items*2)))

    def _can_commute(self, human, workplace):
        if workplace.kind == "Jordbruk" and workplace.owner_id == human.id: return True
        distance = self._commute_distance(human, workplace)
        if distance == 0: return True
        mode = self._transport_mode(human)
        if distance <= TRANSPORT_MODES[mode]["range"]: return True
        for candidate, terms in TRANSPORT_MODES.items():
            owned = candidate == "Gå" or candidate == "Buss" or (
                candidate == "Cykel" and human.has_bike) or (candidate == "Bil" and human.has_car)
            purchase = 0 if owned else terms["purchase"]
            buffer = HOUSING_BUFFER*3 if candidate == "Bil" else HOUSING_BUFFER
            if distance <= terms["range"] and human.money >= purchase+terms["monthly"]+buffer:
                return True
        return False

    def _commute_distance(self, human, workplace):
        if human.home_x is None or human.home_y is None or not workplace.blocks: return 0
        return min(abs(human.home_x-x)+abs(human.home_y-y) for x, y in workplace.blocks)

    def _transport_mode(self, human):
        mode = human.transport_mode if human.transport_mode in TRANSPORT_MODES else "Gå"
        if human.has_car and mode == "Gå": mode = "Bil"  # migrate older saves
        if mode == "Cykel": human.has_bike = True
        human.transport_mode, human.has_car = mode, mode == "Bil"
        return mode

    def _record_purchase(self, human, category, item, amount):
        if amount <= 0: return
        human.recent_purchases.append({"month": self.month, "category": category,
                                       "item": item, "amount": amount})
        human.recent_purchases = human.recent_purchases[-16:]

    def _settle_consumer_spending(self, human, amount, category, item, business_kinds=()):
        businesses = [w for w in self.workplaces if w.kind in business_kinds and w.employed]
        if businesses:
            recipient = min(businesses, key=lambda w: self._commute_distance(human, w))
            recipient.money += amount
            recipient.monthly_profit += amount
            self._record_transaction(category, amount, "Invånare", human.id,
                                     "Företag", recipient.id, item)
        else:
            self._record_transaction(category, amount, "Invånare", human.id,
                                     "Extern", None, item)

    def _apply_transport_choices(self):
        for human in self.humans:
            current = self._transport_mode(human)
            workplace = next((w for w in self.workplaces if w.id == human.job_id), None)
            distance = self._commute_distance(human, workplace) if workplace else 0
            desired = "Gå"
            for candidate in ("Gå", "Cykel", "Buss", "Bil"):
                if distance <= TRANSPORT_MODES[candidate]["range"]:
                    desired = candidate
                    break
            if human.has_car: desired = "Bil"
            available = max(0, human.money-human.reserve_target)
            # Status and convenience can justify a car, but only when the
            # household can preserve its own safety buffer.
            aspirational_car = (not human.retired and not human.has_car and self.month%12 == 0
                                and available >= CAR_PRICE+CAR_MONTHLY_COST
                                and human.mobility_motivation >= .65)
            if aspirational_car: desired = "Bil"
            terms = TRANSPORT_MODES[desired]
            owns = desired in ("Gå", "Buss") or (desired == "Cykel" and human.has_bike) or (
                desired == "Bil" and human.has_car)
            purchase = 0 if owns else terms["purchase"]
            if available < purchase+terms["monthly"]:
                affordable = []
                for mode, values in TRANSPORT_MODES.items():
                    already_owned = mode in ("Gå", "Buss") or (mode == "Cykel" and human.has_bike) or (
                        mode == "Bil" and human.has_car)
                    price = 0 if already_owned else values["purchase"]
                    if distance <= values["range"] and available >= price+values["monthly"]:
                        affordable.append(mode)
                desired = affordable[-1] if affordable else "Gå"
                terms = TRANSPORT_MODES[desired]
                owns = desired in ("Gå", "Buss") or (desired == "Cykel" and human.has_bike) or (
                    desired == "Bil" and human.has_car)
                purchase = 0 if owns else terms["purchase"]
            if purchase:
                human.money -= purchase; human.last_living_cost += purchase
                self._record_purchase(human, "Transport", desired, purchase)
                self._record_transaction("Transportköp", purchase, "Invånare", human.id,
                                         "Extern", None, desired)
                if desired == "Cykel": human.has_bike = True
                if desired == "Bil": human.has_car = True
                human.last_decision = f"Köpte transportsättet {desired.lower()} för {purchase} SM"
                human.decision_reasons = [f"behövde klara en resa på {distance} block",
                                          "kunde behålla sin trygghetsbuffert"]
            monthly = terms["monthly"]
            if monthly and human.money >= monthly:
                human.money -= monthly; human.last_living_cost += monthly
                self._record_purchase(human, "Transport", desired, monthly)
                self._record_transaction("Transportdrift", monthly, "Invånare", human.id,
                                         "Extern", None, desired)
            human.transport_mode = desired
            if desired != current and not purchase:
                human.last_decision = f"Bytte transportsätt till {desired.lower()}"
                human.decision_reasons = [f"anpassade resan på {distance} block till sin ekonomi"]

    def _apply_food(self):
        farms = [w for w in self.workplaces if w.kind == "Jordbruk"]
        stock = sum(w.stock_food+w.employed*FOOD_FARM_PER_EMPLOYEE_MONTH for w in farms)
        for farm in farms: farm.stock_food = 0
        self.last_food_supply = stock; sold = 0
        for h in sorted(self.humans, key=lambda person: person.food):
            consumed = min(h.food, FOOD_MONTHLY_NEED); h.food -= consumed
            desired = min(FOOD_MAX-h.food, max(FOOD_MONTHLY_NEED-consumed, FOOD_BUY_THRESHOLD-h.food))
            bought = min(desired, stock, h.money//self.food_price)
            food_cost = bought*self.food_price
            h.money -= food_cost; h.last_living_cost += food_cost
            self._record_purchase(h, "Mat", f"{bought} portioner", food_cost)
            self._record_transaction("Matköp", food_cost, "Invånare", h.id,
                                     "Matmarknad", None, f"{bought} portioner")
            h.food += bought; stock -= bought; sold += bought
            h.hungry = consumed+bought < FOOD_MONTHLY_NEED
            h.hungry_months = h.hungry_months+1 if h.hungry else 0
        revenue = sold*self.food_price
        retailers = [w for w in self.workplaces if w.kind == "Mataffär" and w.employed]
        retail_revenue = int(revenue*.35) if retailers else 0
        farm_revenue = revenue-retail_revenue
        if farms and farm_revenue:
            total = sum(max(1, w.employed) for w in farms)
            distributed = 0
            for index, w in enumerate(farms):
                share = (farm_revenue-distributed if index == len(farms)-1
                         else farm_revenue*max(1, w.employed)//total)
                distributed += share
                w.money += share; w.monthly_profit += share
                self._record_transaction("Matförsäljning", share, "Matmarknad", None,
                                         "Företag", w.id, "Producentandel")
        if retailers and retail_revenue:
            total = sum(w.employed for w in retailers)
            distributed = 0
            for index, retailer in enumerate(retailers):
                share = (retail_revenue-distributed if index == len(retailers)-1
                         else retail_revenue*retailer.employed//total)
                distributed += share
                retailer.money += share; retailer.monthly_profit += share
                self._record_transaction("Matförsäljning", share, "Matmarknad", None,
                                         "Företag", retailer.id, "Butiksandel")
        # Unsold harvest becomes a local buffer instead of disappearing. Storage
        # is deliberately finite so several bad harvests still matter.
        for farm in farms:
            capacity = farm.capacity*FOOD_FARM_PER_EMPLOYEE_MONTH*FARM_STORAGE_MONTHS
            stored = min(stock, capacity)
            farm.stock_food = stored
            stock -= stored
            if stock <= 0: break
        self.last_food_sold = sold
        return sum(h.hungry for h in self.humans)

    def _evaluate_housing_market(self):
        signals = self._market_signals()
        build_cost = self._house_build_cost()
        expansion_cost = self._house_expansion_cost()
        needy = [h for h in self.humans if h.home_kind in ("Tält", "Bostadslös")]
        # Empty homes do not create demand for another building. Residents who
        # cannot pay rent are a poverty/service problem, not a capacity shortage.
        capacity_shortage = (bool(needy) and self._housing_capacity() < len(self.humans)
                             and signals["Bostad"] >= .25)
        homes_by_owner = {}
        for building in self.buildings:
            if building.active and building.kind == "Bostad" and building.owner_id is not None:
                homes_by_owner.setdefault(building.owner_id, []).append(building)

        expansion_ready = any(
            owner.money >= expansion_cost+max(HOUSING_BUFFER, owner.reserve_target)
            and self.month-owner.last_housing_investment_month >= 18
            and any(home.level < HOUSE_MAX_LEVEL for home in homes_by_owner.get(owner.id, []))
            for owner in self.humans
        )

        # Owning a home is an individual goal. Drives alter its strength, but
        # every solvent resident can eventually choose to build.
        builders = [h for h in self.humans if h.id not in homes_by_owner
                    and capacity_shortage
                    and h.money >= build_cost+max(HOUSING_BUFFER, h.reserve_target)
                    and self.month-h.last_housing_investment_month >= 12
                    and not (self.month % 4 == 0 and expansion_ready)]
        if builders:
            buyer = max(builders, key=lambda h: h.housing_motivation*(1.35 if h in needy else 1)
                        +h.disposable_money/250+h.money/1000)
            coords = self._claim_near_activity("Bostad", "#4aa3ff", buyer.id, 1)
            if coords:
                building = self._building_at(coords[0])
                building.housing_units = HOUSE_CAPACITY
                building.housing_type = ("Gård" if any(w.kind == "Jordbruk" and w.owner_id == buyer.id
                                                        for w in self.workplaces) else "Hydda")
                building.construction_month = self.month
                buyer.money -= build_cost
                self.money += build_cost
                self._record_transaction("Bostadsbyggande", build_cost, "Invånare", buyer.id,
                                         "Kommun", None, "Nytt småhus")
                self._record_purchase(buyer, "Boende", "Byggde eget hus", build_cost)
                buyer.last_housing_investment_month = self.month
                buyer.last_decision = f"Byggde eget {building.housing_type.lower()} för {build_cost} SM"
                buyer.decision_reasons = ["ville lämna sitt tillfälliga boende",
                                          "hade råd efter sin trygghetsbuffert"]
                self.last_development_revenue += build_cost
                return

        # Existing owners prefer extending a lived-in home to endlessly placing
        # new detached houses. Each extension adds two rentable rooms.
        extensions = []
        for owner_id, homes in homes_by_owner.items():
            owner = next((h for h in self.humans if h.id == owner_id), None)
            expandable = next((b for b in homes if b.level < HOUSE_MAX_LEVEL), None)
            if (owner and expandable and owner.money >= expansion_cost+max(HOUSING_BUFFER, owner.reserve_target)
                    and self.month-owner.last_housing_investment_month >= 18):
                extensions.append((owner.housing_motivation+owner.disposable_money/300,
                                   owner, expandable))
        if extensions:
            _, owner, building = max(extensions, key=lambda row: row[0])
            old_capacity = self._private_home_capacity(building)
            building.level += 1
            building.housing_units = old_capacity+2
            if building.housing_type != "Gård":
                building.housing_type = self._home_type(building)
            owner.money -= expansion_cost
            self.money += expansion_cost
            self._record_transaction("Bostadsbyggande", expansion_cost, "Invånare", owner.id,
                                     "Kommun", None, f"Utbyggnad nivå {building.level}")
            self._record_purchase(owner, "Boende", f"Byggde ut till nivå {building.level}", expansion_cost)
            owner.last_housing_investment_month = self.month
            owner.last_decision = f"Byggde ut bostaden för {expansion_cost} SM"
            owner.decision_reasons = ["ville förbättra sitt boende",
                                      "kunde behålla sin trygghetsbuffert"]
            self.last_development_revenue += expansion_cost

    def _maybe_upgrade_housing(self):
        self._evaluate_housing_market()

    def _assign_housing(self):
        houses = [b for b in self.buildings if b.kind == "Bostad" and b.active]
        apartments = [b for b in self.buildings if b.kind == "Flerfamiljshus" and b.active]
        hotels = [b for b in self.buildings if b.kind == "Hotell" and b.active]
        people = {h.id: h for h in self.humans}
        for h in self.humans:
            if h.home_kind in PERMANENT_HOME_KINDS or h.home_kind == "Hotell": h.home_kind = "Tält"
            h.home_owner_id = None
            h.home_x = h.home_y = None
        houses_by_owner = {}
        for house in houses:
            houses_by_owner.setdefault(house.owner_id, []).append(house)
        for owner_id, owned_houses in houses_by_owner.items():
            owner = people.get(owner_id)
            if owner:
                home_type = self._home_type(owned_houses[0])
                owner.home_kind = home_type; owner.home_owner_id = owner_id
                owner.home_x, owner.home_y = owned_houses[0].x, owned_houses[0].y
        room_rent = self.market.room_rent
        apartment_rent = self.market.apartment_rent
        hotel_rate = self.market.hotel_rate
        renters = sorted(
            (h for h in self.humans if h.home_kind not in PERMANENT_HOME_KINDS
             and h.money >= room_rent),
            key=lambda h: (h.housing_motivation, h.disposable_money, h.money),
            reverse=True,
        )
        renter_index = 0
        for owner_id, owned_houses in houses_by_owner.items():
            owner = people.get(owner_id)
            for index, house in enumerate(owned_houses):
                slots = self._private_home_capacity(house)-(1 if owner and index == 0 else 0)
                for _ in range(slots):
                    if renter_index >= len(renters): break
                    tenant = renters[renter_index]; renter_index += 1
                    tenant.money -= room_rent
                    tenant.last_living_cost += room_rent
                    self._record_purchase(tenant, "Boende", "Rumshyra", room_rent)
                    if owner:
                        owner.money += room_rent
                        self._record_transaction("Privathyra", room_rent, "Invånare", tenant.id,
                                                 "Invånare", owner.id, self._home_type(house))
                    else:
                        self._record_transaction("Privathyra", room_rent, "Invånare", tenant.id,
                                                 "Extern", None, "Ägare saknas")
                    tenant.home_kind = self._home_type(house); tenant.home_owner_id = owner_id
                    tenant.home_x, tenant.home_y = house.x, house.y
        for apartment in apartments:
            for _ in range(apartment.housing_units or APARTMENT_CAPACITY):
                if renter_index >= len(renters): break
                tenant = renters[renter_index]; renter_index += 1
                tenant.money -= apartment_rent; tenant.last_living_cost += apartment_rent
                self._record_purchase(tenant, "Boende", "Lägenhetshyra", apartment_rent)
                self.money += apartment_rent
                self._record_transaction("Kommunal hyra", apartment_rent, "Invånare", tenant.id,
                                         "Kommun", None, "Lägenhet")
                tenant.home_kind = "Lägenhet"; tenant.home_owner_id = 0
                tenant.home_x, tenant.home_y = apartment.x, apartment.y

        hotel_by_coordinate = {coordinate: workplace for workplace in self.workplaces
                               if workplace.kind == "Hotell" for coordinate in workplace.blocks}
        guests = sorted(
            (h for h in self.humans if h.home_kind not in PERMANENT_HOME_KINDS
             and h.money >= hotel_rate),
            key=lambda h: (h.housing_motivation, h.money), reverse=True,
        )
        guest_index = 0
        for hotel in hotels:
            for _ in range(hotel.housing_units or HOTEL_ROOMS_PER_BLOCK):
                if guest_index >= len(guests): break
                guest = guests[guest_index]; guest_index += 1
                guest.money -= hotel_rate
                guest.last_living_cost += hotel_rate
                self._record_purchase(guest, "Boende", "Hotellnatt", hotel_rate)
                business = hotel_by_coordinate.get((hotel.x, hotel.y))
                if business:
                    business.money += hotel_rate
                    business.monthly_profit += hotel_rate
                    self._record_transaction("Hotell", hotel_rate, "Invånare", guest.id,
                                             "Företag", business.id, "Övernattning")
                else:
                    self._record_transaction("Hotell", hotel_rate, "Invånare", guest.id,
                                             "Extern", None, "Verksamhet saknas")
                guest.home_kind = "Hotell"; guest.home_owner_id = hotel.owner_id
                guest.home_x, guest.home_y = hotel.x, hotel.y

    def _sync_tents(self):
        needed = math.ceil(sum(h.home_kind == "Tält" for h in self.humans)/TENT_CAPACITY)
        tents = [b for b in self.buildings if b.kind == "Tält" and b.active]
        for b in tents[needed:]: b.active = False; b.kind = "Övergiven"; b.color = "#6b6f7a"
        for _ in range(max(0, needed-len(tents))): self._claim_near_activity("Tält", "#4caf50", None, 1)
        tents = [b for b in self.buildings if b.kind == "Tält" and b.active]
        tent_residents = [h for h in self.humans if h.home_kind == "Tält"]
        for index, human in enumerate(tent_residents):
            if tents:
                tent = tents[min(len(tents)-1, index//TENT_CAPACITY)]
                human.home_x, human.home_y = tent.x, tent.y

    def _housing_capacity(self):
        houses = [b for b in self.buildings if b.kind == "Bostad" and b.active]
        owners = {b.owner_id for b in houses if b.owner_id is not None}
        private_capacity = sum(self._private_home_capacity(b) for b in houses)
        # Multiple houses owned by one person do not duplicate the owner slot.
        private_capacity -= max(0, len(houses)-len(owners))
        apartments = sum((b.housing_units or APARTMENT_CAPACITY) for b in self.buildings
                         if b.active and b.kind == "Flerfamiljshus")
        return private_capacity+apartments

    def _temporary_housing_capacity(self):
        return sum((b.housing_units or HOTEL_ROOMS_PER_BLOCK) for b in self.buildings
                   if b.active and b.kind == "Hotell")

    def _private_home_capacity(self, building):
        if building.housing_units:
            return building.housing_units
        return HOUSE_CAPACITY+(max(1, building.level)-1)*2

    def _home_type(self, building):
        if building.housing_type == "Gård" or any(
            w.kind == "Jordbruk" and w.owner_id == building.owner_id for w in self.workplaces
        ):
            building.housing_type = "Gård"
            return "Gård"
        home_type = {1: "Hydda", 2: "Stuga", 3: "Villa", 4: "Stort hus"}.get(building.level, "Stort hus")
        building.housing_type = home_type
        return home_type

    def _apply_housing_running_costs(self):
        homes = {(b.x, b.y): b for b in self.buildings if b.active and b.kind == "Bostad"}
        for human in self.humans:
            if human.home_owner_id != human.id: continue
            building = homes.get((human.home_x, human.home_y))
            if building is None: continue
            cost = HOME_RUNNING_COSTS.get(self._home_type(building), 0)
            paid = min(human.money, cost)
            human.money -= paid
            human.last_living_cost += cost
            self._record_purchase(human, "Boende", f"Drift {self._home_type(building)}", paid)
            self._record_transaction("Bostadsdrift", paid, "Invånare", human.id,
                                     "Extern", None, self._home_type(building))

    def _building_at(self, coordinate):
        return next(b for b in reversed(self.buildings)
                    if (b.x, b.y) == coordinate and b.active)

    def _mark_homeless(self, count):
        for h in [h for h in self.humans if h.home_kind == "Tält"][:count]:
            h.home_kind = "Bostadslös"; h.home_owner_id = None

    def _claim_block(self, kind, color, owner_id, cost_multiplier):
        coords = self._claim_near_activity(kind, color, owner_id, 1)
        if not coords: return None, None
        return next(b for b in self.buildings if (b.x, b.y) == coords[0]), max(BLOCK_COST_MIN, self.block_cost)*cost_multiplier

    def _update_health(self, hungry):
        for h in self.humans:
            shelter = 3 if h.home_kind == "Bostadslös" else 2 if h.home_kind == "Tält" and self.season() == "Vinter" else 0
            h.energy = max(0, min(100, h.energy+(2 if not h.hungry else -5)-shelter))
            h.health = max(0, min(100, h.health+(1 if h.energy > 50 and not h.hungry else -shelter-int(h.hungry))))
            h.sick = h.health < 40 or h.energy < 20
            h.homeless_months = h.homeless_months+1 if h.home_kind not in PERMANENT_HOME_KINDS else 0
        self.last_sick = sum(h.sick for h in self.humans)
        return self.last_sick

    def _update_dissatisfaction(self):
        for h in self.humans:
            jobless = h.job_id is None and not h.retired
            pressure = (4 if h.hungry else -2)+(2 if jobless else -1)
            pressure += 2 if h.home_kind == "Bostadslös" else 1 if h.home_kind == "Tält" else -1
            pressure += 2 if self.stability < 45 else -1
            if h.dependents:
                pressure += -1 if h.childcare_access else (1 if jobless else 0)
            pressure += max(0, math.ceil((self.tax_rate-.25)*12))
            h.unemployed_months = h.unemployed_months+1 if jobless else 0
            if h.unemployed_months >= 12: pressure += min(5, h.unemployed_months//12)
            financially_stressed = (h.last_living_cost > h.last_income
                                    and h.money < max(HOUSING_BUFFER, h.last_living_cost*2))
            h.financial_stress_months = (h.financial_stress_months+1 if financially_stressed
                                         else max(0, h.financial_stress_months-1))
            if h.financial_stress_months >= 6: pressure += 3
            h.dissatisfaction = max(0, min(100, h.dissatisfaction+pressure))

    def _update_population(self, season, net, hungry):
        people = len(self.humans)
        self.last_arrivals = self.last_departures = 0
        if not people:
            self.population = 0
            return

        job_vacancies = max(0, sum(w.capacity for w in self.workplaces)-self._employed_count())
        housing_capacity = self._housing_capacity()
        housing_vacancies = max(0, housing_capacity-sum(h.home_kind in PERMANENT_HOME_KINDS for h in self.humans))
        housing_vacancies += max(0, self._temporary_housing_capacity()
                                 -sum(h.home_kind == "Hotell" for h in self.humans))
        hungry_ratio = hungry/people
        homeless_ratio = sum(h.home_kind == "Bostadslös" for h in self.humans)/people
        unemployment_ratio = self.unemployed/people

        police_strength = self.service_states["Polis"].effectiveness
        self.crime_rate = max(.5, min(100,
            4+unemployment_ratio*32+homeless_ratio*24+(100-self.stability)*.18-police_strength*22
        ))

        expected_services = 0
        for threshold in (20, 35, 50, 75, 110):
            if people >= threshold: expected_services += 1
        active_service = sum(state.effectiveness for state in self.service_states.values())
        service_gap = max(0, expected_services-active_service)

        low_tax_bonus = max(-20, min(24, (0.20-self.tax_rate)*125))
        opportunity_bonus = min(24, job_vacancies*5)+min(24, housing_vacancies*7)
        fundamentals = (self.stability-50)*.28+(12 if hungry_ratio < .05 else -hungry_ratio*55)
        penalties = self.crime_rate*.42+service_gap*5+homeless_ratio*20+unemployment_ratio*18
        self.attractiveness = max(0, min(100, 42+low_tax_bonus+opportunity_bonus+fundamentals-penalties))

        # A good settlement attracts a steady trickle. Actual vacant homes and jobs
        # turn that trickle into a wave; newcomers may accept tents when jobs exist.
        if self.attractiveness >= 52 and hungry_ratio < .2:
            arrivals = 1
            arrivals += int((self.attractiveness-52)//24)
            arrivals += min(housing_vacancies, job_vacancies)//2
            if housing_vacancies and job_vacancies:
                arrivals += min(1, max(housing_vacancies, job_vacancies)//4)
            arrivals = min(arrivals, max(2, math.ceil(people*.08)), 5)
            farms = [w for w in self.workplaces if w.kind == "Jordbruk"]
            sustainable_food = (sum(w.employed*FOOD_FARM_PER_EMPLOYEE_MONTH for w in farms)
                                +sum(w.stock_food for w in farms)/6)
            sustainable_population = int(sustainable_food/(FOOD_MONTHLY_NEED*1.15))
            # One hopeful newcomer may still arrive while stocks are healthy, but
            # sustained waves require enough local production for the newcomers.
            arrivals = min(arrivals, max(1, sustainable_population-people))
            newcomers = [self._new_human() for _ in range(arrivals)]
            self.humans.extend(newcomers)
            for newcomer in newcomers:
                self._record_transaction("Inflyttat kapital", newcomer.money, "Extern", None,
                                         "Invånare", newcomer.id, newcomer.name)
            self._house_newcomers_in_hotels(newcomers)
            self.last_arrivals = arrivals

        leavers = [h for h in self.humans if h.dissatisfaction >= 65 and (
            h.hungry_months >= 2 or h.unemployed_months >= 12
            or h.financial_stress_months >= 6 or self.tax_rate >= .5)]
        departure_pressure = max(1, math.ceil((45-self.attractiveness)/12)) if self.attractiveness < 45 else 1
        for h in sorted(leavers, key=lambda resident: resident.dissatisfaction, reverse=True)[:departure_pressure]:
            self._remove_resident(h, "flyttade ut")
            self.last_departures += 1
        self.population = len(self.humans)

    def _house_newcomers_in_hotels(self, newcomers):
        hotel_rate = self.market.hotel_rate
        hotels = [b for b in self.buildings if b.active and b.kind == "Hotell"]
        occupied = {(b.x, b.y): sum(h.home_kind == "Hotell" and h.home_x == b.x and h.home_y == b.y
                                    for h in self.humans) for b in hotels}
        businesses = {coordinate: workplace for workplace in self.workplaces
                      if workplace.kind == "Hotell" for coordinate in workplace.blocks}
        for newcomer in newcomers:
            hotel = next((b for b in hotels if occupied[(b.x, b.y)] <
                          (b.housing_units or HOTEL_ROOMS_PER_BLOCK) and newcomer.money >= hotel_rate), None)
            if hotel is None: continue
            newcomer.money -= hotel_rate
            newcomer.last_living_cost += hotel_rate
            self._record_purchase(newcomer, "Boende", "Första hotellnatten", hotel_rate)
            business = businesses.get((hotel.x, hotel.y))
            if business:
                business.money += hotel_rate
                business.monthly_profit += hotel_rate
                self._record_transaction("Hotell", hotel_rate, "Invånare", newcomer.id,
                                         "Företag", business.id, "Första övernattning")
            else:
                self._record_transaction("Hotell", hotel_rate, "Invånare", newcomer.id,
                                         "Extern", None, "Verksamhet saknas")
            newcomer.home_kind = "Hotell"; newcomer.home_owner_id = hotel.owner_id
            newcomer.home_x, newcomer.home_y = hotel.x, hotel.y
            occupied[(hotel.x, hotel.y)] += 1

    def _apply_public_budget(self):
        base = int(len(self.humans)*.4*self.budget_allocations["Basutgifter"]/100)
        service_requests = self._service_operating_requests()
        allocated_requests = {
            name: int(cost*self.budget_allocations["Service"]/100)
            for name, cost in service_requests.items()
        }
        service = sum(allocated_requests.values())
        winter = int(base*{"Norra": .5, "Medel": .25, "Syd": .1}.get(self.region, .25)) if self.season() == "Vinter" else 0
        seasonal = int(winter*self.budget_allocations["Säsong"]/100)
        base_paid = min(self.money, base); self.money -= base_paid
        service_paid = min(self.money, service); self.money -= service_paid
        seasonal_paid = min(self.money, seasonal); self.money -= seasonal_paid
        self._record_transaction("Kommunal basdrift", base_paid, "Kommun", None,
                                 "Extern", None, "Varor och entreprenader")
        self.last_service_operating_paid = {name: 0 for name in self.services}
        remaining = service_paid
        outstanding = service
        for name, requested in allocated_requests.items():
            paid = (remaining if requested == outstanding else
                    min(remaining, round(service_paid*requested/max(1, service))))
            self.last_service_operating_paid[name] = paid
            remaining -= paid
            outstanding -= requested
            self._record_transaction("Servicedrift", paid, "Kommun", None,
                                     "Extern", None, name)
        self._record_transaction("Säsongskostnad", seasonal_paid, "Kommun", None,
                                 "Extern", None, self.season())
        self.expenses = (base_paid+service_paid+seasonal_paid+self.last_unemployment_support
                         +self.last_public_payroll+self.last_public_investment)
        self.last_revenue = self.last_tax_revenue
        self.last_expenses = {"Basutgifter": base_paid, "Service": service_paid, "Säsong": seasonal_paid,
                              "A-kassa utbetalningar": self.last_unemployment_support,
                              "Kommunala löner": self.last_public_payroll,
                              "Investeringar": self.last_public_investment}
        self.year_revenue += self.last_revenue+self.last_development_revenue
        self.year_expenses += self.expenses
        if self.month%12 == 0:
            self.last_year_revenue, self.last_year_expenses = self.year_revenue, self.year_expenses
            self.year_revenue = self.year_expenses = 0
        food_ratio = self.last_hungry/max(1, len(self.humans))
        homeless = sum(h.home_kind == "Bostadslös" for h in self.humans)/max(1, len(self.humans))
        jobless = self.unemployed/max(1, len(self.humans))
        self.stability = max(0, min(100, self.stability+round(2-food_ratio*12-homeless*5-jobless*3)))
        self.last_hungry = sum(h.hungry for h in self.humans); self.last_unemployed = self.unemployed

    def budget_snapshot(self):
        people = len(self.humans)
        payroll_month = sum(round(WORKPLACE_RULES[w.kind]["wage"]*self.market.wage_index)*w.employed
                            for w in self.workplaces)
        base_month = int(people*.4*self.budget_allocations["Basutgifter"]/100)
        service_items = {}
        service_month = 0
        operating_requests = self._service_operating_requests()
        for name, enabled in self.services.items():
            funding = self.service_funding.get(name, 0)
            administration = int(operating_requests[name]*self.budget_allocations["Service"]/100)
            public_job = next((w for w in self.workplaces if w.service_name == name), None)
            jobs = public_job.capacity if public_job else (
                min(self._service_target_positions(name),
                    self._service_facility_positions(name))
                if enabled and funding > 0 else 0
            )
            processable = min(self.unemployed, jobs*30)
            replacement = .25+.55*funding/100
            transfer = (int(round(WORKPLACE_RULES["Basjobb"]["wage"]*self.market.wage_index)*replacement)*processable
                        if name == "A-kassa" and enabled else 0)
            payroll = jobs*round(WORKPLACE_RULES["Service"]["wage"]*self.market.wage_index)
            state = self.service_states[name]
            service_items[name] = {"enabled": enabled, "funding": funding,
                                   "administration": administration, "transfer": transfer,
                                   "jobs": jobs, "payroll": payroll,
                                   "demand": state.demand,
                                   "facility_positions": state.facility_positions,
                                   "staffed": state.staffed,
                                   "coverage": state.coverage,
                                   "effectiveness": state.effectiveness,
                                   "workload": state.workload,
                                   "monthly": administration+transfer+payroll}
            service_month += administration+payroll
        support_month = service_items["A-kassa"]["transfer"]
        winter_month = int(base_month*{"Norra": .5, "Medel": .25, "Syd": .1}.get(self.region, .25)
                           *self.budget_allocations["Säsong"]/100)
        annual_income = int(payroll_month*(1-.08)*self.tax_rate)*12
        annual_base = base_month*12
        annual_service = service_month*12
        annual_support = support_month*12
        annual_seasonal = winter_month*3
        annual_cost = annual_base+annual_service+annual_support+annual_seasonal
        projected_net = annual_income-annual_cost
        annual_payroll = payroll_month*12
        break_even_tax = annual_cost/annual_payroll if annual_payroll else None
        monthly_deficit = max(0, -projected_net/12)
        runway = (self.money/monthly_deficit if monthly_deficit else None)
        return {
            "treasury": self.money, "payroll_month": payroll_month,
            "annual_income": annual_income, "annual_base": annual_base,
            "annual_service": annual_service, "annual_support": annual_support,
            "annual_seasonal": annual_seasonal, "annual_cost": annual_cost,
            "projected_net": projected_net, "break_even_tax": break_even_tax,
            "runway_months": runway, "service_items": service_items,
            "last_tax_revenue": self.last_tax_revenue,
            "last_development_revenue": self.last_development_revenue,
            "last_public_investment": self.last_public_investment,
            "last_public_payroll": self.last_public_payroll,
        }

    def _apply_status_purchases(self):
        for h in self.humans:
            cadence = {"status": 3, "risk": 5, "sparsam": 12}.get(h.drive, 7)
            due = self.month-h.last_discretionary_purchase_month >= cadence
            available = max(0, h.money-h.reserve_target)
            if (due and h.home_kind in PERMANENT_HOME_KINDS and not h.hungry
                    and available >= 10 and h.consumption_motivation >= 1.05):
                h.money -= 10; h.status_items += 1
                h.last_discretionary_purchase_month = self.month
                h.last_decision = "Köpte en statuspryl för 10 SM"
                h.decision_reasons = ["hade pengar över sin trygghetsbuffert",
                                      f"intresset {h.drive} ökade köpviljan"]
                self._record_purchase(h, "Fritid", "Statuspryl", 10)
                self._settle_consumer_spending(h, 10, "Fritidsköp", "Statuspryl", ("Service", "Mataffär"))
            elif due and not h.hungry and available >= 6 and h.consumption_motivation >= .75:
                h.money -= 6
                h.leisure_items += 1
                h.last_discretionary_purchase_month = self.month
                h.last_decision = "Köpte en fritidsaktivitet för 6 SM"
                h.decision_reasons = ["grundbehoven och trygghetsbufferten var täckta"]
                self._record_purchase(h, "Fritid", "Fritidsaktivitet", 6)
                self._settle_consumer_spending(h, 6, "Fritidsköp", "Fritidsaktivitet", ("Service", "Hotell"))

    def _apply_unemployment_support(self):
        self.last_unemployment_support = 0
        if not self.services.get("A-kassa"): return
        unemployed = [h for h in self.humans if h.job_id is None and not h.retired]
        if not unemployed: return
        state = self.service_states["A-kassa"]
        processable = min(len(unemployed), int(state.staffed*30*state.supply_ratio*state.access_ratio))
        if processable <= 0: return
        replacement = .25+.55*self.service_funding["A-kassa"]/100
        requested = int(round(WORKPLACE_RULES["Basjobb"]["wage"]*self.market.wage_index)*replacement)
        if requested <= 0: return
        recipients = sorted(
            unemployed,
            key=lambda h: (h.unemployed_months, h.financial_stress_months, -h.money),
            reverse=True,
        )[:processable]
        payout = min(requested, self.money//len(recipients))
        if payout <= 0: return
        for h in recipients:
            h.money += payout
            h.last_income += payout
            self._record_transaction("A-kassa", payout, "Kommun", None,
                                     "Invånare", h.id, "Arbetslöshetsersättning")
        self.last_unemployment_support = payout*len(recipients)
        self.money -= self.last_unemployment_support

    def _apply_pensions(self):
        pensioners = [h for h in self.humans if h.retired]
        for human in pensioners:
            requested = max(8, min(40, math.ceil(human.pension_balance/180)))
            payout = min(requested, human.pension_balance, self.central_bank.reserves)
            if payout <= 0: continue
            human.pension_balance -= payout
            human.money += payout
            human.last_income += payout
            self.central_bank.reserves -= payout
            self.central_bank.pension_assets = max(0, self.central_bank.pension_assets-payout)
            self.central_bank.last_pension_payouts += payout
            self._record_transaction("Pension", payout, "Centralbank", None,
                                     "Invånare", human.id, "Pensionsutbetalning")

    def _apply_bankruptcy(self):
        for h in self.humans:
            if h.money <= 0 and h.home_owner_id == h.id:
                for b in self.buildings:
                    if b.kind == "Bostad" and b.owner_id == h.id:
                        b.active = False; b.kind = "Övergiven"; b.owner_id = None
                h.job_id = None; h.home_kind = "Tält"; h.home_owner_id = None

    def _take_loan(self, target, amount):
        business_limit = getattr(target, "capacity", 0)*getattr(target, "wage", 0)*3
        credit_limit = max(40, target.money*4, business_limit)
        if (amount <= 0 or amount+target.loan_balance > credit_limit
                or amount > self.central_bank.reserves): return False
        target.loan_balance += amount; target.money += amount
        self.central_bank.reserves -= amount
        self.central_bank.outstanding_loans += amount
        target_type = "Företag" if isinstance(target, Workplace) else "Invånare"
        self._record_transaction("Banklån", amount, "Centralbank", None,
                                 target_type, getattr(target, "id", None), "Nytt lån")
        return True

    def _apply_bank_interest_and_loans(self):
        self.last_bank_rate = max(.01, min(.10, .01+(100-self.stability)/1000))
        self.central_bank.policy_rate = self.last_bank_rate
        if self.month%12: return
        for target in [*self.humans, *self.workplaces]:
            if target.loan_balance <= 0: continue
            interest = int(target.loan_balance*self.last_bank_rate)
            payment = min(target.money, interest+max(1, int(target.loan_balance*.1)))
            principal = min(target.loan_balance, max(0, payment-interest))
            target.money -= payment; target.loan_balance -= principal
            self.central_bank.reserves += payment
            self.central_bank.outstanding_loans = max(0, self.central_bank.outstanding_loans-principal)
            self.central_bank.last_interest_income += min(payment, interest)
            target_type = "Företag" if isinstance(target, Workplace) else "Invånare"
            self._record_transaction("Lånebetalning", payment, target_type,
                                     getattr(target, "id", None), "Centralbank", None,
                                     f"Ränta {min(payment, interest)} SM")

    def _cleanup_abandoned_workplaces(self):
        kept = []
        for w in self.workplaces:
            if w.service_name:
                w.idle_months = 0
                kept.append(w)
                continue
            w.idle_months = w.idle_months+1 if w.employed == 0 else 0
            if w.idle_months < 18 or w.kind == "Jordbruk": kept.append(w); continue
            owner = next((h for h in self.humans if h.id == w.owner_id), None)
            if owner:
                owner.money += w.money
                self._record_transaction("Företagsavveckling", w.money, "Företag", w.id,
                                         "Invånare", owner.id, w.kind)
            elif w.money:
                self._record_transaction("Företagsavveckling", w.money, "Företag", w.id,
                                         "Extern", None, w.kind)
            self.central_bank.outstanding_loans = max(0, self.central_bank.outstanding_loans-w.loan_balance)
            for b in self.buildings:
                if (b.x, b.y) in w.blocks: b.active = False; b.kind = "Övergiven"; b.owner_id = None
        self.workplaces = kept

    # ---------- Physical civic centre and municipal housing ----------
    def _service_demand(self, name):
        people = len(self.humans)
        if people == 0:
            return 0.0
        demand = people*SERVICE_STAFF_PER_RESIDENT[name]
        if name == "Polis":
            demand += self.crime_rate*people/2500
        elif name == "Brandkår":
            demand += sum(b.active for b in self.buildings)/180
        elif name == "Sjukvård":
            demand += sum(h.sick for h in self.humans)/4
        elif name == "A-kassa":
            demand += self.unemployed/30
        return max(0.0, demand)

    def _service_target_positions(self, name):
        if not self.services.get(name) or self.service_funding.get(name, 0) <= 0:
            return 0
        return math.ceil(self._service_demand(name)*self.service_funding[name]/100)

    def _service_buildings(self, name):
        return [b for b in self.buildings if b.active and b.kind == name]

    def _service_facility_positions(self, name):
        return len(self._service_buildings(name))*SERVICE_STAFF_PER_BUILDING[name]

    def _service_access_ratio(self, name):
        buildings = self._service_buildings(name)
        if not buildings or not self.humans:
            return 0.0
        access = 0.0
        for human in self.humans:
            if human.home_x is None or human.home_y is None:
                access += .35
                continue
            distance = min(abs(human.home_x-b.x)+abs(human.home_y-b.y) for b in buildings)
            travel_range = TRANSPORT_MODES[self._transport_mode(human)]["range"]
            access += 1/(1+distance/max(4, travel_range))
        return access/len(self.humans)

    def _individual_service_effect(self, human, name):
        state = self.service_states[name]
        buildings = self._service_buildings(name)
        if not buildings or state.staffed <= 0 or state.supply_ratio <= 0:
            return 0.0
        if human.home_x is None or human.home_y is None:
            access = .35
        else:
            distance = min(abs(human.home_x-b.x)+abs(human.home_y-b.y) for b in buildings)
            travel_range = TRANSPORT_MODES[self._transport_mode(human)]["range"]
            access = 1/(1+distance/max(4, travel_range))
        delivered = state.staffed*state.supply_ratio
        return (1-math.exp(-2*delivered/max(.01, state.demand)))*access

    def _building_service_effect(self, building, name):
        state = self.service_states[name]
        service_buildings = self._service_buildings(name)
        if not service_buildings or state.staffed <= 0 or state.supply_ratio <= 0:
            return 0.0
        distance = min(abs(building.x-b.x)+abs(building.y-b.y) for b in service_buildings)
        access = 1/(1+distance/12)
        delivered = state.staffed*state.supply_ratio
        return (1-math.exp(-2*delivered/max(.01, state.demand)))*access

    def _apply_service_outcomes(self):
        self.last_healthcare_treated = self.last_crime_victims = 0
        self.last_fire_incidents = self.last_students_supported = 0
        self.last_childcare_supported = 0
        for human in self.humans:
            human.childcare_access = False

            healthcare = self._individual_service_effect(human, "Sjukvård")
            illness_risk = .004+max(0, human.age-55)*.00035
            illness_risk += .012 if human.home_kind in ("Tält", "Bostadslös") else 0
            if self._rng.random() < illness_risk:
                damage = self._rng.randint(4, 12)
                human.health = max(0, human.health-damage)
                human.sick = True
                human.last_events.append(f"Blev sjuk (−{damage} hälsa)")
            treatment_chance = .05+.65*healthcare
            if human.sick and self._rng.random() < treatment_chance:
                recovery = max(2, round(4+10*healthcare))
                human.health = min(100, human.health+recovery)
                human.energy = min(100, human.energy+max(1, recovery//3))
                human.healthcare_visits += 1
                self.last_healthcare_treated += 1
                human.last_events.append(f"Fick vård (+{recovery} hälsa)")

            police = self._individual_service_effect(human, "Polis")
            victim_risk = max(.0005, self.crime_rate/100*.025*(1-.70*police))
            if self._rng.random() < victim_risk:
                loss = min(human.money, self._rng.randint(2, 12))
                human.money -= loss
                human.crime_victimizations += 1
                human.dissatisfaction = min(100, human.dissatisfaction+6)
                self.last_crime_victims += 1
                human.last_events.append(f"Utsatt för brott (−{loss} SM)")
                self._record_transaction("Brottsförlust", loss, "Invånare", human.id,
                                         "Extern", None, human.name)

            school = self._individual_service_effect(human, "Skola")
            if human.age <= 35 and self._rng.random() < .35*school:
                gain = round(.5+school, 2)
                human.education_level = min(100, human.education_level+gain)
                human.school_months += 1
                self.last_students_supported += 1
                human.last_events.append(f"Utbildning (+{gain:.1f} kompetens)")

            childcare = self._individual_service_effect(human, "Barnomsorg")
            if human.dependents and self._rng.random() < childcare:
                human.childcare_access = True
                human.childcare_months += 1
                human.energy = min(100, human.energy+2)
                self.last_childcare_supported += 1
                human.last_events.append("Fick barnomsorg och mer vardagsork")

            human.sick = human.health < 40 or human.energy < 20

        candidates = [b for b in self.buildings if b.active and b.kind not in ("Torg", "Centrum")]
        for building in candidates:
            fire_service = self._building_service_effect(building, "Brandkår")
            base_risk = .003 if building.kind == "Industri" else .001
            if self._rng.random() >= base_risk*(1-.80*fire_service):
                continue
            self.last_fire_incidents += 1
            repair_cost = 12
            owner = next((h for h in self.humans if h.id == building.owner_id), None)
            if owner:
                paid = min(owner.money, repair_cost)
                owner.money -= paid
                owner.dissatisfaction = min(100, owner.dissatisfaction+4)
                owner.last_events.append(f"Brandskada på fastighet (−{paid} SM)")
                self._record_transaction("Brandskada", paid, "Invånare", owner.id,
                                         "Extern", None, f"Block ({building.x}, {building.y})")
            else:
                self.stability = max(0, self.stability-1)
        self.last_sick = sum(h.sick for h in self.humans)

    def _service_operating_requests(self):
        requests = {}
        for name in self.services:
            if not self.services[name] or self.service_funding.get(name, 0) <= 0:
                requests[name] = 0
                continue
            workplace = next((w for w in self.workplaces if w.service_name == name), None)
            staffed = workplace.employed if workplace else 0
            buildings = len(self._service_buildings(name))
            requests[name] = buildings*self.service_costs[name] + math.ceil(
                staffed*self.service_costs[name]/2
            )
        return requests

    def _update_service_capacity(self):
        requests = self._service_operating_requests()
        for name, state in self.service_states.items():
            workplace = next((w for w in self.workplaces if w.service_name == name), None)
            state.demand = self._service_demand(name)
            state.target_positions = self._service_target_positions(name)
            state.facility_positions = self._service_facility_positions(name)
            state.staffed = workplace.employed if workplace else 0
            state.requested_operating = requests[name]
            state.paid_operating = self.last_service_operating_paid.get(name, 0)
            state.supply_ratio = (min(1.0, state.paid_operating/state.requested_operating)
                                  if state.requested_operating else 0.0)
            state.access_ratio = self._service_access_ratio(name)
            delivered = state.staffed*state.supply_ratio
            state.coverage = min(1.0, delivered/max(.01, state.demand))
            state.workload = state.demand/max(.01, delivered) if state.demand else 0.0
            # Diminishing returns ensure that even a fully funded service reduces
            # risk instead of becoming a switch that guarantees a perfect result.
            state.effectiveness = ((1-math.exp(-2*delivered/max(.01, state.demand)))
                                   *state.access_ratio if state.demand else 0.0)

    def _sync_public_service_jobs(self):
        public = {w.service_name: w for w in self.workplaces if w.service_name}
        active_names = set()
        for name, enabled in self.services.items():
            buildings = self._service_buildings(name)
            funding = self.service_funding.get(name, 0)
            if not enabled or funding <= 0 or not buildings: continue
            active_names.add(name)
            capacity = min(self._service_target_positions(name), self._service_facility_positions(name))
            if capacity <= 0: continue
            workplace = public.get(name)
            if workplace is None:
                workplace = Workplace(
                    self.next_workplace_id, "Service", WORKPLACE_RULES["Service"]["wage"], capacity,
                    strain=WORKPLACE_RULES["Service"]["strain"], owner_id=None, money=0,
                    blocks=[(b.x, b.y) for b in buildings], demand_score=10, service_name=name,
                )
                self.next_workplace_id += 1
                self.workplaces.append(workplace)
            else:
                workplace.capacity = capacity
                workplace.blocks = [(b.x, b.y) for b in buildings]
        self.workplaces = [w for w in self.workplaces if not w.service_name or w.service_name in active_names]

    def _develop_civic_center(self):
        service_build_cost = max(1, round(SERVICE_BUILD_COST*self.market.construction_index))
        conversion_cost = max(1, service_build_cost//3)
        civic_block_cost = max(1, round(CIVIC_BLOCK_COST*self.market.construction_index))
        active_services = [name for name, enabled in self.services.items()
                           if enabled and self.service_funding.get(name, 0) > 0]
        service_kinds = set(SERVICE_COLORS)
        existing_services = [b for b in self.buildings if b.active and b.kind in service_kinds]

        for name in active_services:
            desired = math.ceil(self._service_target_positions(name)/SERVICE_STAFF_PER_BUILDING[name])
            if len(self._service_buildings(name)) >= desired: continue
            # A sufficiently empty apartment block is deliberately reusable as
            # school, clinic or another public building.
            convertible = next((b for b in self.buildings
                if b.active and b.kind == "Flerfamiljshus"
                and self._housing_capacity()-(b.housing_units or APARTMENT_CAPACITY) >= len(self.humans)), None)
            if convertible is not None and self.money >= conversion_cost:
                self.money -= conversion_cost
                self._record_transaction("Kommunal investering", conversion_cost,
                                         "Kommun", None, "Extern", None, f"Konvertering till {name}")
                self.last_public_investment += conversion_cost
                convertible.kind, convertible.color = name, SERVICE_COLORS[name]
                convertible.housing_units, convertible.service_name = 0, name
                existing_services.append(convertible)
                continue
            if self.money < service_build_cost: continue
            building = self._claim_central_building(name, SERVICE_COLORS[name])
            if building:
                building.service_name = name; building.construction_month = self.month
                self.money -= service_build_cost
                self._record_transaction("Kommunal investering", service_build_cost,
                                         "Kommun", None, "Extern", None, name)
                self.last_public_investment += service_build_cost
                existing_services.append(building)

        # Service buildings pull additional mixed-use centre blocks around them.
        target = len(existing_services)+len(self.humans)//75
        current = sum(b.active and b.kind == "Centrum" for b in self.buildings)
        if current < target and self.money >= civic_block_cost:
            if self._claim_central_building("Centrum", "#c45a55"):
                self.money -= civic_block_cost
                self._record_transaction("Kommunal investering", civic_block_cost,
                                         "Kommun", None, "Extern", None, "Centrum")
                self.last_public_investment += civic_block_cost

    def _develop_apartment_housing(self):
        apartment_build_cost = max(1, round(APARTMENT_BUILD_COST*self.market.construction_index))
        shortage = len(self.humans)-self._housing_capacity()
        civic_exists = any(b.active and (b.kind == "Centrum" or b.kind in SERVICE_COLORS)
                           for b in self.buildings)
        if len(self.humans) < 35 or shortage < 1 or not civic_exists or self.money < apartment_build_cost:
            return
        building = self._claim_central_building("Flerfamiljshus", "#8b78a8")
        if building:
            building.housing_units = APARTMENT_CAPACITY
            building.construction_month = self.month
            self.money -= apartment_build_cost
            self._record_transaction("Kommunal investering", apartment_build_cost,
                                     "Kommun", None, "Extern", None, "Flerfamiljshus")
            self.last_public_investment += apartment_build_cost

    def _claim_central_building(self, kind, color):
        used = {(b.x, b.y) for b in self.buildings if b.active}
        inactive = {(b.x, b.y): b for b in self.buildings if not b.active}
        anchors = [b for b in self.buildings if b.active and
                   (b.kind in ("Torg", "Centrum", "Flerfamiljshus") or b.kind in SERVICE_COLORS)]
        anchors.sort(key=lambda b: b.centrality, reverse=True)
        for distance in range(1, 8):
            candidates = set()
            for anchor in anchors[:12]:
                for dx in range(-distance, distance+1):
                    dy = distance-abs(dx)
                    candidates.add((anchor.x+dx, anchor.y+dy))
                    candidates.add((anchor.x+dx, anchor.y-dy))
            candidates = [(x, y) for x, y in candidates if
                          BUILD_MARGIN <= x < self.grid_size-BUILD_MARGIN
                          and BUILD_MARGIN <= y < self.grid_size-BUILD_MARGIN and (x, y) not in used]
            if not candidates: continue
            x, y = min(candidates, key=lambda pos: (abs(pos[0]-self.grid_size//2)+abs(pos[1]-self.grid_size//2), self._rng.random()))
            building = inactive.get((x, y))
            if building:
                building.kind, building.color, building.owner_id, building.active = kind, color, None, True
            else:
                building = Building(x, y, color, kind, owner_id=None, construction_month=self.month)
                self.buildings.append(building)
            return building
        return None

    def _update_centrality(self):
        weights = {"Torg": 2, "Mataffär": 3, "Service": 3, "Basjobb": 2,
                   "Industri": 2, "Jordbruk": 1, "Bostad": 1, "Tält": .25,
                   "Centrum": 3, "Flerfamiljshus": 2.5, "Polis": 3,
                   "Brandkår": 3, "Sjukvård": 3, "Skola": 3,
                   "Barnomsorg": 3, "A-kassa": 2}
        active = [b for b in self.buildings if b.active]
        by_position = {(b.x, b.y): b for b in active}
        scores = {}
        for b in active:
            local = weights.get(b.kind, 0)
            for dx in range(-6, 7):
                remaining = 6-abs(dx)
                for dy in range(-remaining, remaining+1):
                    if dx == 0 and dy == 0: continue
                    other = by_position.get((b.x+dx, b.y+dy))
                    if other is not None:
                        local += weights.get(other.kind, 0)/(1+abs(dx)+abs(dy))
            b.centrality = round(local, 2); scores[(b.x, b.y)] = b.centrality
        self.centrality = scores

    def central_blocks(self, limit=5):
        return sorted(self.centrality.items(), key=lambda row: row[1], reverse=True)[:limit]

    def _employed_count(self):
        return sum(h.job_id is not None for h in self.humans)

    def _calc_food_status(self):
        return 1-self.last_hungry/max(1, len(self.humans))

    def to_dict(self):
        keys = ("name", "size_label", "region", "money", "population", "stability", "expenses",
                "tax_rate", "services", "service_costs", "service_funding", "budget_allocations",
                "block_cost", "block_restore_cost", "food_price", "unemployed", "month", "history",
                "history_year", "last_revenue", "last_expenses", "last_hungry", "last_sick",
                "last_unemployed", "last_food_supply", "last_food_sold", "last_bank_rate",
                "year_revenue", "year_expenses", "last_year_revenue", "last_year_expenses",
                "next_human_id", "next_workplace_id", "attractiveness", "crime_rate",
                "last_arrivals", "last_departures", "last_unemployment_support",
                "last_tax_revenue", "last_development_revenue", "last_public_investment",
                "last_public_payroll", "last_deaths", "last_retirements", "population_events",
                "last_external_inflow", "last_external_outflow", "last_money_discrepancy",
                "last_money_supply", "last_healthcare_treated", "last_crime_victims",
                "last_fire_incidents", "last_students_supported", "last_childcare_supported")
        data = {k: getattr(self, k) for k in keys}
        data.update(buildings=[b.__dict__ for b in self.buildings], humans=[h.__dict__ for h in self.humans],
                    workplaces=[w.__dict__ for w in self.workplaces],
                    service_states={name: state.__dict__ for name, state in self.service_states.items()},
                    last_service_operating_paid=self.last_service_operating_paid,
                    market=self.market.__dict__,
                    central_bank=self.central_bank.__dict__,
                    transactions=[t.__dict__ for t in self.transactions])
        return data

    @staticmethod
    def from_dict(data):
        world = World(WorldConfig(data.get("name", "Ny värld"), data.get("size_label", "Medium"), data.get("region", "Medel")))
        has_household_plans = all("reserve_target" in row for row in data.get("humans", []))
        skip = {"buildings", "humans", "workplaces", "central_bank", "transactions", "service_states", "market",
                "name", "size_label", "region"}
        for key, value in data.items():
            if key not in skip and hasattr(world, key): setattr(world, key, value)
        world.buildings = [Building(**{k:v for k,v in row.items() if k in Building.__dataclass_fields__}) for row in data.get("buildings", [])]
        world.humans = [Human(**{k:v for k,v in row.items() if k in Human.__dataclass_fields__}) for row in data.get("humans", [])]
        world.workplaces = [Workplace(**{k:v for k,v in row.items() if k in Workplace.__dataclass_fields__}) for row in data.get("workplaces", [])]
        world.transactions = [Transaction(**{k:v for k,v in row.items()
                                              if k in Transaction.__dataclass_fields__})
                              for row in data.get("transactions", [])]
        for name, row in data.get("service_states", {}).items():
            if name in world.service_states:
                world.service_states[name] = ServiceState(**{
                    k: v for k, v in row.items() if k in ServiceState.__dataclass_fields__
                })
        market_data = data.get("market", {})
        if market_data:
            world.market = MarketState(**{
                k: v for k, v in market_data.items() if k in MarketState.__dataclass_fields__
            })
        else:
            world.market.food_price = int(data.get("food_price", FOOD_PRICE))
        world.food_price = world.market.food_price
        bank_data = data.get("central_bank", {})
        world.central_bank = CentralBank(**{k:v for k,v in bank_data.items()
                                            if k in CentralBank.__dataclass_fields__})
        for human in world.humans: world._transport_mode(human)
        if not bank_data:
            world.central_bank.pension_assets = sum(h.pension_balance for h in world.humans)
            world.central_bank.outstanding_loans = (sum(h.loan_balance for h in world.humans)
                                                    +sum(w.loan_balance for w in world.workplaces))
        if "last_money_supply" not in data:
            world.last_money_supply = world._money_supply()
        world.population = len(world.humans); world._update_centrality()
        if not has_household_plans:
            world._update_household_plans()
        return world
