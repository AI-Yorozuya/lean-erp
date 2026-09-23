"""伺服器端分頁：清單頁與挑選框共用。page 從 1 起；page_size 夾在 1～100。"""


def paginate(qs, page: int = 1, page_size: int = 20):
    page_size = max(1, min(int(page_size), 100))
    page = max(1, int(page))
    count = qs.count()
    start = (page - 1) * page_size
    return list(qs[start:start + page_size]), count
