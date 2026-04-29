import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.anthropic.com"
BLOG_URL = f"{BASE_URL}/engineering"


def fetch_anthropic_post() -> dict | None:
    try:
        response = requests.get(BLOG_URL, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        article = soup.find("article")
        if not article:
            return None
        anchor = article.find("a", href=True)
        if not anchor:
            return None
        title = anchor.get_text(strip=True)
        href = anchor["href"]
        url = href if href.startswith("http") else f"{BASE_URL}{href}"
        return {"title": title, "url": url}
    except Exception:
        return None
