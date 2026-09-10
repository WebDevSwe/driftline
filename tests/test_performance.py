import time

from world import World, WorldConfig


def test_simulation_speed_small_world():
    world = World(WorldConfig(name="Test", size_label="Liten", region="Medel"))
    start = time.perf_counter()
    for _ in range(120):
        world.advance_month()
    duration = time.perf_counter() - start
    assert duration < 5.0
