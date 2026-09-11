from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageTk
import customtkinter as ctk


UX_DIR = Path(__file__).resolve().parent / "UX"

PORTRAIT_SHEETS = (
    "ChatGPT Image 11 sep. 2026 08_49_41.png",
    "ChatGPT Image 11 sep. 2026 08_49_47.png",
    "ChatGPT Image 11 sep. 2026 08_49_50.png",
    "ChatGPT Image 11 sep. 2026 08_49_54.png",
)
HOME_SHEET = "ChatGPT Image 11 sep. 2026 08_50_23 (1).png"
CIVIC_SHEET = "ChatGPT Image 11 sep. 2026 08_50_23 (2).png"
BUSINESS_SHEET = "ChatGPT Image 11 sep. 2026 08_50_23 (3).png"
TRANSPORT_SHEET = "ChatGPT Image 11 sep. 2026 09_03_18.png"


BUILDING_SPRITES = {
    "Tält": (HOME_SHEET, 3, 2, 0, 0),
    "Hydda": (HOME_SHEET, 3, 2, 1, 0),
    "Bostad": (HOME_SHEET, 3, 2, 1, 0),
    "Stuga": (HOME_SHEET, 3, 2, 2, 0),
    "Villa": (HOME_SHEET, 3, 2, 0, 1),
    "Stort hus": (HOME_SHEET, 3, 2, 1, 1),
    "Gård": (HOME_SHEET, 3, 2, 2, 1),
    "Hotell": (CIVIC_SHEET, 5, 2, 0, 0),
    "Polis": (CIVIC_SHEET, 5, 2, 2, 0),
    "Sjukvård": (CIVIC_SHEET, 5, 2, 3, 0),
    "Skola": (CIVIC_SHEET, 5, 2, 4, 0),
    "Barnomsorg": (CIVIC_SHEET, 5, 2, 1, 1),
    "A-kassa": (CIVIC_SHEET, 5, 2, 2, 1),
    "Flerfamiljshus": (CIVIC_SHEET, 5, 2, 3, 1),
    "Centrum": (CIVIC_SHEET, 5, 2, 2, 1),
    "Jordbruk": (BUSINESS_SHEET, 5, 1, 0, 0),
    "Mataffär": (BUSINESS_SHEET, 5, 1, 1, 0),
    "Industri": (BUSINESS_SHEET, 5, 1, 2, 0),
    "Service": (BUSINESS_SHEET, 5, 1, 3, 0),
    "Basjobb": (BUSINESS_SHEET, 5, 1, 4, 0),
}

TRANSPORT_SPRITES = {
    "Gå": (TRANSPORT_SHEET, 4, 1, 0, 0),
    "Cykel": (TRANSPORT_SHEET, 4, 1, 1, 0),
    "Buss": (TRANSPORT_SHEET, 4, 1, 2, 0),
    "Bil": (TRANSPORT_SHEET, 4, 1, 3, 0),
}


class SpriteLibrary:
    """Cuts the supplied UX sheets in memory and preserves their crisp pixels."""

    def __init__(self):
        self._sheets: dict[str, Image.Image] = {}
        self._pil_cache: dict[tuple, Image.Image] = {}
        self._ctk_cache: dict[tuple, ctk.CTkImage] = {}
        self._canvas_cache: dict[tuple, ImageTk.PhotoImage] = {}

    @property
    def available(self):
        return UX_DIR.exists()

    def _sheet(self, filename):
        if filename not in self._sheets:
            self._sheets[filename] = Image.open(UX_DIR / filename).convert("RGBA")
        return self._sheets[filename]

    def _grid_crop(self, filename, columns, rows, column, row):
        key = (filename, columns, rows, column, row)
        if key not in self._pil_cache:
            sheet = self._sheet(filename)
            left = round(column*sheet.width/columns)
            top = round(row*sheet.height/rows)
            right = round((column+1)*sheet.width/columns)
            bottom = round((row+1)*sheet.height/rows)
            self._pil_cache[key] = sheet.crop((left, top, right, bottom))
        return self._pil_cache[key]

    def portrait(self, human, size=(190, 190)):
        age_column = 0 if human.age < 25 else 1 if human.age < 45 else 2 if human.age < 65 else 3 if human.age < 85 else 4
        sheet_index = human.id % len(PORTRAIT_SHEETS)
        row = (human.id // len(PORTRAIT_SHEETS)) % 6
        spec = (PORTRAIT_SHEETS[sheet_index], 5, 6, age_column, row)
        return self._ctk(spec, size)

    def building(self, kind, size=(280, 210)):
        spec = BUILDING_SPRITES.get(kind, BUILDING_SPRITES.get("Centrum"))
        return self._ctk(spec, size) if spec else None

    def transport(self, mode, size=(90, 70)):
        return self._ctk(TRANSPORT_SPRITES.get(mode, TRANSPORT_SPRITES["Gå"]), size)

    def canvas_building(self, kind, size):
        spec = BUILDING_SPRITES.get(kind)
        if not spec: return None
        key = (*spec, size, "canvas")
        if key not in self._canvas_cache:
            source = self._grid_crop(*spec)
            thumbnail = source.resize((size, size), Image.Resampling.NEAREST)
            self._canvas_cache[key] = ImageTk.PhotoImage(thumbnail)
        return self._canvas_cache[key]

    def _ctk(self, spec, size):
        key = (*spec, size, "ctk")
        if key not in self._ctk_cache:
            source = self._grid_crop(*spec)
            self._ctk_cache[key] = ctk.CTkImage(light_image=source, dark_image=source, size=size)
        return self._ctk_cache[key]
