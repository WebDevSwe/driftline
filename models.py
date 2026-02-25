from __future__ import annotations

from dataclasses import dataclass

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

@dataclass
class Human:
    id: int
    money: int
    job_id: int | None = None
    hungry: bool = False
    energy: int = 100
    health: int = 100
    sick: bool = False

@dataclass
class Workplace:
    id: int
    kind: str
    wage: int
    capacity: int
    employed: int = 0
    strain: int = 1

@dataclass
class FoodStore:
    id: int
    kind: str
    price: int
    capacity: int
    sold: int = 0

