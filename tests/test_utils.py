import unittest
from lopocs import utils


class TestUtils(unittest.TestCase):

    def setUp(cls):
        pass

    def tearDown(cls):
        pass

    def test_list_from_str(cls):
        str_list = "[1, 5, 2, 3]"
        l = utils.list_from_str(str_list)
        cls.assertEqual(l, [1, 5, 2, 3])

    def test_boundingbox_to_polygon(cls):
        bbox = [1, 2, 3, 4, 5, 6]
        poly = utils.boundingbox_to_polygon(bbox)
        poly_expected = '1 2, 4 2, 4 5, 1 5, 1 2'
        cls.assertEqual(poly, poly_expected)

    def test_list_from_str_box(cls):
        str_box = 'BOX(1 2 3 4)'
        l_box = utils.list_from_str_box(str_box)
        cls.assertEqual(l_box, [1, 2, 3, 4])
