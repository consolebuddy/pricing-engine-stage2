#!/usr/bin/env python3
import argparse, sys, json, os, time, itertools
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

import yaml

try:
    import requests
    from bs4 import BeautifulSoup
except Exception:
    requests = None
    BeautifulSoup = None

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except Exception:
    pass

from scraper_lib.utils import jitter_sleep, iso_now, normalize_price, clean_text

def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def ensure_dirs(out_dir: Path):
    (out_dir / "history").mkdir(parents=True, exist_ok=True)

def get_session(headers: Dict[str,str] = None):
    if requests is None:
        raise RuntimeError("requests and bs4 are required for static scraping. Please install: pip install requests beautifulsoup4 pyyaml")
    s = requests.Session()
    s.headers.update({
        "User-Agent": (headers.get("User-Agent") if headers else None) or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
        "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    })
    return s

def scrape_static_category(session, site_conf: Dict[str,Any], category_key: str, cat_conf: Dict[str,Any]) -> List[Dict[str,Any]]:
    results = []
    base = site_conf["base_url"].rstrip("/")
    url = base + cat_conf["path"]
    sel = site_conf["selectors"]
    page = 1
    max_pages = cat_conf.get("max_pages", 5)
    while url and page <= max_pages:
        r = session.get(url, timeout=30)
        if r.status_code != 200:
            break
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select(sel["product_card"])
        for c in cards:
            name = clean_text(next((x.get_text() for x in c.select(sel.get("name",""))), None))
            price_text = clean_text(next((x.get_text() for x in c.select(sel.get("price",""))), None))
            price, currency = normalize_price(price_text)
            href = None
            a = c.select_one(sel.get("url","a"))
            if a and a.get("href"):
                href = a.get("href")
                if href.startswith("/"):
                    href = base + href
            brand = clean_text(next((x.get_text() for x in c.select(sel.get("brand",""))), None))
            pack = clean_text(next((x.get_text() for x in c.select(sel.get("pack",""))), None))
            image = None
            img = c.select_one(sel.get("image","img"))
            if img and (img.get("src") or img.get("data-src")):
                image = img.get("src") or img.get("data-src")
                if image.startswith("//"):
                    image = "https:" + image
            availability = None
            avail_sel = sel.get("availability")
            if avail_sel:
                avail_txt = clean_text(next((x.get_text() for x in c.select(avail_sel)), None))
                if avail_txt:
                    availability = "out_of_stock" if "rupture" in avail_txt.lower() or "indisponible" in avail_txt.lower() else "in_stock"

            item = {
                "id": None,
                "product_name": name,
                "category": category_key,
                "price": price,
                "currency": currency or site_conf.get("currency","EUR"),
                "product_url": href,
                "brand": brand,
                "pack_size": pack,
                "updated_at": iso_now(),
                "source": url,
                "image_url": image,
                "availability": availability,
                "supplier": site_conf["name"],
                "supplier_site": site_conf["base_url"],
            }
            item["id"] = f"{item['supplier']}::{item['category']}::{(item['product_name'] or '')[:64]}"
            results.append(item)

            var_sel = sel.get("variation_badges")
            if var_sel:
                for v in c.select(var_sel):
                    vname = clean_text(v.get_text())
                    if vname and vname.lower() not in (item["product_name"] or "").lower():
                        var_item = dict(item)
                        var_item["product_name"] = f"{item['product_name']} - {vname}"
                        var_item["id"] = f"{item['id']}::{vname}"
                        results.append(var_item)

        next_selector = site_conf.get("pagination", {}).get("next_selector")
        next_url = None
        if next_selector:
            nxt = soup.select_one(next_selector)
            if nxt and nxt.get("href"):
                nxt_href = nxt.get("href")
                next_url = nxt_href if nxt_href.startswith("http") else (base + nxt_href)
        url = next_url
        page += 1
        jitter_sleep(1.2, 0.6)
    return results

def scrape_dynamic_category(site_conf: Dict[str,Any], category_key: str, cat_conf: Dict[str,Any]) -> List[Dict[str,Any]]:
    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError("Playwright is not installed. Install and run: pip install playwright && playwright install")
    sel = site_conf["selectors"]
    base = site_conf["base_url"].rstrip("/")
    url = base + cat_conf["path"]
    results = []
    from bs4 import BeautifulSoup
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=site_conf.get("user_agent"))
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded")
        scrolls = site_conf.get("pagination", {}).get("scrolls", 8)
        for _ in range(scrolls):
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(site_conf.get("pagination", {}).get("wait", 1.5))
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        cards = soup.select(sel["product_card"])
        for c in cards:
            name = clean_text(next((x.get_text() for x in c.select(sel.get("name",""))), None))
            price_text = clean_text(next((x.get_text() for x in c.select(sel.get("price",""))), None))
            price, currency = normalize_price(price_text)
            href = None
            a = c.select_one(sel.get("url","a"))
            if a and a.get("href"):
                href = a.get("href")
                if href.startswith("/"):
                    href = base + href
            brand = clean_text(next((x.get_text() for x in c.select(sel.get("brand",""))), None))
            pack = clean_text(next((x.get_text() for x in c.select(sel.get("pack",""))), None))
            image = None
            img = c.select_one(sel.get("image","img"))
            if img and (img.get("src") or img.get("data-src")):
                image = img.get("src") or img.get("data-src")
                if image.startswith("//"):
                    image = "https:" + image
            availability = None
            avail_sel = sel.get("availability")
            if avail_sel:
                avail_txt = clean_text(next((x.get_text() for x in c.select(avail_sel)), None))
                if avail_txt:
                    availability = "out_of_stock" if "rupture" in avail_txt.lower() or "indisponible" in avail_txt.lower() else "in_stock"

            item = {
                "id": None,
                "product_name": name,
                "category": category_key,
                "price": price,
                "currency": currency or site_conf.get("currency","EUR"),
                "product_url": href,
                "brand": brand,
                "pack_size": pack,
                "updated_at": iso_now(),
                "source": url,
                "image_url": image,
                "availability": availability,
                "supplier": site_conf["name"],
                "supplier_site": site_conf["base_url"],
            }
            item["id"] = f"{item['supplier']}::{item['category']}::{(item['product_name'] or '')[:64]}"
            results.append(item)
        browser.close()
    return results

def write_outputs(items: List[Dict[str,Any]], out_dir: Path, basename: str = "materials"):
    (out_dir / "history").mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    current_json = out_dir / f"{basename}.json"
    versioned_json = out_dir / "history" / f"{basename}_{ts}.json"
    with open(current_json, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)
    with open(versioned_json, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

    csv_path = out_dir / f"{basename}.csv"
    if items:
        keys = ["id","product_name","category","price","currency","product_url","brand","pack_size","updated_at","source","image_url","availability","supplier","supplier_site"]
        import csv
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=keys)
            w.writeheader()
            for it in items:
                w.writerow({k: it.get(k) for k in keys})
    return {"json": str(current_json), "json_versioned": str(versioned_json), "csv": str(csv_path)}

def main():
    ap = argparse.ArgumentParser(description="Donizo Material Scraper")
    ap.add_argument("--config", default="config/scraper_config.yaml", help="Path to scraper_config.yaml")
    ap.add_argument("--site", default=None, help="Only scrape a specific site key from config")
    ap.add_argument("--dynamic", action="store_true", help="Use Playwright dynamic mode if configured")
    ap.add_argument("--out", default="data", help="Output directory")
    args = ap.parse_args()

    cfg = load_config(args.config)
    out_dir = Path(args.out)
    all_items: List[Dict[str,Any]] = []

    for site_key, site_conf in cfg["sites"].items():
        if args.site and args.site != site_key:
            continue
        mode = site_conf.get("mode", "static")
        for category_key, cat_conf in site_conf.get("categories", {}).items():
            try:
                print(f"[{site_key}] {category_key} -> {cat_conf['path']} (mode={mode})")
                if mode == "dynamic" or args.dynamic:
                    items = scrape_dynamic_category(site_conf, category_key, cat_conf)
                else:
                    session = get_session()
                    items = scrape_static_category(session, site_conf, category_key, cat_conf)
                all_items.extend(items)
            except Exception as e:
                print(f"Error scraping {site_key}/{category_key}: {e}")

    outputs = write_outputs(all_items, out_dir, basename="materials")
    print("Wrote:", outputs)

if __name__ == "__main__":
    main()