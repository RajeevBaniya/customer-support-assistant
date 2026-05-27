import markdown
from bs4 import BeautifulSoup


def extract_text(data: bytes) -> str:
    raw = data.decode("utf-8", errors="replace")
    html = markdown.markdown(raw, extensions=["tables"])
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")
    lines = [ln.strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)
