from models import WorldConfig
from world import (
    APARTMENT_CAPACITY,
    HOUSE_BUILD_COST,
    HOUSE_CAPACITY,
    HOUSE_EXPANSION_COST,
    Building,
    Workplace,
    World,
)


def make_world():
    return World(WorldConfig("Test", "Liten", "Medel"))


def test_food_shortage_creates_farming_before_advanced_businesses():
    world = make_world()
    assert world.workplaces == []

    world.advance_month()

    assert [workplace.kind for workplace in world.workplaces] == ["Jordbruk"]


def test_social_need_outweighs_a_non_farming_drive():
    world = make_world()
    for human in world.humans:
        human.drive = "sparsam"

    world.advance_month()

    assert any(workplace.kind == "Jordbruk" for workplace in world.workplaces)


def test_food_cannot_appear_without_local_production():
    world = make_world()
    world.workplaces.clear()
    for human in world.humans:
        human.food = 0
        human.money = 100

    hungry = world._apply_food()

    assert hungry == world.population
    assert world.last_food_supply == 0
    assert all(human.food == 0 for human in world.humans)


def test_housing_pressure_causes_solvent_resident_to_build():
    world = make_world()
    richest = max(world.humans, key=lambda human: human.money)
    richest.money = 200

    world._evaluate_housing_market()

    houses = [building for building in world.buildings if building.kind == "Bostad"]
    assert len(houses) == 1
    assert houses[0].owner_id == richest.id


def test_house_holds_owner_and_four_tenants_and_pays_rent():
    world = make_world()
    owner = world.humans[0]
    world.buildings.append(Building(3, 3, "#4aa3ff", "Bostad", owner_id=owner.id))
    owner_before = owner.money

    world._assign_housing()

    occupants = [human for human in world.humans if human.home_owner_id == owner.id]
    assert len(occupants) == HOUSE_CAPACITY == 5
    assert owner.money == owner_before + 4 * 6


def test_housing_market_does_not_build_when_capacity_is_vacant():
    world = make_world()
    owner = max(world.humans, key=lambda human: human.money)
    owner.money = 500
    for offset in range(3):
        world.buildings.append(Building(3+offset, 3, "#4aa3ff", "Bostad", owner_id=owner.id))
    before = sum(building.kind == "Bostad" for building in world.buildings)

    world._evaluate_housing_market()

    assert sum(building.kind == "Bostad" for building in world.buildings) == before


def test_private_house_has_a_builder_and_real_cost():
    world = make_world()
    buyer = max(world.humans, key=lambda human: human.money)
    for human in world.humans:
        human.money = 0
    buyer.money = 200

    world._evaluate_housing_market()

    house = next(building for building in world.buildings if building.kind == "Bostad")
    assert house.owner_id == buyer.id
    assert house.housing_units == HOUSE_CAPACITY
    assert buyer.money == 200-HOUSE_BUILD_COST


def test_owner_can_expand_existing_home_over_time():
    world = make_world()
    owner = world.humans[0]
    for human in world.humans:
        human.money = 0
    owner.money = 500
    owner.last_housing_investment_month = 0
    world.month = 24
    house = Building(3, 3, "#4aa3ff", "Bostad", owner_id=owner.id, housing_units=5)
    world.buildings.append(house)

    world._evaluate_housing_market()

    assert house.level == 2
    assert house.housing_units == 7
    assert owner.money == 500-HOUSE_EXPANSION_COST


def test_services_physically_expand_the_centre():
    world = make_world()
    world.money = 500
    world.services["Skola"] = True
    world._develop_civic_center()
    first_civic_area = sum(b.kind in ("Skola", "Centrum") for b in world.buildings if b.active)
    world.services["Sjukvård"] = True
    world._develop_civic_center()

    assert any(b.active and b.kind == "Skola" for b in world.buildings)
    assert any(b.active and b.kind == "Sjukvård" for b in world.buildings)
    assert sum(b.kind in ("Skola", "Sjukvård", "Centrum") for b in world.buildings if b.active) > first_civic_area


