from __future__ import annotations

from dataclasses import dataclass, field

@dataclass
class WorldConfig:
    name: str
    size_label: str
    region: str

@dataclass
class Building:
    x: int
    y: int
    color: str
    kind: str
    active: bool = True
    owner_id: int | None = None
    centrality: float = 0.0
    level: int = 1
    housing_units: int = 0
    construction_month: int = 0
    service_name: str | None = None
    housing_type: str | None = None

@dataclass
class Human:
    id: int
    money: int
    name: str = "Invånare"
    age: int = 18
    drive: str = "sparsam"
    job_id: int | None = None
    hungry: bool = False
    energy: int = 100
    health: int = 100
    sick: bool = False
    food: int = 40
    status_items: int = 0
    loan_balance: int = 0
    loan_years_missed: int = 0
    homeless_months: int = 0
    home_kind: str = "Tält"
    home_owner_id: int | None = None
    dissatisfaction: float = 0.0
    hungry_months: int = 0
    unemployed_months: int = 0
    housing_ambition: float = 1.0
    last_housing_investment_month: int = -24
    home_x: int | None = None
    home_y: int | None = None
    has_car: bool = False
    has_bike: bool = False
    leisure_items: int = 0
    pinned: bool = False
    personal_history: list[dict] = field(default_factory=list)
    transport_mode: str = "Gå"
    pension_balance: int = 0
    retired: bool = False
    last_income: int = 0
    last_living_cost: int = 0
    financial_stress_months: int = 0
    recent_purchases: list[dict] = field(default_factory=list)

@dataclass
class Workplace:
    id: int
    kind: str
    wage: int
    capacity: int
    employed: int = 0
    strain: int = 1
    owner_id: int | None = None
    money: int = 0
    blocks: list[tuple[int, int]] = field(default_factory=list)
    loan_balance: int = 0
    loan_years_missed: int = 0
    idle_months: int = 0
    stock_food: int = 0
    demand_score: float = 0.0
    monthly_profit: int = 0
    service_name: str | None = None

@dataclass
class FoodStore:
    id: int
    kind: str
    price: int
    capacity: int
    sold: int = 0


@dataclass
class CentralBank:
    reserves: int = 500
    policy_rate: float = 0.02
    deposits: int = 0
    outstanding_loans: int = 0
    pension_assets: int = 0
    last_pension_contributions: int = 0
    last_pension_payouts: int = 0
    last_interest_income: int = 0


@dataclass
class Transaction:
    month: int
    category: str
    amount: int
    source_type: str
    source_id: int | None
    destination_type: str
    destination_id: int | None
    description: str = ""


@dataclass
class ServiceState:
    name: str
    demand: float = 0.0
    target_positions: int = 0
    facility_positions: int = 0
    staffed: int = 0
    requested_operating: int = 0
    paid_operating: int = 0
    supply_ratio: float = 0.0
    access_ratio: float = 0.0
    coverage: float = 0.0
    effectiveness: float = 0.0
    workload: float = 0.0

