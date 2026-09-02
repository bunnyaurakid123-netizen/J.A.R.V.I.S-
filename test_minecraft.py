from core.minecraft import *


def test_has_50_plus_features():
    assert feature_count() >= 50


def test_math_helpers():
    assert distance((0,0,0),(3,4,0)) == 5
    assert nether_to_overworld(100, -200) == (800, -1600)
    assert overworld_to_nether(800, -1600) == (100, -200)
    assert blocks_for_box(10, 10, 10) == 1000
    assert stacks(130) == (2, 2)
    assert crafting_batches(9, 4) == 3
    assert fuel_items(17, 8) == 3


def test_commands_are_generated():
    assert command_fill((0,64,0),(3,67,3),'minecraft:stone').startswith('/fill ')


def test_parser():
    assert '5.00' in parse_request('minecraft distance 0 0 0 to 3 4 0')
    assert '800' in parse_request('minecraft nether coords 100 -200')
    assert '1,000' in parse_request('minecraft box 10x10x10')
