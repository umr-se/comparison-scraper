import random
from bs4 import BeautifulSoup
from flask import Flask, json, jsonify, send_file
from flask_limiter import HEADERS
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from sqlalchemy import values
from webdriver_manager.chrome import ChromeDriverManager
from google.oauth2 import service_account
from googleapiclient.discovery import build
from chrome_setup import create_chrome_driver, options_driver
import time
from fuzzywuzzy import fuzz
import re
from collections import defaultdict

app = Flask(__name__)

# Google Sheets Configuration
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = 'credentials.json'
SPREADSHEET_ID = 'your_sheets_id'

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1'
]

HEADERS = {
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Referer': 'https://www.google.com/',
    'DNT': '1'
}

SIMILARITY_THRESHOLD = 100


def write_to_sheets(data):
    """Write data to Google Sheets with comparisons and URLs"""
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)

        # Clear existing data
        service.spreadsheets().values().clear(
            spreadsheetId=SPREADSHEET_ID,
            range='A:Z',
            body={}
        ).execute()

        values = [
            ["Platform", "Product Name", "Price", "Product URL"],
        ]

        # eBay products
        for product in data['ebay_products']:
            try:
                values.append([
                    "eBay",
                    product['title'].strip(),
                    product['price'].strip(),
                    product['url'].strip()
                ])
            except Exception as e:
                print(f"Skipping eBay entry: {product}")
                continue

        # Amazon products
        for product in data['amazon_products']:
            try:
                values.append([
                    "Amazon",
                    product['title'].strip(),
                    product['price'].strip(),
                    product['link'].strip()  # Updated to link
                ])
            except Exception as e:
                print(f"Skipping Amazon entry: {product}")
                continue

        # Add comparison section
        values += [
            [],
            ["Price Comparisons"],
            ["eBay Product", "Amazon Product", "Similarity Score",
             "eBay Price", "Amazon Price", "Cheaper Platform", "Price Difference"]
        ]

        for comp in data['comparisons']:
            values.append([
                comp['ebay_title'],
                comp['amazon_title'],
                f"{comp['similarity']}%",
                comp['ebay_price'],
                comp['amazon_price'],
                comp['cheaper'],
                f"${comp['price_diff']:.2f}"
            ])

        body = {'values': values, 'majorDimension': "ROWS"}
        result = service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range='A1',
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()

        print(f"Updated {result.get('updatedCells')} cells")
        return True

    except Exception as e:
        print(f"Google Sheets error: {str(e)}")
        return False

def parse_price(price_str):
    """Extract numerical value from price string"""
    try:
        return float(re.sub(r'[^\d.]', '', price_str))
    except:
        return 0.0

def get_page(url, retries=3):
    session = requests.Session()
    for _ in range(retries):
        try:
            headers = {**HEADERS, 'User-Agent': random.choice(USER_AGENTS)}
            time.sleep(random.uniform(1, 3))
            response = session.get(url, headers=headers, timeout=10)
            if "api-services-support@amazon.com" in response.text:
                print("CAPTCHA encountered. Try again later.")
                return None
            if response.status_code == 200:
                return response.text
            elif response.status_code == 403:
                print("Access denied. Consider using proxies.")
                return None
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)
    return None

def search_ebay_products():
    driver = create_chrome_driver()
    product_lines = []
    seen = set()

    try:
        search_terms = ["playstation 5", "playstation 4"]

        for term in search_terms:
            driver.get("https://www.ebay.com")
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "gh-logo"))
            )

            search_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "gh-ac"))
            )
            search_input.clear()
            search_input.send_keys(term)
            search_input.send_keys(Keys.RETURN)

            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".srp-river-results"))
            )

            products = []
            last_position = 0
            scroll_attempt = 0
            collected = 0

            while len(products) < 22 and scroll_attempt < 3 and collected < 5:
                driver.execute_script(f"window.scrollTo(0, {last_position + 2000});")
                time.sleep(2)
                new_products = driver.find_elements(By.CSS_SELECTOR, "li.s-item")

                if len(new_products) > len(products):
                    products = new_products
                    last_position += 2000
                    scroll_attempt = 0
                else:
                    scroll_attempt += 1

                # Process products
                for item in products:
                    if collected >= 5:
                        break
                    try:
                        name_elem = item.find_element(By.CSS_SELECTOR, "div.s-item__title > span[role='heading']")
                        price_elem = item.find_element(By.CSS_SELECTOR, "div.s-item__detail.s-item__detail--primary > span.s-item__price")
                        link_elem = item.find_element(By.CSS_SELECTOR, "a.s-item__link")
                        name = name_elem.text.strip()
                        url = link_elem.get_attribute("href")
                        price = price_elem.text.strip()

                        identifier = f"{name}-{price}"
                        if name and identifier not in seen:
                            seen.add(identifier)
                            collected += 1
                            product_lines.append({
                                "title": name,
                                "price": price,
                                "url": url,
                            })
                    except:
                        continue

        return product_lines

    finally:
        driver.quit()

