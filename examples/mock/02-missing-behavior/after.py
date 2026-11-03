def apply_filter(rows, query, page):
    return {"rows": [row for row in rows if query in row], "page": page}
