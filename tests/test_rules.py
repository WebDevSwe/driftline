from world import World, WorldConfig, WORKPLACE_RULES, TENT_CAPACITY


def test_starting_capital_range():
    world = World(WorldConfig(name="Test", size_label="Liten", region="Medel"))
    base_wage = WORKPLACE_RULES["Basjobb"]["wage"]
    low = base_wage // 2
    high = base_wage * 3
    for human in world.humans:
        assert low <= human.money <= high


def test_tent_capacity_is_four_per_tent():
    world = World(WorldConfig(name="Test", size_label="Liten", region="Medel"))
    world.month = 3
    for human in world.humans:
        human.home_kind = "Tält"
        human.home_owner_id = None
    world._sync_tents()
    expected = (len(world.humans) + TENT_CAPACITY - 1) // TENT_CAPACITY
    tents = [b for b in world.buildings if b.kind == "Tält" and b.active]
    assert len(tents) == expected


def test_bankruptcy_sells_housing_and_resets_job():
    world = World(WorldConfig(name="Test", size_label="Liten", region="Medel"))
    human = world.humans[0]
    human.money = 0
    human.job_id = 1
    building, _cost = world._claim_block("Bostad", "#4aa3ff", human.id, 1)
    assert building is not None
    human.home_kind = "Bostad"
    human.home_owner_id = human.id

    world._apply_bankruptcy()

    assert human.job_id is None
    assert human.home_owner_id is None
    assert human.home_kind in ("Tält", "Bostadslös")
    assert all(b.owner_id != human.id for b in world.buildings if b.kind == "Bostad")
