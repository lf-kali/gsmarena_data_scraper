"""
GSMArena Scraper
================
Scrapes all brands and their devices from GSMArena and saves the data as JSON files.

Output structure:
    output/
    ├── brands.json                  # List of all brands with metadata
    └── brands/
        ├── samsung.json             # All Samsung devices with full specs
        ├── apple.json
        └── ...

Usage:
    # Scrape everything (may take many hours):
    python gsmarena_scraper.py

    # Scrape only specific brands:
    python gsmarena_scraper.py --brands samsung apple nothing

    # Limit devices per brand (for testing):
    python gsmarena_scraper.py --brands nothing --max-devices 5

    # Adjust delay between requests (seconds, default 2.0):
    python gsmarena_scraper.py --delay 1.5

    # Custom output directory:
    python gsmarena_scraper.py --output ./data

Requirements:
    pip install requests beautifulsoup4 lxml
"""

import argparse
import json
import os
import random
import re
import time
import logging
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Parser detection — use lxml if available, fall back to html.parser
# ---------------------------------------------------------------------------

try:
    import lxml  # noqa: F401
    HTML_PARSER = "lxml"
except ImportError:
    HTML_PARSER = "html.parser"

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://www.gsmarena.com"
MAKERS_URL = f"{BASE_URL}/makers.php3"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": BASE_URL,
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)
log.info("HTML parser: %s", HTML_PARSER)


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def get_page(url: str, session: requests.Session, delay: float = 2.0, retries: int = 5) -> Optional[BeautifulSoup]:
    """
    Fetch a URL and return a BeautifulSoup object.

    - Applies a randomized delay (jitter ±50%) before every request to avoid
      triggering rate-limit detection from fixed-interval patterns.
    - Explicitly handles HTTP 429 (Too Many Requests): respects the
      Retry-After response header if present, otherwise waits progressively
      longer on each attempt (60s → 120s → 180s …).
    - Falls back gracefully on other network errors with exponential backoff.
    """
    for attempt in range(1, retries + 1):
        # Jitter: randomize the delay by ±50% to break fixed-interval patterns.
        # e.g. delay=8 → actual wait is anywhere between 4s and 12s.
        jitter = delay * random.uniform(0.5, 1.5)
        log.debug("Waiting %.1fs before request (attempt %d/%d)", jitter, attempt, retries)
        time.sleep(jitter)

        try:
            resp = session.get(url, headers=HEADERS, timeout=20)

            # Handle 429 explicitly before raise_for_status so we can read
            # the Retry-After header and wait the correct amount of time.
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 60 * attempt))
                log.warning(
                    "429 Too Many Requests for %s — waiting %ds before retry (attempt %d/%d)",
                    url, retry_after, attempt, retries,
                )
                time.sleep(retry_after)
                continue

            resp.raise_for_status()
            return BeautifulSoup(resp.text, HTML_PARSER)

        except requests.RequestException as exc:
            wait = delay * (2 ** attempt)
            log.warning(
                "Attempt %d/%d failed for %s: %s — retrying in %.1fs",
                attempt, retries, url, exc, wait,
            )
            time.sleep(wait)

    log.error("All retries exhausted for %s", url)
    return None


# ---------------------------------------------------------------------------
# Brand scraping
# ---------------------------------------------------------------------------

def scrape_brands(session: requests.Session, delay: float) -> list[dict]:
    """
    Parse makers.php3 and return a list of brand dicts:
        {
            "brand_id": "9",
            "name": "Samsung",
            "slug": "samsung",
            "url": "https://www.gsmarena.com/samsung-phones-9.php",
            "device_count": 1454
        }
    """
    log.info("Fetching brands list from %s", MAKERS_URL)
    soup = get_page(MAKERS_URL, session, delay)
    if not soup:
        raise RuntimeError("Could not fetch brands page")

    brands = []
    # The table in makers.php3 contains <a> tags like:
    #   <a href="samsung-phones-9.php">Samsung 1454 devices</a>
    table = soup.find("table")
    if not table:
        raise RuntimeError("Could not find brands table in makers.php3")

    for a in table.find_all("a", href=True):
        href = a["href"]
        # Pattern: {slug}-phones-{id}.php
        match = re.match(r"^([\w&_\-\.]+)-phones-(\d+)\.php$", href)
        if not match:
            continue
        slug_raw, brand_id = match.group(1), match.group(2)

        text = a.get_text(strip=True)
        # Text is like "Samsung 1454 devices"
        count_match = re.search(r"(\d+)\s+devices?$", text, re.IGNORECASE)
        device_count = int(count_match.group(1)) if count_match else 0
        name = re.sub(r"\s+\d+\s+devices?$", "", text, flags=re.IGNORECASE).strip()

        brands.append({
            "brand_id": brand_id,
            "name": name,
            "slug": slug_raw.replace("_", "-").lower(),
            "url": f"{BASE_URL}/{href}",
            "device_count": device_count,
        })

    log.info("Found %d brands", len(brands))
    return brands


