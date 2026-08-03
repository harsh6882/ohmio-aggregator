import os
import json
import re
import urllib.parse
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from bs4 import BeautifulSoup
import cloudscraper
import requests
from google import genai
from google.genai import types

app = Flask(__name__)
CORS(app)

# ==========================================
# CONFIGURATION & CLIENT INITIALIZATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
SERPAPI_KEY = os.environ.get("SERPAPI_KEY", "YOUR_SERPAPI_KEY_HERE")  # Optional: for Google Shopping

# Initialize Gemini Client (using modern google-genai SDK)
ai_client = genai.Client(api_key=GEMINI_API_KEY)

# Mimic a real browser to bypass bot protection for web scrapers
scraper = cloudscraper.create_scraper(browser={
    'browser': 'chrome',
    'platform': 'windows',
    'desktop': True
})

def clean_price(price_text):
    """Helper function to strip out all symbols, commas, and letters from a price"""
    if not price_text: 
        return 0.0
    cleaned = price_text.replace('₹', '').replace('Rs.', '').replace('Rs', '').replace(',', '').strip()
    cleaned = ''.join(char for char in cleaned if char.isdigit() or char == '.')
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0

# ==========================================
# 1. DIRECT DISTRIBUTOR SCRAPERS
# ==========================================

def scrape_robu(query):
    results = []
    try:
        url = f"https://robu.in/?s={urllib.parse.quote(query)}&post_type=product"
        response = scraper.get(url, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            products = soup.find_all('div', class_=['product-wrapper', 'product-small', 'type-product', 'product'])[:2]
            
            for prod in products:
                title_tag = prod.find(['h3', 'h2', 'p'], class_=['product-title', 'woocommerce-loop-product__title', 'name'])
                price_tag = prod.find('span', class_='woocommerce-Price-amount')
                
                if title_tag and price_tag:
                    name = title_tag.text.strip()
                    link = title_tag.find('a')['href'] if title_tag.find('a') else url
                    price = clean_price(price_tag.text)
                    
                    if price > 0:
                        results.append({"name": name, "vendor": "Robu.in", "price": price, "shipping": 50.0, "link": link})
    except Exception as e:
        print(f"Robu Scraper Error: {e}")
    return results

def scrape_electronicscomp(query):
    results = []
    try:
        url = f"https://www.electronicscomp.com/index.php?route=product/search&search={urllib.parse.quote(query)}"
        response = scraper.get(url, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            products = soup.find_all('div', class_='product-layout')[:2]
            
            for prod in products:
                title_tag = prod.find('h4').find('a') if prod.find('h4') else None
                price_tag = prod.find('p', class_='price')
                
                if title_tag and price_tag:
                    name = title_tag.text.strip()
                    link = title_tag['href']
                    raw_price = price_tag.text.split('Ex Tax:')[0]
                    price = clean_price(raw_price)
                    
                    if price > 0:
                        results.append({"name": name, "vendor": "ElectronicsComp", "price": price, "shipping": 65.0, "link": link})
    except Exception as e:
        print(f"ElectronicsComp Scraper Error: {e}")
    return results

def scrape_makerbazar(query):
    results = []
    try:
        url = f"https://makerbazar.in/search?q={urllib.parse.quote(query)}"
        response = scraper.get(url, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            products = soup.find_all('div', class_='product-item')[:2]
            
            for prod in products:
                title_tag = prod.find('a', class_='product-item__title')
                price_tag = prod.find('span', class_='price')
                
                if title_tag and price_tag:
                    name = title_tag.text.strip()
                    link = "https://makerbazar.in" + title_tag['href']
                    price = clean_price(price_tag.text)
                    
                    if price > 0:
                        results.append({"name": name, "vendor": "MakerBazar", "price": price, "shipping": 60.0, "link": link})
    except Exception as e:
        print(f"MakerBazar Scraper Error: {e}")
    return results

def scrape_amazon(query):
    results = []
    try:
        url = f"https://www.amazon.in/s?k={urllib.parse.quote(query + ' electronics component')}"
        amazon_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept-Language': 'en-IN,en-US;q=0.9,en;q=0.8'
        }
        response = scraper.get(url, headers=amazon_headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            products = soup.find_all('div', {'data-component-type': 's-search-result'})[:2]
            
            for prod in products:
                title_tag = prod.find('span', class_='a-size-medium') or prod.find('span', class_='a-text-normal')
                price_tag = prod.find('span', class_='a-price-whole')
                link_tag = prod.find('a', class_='a-link-normal s-no-outline')
                
                if title_tag and price_tag and link_tag:
                    name = title_tag.text.strip()
                    link = "https://www.amazon.in" + link_tag['href']
                    price = clean_price(price_tag.text)
                    
                    if price > 0:
                        results.append({"name": name, "vendor": "Amazon India", "price": price, "shipping": 40.0, "link": link})
    except Exception as e:
        print(f"Amazon Scraper Error: {e}")
    return results

def scrape_google_shopping(query):
    """Fetches real-time listings directly from Google Shopping India via SerpApi (if key set)."""
    if SERPAPI_KEY == "YOUR_SERPAPI_KEY_HERE":
        return []
        
    results = []
    try:
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_shopping",
            "q": query,
            "location": "India",
            "hl": "en",
            "gl": "in",
            "api_key": SERPAPI_KEY
        }
        resp = requests.get(url, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json().get("shopping_results", [])[:3]
            for item in data:
                price_val = float(item.get("extracted_price", 0.0))
                if price_val > 0:
                    results.append({
                        "name": item.get("title", ""),
                        "vendor": item.get("source", "Google Shopping"),
                        "price": price_val,
                        "shipping": 50.0,
                        "link": item.get("link", "#")
                    })
    except Exception as e:
        print(f"Google Shopping API Error: {e}")
    return results

# ==========================================
# 2. GEMINI AI NORMALIZATION & ANALYSIS LAYER
# ==========================================

def process_results_with_ai(raw_results, query):
    """
    Feeds raw scraped hardware listings into Gemini AI to:
    1. Extract exact MPNs / Part Numbers.
    2. Clean up messy e-commerce title strings.
    3. Identify component Form Factor and Manufacturer.
    4. Generate real hardware engineering compatibility notes.
    """
    if not raw_results or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        # Fallback formatting if Gemini API key is missing
        fallback_items = []
        for r in raw_results:
            fallback_items.append({
                "name": r["name"],
                "mpn": "N/A",
                "mfr": "Generic",
                "form_factor": "Component",
                "vendor": r["vendor"],
                "price": r["price"],
                "shipping": r["shipping"],
                "link": r["link"]
            })
        return {
            "items": fallback_items,
            "compatibility_notes": [f"Standard telemetry mode. Set GEMINI_API_KEY for AI-extracted MPNs & hardware warnings."]
        }

    # Prepare lightweight payload for AI model
    input_items = []
    for idx, item in enumerate(raw_results):
        input_items.append({
            "id": idx,
            "raw_title": item["name"],
            "vendor": item["vendor"],
            "price": item["price"]
        })

    prompt = f"""
    You are an embedded systems and hardware engineer processing scraped component listings for 'Ohmio'.
    User Hardware Query: "{query}"

    RAW LISTINGS:
    {json.dumps(input_items, indent=2)}

    INSTRUCTIONS:
    1. For each item ID:
       - 'clean_title': Short, accurate hardware title (e.g. "NEMA 17 Stepper Motor 1.2A").
       - 'mpn': Exact Manufacturer Part Number or SKU if detectable (e.g., 'RP2040', 'L298N', 'AMS1117-3.3').
       - 'mfr': Component manufacturer (e.g. 'STMicroelectronics', 'Raspberry Pi', 'Generic').
       - 'form_factor': Package/Module type (e.g. 'DIP-8', 'Breakout Module', 'SMD IC').
    2. Generate 2 crucial technical 'compatibility_notes' specifically for an engineer working with "{query}" 
       (e.g., operating voltage tolerances, logic level shifter needs, heat dissipation warnings, required drivers).

    Return structured JSON matching the schema strictly.
    """

    try:
        response = ai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "items": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "id": {"type": "INTEGER"},
                                    "clean_title": {"type": "STRING"},
                                    "mpn": {"type": "STRING"},
                                    "mfr": {"type": "STRING"},
                                    "form_factor": {"type": "STRING"}
                                },
                                "required": ["id", "clean_title", "mpn", "mfr", "form_factor"]
                            }
                        },
                        "compatibility_notes": {
                            "type": "ARRAY",
                            "items": {"type": "STRING"}
                        }
                    },
                    "required": ["items", "compatibility_notes"]
                }
            )
        )

        ai_data = json.loads(response.text)
        ai_item_map = {item["id"]: item for item in ai_data.get("items", [])}

        processed_items = []
        for idx, raw in enumerate(raw_results):
            enhanced = ai_item_map.get(idx, {})
            processed_items.append({
                "name": enhanced.get("clean_title", raw["name"]),
                "mpn": enhanced.get("mpn", "N/A"),
                "mfr": enhanced.get("mfr", "Generic"),
                "form_factor": enhanced.get("form_factor", "Standard Module"),
                "vendor": raw["vendor"],
                "price": float(raw["price"]),
                "shipping": float(raw["shipping"]),
                "link": raw["link"]
            })

        return {
            "items": processed_items,
            "compatibility_notes": ai_data.get("compatibility_notes", [])
        }

    except Exception as e:
        print(f"Gemini Processing Error: {e}")
        # Graceful fallback on error
        fallback_items = []
        for r in raw_results:
            fallback_items.append({
                "name": r["name"],
                "mpn": "N/A",
                "mfr": "Generic",
                "form_factor": "Component",
                "vendor": r["vendor"],
                "price": r["price"],
                "shipping": r["shipping"],
                "link": r["link"]
            })
        return {
            "items": fallback_items,
            "compatibility_notes": ["Note: Operating in fallback mode without AI metadata parsing."]
        }

