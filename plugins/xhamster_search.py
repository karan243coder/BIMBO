# -*- coding: utf-8 -*-
# ============================================================
# BIMBO xHamster Search Engine - v7 UNIVERSAL DOMAIN
# ANY domain / subdomain works for search.
# ============================================================

import re
import html
import logging
import requests
from urllib.parse import quote_plus, urlparse

logger = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def _normalize_domain(url: str) -> str:
    try:
        host = urlparse(str(url)).hostname or ""
        host = host.lower()
        host = re.sub(r"^(www\.|m\.|mobile\.|de\.|fr\.|es\.|it\.|pt\.|nl\.|ru\.|jp\.|en)\.", "", host)
        return host
    except Exception:
        return ""


def _get_base_domain(url: str) -> str:
    try:
        p = urlparse(str(url))
        scheme = p.scheme or "https"
        host = p.hostname or (p.path.split("/")[0] if "/" in p.path else "xhamster.com")
        return f"{scheme}://{host}"
    except Exception:
        return "https://xhamster.com"


def _build_search_url(query: str, base_domain: str = None) -> str:
    if base_domain is None:
        base_domain = "https://xhamster.com"
    encoded = quote_plus(query)
    return f"{base_domain}/search/{encoded}"


def _extract_search_results(html_text: str, base_domain: str, base_search_url: str):
    videos = []
    url_matches = re.finditer(
        r'href=["\']((?:https?://[^/]+)?/videos/[a-zA-Z0-9_-][^"\'\s<>]*?)["\']',
        html_text,
        re.IGNORECASE
    )
    for m in url_matches:
        relative_url = m.group(1)
        full_url = f"{base_domain}{relative_url}" if not relative_url.startswith("http") else relative_url
        pos = m.start()
        snippet = html_text[max(0, pos-1000):pos+1200]
        
        title = "xHamster Video"
        # Try alt/title near video link first
        title_match = re.search(
            r'<[^>]+(?:alt|title)=["\']([^"\']{3,120})["\']',
            snippet,
            re.IGNORECASE
        )
        if title_match:
            title = html.unescape(title_match.group(1)).strip()
        else:
            title_candidates = re.findall(
                r'<[^>]+class=["\'][^"\']*(?:video-title|title|name)[^"\']*["\'][^>]*>([^<]{5,120})',
                snippet,
                re.IGNORECASE
            )
            if title_candidates:
                title = html.unescape(title_candidates[0]).strip()
        
        duration_str = "0:00"
        duration_sec = 0
        duration_patterns = [
            r'(\d{1,2}:\d{2}(?::\d{2})?)',
            r'(\d+)\s*min(?:ute)?',
        ]
        for dp in duration_patterns:
            dmatch = re.search(dp, snippet)
            if dmatch:
                duration_str = dmatch.group(1)
                if duration_str.isdigit():
                    duration_sec = int(duration_str)
                else:
                    parts = duration_str.split(":")
                    try:
                        if len(parts) == 2:
                            duration_sec = int(parts[0])*60 + int(parts[1])
                        elif len(parts) == 3:
                            duration_sec = int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
                    except:
                        duration_sec = 0
                break
        
        if not any(v.get("url") == full_url for v in videos):
            videos.append({
                "url": full_url,
                "title": title,
                "duration_str": duration_str,
                "duration_sec": duration_sec,
                "label": f"{title[:40]} | ⏱ {duration_str}" if len(title) <= 40 else f"{title[:35]}... | ⏱ {duration_str}",
            })
    seen = set()
    unique = []
    for v in videos:
        if v["url"] not in seen:
            seen.add(v["url"])
            unique.append(v)
    return unique  # More videos; pagination for rest


def _find_pagination_search(html_text: str, base_url: str, base_domain: str):
    pagination = {"next": None, "prev": None, "has_more": False}
    page_links = re.finditer(
        r'<a[^>]+href="([^"]*)"[^>]*>([^<]{0,20})</a>',
        html_text,
        re.IGNORECASE
    )
    for m in page_links:
        link = m.group(1)
        text = m.group(2)
        if ("next" in text.lower() or "›" in text) and link:
            full_link = link if link.startswith("http") else f"{base_domain}{link}" if link.startswith("/") else f"{base_domain}/{link}"
            pagination["next"] = full_link
            pagination["has_more"] = True
            break
    return pagination


async def search_videos(query: str, cookies_path: str = None, base_domain: str = None):
    # If query is already a full URL, use it directly
    if isinstance(query, str) and query.startswith("http"):
        url = query
        base_domain_from_url = urlparse(query).scheme + "://" + (urlparse(query).hostname or "xhamster.com")
        base_domain = base_domain or base_domain_from_url
    else:
        base_domain = base_domain or "https://xhamster.com"
        url = _build_search_url(query, base_domain)
    try:
        session = requests.Session()
        headers = {
            "User-Agent": UA,
            "Referer": base_domain,
            "Accept": "text/html",
        }
        cookies = {}
        if cookies_path and __import__('os').path.exists(cookies_path):
            try:
                with open(cookies_path, "r") as f:
                    for line in f:
                        if not line.startswith('#') and line.strip() and '\t' in line:
                            parts = line.strip().split('\t')
                            if len(parts) >= 7:
                                cookies[parts[5]] = parts[6]
            except Exception as e:
                logger.warning(f"Cookie load error: {e}")
        resp = session.get(url, headers=headers, cookies=cookies, timeout=25)
        # If cookies cause 400/403, retry without cookies
        if resp.status_code in (400, 403, 401):
            resp = session.get(url, headers=headers, cookies={}, timeout=25)
        resp.raise_for_status()
        html_text = resp.text
        videos = _extract_search_results(html_text, base_domain, url)
        pagination = _find_pagination_search(html_text, url, base_domain)
        return {
            "type": "search",
            "query": query,
            "search_url": url,
            "base_domain": base_domain,
            "videos": videos,
            "pagination": pagination,
            "count": len(videos),
        }
    except Exception as e:
        logger.error(f"Search error: {e}")
        return {
            "type": "search",
            "query": query,
            "search_url": url,
            "base_domain": base_domain,
            "videos": [],
            "pagination": {"next": None, "prev": None, "has_more": False},
            "count": 0,
            "error": str(e),
        }
