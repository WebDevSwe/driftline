from world import World, WorldConfig


def test_world_initializes_with_buildings():
    world = World(WorldConfig(name="Test", size_label="Medium", region="Medel"))
    assert world.buildings
    assert world.grid_size == 60


def test_annual_tax_only_on_month_12():
    world = World(WorldConfig(name="Test", size_label="Liten", region="Medel"))
    start_money = world.money
    world.advance_month()
    assert world.month == 1
    assert world.last_revenue == 0
    for _ in range(10):
        world.advance_month()
    assert world.month == 11
    assert world.last_revenue == 0
    world.advance_month()
    assert world.month == 12
    assert world.last_revenue >= 0
    assert world.money >= 0


def test_housing_tents_scale_with_population():
    world = World(WorldConfig(name="Test", size_label="Liten", region="Medel"))
    world.population = 25
    world._sync_population()
    assert world.housing_units["Tält"] >= 25