def search_amazon_products():
    driver = None
    try:
        driver = options_driver()
        driver.get("https://www.amazon.com")
        time.sleep(5)
        print("Amazon page title:", driver.title)

        start_time = time.time()
        while time.time() - start_time < 25:
            if "captcha" not in driver.page_source.lower():
                break
            time.sleep(20)
        else:
            print("CAPTCHA might still be present")

        def search_and_scrape(keyword):
            print(f"\nSearching for '{keyword}'...")
            search_box = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "twotabsearchtextbox"))
            )
            search_box.clear()
            search_box.send_keys(keyword)
            search_box.send_keys(Keys.RETURN)
            time.sleep(5)

            products = driver.find_elements(By.XPATH, "//div[@data-component-type='s-search-result']")
            results = []
            count = 0

            for product in products:
                try:
                    # Find product title
                    h2 = product.find_element(By.XPATH, ".//h2[@aria-label]")
                    title = h2.find_element(By.XPATH, ".//span").text.strip()
                    if not title or "case" in title.lower():
                        continue

                    # Find product URL
                    try:
                        link = h2.find_element(By.XPATH, ".//a").get_attribute('href')
                    except:
                        try:
                            link = product.find_element(By.XPATH, ".//a[contains(@class, 's-image') or contains(@class, 'a-link-normal')]").get_attribute('href')
                        except:
                            link = "N/A"

                    # Find product price
                    try:
                        price_whole = product.find_element(By.XPATH, ".//span[@class='a-price-whole']").text.replace(',', '')
                        price_fraction = product.find_element(By.XPATH, ".//span[@class='a-price-fraction']").text
                        price = f"${price_whole}.{price_fraction}"
                    except:
                        try:
                            price = product.find_element(By.XPATH, ".//span[@class='a-price']").text.replace("\n", ".")
                        except:
                            price = "N/A"

                    if price != "N/A" and link != "N/A":
                        results.append({
                            "title": title,
                            "price": price,
                            "link": link
                        })
                        count += 1
                        print(f"{count}. {title} - {price} - {link}")

                    time.sleep(random.uniform(1.5, 3.5))

                    if count >= 5:
                        break
                except Exception as e:
                    print(f"Error processing product: {e}")
                    continue

            return results

        all_results = []
        search_terms = ["playstation 5", "playstation 4"]
        
        for term in search_terms:
            all_results.extend(search_and_scrape(term))

        print(f"Collected {len(all_results)} Amazon products")
        return all_results

    except Exception as e:
        print(f"Amazon scraping error: {str(e)}")
        return []
    finally:
        if 'driver' in locals():
            driver.quit()

def normalize_title(title):
    """Standardize product titles for comparison"""
    return re.sub(r'[^a-zA-Z0-9]', '', title.lower()).replace('playstation', 'ps')

def find_similar_products(ebay_products, amazon_products):
    """Find matching products between platforms"""
    comparisons = []

    for ebay_item in ebay_products:
        best_match = None
        highest_score = 0

        for amazon_item in amazon_products:
            # Basic model number matching
            ebay_model = re.findall(r'\b(PS\d+|PlayStation\s*\d+)\b', ebay_item['title'], re.I)
            amazon_model = re.findall(r'\b(PS\d+|PlayStation\s*\d+)\b', amazon_item['title'], re.I)

            # If models match, prioritize them
            if ebay_model and amazon_model and ebay_model[0].upper() == amazon_model[0].upper():
                score = 100
            else:
                # Calculate similarity score
                score = fuzz.token_sort_ratio(
                    normalize_title(ebay_item['title']),
                    normalize_title(amazon_item['title'])
                )

            if score > highest_score and score > 65:
                highest_score = score
                best_match = amazon_item

        if best_match:
            ebay_price = parse_price(ebay_item['price'])
            amazon_price = parse_price(best_match['price'])
            price_diff = abs(ebay_price - amazon_price)

            comparisons.append({
                'ebay_title': ebay_item['title'][:50],  # Truncate for display
                'amazon_title': best_match['title'][:50],
                'similarity': highest_score,
                'ebay_price': ebay_item['price'],
                'amazon_price': best_match['price'],
                'price_diff': price_diff,
                'cheaper': 'eBay' if ebay_price < amazon_price else 'Amazon'
            })

    # Sort by similarity then price difference
    return sorted(comparisons, key=lambda x: (-x['similarity'], x['price_diff']))[:20]  # Top 20 matches

def save_combined_results(ebay_data, amazon_data):
    try:
        comparisons = find_similar_products(ebay_data, amazon_data)

        combined_data = {
            "ebay_products": ebay_data,
            "amazon_products": amazon_data,
            "comparisons": comparisons
        }

        with open("combined_prices.json", "w", encoding="utf-8") as f:
            json.dump(combined_data, f, ensure_ascii=False, indent=2)

        return write_to_sheets(combined_data)
    except Exception as e:
        print(f"Save error: {str(e)}")
        return False

@app.route('/')
def home():
    ebay_data = search_ebay_products()
    amazon_data = search_amazon_products()

    if save_combined_results(ebay_data, amazon_data):
        total = len(ebay_data) + len(amazon_data)
        return jsonify({
            "status": "success",
            "message": f"Scraped and saved data for {total} products",
            "counts": {
                "ebay": len(ebay_data),
                "amazon": len(amazon_data)
            }
        })
    else:
        return jsonify({"status": "error", "message": "Failed to save data."}), 500

@app.route('/download_prices')
def download_prices():
    try:
        return send_file(
            "combined_prices.json",
            as_attachment=True,
            mimetype='application/json'
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)