def test_municipality_builds_central_apartment_housing():
    world = make_world()
    world.money = 500
    world.services["Skola"] = True
    world._develop_civic_center()
    while len(world.humans) < 40:
        world.humans.append(world._new_human())
    world.population = len(world.humans)

    world._develop_apartment_housing()

    apartment = next(b for b in world.buildings if b.kind == "Flerfamiljshus")
    assert apartment.owner_id is None
    assert apartment.housing_units == APARTMENT_CAPACITY


def test_surplus_apartment_building_can_become_service():
    world = make_world()
    world.money = 500
    for x in (3, 4):
        world.buildings.append(Building(x, 3, "#8b78a8", "Flerfamiljshus",
                                        housing_units=APARTMENT_CAPACITY))
    world.services["Sjukvård"] = True

    world._develop_civic_center()

    assert any(b.kind == "Sjukvård" and b.service_name == "Sjukvård" for b in world.buildings)


def test_unemployment_support_is_paid_by_the_municipality():
    world = make_world()
    world.services["A-kassa"] = True
    world.service_funding["A-kassa"] = 100
    world.money = 1000
    balances = [human.money for human in world.humans]

    world._apply_unemployment_support()

    assert world.last_unemployment_support == 36*world.population
    assert world.money == 1000-world.last_unemployment_support
    assert all(human.money == before+36 for human, before in zip(world.humans, balances))


def test_farm_is_placed_as_a_contiguous_plot_outside_centre():
    world = make_world()
    coordinates = world._claim_farmland(world.humans[0].id)
    centre = world.grid_size//2

    assert len(coordinates) == 4
    assert len({x for x, _ in coordinates}) == 2
    assert len({y for _, y in coordinates}) == 2
    assert min(abs(x-centre)+abs(y-centre) for x, y in coordinates) > world.grid_size//3


def test_farm_workers_keep_their_profession():
    world = make_world()
    farm = Workplace(90, "Jordbruk", 20, 4, money=1000, demand_score=2)
    world.workplaces.append(farm)
    world._assign_jobs_and_pay_wages()
    farmers = {human.id for human in world.humans if human.job_id == farm.id}
    world.workplaces.append(Workplace(91, "Industri", 65, 10, money=10000, demand_score=100))

    world._assign_jobs_and_pay_wages()

    assert farmers
    assert all(next(h for h in world.humans if h.id == farmer_id).job_id == farm.id
               for farmer_id in farmers)


def test_unsold_harvest_is_stored_for_later_months():
    world = make_world()
    farm = Workplace(90, "Jordbruk", 20, 2, employed=2, money=1000)
    world.workplaces.append(farm)

    world._apply_food()

    assert farm.stock_food > 0


def test_statistics_records_system_outputs():
    world = make_world()
    world.advance_month()

    expected = {
        "hungry", "unemployed", "food_supply", "food_stored",
        "housing_capacity", "workplaces", "farms", "attractiveness",
        "crime", "arrivals", "departures", "central_area",
        "unemployment_support",
    }
    assert expected <= world.history.keys()
    assert all(len(world.history[key]) == 2 for key in expected)


def test_yearly_migration_statistics_are_sums_not_last_month_snapshot():
    world = make_world()
    for _ in range(12):
        world.advance_month()

    assert world.history_year["arrivals"][-1] == sum(world.history["arrivals"][-12:])
    assert world.history_year["departures"][-1] == sum(world.history["departures"][-12:])


def test_income_tax_is_withheld_from_each_months_wages():
    world = make_world()
    world.tax_rate = .20
    world.workplaces.append(Workplace(90, "Basjobb", 36, 10, money=1000))

    world._assign_jobs_and_pay_wages()

    pension = max(1, int(36*.08))
    assert world.last_tax_revenue == 10*int((36-pension)*.20)
    assert sum(t.amount for t in world.transactions if t.category == "Inkomstskatt") == world.last_tax_revenue


def test_budget_forecast_exposes_break_even_tax_and_service_costs():
    world = make_world()
    world.workplaces.append(Workplace(90, "Basjobb", 36, 10, employed=10))
    world.services["Skola"] = True
    world.service_funding["Skola"] = 100

    forecast = world.budget_snapshot()

    assert forecast["annual_income"] == int(36*10*(1-.08)*world.tax_rate)*12
    assert forecast["annual_cost"] > 0
    assert forecast["break_even_tax"] > 0
    assert forecast["service_items"]["Skola"]["monthly"] > 0


