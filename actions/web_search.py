"""
actions/web_search.py — Omni-Engine Internet Surfer & Visible Browser Search Engine (Mark 78)
Gives JARVIS unrestricted access to every major search engine:
Google, Bing, DuckDuckGo, Brave Search, Perplexity, YouTube, Google Scholar,
GitHub, Reddit, Wikipedia, ArXiv, StackOverflow, WolframAlpha, Yahoo, and Yandex.
Supports:
- Federated multi-engine background scraping & synthesis ('search', 'deep_surf')
- Direct live webpage reading ('surf', 'read_url')
- Visible on-screen browser search ('visible_search' or open_browser=True) across any or multiple engines.
"""

import re
import json
import webbrowser
import urllib.parse
import urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

MAX_RESULTS = 7

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

SEARCH_ENGINES = {
    "google":        "https://www.google.com/search?q={q}",
    "bing":          "https://www.bing.com/search?q={q}",
    "duckduckgo":    "https://duckduckgo.com/?q={q}",
    "ddg":           "https://duckduckgo.com/?q={q}",
    "brave":         "https://search.brave.com/search?q={q}",
    "perplexity":    "https://www.perplexity.ai/search?q={q}",
    "youtube":       "https://www.youtube.com/results?search_query={q}",
    "scholar":       "https://scholar.google.com/scholar?q={q}",
    "github":        "https://github.com/search?q={q}",
    "reddit":        "https://www.reddit.com/search/?q={q}",
    "wikipedia":     "https://en.wikipedia.org/w/index.php?search={q}",
    "arxiv":         "https://arxiv.org/search/?query={q}&searchtype=all",
    "stackoverflow": "https://stackoverflow.com/search?q={q}",
    "wolfram":       "https://www.wolframalpha.com/input?i={q}",
    "yahoo":         "https://search.yahoo.com/search?p={q}",
    "yandex":        "https://yandex.com/search/?text={q}",
}


def _get_api_key() -> str:
    try:
        p = Path(__file__).resolve().parent.parent / "config" / "api_keys.json"
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8")).get("gemini_api_key", "")
    except Exception:
        pass
    return ""


def build_engine_url(query: str, engine: str = "google") -> str:
    eng = (engine or "google").lower().strip()
    tmpl = SEARCH_ENGINES.get(eng, SEARCH_ENGINES["google"])
    return tmpl.format(q=urllib.parse.quote_plus(query))


def open_visible_search(query: str, engine: str = "google") -> list[str]:
    """
    Opens the search query visibly in the user's browser on the specified search engine
    (or across multiple flagship engines if engine == 'all' or 'multi').
    """
    eng = (engine or "google").lower().strip()
    opened = []
    if eng in ("all", "multi", "every"):
        for e_name in ("google", "bing", "brave", "duckduckgo", "perplexity"):
            u = build_engine_url(query, e_name)
            webbrowser.open(u)
            opened.append(f"{e_name.title()}: {u}")
    else:
        # Support comma-separated engines e.g. "google,youtube"
        parts = [p.strip() for p in eng.split(",") if p.strip()] or ["google"]
        for p in parts:
            u = build_engine_url(query, p)
            webbrowser.open(u)
            opened.append(f"{p.title()}: {u}")
    return opened


