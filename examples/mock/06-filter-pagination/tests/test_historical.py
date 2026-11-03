import unittest

from api import CatalogAPI
from ui import CatalogView


class Historical(unittest.TestCase):
    def test_reset_from_third_page(self):
        view = CatalogView(CatalogAPI(), category='books', page=3)
        result = view.select_category('tools')
        self.assertEqual(view.page, 1)
        self.assertEqual([item['id'] for item in result['items']], ['T1', 'T2'])
