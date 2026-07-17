# -*- coding: utf-8 -*-
# ============================================================
# BIMBO xHamster Custom Engine - v7 UNIVERSAL DOMAIN
# ANY subdomain / mirror / brand works perfectly:
# xhamster.com, xhamster.desi, xhamster.one, xhamster.tv,
# xhamster.pro, xhamster.net, xhms.pro, xhday, xhvid, xhwide,
# xhwebcam, xhopen, xhtab, xhtotal, xhofficial, xhaccess, xhmoon,
# xhbig, xhbranch, xhchannel, xhdate, xhlease, xhcdn, xhamster46, etc.
# ============================================================

import re
import json
import html as html_lib
import logging
from urllib.parse import urlparse, unquote
import requests

logger = logging.getLogger(__name__)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

_XH_BRANDS = (
    "xhamster", "xhms", "xhday", "xhvid", "xhwide", "xhwebcam",
    "xhopen", "xhtab", "xhtotal", "xhofficial", "xhaccess", "xhmoon",
    "xhbig", "xhbranch", "xhchannel", "xhdate", "xhlease", "xhcdn",
    "xhamster46", "xhamster2", "xhopen", "xhms",
)
_XH_TLDS = (
    ".com", ".desi", ".one", ".tv", ".pro", ".net", ".to",
    ".xxx", ".porn", ".sex", ".mobi", ".cc", ".org",
)

QLABEL = {
    144: "144p", 240: "240p", 360: "360p", 480: "480p (SD)",
    720: "720p (HD)", 1080: "1080p (FHD)", 1440: "1440p", 2160: "4K",
}


def _normalize_domain(url: str) -> str:
    """Extract clean domain from any xHamster URL (any subdomain/mirror)."""
    try:
        host = urlparse(str(url)).hostname or ""
        host = host.lower()
        # Remove common prefixes
        host = re.sub(r"^(www\.|m\.|mobile\.|de\.|fr\.|es\.|it\.|pt\.|nl\.|ru\.|jp\.|en)\.", "", host)
        return host
    except Exception:
        return ""


def _get_base_domain(url: str) -> str:
    """Return full base URL (scheme + host) from any input."""
    try:
        p = urlparse(str(url))
        scheme = p.scheme or "https"
        host = p.hostname or (p.path.split("/")[0] if "/" in p.path else "xhamster.com")
        return f"{scheme}://{host}"
    except Exception:
        return "https://xhamster.com"


def is_xhamster(url: str) -> bool:
    host = _normalize_domain(url)
    if "xhamster" in host:
        return True
    for brand in _XH_BRANDS:
        if host == brand or host.startswith(brand + ".") or f".{brand}." in host:
            return True
    for brand in _XH_BRANDS:
        for tld in _XH_TLDS:
            full = brand + tld
            if host == full or host.startswith(full + ".") or host.endswith("." + full):
                return True
    if re.match(r"^xh[a-z0-9]{1,12}\.(com|desi|one|tv|pro|net|to|xxx|porn|cc)$", host):
        return True
    return False


def _clean_xhamster_page_url(url: str) -> str:
    url = html_lib.unescape(str(url or "").strip())
    m = re.search(r"https?://[^\s<>\"'\)]+", url)
    if m:
        url = m.group(0)
    url = url.strip().strip("`'\"<>[]()")
    try:
        p = urlparse(url)
        return p._replace(query="", fragment="").geturl()
    except Exception:
        return url.split("?", 1)[0].split("#", 1)[0]


def _to_desktop(url: str) -> str:
    return re.sub(r"^(https?://(?:.+?\.)?)m\.", r"\1", str(url or "").strip())


def _base_of(url: str) -> str:
    return _get_base_domain(url)


def _normalize_html_for_urls(text: str) -> str:
    if not text:
        return ""
    out = html_lib.unescape(str(text))
    out = out.replace("\\/", "/").replace("\\u002F", "/").replace("\\u002f", "/")
    out = out.replace("\\u0026", "&").replace("\\u003D", "=").replace("\\u003d", "=")
    try:
        out2 = unquote(out)
        if out2 != out:
            out = out + "\n" + out2
    except Exception:
        pass
    return out


def _find_m3u8_candidates(text: str):
    text = _normalize_html_for_urls(text)
    candidates = []
    for m in re.finditer(r'https?://[^"\'\s<>]+?\.m3u8[^"\'\s<>]*', text, re.I):
        u = m.group(0).rstrip('\\,;)}]')
        if u not in candidates:
            candidates.append(u)
    return candidates


