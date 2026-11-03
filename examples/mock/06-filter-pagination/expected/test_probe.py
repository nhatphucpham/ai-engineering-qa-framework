import unittest

from api import CatalogAPI
from ui import CatalogView


class Probe(unittest.TestCase):
    def test_reset_with_recorded_api_call(self):
        class RecordingAPI(CatalogAPI):
            def get_items(self, category, page, page_size=2):
                self.request = (category, page, page_size)
                return super().get_items(category, page, page_size)

        api = RecordingAPI()
        view = CatalogView(api, category='books', page=3)
        view.select_category('tools')
        self.assertEqual(api.request, ('tools', 1, 2))

    def test_cache_across_categories(self):
        api = CatalogAPI()
        first = api.get_items('books', 1, 2)
        second = api.get_items('tools', 1, 2)
        self.assertEqual([item['id'] for item in first['items']], ['B1', 'B2'])
        self.assertEqual([item['id'] for item in second['items']], ['T1', 'T2'])
        self.assertEqual(second['total'], 2)