def _scrape_url(url: str, max_chars: int = 4000) -> dict:
    """Fetches and extracts clean readable text + title from any live web URL."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=7) as resp:
            ctype = resp.headers.get("Content-Type", "")
            raw = resp.read(300_000)
            html = raw.decode("utf-8", errors="ignore")

        if "application/json" in ctype:
            return {"url": url, "title": url, "text": html[:max_chars]}

        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "noscript", "svg", "footer", "nav", "header", "aside", "form"]):
                tag.decompose()
            title = soup.title.string.strip() if (soup.title and soup.title.string) else url
            paras = [p.get_text(" ", strip=True) for p in soup.find_all(["p", "h1", "h2", "h3", "li", "article"])]
            paras = [p for p in paras if len(p) > 25]
            body = "\n".join(paras)
            if len(body) < 120:
                body = soup.get_text(" ", strip=True)
            body = re.sub(r"\s{2,}", " ", body)
            return {"url": url, "title": title[:120], "text": body[:max_chars]}
        except Exception:
            clean = re.sub(r"<[^>]+>", " ", html)
            clean = re.sub(r"\s+", " ", clean).strip()
            return {"url": url, "title": url, "text": clean[:max_chars]}
    except Exception as e:
        return {"url": url, "title": url, "text": f"[Could not scrape {url}: {e}]"}


def _search_ddg(query: str, max_results: int = MAX_RESULTS) -> list:
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except Exception:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=max_results))
        except Exception:
            return []


def _search_bing_rss(query: str, max_results: int = 5) -> list:
    """Scrapes Bing search RSS feed for fast multi-engine cross-verification."""
    results = []
    try:
        url = f"https://www.bing.com/search?q={urllib.parse.quote_plus(query)}&format=rss"
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=5) as resp:
            xml_text = resp.read(150_000).decode("utf-8", errors="ignore")
        items = re.findall(r"<item>(.*?)</item>", xml_text, re.DOTALL)
        for item in items[:max_results]:
            t_m = re.search(r"<title>(.*?)</title>", item)
            l_m = re.search(r"<link>(.*?)</link>", item)
            d_m = re.search(r"<description>(.*?)</description>", item)
            if t_m and l_m:
                results.append({
                    "title": re.sub(r"<!\[CDATA\[|\]\]>", "", t_m.group(1)).strip(),
                    "href": l_m.group(1).strip(),
                    "body": re.sub(r"<[^>]+>|<!\[CDATA\[|\]\]>", "", d_m.group(1) if d_m else "").strip(),
                    "engine": "Bing",
                })
    except Exception:
        pass
    return results


def _search_wikipedia_api(query: str, max_results: int = 3) -> list:
    """Queries Wikipedia OpenSearch API for authoritative encyclopedic context."""
    results = []
    try:
        url = (
            "https://en.wikipedia.org/w/api.php?action=query&list=search"
            f"&srsearch={urllib.parse.quote_plus(query)}&utf8=&format=json&srlimit={max_results}"
        )
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        for item in data.get("query", {}).get("search", []):
            title = item.get("title", "")
            snippet = re.sub(r"<[^>]+>", "", item.get("snippet", ""))
            results.append({
                "title": f"{title} (Wikipedia)",
                "href": f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
                "body": snippet,
                "engine": "Wikipedia",
            })
    except Exception:
        pass
    return results


def _search_reddit_json(query: str, max_results: int = 3) -> list:
    """Queries Reddit public search JSON for real human discussions."""
    results = []
    try:
        url = f"https://www.reddit.com/search.json?q={urllib.parse.quote_plus(query)}&limit={max_results}&sort=relevance"
        req = urllib.request.Request(url, headers={**_HEADERS, "User-Agent": "JARVIS-Mark58/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        for child in data.get("data", {}).get("children", [])[:max_results]:
            post = child.get("data", {})
            results.append({
                "title": f"[r/{post.get('subreddit', 'reddit')}] {post.get('title', '')}",
                "href": f"https://www.reddit.com{post.get('permalink', '')}",
                "body": (post.get("selftext") or "")[:300],
                "engine": "Reddit",
            })
    except Exception:
        pass
    return results


def _federated_multi_engine_search(query: str) -> list:
    """Runs DuckDuckGo, Bing, Wikipedia, and Reddit searches in parallel and merges unique results."""
    combined = []
    seen_urls = set()
    with ThreadPoolExecutor(max_workers=4) as ex:
        f_ddg = ex.submit(_search_ddg, query, 6)
        f_bing = ex.submit(_search_bing_rss, query, 4)
        f_wiki = ex.submit(_search_wikipedia_api, query, 2)
        f_red = ex.submit(_search_reddit_json, query, 2)

        for fut in (f_ddg, f_bing, f_wiki, f_red):
            try:
                for item in fut.result(timeout=6):
                    href = item.get("href", "")
                    if href and href not in seen_urls:
                        seen_urls.add(href)
                        combined.append(item)
            except Exception:
                pass
    return combined[:12]


def _deep_surf(query: str, max_pages: int = 4) -> str:
    """
    Federated multi-engine search + concurrent full-page scraper + Gemini synthesis.
    """
    hits = _federated_multi_engine_search(query)
    if not hits:
        return f"No live results found for: {query}"

    urls = [h.get("href", "") for h in hits if h.get("href", "").startswith("http")][:max_pages]
    scraped_pages = []
    with ThreadPoolExecutor(max_workers=max(1, len(urls))) as pool:
        futs = {pool.submit(_scrape_url, u, 2500): u for u in urls}
        for fut in as_completed(futs):
            try:
                scraped_pages.append(fut.result())
            except Exception:
                pass

    compiled = [f"Federated Multi-Engine Web Intelligence for: '{query}'\n"]
    for idx, h in enumerate(hits[:6], 1):
        eng_tag = h.get("engine", "Web")
        compiled.append(f"[{idx}] ({eng_tag}) {h.get('title', '')} — {h.get('href', '')}\n    {h.get('body', '')[:220]}")

    compiled.append("\n--- Deep Scraped Live Page Extracts ---")
    for p in scraped_pages:
        compiled.append(f"\nSOURCE: {p['title']} ({p['url']})\n{p['text'][:1800]}")

    raw_dossier = "\n".join(compiled)

    api_key = _get_api_key()
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=(
                    "You are JARVIS synthesizing live multi-engine web pages scraped right now. "
                    "Provide a sharp, factual, well-structured answer with key facts, numbers, and source citations.\n\n"
                    f"{raw_dossier[:18000]}"
                ),
            )
            if resp and resp.text:
                return resp.text.strip()
        except Exception:
            pass

    return raw_dossier[:4000]


def search_all(query: str, engine: str = "all") -> str:
    eng = (engine or "all").lower().strip()
    if eng in ("all", "multi", "federated"):
        raw = _federated_multi_engine_search(query)
    elif eng == "bing":
        raw = _search_bing_rss(query, 7) or _search_ddg(query, 6)
    elif eng == "wikipedia":
        raw = _search_wikipedia_api(query, 5) or _search_ddg(query, 5)
    elif eng == "reddit":
        raw = _search_reddit_json(query, 5) or _search_ddg(f"site:reddit.com {query}", 5)
    elif eng in ("youtube", "scholar", "github", "arxiv", "stackoverflow"):
        raw = _search_ddg(f"site:{eng}.com {query}" if eng != "scholar" else f"{query} research paper", 6)
    else:
        raw = _federated_multi_engine_search(query)

    if not raw:
        return f"No results found for: {query}"

    lines = []
    for i, r in enumerate(raw[:8], 1):
        title = r.get("title", "")
        body = r.get("body", "")
        href = r.get("href", "")
        eng_tag = r.get("engine", "DDG")
        if title and body:
            lines.append(f"{i}. [{eng_tag}] {title}: {body[:240]} ({href})")
    return "\n".join(lines) if lines else f"No results for: {query}"


def compare(items: list, aspect: str = "general") -> str:
    results = []
    for item in items[:3]:
        q = f"{item} {aspect}" if aspect != "general" else item
        raw = _search_ddg(q, max_results=4)
        snippets = [r.get("body", "")[:160] for r in raw if r.get("body")]
        results.append(f"=== {item.upper()} ===\n" + ("\n".join(snippets[:3]) or "No info found."))
    return "\n\n".join(results)


def web_search(
    parameters: dict,
    response=None,
    player=None,
    session_memory=None,
) -> str:
    """
    Omni-Engine Internet Surfer & Visible Search Action.
    parameters:
        query        : Search query or topic to surf
        mode         : 'search' | 'visible_search' | 'surf' | 'read_url' | 'deep_surf' | 'research' | 'compare'
        engine       : 'google' | 'bing' | 'duckduckgo' | 'brave' | 'perplexity' | 'youtube' | 'scholar' |
                       'github' | 'reddit' | 'wikipedia' | 'arxiv' | 'stackoverflow' | 'wolfram' | 'all'
        url          : Direct URL to scrape/read (or open in browser)
        open_browser : Bool — if True (or mode=='visible_search'), visibly launches the search in the user's browser
        visible      : Alias for open_browser
    """
    params = parameters or {}
    query = params.get("query", "").strip()
    mode = params.get("mode", "search").lower().strip()
    engine = params.get("engine", "google").lower().strip()
    url = params.get("url", "").strip()
    items = params.get("items", [])
    aspect = params.get("aspect", "general")
    open_browser = bool(
        params.get("open_browser", False)
        or params.get("visible", False)
        or mode in ("visible", "visible_search", "browser", "open")
    )

    if not query and not url and not items:
        return "Please provide a search query or URL to surf, sir."

    if player and hasattr(player, "write_log"):
        target_lbl = url or query or ", ".join(items)
        player.write_log(f"SURF [{engine.upper()}/{mode.upper()}]: {target_lbl[:46]}")

    try:
        # 1. Direct URL Surf / Scrape
        if url or mode in ("surf", "read_url", "scrape") and query.startswith(("http://", "https://", "www.")):
            target_url = url or query
            if open_browser:
                webbrowser.open(target_url if target_url.startswith("http") else "https://" + target_url)
            page = _scrape_url(target_url, max_chars=4500)
            return f"Live Page Surf — {page['title']} ({page['url']}):\n{page['text']}"

        # 2. Visible Browser Search across any or all search engines
        opened_urls = []
        if open_browser and query:
            opened_urls = open_visible_search(query, engine=engine)

        # 3. Compare Mode
        if mode == "compare" and items:
            result = compare(items, aspect)
        # 4. Deep Autonomous Multi-Site Surf & Synthesis
        elif mode in ("deep_surf", "research", "deep", "surf"):
            result = _deep_surf(query)
        # 5. Federated Multi-Engine Search
        else:
            result = search_all(query, engine=engine)

        if opened_urls:
            vis_header = f"Visibly opened search on {', '.join(opened_urls)} in your browser.\n\n"
            result = vis_header + result

        return result

    except Exception as e:
        return f"Web surf error: {e}"