def _pick_best_master(candidates):
    if not candidates:
        return None
    def score(u):
        lu = u.lower()
        sc = 0
        if "_tpl_" in lu:
            sc += 100
        if "hls" in lu:
            sc += 40
        if "h264" in lu:
            sc += 30
        if "av1" in lu:
            sc += 10
        if "multi=" in lu:
            sc += 20
        if "/seg-" in lu:
            sc -= 100
        return sc
    return sorted(candidates, key=score, reverse=True)[0]


def _ytdlp_decipher():
    try:
        import yt_dlp
        from yt_dlp.extractor.xhamster import XHamsterIE
        ydl = yt_dlp.YoutubeDL({"quiet": True, "no_warnings": True})
        ie = XHamsterIE()
        ie.set_downloader(ydl)
        def dec(u, fid="hls"):
            try:
                return ie._decipher_format_url(u, fid)
            except Exception:
                return None
        return dec
    except Exception as e:
        logger.warning("xhamster: yt-dlp decipher unavailable: %s", e)
        return None


def _extract_window_initials(html: str):
    if not html:
        return None
    idx = html.find("window.initials")
    if idx < 0:
        return None
    start = html.find("{", idx)
    if start < 0:
        return None
    depth = 0
    in_str = False
    quote = ""
    esc = False
    end = None
    for i in range(start, len(html)):
        ch = html[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == quote:
                in_str = False
            continue
        if ch in ('"', "'"):
            in_str = True
            quote = ch
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    if end is None:
        return None
    raw = html[start:end]
    try:
        return json.loads(raw)
    except Exception as e:
        logger.warning("xhamster: window.initials json load failed: %s", e)
        return None


def _walk_strings(obj):
    if isinstance(obj, dict):
        for v in obj.values():
            yield from _walk_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk_strings(v)
    elif isinstance(obj, str):
        yield obj


def _walk_key_values(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else str(k)
            yield p, k, v
            yield from _walk_key_values(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk_key_values(v, f"{path}[{i}]")


def _decipher_candidates(values):
    if not values:
        return None
    dec = _ytdlp_decipher()
    seen = set()
    cleaned = []
    for val in values:
        if not isinstance(val, str):
            continue
        val = _normalize_html_for_urls(val).strip().strip('"\'')
        if val and val not in seen:
            seen.add(val)
            cleaned.append(val)
    direct = []
    for val in cleaned:
        if ".m3u8" in val or "m3u8" in val.lower():
            direct.extend(_find_m3u8_candidates(val))
        if val.startswith("http") and ".m3u8" in val:
            direct.append(val)
    picked = _pick_best_master(direct)
    if picked:
        return picked
    if not dec:
        return None
    for val in cleaned:
        low = val.lower()
        looks_candidate = (
            re.fullmatch(r"[0-9a-fA-F]{40,}", val)
            or (val.startswith("http") and re.search(r"/[0-9a-fA-F]{40,}(?:[/,]|$)", val))
            or ("hls" in low and len(val) > 30)
        )
        if not looks_candidate:
            continue
        for fid in ("h264", "av1", "hls"):
            out = dec(val, fid)
            if out and ".m3u8" in out:
                return out
    return None


def _find_hls_from_initials(initials):
    if not isinstance(initials, dict):
        return None
    direct = []
    for val in _walk_strings(initials):
        if ".m3u8" in val or "m3u8" in val.lower():
            direct.extend(_find_m3u8_candidates(val))
        if val.startswith("http") and ".m3u8" in val:
            direct.append(val)
    picked = _pick_best_master(direct)
    if picked:
        return picked
    candidates = []
    priority = []
    for path, key, value in _walk_key_values(initials):
        p = path.lower()
        k = str(key).lower()
        if isinstance(value, str):
            if any(w in p for w in ("hls", "source", "sources", "h264", "av1", "fallback", "video")):
                candidates.append(value)
            if any(w in p for w in ("hls", "h264", "fallback")):
                priority.append(value)
        elif k in ("url", "fallback", "src", "file") and len(value) > 30:
            candidates.append(value)
        elif isinstance(value, dict) and any(w in p for w in ("hls", "h264", "av1", "source", "sources")):
            for sv in _walk_strings(value):
                candidates.append(sv)
            priority.append(sv)
    out = _decipher_candidates(priority)
    if out:
        return out
    out = _decipher_candidates(candidates)
    if out:
        return out
    broad = [v for v in _walk_strings(initials) if len(v) > 40]
    return _decipher_candidates(broad)


def _heights_from_master(master_text: str):
    hs = set()
    for m in re.finditer(r"RESOLUTION=\d+x(\d+)", master_text or ""):
        hs.add(int(m.group(1)))
    return sorted(hs)


def _build_variant_url(master_url: str, height: int) -> str:
    u = master_url or ""
    u = u.replace(".av1.mp4.m3u8", ".h264.mp4.m3u8")
    u = u.replace("/av1/", "/h264/")
    u = u.replace(".av1.", ".h264.")
    if "_TPL_" in u:
        u = u.replace("_TPL_", f"{height}p")
    return u


def is_profile_url(url: str) -> bool:
    clean = _clean_xhamster_page_url(url)
    host = _normalize_domain(url)
    # Any subdomain with profile paths
    patterns = [
        r"/channels/[^/]+",
        r"/creators/[^/]+",
        r"/profile/[^/]+",
        r"/user/[^/]+",
    ]
    for p in patterns:
        if re.search(p, clean, re.IGNORECASE):
            return True
    # Brand-based profile patterns
    for brand in _XH_BRANDS:
        if brand in host:
            match = re.search(r"(?:channels|creators)/[^/]+", clean, re.I)
            if match:
                return True
    return False


def is_page_url(url: str) -> bool:
    clean = _clean_xhamster_page_url(url)
    if "/search/" in clean:
        return False
    if is_xhamster(url) and not is_single_video(clean) and not is_profile_url(url):
        return True
    return False


def is_search_url(url: str) -> bool:
    clean = _clean_xhamster_page_url(url)
    return "/search/" in clean


def is_single_video(url: str) -> bool:
    clean = _clean_xhamster_page_url(url)
    if not clean.startswith("http"):
        clean = f"https://{_normalize_domain(url) or 'xhamster.com'}{clean}" if clean.startswith("/") else f"https://{_normalize_domain(url) or 'xhamster.com'}/{clean}"
    return bool(re.search(r"/videos/\d+/[^/]*$", clean)) or bool(re.search(r"/videos/\d+$", clean))


def extract(url: str, cookies_path: str = None) -> dict:
    try:
        cookies_path = cookies_path if cookies_path and __import__('os').path.exists(cookies_path) else None
        clean_url = _clean_xhamster_page_url(url)
        base_domain = _get_base_domain(url)
        if not clean_url.startswith("http"):
            clean_url = f"{base_domain}{clean_url}" if clean_url.startswith("/") else f"{base_domain}/{clean_url}"
        
        headers = {
            "User-Agent": UA,
            "Referer": base_domain,
            "Accept": "text/html",
        }
        session = requests.Session()
        resp = session.get(clean_url, headers=headers, timeout=25)
        resp.raise_for_status()
        
        initials = _extract_window_initials(resp.text)
        
        if initials:
            hls_url = _find_hls_from_initials(initials)
            if hls_url:
                qualities = []
                master_text = hls_url
                heights = _heights_from_master(master_text)
                for h in heights:
                    qualities.append({
                        "height": h,
                        "label": QLABEL.get(h, f"{h}p"),
                        "m3u8": _build_variant_url(hls_url, h),
                    })
                if not qualities:
                    qualities.append({
                        "height": 720,
                        "label": "720p (HD)",
                        "m3u8": hls_url,
                    })
                duration = None
                title = "xHamster Video"
                for path, k, v in _walk_key_values(initials):
                    if isinstance(v, str) and ("title" in k.lower() or "name" in k.lower()):
                        title = v[:200]
                        break
                return {
                    "type": "video",
                    "url": clean_url,
                    "title": title,
                    "qualities": sorted(qualities, key=lambda x: -x["height"]),
                    "duration": duration,
                    "engine_version": "v7-universal",
                }
        
        candidates = _find_m3u8_candidates(resp.text)
        best = _pick_best_master(candidates)
        if best:
            return {
                "type": "video",
                "url": clean_url,
                "title": "xHamster Video",
                "qualities": [{"height": 720, "label": "720p (HD)", "m3u8": best}],
                "duration": None,
                "engine_version": "v7-universal",
            }
        
        return {"type": "unknown", "url": clean_url, "error": "No m3u8 found"}
    except Exception as e:
        logger.error(f"xHamster extract error: {e}")
        return {"type": "error", "url": url, "error": str(e)}
