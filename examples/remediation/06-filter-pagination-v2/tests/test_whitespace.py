"""Checks for the user-selected ASCII-space behavior in mock-req-06-v2."""

import unittest

from api import CatalogAPI
from service import list_items
from ui import CatalogView


def ids(response):
    return [item['id'] for item in response['items']]


class Whitespace(unittest.TestCase):
    def test_service_spaces_mean_all(self):
        result = list_items('   ', 1, 2)
        self.assertEqual(result, list_items('', 1, 2))
        self.assertEqual(result['total'], 8)
        self.assertEqual(ids(result), ['B1', 'B2'])

    def test_service_padded_category_and_pagination(self):
        result = list_items(' books ', 2, 2)
        self.assertEqual(ids(result), ['B3', 'B4'])
        self.assertEqual(result['total'], 6)
        self.assertEqual(result['page'], 2)
        self.assertEqual(list_items(' Books ', 1, 2)['total'], 0)
        self.assertEqual(list_items('bo oks', 1, 2)['total'], 0)

    def test_api_mixed_categories(self):
        api = CatalogAPI()
        self.assertEqual(api.get_items(' books ', 1)['total'], 6)
        self.assertEqual(ids(api.get_items(' tools ', 1)), ['T1', 'T2'])
        self.assertEqual(api.get_items('   ', 1)['total'], 8)
        self.assertEqual(ids(api.get_items('books', 1)), ['B1', 'B2'])

    def test_ui_spaces_and_padded_category(self):
        view = CatalogView(CatalogAPI(), category='books', page=3)
        result = view.select_category(' tools ')
        self.assertEqual(view.page, 1)
        self.assertEqual(ids(result), ['T1', 'T2'])
        result = view.select_category('   ')
        self.assertEqual(view.page, 1)
        self.assertEqual(result['total'], 8)