# ---------------------------------------------------------------------------
# Device list scraping (with pagination)
# ---------------------------------------------------------------------------

def _parse_device_list_page(soup: BeautifulSoup) -> list[dict]:
    """
    Extract device stubs from a brand listing page.
    Returns list of {name, url, device_id, thumbnail}.
    """
    devices = []
    # Devices are listed inside <div class="makers"> > <ul> > <li> > <a>
    makers_div = soup.find("div", class_="makers")
    if not makers_div:
        return devices

    for li in makers_div.find_all("li"):
        a = li.find("a", href=True)
        if not a:
            continue
        href = a["href"]
        # href looks like: nothing_phone_(4a)_5g-14503.php
        id_match = re.search(r"-(\d+)\.php$", href)
        if not id_match:
            continue
        device_id = id_match.group(1)

        # Name from <span> or <strong> inside the <a>
        span = a.find("span")
        strong = a.find("strong")
        name = (strong or span or a).get_text(strip=True) if (strong or span) else a.get_text(strip=True)

        # Thumbnail
        img = a.find("img")
        thumbnail = img["src"] if img and img.get("src") else ""

        # Quick-spec from img title attribute
        quick_spec = img.get("title", "").strip() if img else ""

        devices.append({
            "name": name,
            "device_id": device_id,
            "url": f"{BASE_URL}/{href}",
            "thumbnail": thumbnail,
            "quick_spec": quick_spec,
        })

    return devices


def scrape_device_list(brand: dict, session: requests.Session, delay: float, max_devices: Optional[int] = None) -> list[dict]:
    """
    Crawl all paginated pages for a brand and return the full device stub list.
    GSMArena pagination pattern: {slug}-phones-f-{brand_id}-0-r1-p{page}.php
    """
    url = brand["url"]
    all_devices = []
    page_num = 1

    while True:
        log.info("  [%s] Fetching device list page %d (%s)", brand["name"], page_num, url)
        soup = get_page(url, session, delay)
        if not soup:
            break

        devices = _parse_device_list_page(soup)
        if not devices:
            break

        all_devices.extend(devices)
        log.info("  [%s] Found %d devices so far", brand["name"], len(all_devices))

        if max_devices and len(all_devices) >= max_devices:
            all_devices = all_devices[:max_devices]
            break

        # Check for "next page" link
        # GSMArena uses <a class="pages-next"> or a link with title "Next page"
        next_link = soup.find("a", title="Next page") or soup.find("a", class_="pages-next")
        if not next_link or not next_link.get("href"):
            break

        next_href = next_link["href"]
        url = f"{BASE_URL}/{next_href}" if not next_href.startswith("http") else next_href
        page_num += 1

    return all_devices


# ---------------------------------------------------------------------------
# Device spec scraping
# ---------------------------------------------------------------------------

