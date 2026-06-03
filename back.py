from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from bs4 import BeautifulSoup
import urllib.parse
import cloudscraper 

app = Flask(__name__)
CORS(app)

# Mimic a real browser to bypass bot protection
scraper = cloudscraper.create_scraper(browser={
    'browser': 'chrome',
    'platform': 'windows',
    'desktop': True
})

def clean_price(price_text):
    """Helper function to strip out all symbols, commas, and letters from a price"""
    if not price_text: return 0.0
    cleaned = price_text.replace('₹', '').replace('Rs.', '').replace('Rs', '').replace(',', '').strip()
    # Handle cases where tax or other text is bundled with the price
    cleaned = ''.join(char for char in cleaned if char.isdigit() or char == '.')
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0

def scrape_robu(query):
    results = []
    try:
        url = f"https://robu.in/?s={urllib.parse.quote(query)}&post_type=product"
        response = scraper.get(url, timeout=10)
        print(f"Robu Code: {response.status_code}") 
        
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
                        results.append({"name": name, "vendor": "Robu.in", "price": price, "shipping": 50, "link": link})
    except Exception as e:
        print(f"Robu Error: {e}")
    return results

def scrape_electronicscomp(query):
    results = []
    try:
        url = f"https://www.electronicscomp.com/index.php?route=product/search&search={urllib.parse.quote(query)}"
        response = scraper.get(url, timeout=10)
        print(f"ElectronicsComp Code: {response.status_code}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            products = soup.find_all('div', class_='product-layout')[:2]
            
            for prod in products:
                title_tag = prod.find('h4').find('a')
                price_tag = prod.find('p', class_='price')
                
                if title_tag and price_tag:
                    name = title_tag.text.strip()
                    link = title_tag['href']
                    raw_price = price_tag.text.split('Ex Tax:')[0]
                    price = clean_price(raw_price)
                    
                    if price > 0:
                        results.append({"name": name, "vendor": "ElectronicsComp", "price": price, "shipping": 65, "link": link})
    except Exception as e:
        print(f"ElectronicsComp Error: {e}")
    return results

def scrape_makerbazar(query):
    results = []
    try:
        url = f"https://makerbazar.in/search?q={urllib.parse.quote(query)}"
        response = scraper.get(url, timeout=10)
        print(f"MakerBazar Code: {response.status_code}")
        
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
                        results.append({"name": name, "vendor": "MakerBazar", "price": price, "shipping": 60, "link": link})
    except Exception as e:
        print(f"MakerBazar Error: {e}")
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
        print(f"Amazon Code: {response.status_code} (Expect 503 if blocked)")
        
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
                        results.append({"name": name[:60] + "...", "vendor": "Amazon India", "price": price, "shipping": 40, "link": link})
    except Exception as e:
        print(f"Amazon Error: {e}")
    return results

def scrape_flipkart(query):
    results = []
    try:
        url = f"https://www.flipkart.com/search?q={urllib.parse.quote(query)}"
        response = scraper.get(url, timeout=10)
        print(f"Flipkart Code: {response.status_code} (Expect 500/403 if blocked)")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            products = soup.find_all('div', class_=['_4ddWXP', '_1xFAF9', 'slAVV4'])[:2]
            
            for prod in products:
                title_tag = prod.find('a', class_=['s1Q9rs', 'IRpwTa'])
                price_tag = prod.find('div', class_='_30jeq3')
                
                if title_tag and price_tag:
                    name = title_tag.text.strip()
                    link = "https://www.flipkart.com" + title_tag['href']
                    price = clean_price(price_tag.text)
                    
                    if price > 0:
                        results.append({"name": name[:60] + "...", "vendor": "Flipkart", "price": price, "shipping": 50, "link": link})
    except Exception as e:
        print(f"Flipkart Error: {e}")
    return results


# ==========================================
# THIS IS THE ROUTE THAT SERVES YOUR HTML
# ==========================================
@app.route('/')
def home():
    """This serves page.html to anyone who visits the IP"""
    return send_file('page.html')


@app.route('/api/compare', methods=['GET'])
def compare_prices():
    query = request.args.get('query', '')
    
    if not query:
        return jsonify({"error": "Missing query argument"}), 400

    print(f"\n--- Searching the Web for: {query} ---")
    live_results = []
    
    # Run all scrapers
    live_results.extend(scrape_robu(query))
    live_results.extend(scrape_electronicscomp(query))
    live_results.extend(scrape_makerbazar(query))
    live_results.extend(scrape_amazon(query))
    live_results.extend(scrape_flipkart(query))
    
    # Sort from cheapest to most expensive
    live_results.sort(key=lambda x: x['price'])

    # Fallback if the internet breaks
    if len(live_results) == 0:
        print("All scrapers blocked or failed. Injecting fallback data...")
        live_results = [
            { "name": f"{query} Module", "vendor": "Amazon (Simulated)", "price": 450, "shipping": 50, "link": "#" },
            { "name": f"{query} Authentic", "vendor": "Robu (Simulated)", "price": 460, "shipping": 40, "link": "#" }
        ]

    return jsonify(live_results)

if __name__ == '__main__':
    print("Starting Ohmio Multi-Vendor Engine...")
    # host='0.0.0.0' opens the server to your Wi-Fi network
    app.run(host='0.0.0.0', debug=True, port=5000)