def test_support_and_public_investments_are_visible_as_real_expenses():
    world = make_world()
    world.money = 1000
    world.services["A-kassa"] = True
    world.service_funding["A-kassa"] = 100
    world._apply_unemployment_support()
    support = world.last_unemployment_support
    world.last_public_investment = 45
    world.money -= 45

    world._apply_public_budget()

    assert world.last_expenses["A-kassa utbetalningar"] == support
    assert world.last_expenses["Investeringar"] == 45
    assert world.expenses == sum(world.last_expenses.values())


def test_funded_service_activates_and_registers_a_cost():
    world = make_world()
    world.service_funding["Skola"] = 100

    world.advance_month()

    assert world.services["Skola"] is True
    assert world.last_expenses["Service"] > 0


def test_hotel_provides_paid_temporary_addresses():
    world = make_world()
    owner = world.humans[0]
    hotel = Building(3, 3, "#cf7fc2", "Hotell", owner_id=owner.id, housing_units=12)
    business = Workplace(90, "Hotell", 42, 2, owner_id=owner.id, money=0, blocks=[(3, 3)])
    world.buildings.append(hotel)
    world.workplaces.append(business)

    world._assign_housing()

    guests = [human for human in world.humans if human.home_kind == "Hotell"]
    assert guests
    assert all((guest.home_x, guest.home_y) == (3, 3) for guest in guests)
    assert business.money == len(guests)*10


def test_resident_has_a_real_home_address():
    world = make_world()
    owner = world.humans[0]
    world.buildings.append(Building(3, 3, "#4aa3ff", "Bostad", owner_id=owner.id))

    world._assign_housing()

    assert (owner.home_x, owner.home_y) == (3, 3)


def test_car_extends_commuting_range_and_has_running_cost():
    world = make_world()
    human = world.humans[0]
    human.home_x = human.home_y = 2
    workplace = Workplace(90, "Industri", 65, 2, blocks=[(25, 25)])
    assert world._can_commute(human, workplace) is False
    human.has_car = True
    assert world._can_commute(human, workplace) is True
    human.money = 100

    world._apply_transport_choices()

    assert human.money == 84


def test_wages_build_pension_and_retirement_pays_from_central_bank():
    world = make_world()
    human = world.humans[0]
    human.age = 66
    human.money = 0
    human.pension_balance = 120
    world.central_bank.pension_assets = 120
    world.month = 12

    world._age_population()
    world._apply_pensions()

    assert human.retired is True
    assert human.money > 0
    assert world.central_bank.last_pension_payouts == human.money


def test_very_old_resident_dies_and_is_recorded():
    world = make_world()
    human = world.humans[0]
    human.age = 104
    world.month = 12

    world._age_population()

    assert human not in world.humans
    assert world.last_deaths == 1
    assert world.population_events[-1]["event"] == "avled"


def test_high_tax_and_long_financial_stress_can_cause_outmigration():
    world = make_world()
    human = world.humans[0]
    human.dissatisfaction = 100
    human.financial_stress_months = 12
    world.tax_rate = .7
    world.attractiveness = 30

    world._update_population(world.season(), 0, 0)

    assert human not in world.humans
    assert world.last_departures >= 1


def test_buildable_map_reaches_the_new_one_block_margin():
    world = make_world()
    world.buildings = []
    cells = world._claim_farmland(world.humans[0].id)

    assert cells
    assert any(1 in coordinate for coordinate in cells)


def test_better_paid_shop_can_recruit_from_a_well_supplied_farm():
    world = make_world()
    for human in world.humans: human.job_id = 1
    farm = Workplace(1, "Jordbruk", 20, 10, employed=10, money=1000,
                     stock_food=1000, blocks=[(15, 15)])
    shop = Workplace(2, "Mataffär", 32, 2, money=1000, blocks=[(16, 15)])
    world.workplaces = [farm, shop]

    world._assign_jobs_and_pay_wages()

    assert shop.employed >= 1
    assert farm.employed >= 8


