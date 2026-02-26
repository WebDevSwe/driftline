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

@dataclass
class Human:
    id: int
    money: int
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

@dataclass
class FoodStore:
    id: int
    kind: str
    price: int
    capacity: int
    sold: int = 0

