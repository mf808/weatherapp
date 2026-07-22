from src.modules.constants import BASE_CELL_HEIGHT, BASE_CELL_WIDTH, TREND_MAP, cell_scale


def test_scale_identity_at_base_dimensions():
    assert cell_scale(BASE_CELL_WIDTH, BASE_CELL_HEIGHT) == (1.0, 1.0)


def test_scale_doubles_at_double_dimensions():
    assert cell_scale(BASE_CELL_WIDTH * 2, BASE_CELL_HEIGHT * 2) == (2.0, 2.0)


def test_scale_independent_axes():
    sx, sy = cell_scale(BASE_CELL_WIDTH, BASE_CELL_HEIGHT * 3)
    assert sx == 1.0
    assert sy == 3.0


def test_trend_map_covers_all_directions():
    assert TREND_MAP == {"stable": "2", "down": "1", "up": "0"}
