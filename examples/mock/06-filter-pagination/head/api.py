from service import list_items


class CatalogAPI:
    """In-process API simulation; never opens a socket."""

    def __init__(self):
        self.cache = {}

    def get_items(self, category, page, page_size=2):
        key = (page, page_size)
        if key not in self.cache:
            self.cache[key] = list_items(category, page, page_size)
        return self.cache[key]
