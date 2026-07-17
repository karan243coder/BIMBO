# -*- coding: utf-8 -*-
# ============================================================
# BIMBO xHamster Profile Scraper - v7 UNIVERSAL DOMAIN
# ANY subdomain / mirror works: xhamster.com, .desi, .pro, xhms, etc.
# ============================================================

import re
import json
import html
import logging
import requests
from urllib.parse import urlparse, quote_plus, unquote

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


def _is_profile_url(url: str) -> bool:
    clean = _clean_url(url)
    host = _normalize_domain(url)
    patterns = [
        r"/channels/[^/]+",
        r"/creators/[^/]+",
        r"/profile/[^/]+",
        r"/user/[^/]+",
    ]
    for p in patterns:
        if re.search(p, clean, re.IGNORECASE):
            return True
    # Brand-based profile patterns on any subdomain
    for brand in ("xhamster", "xhms", "xhday", "xhvid", "xhopen", "xhwide", "xhchannel"):
        if brand in host:
            if re.search(r"(?:channels|creators)/[^/]+", clean, re.I):
                return True
    return False


def _extract_video_cards(html_text: str, base_domain: str):
    videos = []
    # Find all video URLs in HTML
    url_matches = re.finditer(
        r'href=["\'](/videos/\d+[^"\'\s<>]+)["\']',
        html_text,
        re.IGNORECASE
    )
    for m in url_matches:
        relative_url = m.group(1)
        full_url = f"{base_domain}{relative_url}" if not relative_url.startswith("http") else relative_url
        pos = m.start()
        snippet = html_text[max(0, pos-500):pos+500]
        
        title = "xHamster Video"
        title_candidates = re.findall(
            r'<[^>]+class=["\'][^"\']*(?:title|name|video-title)[^"\']*["\'][^>]*>([^<]{5,120})',
            snippet,
            re.IGNORECASE
        )
        if title_candidates:
            title = html.unescape(title_candidates[0]).strip()
        else:
            alt_title = re.search(r'<h2[^>]*>([^<]{5,100})</h2>', snippet, re.IGNORECASE)
            if alt_title:
                title = html.unescape(alt_title.group(1)).strip()
        
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
    next_patterns = [
        r'<a[^>]+href="([^"]+)"[^>]*>(?:Next|›|>&nbsp;Next|next page)</a>',
        r'<a[^>]+href="([^"]+)"[^>]*class=["\'][^"\']*next',
        r'class=["\'][^"\']*next[^"\']*["\'][^>]*href="([^"]+)"',
    ]
    for pat in next_patterns:
        match = re.search(pat, html_text, re.IGNORECASE)
        if match:
            next_url = match.group(1)
            if not next_url.startswith("http"):
                next_url = base_url.rsplit("/", 1)[0] + "/" + next_url.lstrip("/")
            pagination["next"] = next_url
            pagination["has_more"] = True
            break
    prev_patterns = [
        r'<a[^>]+href="([^"]+)"[^>]*>(?:Prev|‹|Previous|previous page)</a>',
    ]
    for pat in prev_patterns:
        match = re.search(pat, html_text, re.IGNORECASE)
        if match:
            prev_url = match.group(1)
            if not prev_url.startswith("http"):
                prev_url = base_url.rsplit("/", 1)[0] + "/" + prev_url.lstrip("/")
            pagination["prev"] = prev_url
            break
    return pagination


async def scrape_profile(url: str, cookies_path: str = None):
    try:
        session = requests.Session()
        clean_url = _clean_url(url)
        base_domain = _get_base_domain(url)
        headers = {
            "User-Agent": UA,
            "Referer": base_domain,
            "Accept": "text/html",
            "Connection": "keep-alive",
        }
        resp = session.get(clean_url, headers=headers, timeout=25)
        resp.raise_for_status()
        html_text = resp.text
        videos = _extract_video_cards(html_text, base_domain)
        pagination = _find_pagination(html_text, clean_url)
        return {
            "type": "profile",
            "original_url": clean_url,
            "base_domain": base_domain,
            "videos": videos,
            "pagination": pagination,
            "count": len(videos),
        }
    except Exception as e:
        logger.error(f"Profile scrape error: {e}")
        return {
            "type": "profile",
            "original_url": url,
            "base_domain": _get_base_domain(url),
            "videos": [],
            "pagination": {"next": None, "prev": None, "has_more": False},
            "count": 0,
            "error": str(e),
        }
