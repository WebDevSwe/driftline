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
- Seasons affect expenses
- Norra: higher winter/seasonal costs + winter stability penalty
- Medel: moderate seasonal effects
- Syd: mild seasonal effects

### Money & Budget (Player/State)
- State budget only covers `Basutgifter`, `Service`, `Säsong`
- Citizens and companies pay their own food and housing costs
- Budget window shows last completed year’s income/expenses and latest monthly costs
- Budget sliders
- `Basutgifter`, `Service`, `Säsong` (0–100%)
- Tax rate (0–70%)
- Service funding per service (0–100%)
- Block cost slider (min 1)

### Taxes
- Tax collected once per year, based on employed population
- Very high tax (>50%) reduces stability

## Population
- Population changes each tick based on stability, money, season, hunger, unemployment, and health
- There is no auto-job creation; jobs come from citizen-owned workplaces

## Blocks & Ownership
- The state sells unused blocks
- Abandoned blocks become gray and return to the state
- Abandoned blocks can be restored for a fixed restoration cost
- Tents use blocks at no cost and are freed when no longer needed
- Blocks used for housing or workplaces must be purchased
- Block cost is never below 100 and can be adjusted in the budget window

## Housing
- Citizens start in tents and can buy housing blocks to upgrade to `Hydda`
- If a tent is taken over by construction, that citizen becomes homeless
- Homeless citizens lose all status items after 12 months
- Homeless citizens can re-enter tents over time

## Workplaces & Jobs
- Workplaces are created by citizens, not auto-generated
- Each workplace has output equal to 4x wage cost
- If a workplace cannot pay everyone, remaining employees become unemployed
- Workplaces expand to adjacent free or abandoned blocks if they can afford it

### Workplace Types
- `Jordbruk`
- 2x2 blocks
- Must be placed adjacent to a tent or housing
- 0 block cost, but abandoned blocks still cost restoration
- Up to 10 workers (including owner)
- Produces food (8x yearly need per employee)
- Abandoned if an industry is within 4 blocks
- `Basjobb`
- 1–2 blocks
- Requires at least 1 status item
- `Service`
- 2–6 blocks
- Requires at least 2 status items
- `Industri`
- 4, 6, 8, or 16 blocks
- Requires at least 10 status items

## Bank & Loans
- One bank holds all unused money
- Base interest is low at high stability and higher at low stability
- Deposits earn annual interest
- Loans charge double the base rate
- Status items reduce loan interest by 0.01% per item
- Bank lends at most 50% of total deposits
- Individuals can borrow up to 10x their bank balance
- Unpaid loans reduce health; after 3 years in default, bankruptcy occurs

## Food
- Citizens store up to 100 food
- They consume 2 food per month
- When food is below 30 they try to buy more
- If food hits 0 they become hungry and health drops
- The state can provide 10 food to starving, sick citizens

## Status Items
- Available only when living in housing better than a tent
- Cost 10 block cost each
- Reduce energy loss and improve health
- Lost after 12 months of homelessness
- Money spent on status items leaves the economy

## Services
- Polis, Brandkår, Sjukvård, Skola, Barnomsorg, A-kassa
- Active services add costs
- Polis, Sjukvård, Skola improve stability
- High funding for Polis/Brandkår adds stability

## Stability
- Stability rises/falls based on tax levels, region winter penalties, service coverage, unemployment, hunger, and sickness

## UI & Visualization
- Torg is red in the center
- Tents are green circles
- Housing is blue blocks
- Basjobb is light blue blocks
- Service is yellow blocks
- Industry is orange blocks
- Farms are brown dotted blocks
- Abandoned blocks are gray
- Food bar shows percent not hungry
- Status bar shows money, population, employment, unemployment, sick, stability, bank rate, and tax timing

## Save/Load
- JSON save/load from menu

## Tests
```bash
pytest
```
