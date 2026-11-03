from data import ROWS


def list_items(category, page, page_size):
    rows = [row for row in ROWS if category == "" or row["category"] == category]
    start = (page - 1) * page_size
    return {"items": rows[start:start + page_size], "total": len(rows), "page": page}