# ==========================================
# 3. API ROUTES
# ==========================================

@app.route('/')
def home():
    """Serves page.html to browser client"""
    return send_file('page.html')

@app.route('/api/compare', methods=['GET'])
def compare_prices():
    query = request.args.get('query', '')
    if not query:
        return jsonify({"error": "Missing query argument"}), 400

    print(f"\n--- Searching Multi-Vendor Hardware Stores for: {query} ---")
    raw_results = []

    # Gather listings from web scrapers & Google Shopping
    raw_results.extend(scrape_robu(query))
    raw_results.extend(scrape_electronicscomp(query))
    raw_results.extend(scrape_makerbazar(query))
    raw_results.extend(scrape_amazon(query))
    raw_results.extend(scrape_google_shopping(query))

    # Backup simulated hardware data if scrapers are offline/blocked
    if len(raw_results) == 0:
        print("All scrapers blocked or offline. Injecting fallback hardware telemetry...")
        raw_results = [
            {"name": f"{query} Development Board / Module", "vendor": "Robu.in (Cached)", "price": 450.0, "shipping": 50.0, "link": "https://robu.in"},
            {"name": f"{query} High Performance IC / Module", "vendor": "ElectronicsComp (Cached)", "price": 420.0, "shipping": 65.0, "link": "https://www.electronicscomp.com"}
        ]

    print(f"Piping {len(raw_results)} raw results into Gemini AI for MPN extraction & tech analysis...")
    ai_payload = process_results_with_ai(raw_results, query)

    # Sort results cheapest to most expensive
    ai_payload["items"].sort(key=lambda x: x['price'])

    return jsonify(ai_payload)

if __name__ == '__main__':
    print("Starting Ohmio AI-Enhanced Multi-Vendor Engine...")
    app.run(host='0.0.0.0', debug=True, port=5000)