def test_transport_is_chosen_for_the_actual_commute():
    expectations = ((10, 100, "Cykel"), (25, 100, "Buss"), (50, 500, "Bil"))
    for distance, money, expected in expectations:
        world = make_world()
        human = world.humans[0]
        human.home_x = human.home_y = 1
        human.money = money
        human.job_id = 90
        world.workplaces = [Workplace(90, "Industri", 65, 1, money=1000,
                                      blocks=[(1+distance, 1)])]

        world._apply_transport_choices()

        assert human.transport_mode == expected


def test_staffed_food_shop_receives_a_share_of_food_sales():
    world = make_world()
    for human in world.humans:
        human.food = 0
        human.money = 100
    farm = Workplace(1, "Jordbruk", 20, 2, employed=1, money=0, stock_food=1000)
    shop = Workplace(2, "Mataffär", 32, 2, employed=1, money=0)
    world.workplaces = [farm, shop]

    world._apply_food()

    assert shop.money > 0
    assert shop.monthly_profit > 0


def test_housing_can_form_more_than_one_neighbourhood():
    world = make_world()
    for _ in range(30):
        world._claim_near_activity("Bostad", "#4aa3ff", None, 1)
    coordinates = {(b.x, b.y) for b in world.buildings if b.kind == "Bostad"}
    unseen = set(coordinates)
    components = 0
    while unseen:
        components += 1
        stack = [unseen.pop()]
        while stack:
            x, y = stack.pop()
            neighbours = {(x+1, y), (x-1, y), (x, y+1), (x, y-1)} & unseen
            unseen -= neighbours
            stack.extend(neighbours)

    assert components > 1


def test_monthly_money_supply_reconciles_with_external_flows():
    world = make_world()
    world.money = 5000
    for name in world.services:
        world.services[name] = True
        world.service_funding[name] = 60

    for _ in range(48):
        world.advance_month()
        assert world.last_money_discrepancy == 0


def test_tax_is_a_transfer_and_not_new_money():
    world = make_world()
    world.tax_rate = .25
    world.workplaces = [Workplace(90, "Basjobb", 36, 10, money=1000)]
    opening = world._money_supply()
    start = len(world.transactions)

    world._assign_jobs_and_pay_wages()
    world._reconcile_money(opening, start)

    assert world.last_tax_revenue > 0
    assert world.last_money_discrepancy == 0
    assert any(t.category == "Inkomstskatt" and t.destination_type == "Kommun"
               for t in world.transactions[start:])


def test_transactions_survive_save_and_load():
    world = make_world()
    world.advance_month()

    restored = World.from_dict(world.to_dict())

    assert restored.transactions
    assert restored.transactions[-1] == world.transactions[-1]
    assert restored.last_money_supply == world.last_money_supply


def test_pinned_resident_collects_personal_history():
    world = make_world()
    human = world.humans[0]
    human.pinned = True

    world.advance_month()

    assert human.personal_history
    assert human.personal_history[-1]["month"] == world.month
    assert {"money", "food", "health", "job", "home"} <= human.personal_history[-1].keys()


def test_food_reserve_supports_growth_instead_of_false_capacity_ceiling():
    world = make_world()
    owner = world.humans[0]
    for offset in range(3):
        world.buildings.append(Building(3+offset, 3, "#4aa3ff", "Bostad", owner_id=owner.id))
    world.workplaces.append(Workplace(90, "Basjobb", 36, 10, money=1000))
    world.workplaces.append(Workplace(91, "Jordbruk", 20, 2, employed=1,
                                      stock_food=1000, money=1000))
    before = world.population

    world._update_population(world.season(), 0, 0)

    assert world.population >= before+2


def test_newcomers_use_available_hotel_immediately():
    world = make_world()
    owner = world.humans[0]
    world.buildings.append(Building(3, 3, "#cf7fc2", "Hotell",
                                    owner_id=owner.id, housing_units=12))
    hotel = Workplace(90, "Hotell", 42, 2, owner_id=owner.id,
                      money=0, blocks=[(3, 3)])
    world.workplaces.append(hotel)
    newcomer = world._new_human()

    world._house_newcomers_in_hotels([newcomer])

    assert newcomer.home_kind == "Hotell"
    assert (newcomer.home_x, newcomer.home_y) == (3, 3)
    assert hotel.money == 10


