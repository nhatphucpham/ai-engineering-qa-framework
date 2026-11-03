class CatalogView:
    """UI state simulation; no browser or framework dependency."""

    def __init__(self, api, category="books", page=1):
        self.api = api
        self.category = category
        self.page = page

    def select_category(self, category):
        self.category = category
        return self.api.get_items(self.category, self.page)
