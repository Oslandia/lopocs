from lopocs import utils


def test_list_from_str():
    str_list = "[1, 5, 2, 3]"
    l = utils.list_from_str(str_list)
    assert l == [1, 5, 2, 3]


def test_boundingbox_to_polygon():
    bbox = [1, 2, 3, 4, 5, 6]
    poly = utils.boundingbox_to_polygon(bbox)
    poly_expected = '1 2, 4 2, 4 5, 1 5, 1 2'
    assert poly == poly_expected


def test_list_from_str_box():
    str_box = 'BOX(1 2 3 4)'
    l_box = utils.list_from_str_box(str_box)
    assert l_box == [1, 2, 3, 4]


def test_compute_scales_cesium():
    scale = utils.compute_scale_for_cesium(1.56, 1.80)
    assert scale == 1e-5
    scale = utils.compute_scale_for_cesium(4.5556e6, 4.5557e6)
    assert scale == 0.01
    scale = utils.compute_scale_for_cesium(4e5, 5e5)
    assert scale == 1
    scale = utils.compute_scale_for_cesium(100, 300000)
    assert scale == 1
