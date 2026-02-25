# driftline
A small simulation of a society's economy with a grid-based world and a simple policy/budget UI.

## Run
```bash
pip install customtkinter
python main.py
```

## Project Structure
- `main.py` – entrypoint
- `ui.py` – UI (CustomTkinter)
- `world.py` – simulation logic
- `models.py` – dataclasses
- `tests/` – pytest tests

## Core Concepts
### Time
- 1 tick = 1 month
- 12 months = 1 year
- Tax revenue is collected once per year (month 12)

### World & Regions
- Grid size from `Liten/Medium/Stor`
- Regions: `Norra`, `Medel`, `Syd`
- Seasons affect expenses:
- Norra: higher winter/seasonal costs + winter stability penalty
- Medel: moderate seasonal effects
- Syd: mild seasonal effects

### Money & Budget (Player/State)
- State budget only covers:
- Basutgifter
- Service
- Säsong
- Citizens pay their own food and housing.
- Budget window shows:
- Last completed year’s income/expenses (tax only collected yearly)
- Latest monthly category costs for context
- Budget sliders:
- `Basutgifter`, `Service`, `Säsong` (0–100%)
- Tax rate (0–70%)
- Service funding per service (0–100%)

### Taxes
- Tax collected once per year, based on employed population
- Lower tax (<=10%) boosts job growth and immigration
- Very high tax (>50%) reduces stability

## Population & Immigration
- Population changes each tick based on:
- Stability
- Money
- Housing capacity
- Season (winter penalizes unsafe housing)
- Hunger / homelessness / unpaid rent
- Immigration score (stability, money, job availability, low tax)

## Housing
- Housing types: `Tält`, `Hydda`, `Lägenhet`, `Villa`
- Tents are free and scale with population but are not allowed in winter.
- Permanent housing is built to stay ahead of population (>=10% buffer).
- Housing shortages increase instability and reduce population growth.
- Empty housing turns gray (inactive) and is reused first.

## Jobs & Industry
- Jobs are auto-created as population grows.
- A large “megafactory” appears when population reaches 15 (capacity 1000).
- Job growth is slower if:
- Low stability
- After 6 months, if Polis/Brandkår are missing or underfunded

## Food
- Food stores (Mataffär) are created if supply is low or people go hungry.
- Hunger reduces stability and energy.

## Health & Energy
- Each citizen has:
- `energy`, `health`, `sick`
- Energy loss increases with:
- Hunger
- Homelessness / unpaid rent
- Winter
- Job strain (Basjobb < Service < Industri)
- Low energy reduces health.
- Sick citizens do not work.
- Sjukvård (if active and funded) helps recover health.
- More sick people increases healthcare cost.

## Services
Services can be toggled and funded:
- Polis
- Brandkår
- Sjukvård
- Skola
- Barnomsorg
- A-kassa

Effects:
- Each active service adds costs.
- Some services add stability (Polis, Sjukvård, Skola).
- High funding (>=60%) for Polis/Brandkår adds stability.
- Underfunding basutgifter/service reduces stability.

## Stability
Stability rises/falls based on:
- Tax level (high tax hurts)
- Region winter penalties
- Budget underfunding
- Crime prevention and healthcare services
- Net negative tax year
- Unemployment, hunger, homelessness, unpaid rent, sickness
- High stability + positive economy gives small bonus

## UI & Visualization
- Colored buildings:
- Red: Torg (center)
- Blue: Bostad
- Orange: Industri
- Yellow: Service
- Light blue: Basjobb
- Green: Mataffär
- Gray: Inactive/abandoned
- Food bar shows percent of population not hungry.
- Status bar shows money, population, employment, sick, stability, tax timing.

## Save/Load
- JSON save/load from menu.

## Tests
```bash
pytest
```
