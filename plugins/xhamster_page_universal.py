# -*- coding: utf-8 -*-
# ============================================================
# BIMBO xHamster Page Scraper - v7 UNIVERSAL + BROAD REGEX
# ANY domain/subdomain works with enhanced video detection.
# ============================================================

import re
import html
import logging
import requests
from urllib.parse import urlparse, unquote

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


def _clean_url(url: str) -> str:
    url = str(url or "").strip()
    url = unquote(url)
    url = url.replace("&amp;", "&")
    m = re.search(r"https?://[^\s<>\"'\)]+", url)
    if m:
        url = m.group(0)
    return url.strip("`'\"<>[]()")


def _find_video_links(html_text: str):
    links = []
    # Broad patterns for video links
    patterns = [
        r'href=["\'](/videos/\d+[^"\'\s<>]*?)["\']',
        r'href=["\'](/videos/[0-9]+/[^"\'\s<>]+?)["\']',
    ]
    for pat in patterns:
        for m in re.finditer(pat, html_text, re.IGNORECASE):
            rel = m.group(1)
            if rel not in links:
                links.append(rel)
    return links[:30]


def _extract_video_cards(html_text: str, base_domain: str):
    videos = []
    links = _find_video_links(html_text)
    for rel_url in links:
        full_url = f"{base_domain}{rel_url}" if not rel_url.startswith("http") else rel_url
        pos = html_text.find(rel_url)
        if pos < 0:
            pos = html_text.find('href="' + rel_url)
        snippet = html_text[max(0, pos-600):pos+600] if pos >= 0 else html_text[:1200]
        
        title = "xHamster Video"
        # Very broad title extraction
        title_match = re.search(
            r'<[^>]+(?:alt|title)=["\']([^"\']{3,120})["\']',
            snippet,
            re.IGNORECASE
        )
        if title_match:
            title = html.unescape(title_match.group(1)).strip()
        else:
            h_match = re.search(
                r'<h[234][^>]*>([^<]{3,120})</h[234]>',
                snippet,
                re.IGNORECASE | re.DOTALL
            )
            if h_match:
                title = html.unescape(re.sub(r'<[^>]+>', '', h_match.group(1))).strip()
            else:
                a_match = re.search(
                    r'<a[^>]*>\s*([^<]{3,120})\s*</a>',
                    snippet,
                    re.IGNORECASE
                )
                if a_match:
                    title = html.unescape(a_match.group(1)).strip()
        
        duration_str = "0:00"
        duration_sec = 0
        duration_patterns = [
            r'(\d{1,2}:\d{2}(?::\d{2})?)',
            r'(\d+)\s*min(?:ute)?',
            r'(\d+)\s*sec(?:ond)?',
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
    return unique[:20]


def _find_pagination(html_text: str, base_url: str):
    pagination = {"next": None, "prev": None, "has_more": False}
    pag_links = re.finditer(
        r'<a[^>]+href="([^"]+)"[^>]*>([^<]{0,30})</a>',
        html_text,
        re.IGNORECASE
    )
    for m in pag_links:
        link = m.group(1)
        text = m.group(2).lower()
        is_next_indicator = ("next" in text or "›" in text or ">" in text or "older" in text)
        is_pagination_param = ("p=" in link or "page=" in link or "/page/" in link)
        if (is_next_indicator or is_pagination_param) and link and link != base_url:
            if not link.startswith("http"):
                link = base_url.rsplit("/", 1)[0] + "/" + link.lstrip("/") if link.startswith("/") else base_url + "/" + link
            pagination["next"] = link
            pagination["has_more"] = True
            break
    prev_links = re.finditer(
        r'<a[^>]+href="([^"]+)"[^>]*>([^<]{0,30})</a>',
        html_text,
        re.IGNORECASE
    )
    for m in prev_links:
        link = m.group(1)
        text = m.group(2).lower()
        if ("prev" in text or "‹" in text or "previous" in text or "newer" in text) and link and link != base_url:
            if not link.startswith("http"):
                link = base_url.rsplit("/", 1)[0] + "/" + link.lstrip("/") if link.startswith("/") else base_url + "/" + link
            pagination["prev"] = link
            break
    return pagination


async def scrape_page(url: str, cookies_path: str = None):
    try:
        session = requests.Session()
        clean_url = _clean_url(url)
        base_domain = _get_base_domain(url)
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
        headers = {
            "User-Agent": UA,
            "Referer": base_domain,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Connection": "keep-alive",
        }
        resp = session.get(clean_url, headers=headers, cookies=cookies, timeout=30)
        resp.raise_for_status()
        html_text = resp.text
        videos = _extract_video_cards(html_text, base_domain)
        pagination = _find_pagination(html_text, clean_url)
        
        # Fallback if no videos
        if not videos:
            try:
                from plugins.xhamster_engine import extract as xh_extract
                xh = xh_extract(url, cookies_path)
                if xh and xh.get("type") == "video":
                    videos.append({
                        "url": url,
                        "title": xh.get("title", "xHamster Video"),
                        "duration_str": "0:00",
                        "duration_sec": xh.get("duration", 0),
                        "label": f"{xh.get('title', 'Video')[:40]} | ⏱ 0:00",
                    })
            except Exception as fallback_e:
                logger.warning(f"Page fallback error: {fallback_e}")
        
        return {
            "type": "page",
            "original_url": clean_url,
            "base_domain": base_domain,
            "videos": videos,
            "pagination": pagination,
            "count": len(videos),
        }
    except Exception as e:
        logger.error(f"Page scrape error: {e}")
        return {
            "type": "page",
            "original_url": url,
            "base_domain": _get_base_domain(url),
            "videos": [],
            "pagination": {"next": None, "prev": None, "has_more": False},
            "count": 0,
            "error": str(e),
        }
