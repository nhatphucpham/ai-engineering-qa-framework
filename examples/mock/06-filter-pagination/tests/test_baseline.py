import unittest

from api import CatalogAPI
from service import list_items
from ui import CatalogView


def ids(response):
    return [item['id'] for item in response['items']]


class Baseline(unittest.TestCase):
    def test_service_category_and_case(self):
        result = list_items('tools', 1, 2)
        self.assertEqual(ids(result), ['T1', 'T2'])
        self.assertEqual(result['total'], 2)
        self.assertEqual(list_items('Tools', 1, 2)['total'], 0)

    def test_service_pagination_and_out_of_range(self):
        self.assertEqual(ids(list_items('books', 2, 2)), ['B3', 'B4'])
        result = list_items('tools', 3, 2)
        self.assertEqual(result, {'items': [], 'total': 2, 'page': 3})

    def test_empty_category(self):
        result = list_items('', 1, 2)
        self.assertEqual(result['total'], 8)
        self.assertEqual(ids(result), ['B1', 'B2'])

    def test_api_repeat_same_request(self):
        api = CatalogAPI()
        self.assertEqual(ids(api.get_items('tools', 1)), ['T1', 'T2'])
        self.assertEqual(ids(api.get_items('tools', 1)), ['T1', 'T2'])
        self.assertEqual(len(api.cache), 1)

    def test_api_page_and_size(self):
        api = CatalogAPI()
        self.assertEqual(ids(api.get_items('books', 1, 2)), ['B1', 'B2'])
        self.assertEqual(ids(api.get_items('books', 2, 2)), ['B3', 'B4'])
        self.assertEqual(ids(api.get_items('books', 1, 1)), ['B1'])

    def test_ui_select_from_first_page(self):
        view = CatalogView(CatalogAPI())
        result = view.select_category('tools')
        self.assertEqual(view.category, 'tools')
        self.assertEqual(view.page, 1)
        self.assertEqual(ids(result), ['T1', 'T2'])