def scrape_device_specs(device: dict, session: requests.Session, delay: float) -> dict:
    """
    Fetch a device page and parse the spec tables into a nested dict.
    """
    soup = get_page(device["url"], session, delay)
    if not soup:
        return {}

    specs = {}

    # The specs are in <table> elements inside <div id="specs-list">
    # Each table has a heading row (th with colspan=3), then rows:
    #   <td class="ttl"><a>Spec Name</a></td>
    #   <td class="nfo">Value</td>
    specs_div = soup.find("div", id="specs-list")
    if not specs_div:
        # Fallback: try any table with class "table-striped"
        specs_div = soup

    current_section = "General"
    for table in specs_div.find_all("table"):
        # Section heading: first <th> with colspan
        th = table.find("th")
        if th:
            current_section = th.get_text(strip=True)
            specs.setdefault(current_section, {})

        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) < 2:
                continue

            # Cell 0 is "ttl" (spec name), cell 1 is "nfo" (value)
            key = cells[0].get_text(separator=" ", strip=True)
            value = cells[1].get_text(separator="\n", strip=True)
            if key and value:
                specs.setdefault(current_section, {})[key] = value

    # Also grab quick summary stats from the highlighted bar
    highlights = {}
    for li in soup.select("ul.specs-highlight li, ul.key-specs li"):
        icon_span = li.find("span", class_="spec-title") or li.find("span")
        val_span = li.find("em") or li.find("strong")
        if icon_span and val_span:
            highlights[icon_span.get_text(strip=True)] = val_span.get_text(strip=True)

    return {
        "name": device["name"],
        "device_id": device["device_id"],
        "url": device["url"],
        "thumbnail": device["thumbnail"],
        "quick_spec": device.get("quick_spec", ""),
        "highlights": highlights,
        "specs": specs,
    }


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def save_json(data, path: Path, indent: int = 2):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)
    log.info("Saved → %s", path)


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="GSMArena scraper")
    parser.add_argument("--brands", nargs="*", metavar="SLUG",
                        help="Brands to scrape by slug (e.g. samsung apple). Default: all brands.")
    parser.add_argument("--max-devices", type=int, default=None,
                        help="Max devices per brand (useful for testing).")
    parser.add_argument("--delay", type=float, default=2.0,
                        help="Seconds between requests (default: 2.0).")
    parser.add_argument("--output", type=str, default="output",
                        help="Output directory (default: ./output).")
    parser.add_argument("--skip-specs", action="store_true",
                        help="Only save device list, skip fetching individual spec pages.")
    args = parser.parse_args()

    output_dir = Path(args.output)
    brands_dir = output_dir / "brands"
    brands_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update(HEADERS)

    # 1. Scrape brands
    all_brands = scrape_brands(session, args.delay)

    # Filter to requested brands if --brands was given
    if args.brands:
        filter_slugs = {s.lower() for s in args.brands}
        target_brands = [b for b in all_brands if b["slug"] in filter_slugs or b["name"].lower() in filter_slugs]
        if not target_brands:
            log.error("No brands matched %s. Available slugs: %s",
                      args.brands, [b["slug"] for b in all_brands])
            return
    else:
        target_brands = all_brands

    # Save brands.json
    save_json(all_brands, output_dir / "brands.json")

    # 2. For each brand: scrape device list, then specs
    for brand in target_brands:
        brand_slug = brand["slug"]
        brand_output = brands_dir / f"{brand_slug}.json"

        # Load previously scraped data if available (resume support)
        existing_data = {}
        existing_ids = set()
        if brand_output.exists():
            try:
                with open(brand_output, encoding="utf-8") as f:
                    existing_data = json.load(f)
                existing_ids = {d["device_id"] for d in existing_data.get("devices", [])}
                log.info("[%s] Resuming — %d devices already saved", brand["name"], len(existing_ids))
            except Exception:
                pass

        log.info("── Brand: %s ──────────────────────────", brand["name"])

        # Scrape device stubs
        device_stubs = scrape_device_list(brand, session, args.delay, args.max_devices)

        if not device_stubs:
            log.warning("[%s] No devices found — skipping", brand["name"])
            continue

        # Enrich each stub with full specs (unless --skip-specs)
        enriched_devices = list(existing_data.get("devices", []))  # start from existing
        for i, stub in enumerate(device_stubs):
            if stub["device_id"] in existing_ids:
                log.info("  [%s] (%d/%d) %s — already scraped, skipping",
                         brand["name"], i + 1, len(device_stubs), stub["name"])
                continue

            if args.skip_specs:
                enriched_devices.append(stub)
            else:
                log.info("  [%s] (%d/%d) Scraping specs: %s",
                         brand["name"], i + 1, len(device_stubs), stub["name"])
                full = scrape_device_specs(stub, session, args.delay)
                enriched_devices.append(full if full else stub)

            # Auto-save after every 10 devices in case of interruption
            if (i + 1) % 10 == 0:
                save_json(
                    {"brand": brand, "devices": enriched_devices},
                    brand_output,
                )

        # Final save for this brand
        save_json(
            {"brand": brand, "devices": enriched_devices},
            brand_output,
        )
        log.info("[%s] Done — %d devices saved to %s", brand["name"], len(enriched_devices), brand_output)

    log.info("═══════════════════════════════════════")
    log.info("All done! Output at: %s", output_dir.resolve())


if __name__ == "__main__":
    main()