def test_public_services_create_population_scaled_paid_jobs():
    world = make_world()
    while len(world.humans) < 100:
        world.humans.append(world._new_human())
    world.population = len(world.humans)
    world.money = 10000
    world.services["Skola"] = True
    world.service_funding["Skola"] = 100
    world._develop_civic_center()
    world._sync_public_service_jobs()
    school = next(workplace for workplace in world.workplaces
                  if workplace.service_name == "Skola")

    world._assign_jobs_and_pay_wages()

    assert school.capacity == 5
    assert school.employed == 5
    assert world.last_public_payroll == 5*school.wage
    assert world.money == 10000-world.last_public_investment-world.last_public_payroll


def test_home_type_and_running_cost_follow_home_level():
    world = make_world()
    owner = world.humans[0]
    house = Building(3, 3, "#4aa3ff", "Bostad", owner_id=owner.id,
                     housing_units=5, housing_type="Hydda")
    world.buildings.append(house)
    world._assign_housing()
    owner.money = 100

    world._apply_housing_running_costs()

    assert owner.home_kind == "Hydda"
    assert owner.money == 99


def test_only_farmer_home_can_be_a_farmstead():
    world = make_world()
    owner = world.humans[0]
    house = Building(3, 3, "#4aa3ff", "Bostad", owner_id=owner.id)
    world.buildings.append(house)
    assert world._home_type(house) == "Hydda"
    world.workplaces.append(Workplace(90, "Jordbruk", 20, 2, owner_id=owner.id))

    assert world._home_type(house) == "Gård"


def test_emigration_requires_accumulated_dissatisfaction():
    world = make_world()
    human = world.humans[0]
    human.dissatisfaction = 64
    human.hungry_months = 1
    human.hungry = True
    human.job_id = None
    human.home_kind = "Bostadslös"

    world._update_population(world.season(), -10, world.population)
    assert human in world.humans

    world._update_dissatisfaction()
    human.hungry_months = 2
    world._update_population(world.season(), -10, world.population)
    assert human not in world.humans


def test_centrality_is_activity_based_and_round_trips():
    world = make_world()
    owner = world.humans[0]
    world._claim_near_activity("Service", "#ffd166", owner.id, 1)
    world._update_centrality()

    assert world.central_blocks()[0][1] > 0
    restored = World.from_dict(world.to_dict())
    assert restored.central_blocks() == world.central_blocks()


def test_vacant_homes_and_jobs_create_fast_immigration():
    world = make_world()
    owner = world.humans[0]
    for offset in range(3):
        world.buildings.append(Building(3+offset, 3, "#4aa3ff", "Bostad", owner_id=owner.id))
    world.workplaces.append(Workplace(99, "Basjobb", 36, 8, money=1000, demand_score=1))
    world.workplaces.append(Workplace(100, "Jordbruk", 20, 10, employed=10,
                                      money=1000, demand_score=1))
    before = world.population

    world._update_population(world.season(), 0, 0)

    assert world.population >= before+2
    assert world.last_arrivals >= 2


def test_low_tax_is_more_attractive_than_high_tax():
    low_tax = make_world()
    high_tax = make_world()
    low_tax.tax_rate = .01
    high_tax.tax_rate = .45

    low_tax._update_population(low_tax.season(), 0, 0)
    high_tax._update_population(high_tax.season(), 0, 0)

    assert low_tax.attractiveness > high_tax.attractiveness


def test_crime_and_missing_services_reduce_attractiveness():
    world = make_world()
    world.humans.extend(world._new_human() for _ in range(45))
    world.population = len(world.humans)
    world.stability = 35
    for human in world.humans:
        human.job_id = None

    world._update_population(world.season(), 0, 0)
    without_services = world.attractiveness
    world.services["Polis"] = True
    world.service_funding["Polis"] = 100
    world.services["Sjukvård"] = True
    world.service_funding["Sjukvård"] = 100
    world._update_population(world.season(), 0, 0)

    assert world.crime_rate < 30
    assert world.attractiveness > without_services
