import json
import time
from playwright.sync_api import sync_playwright, expect

# --- Configuration ---
COOKIES_FILE_PATH = "cookies.json"
COMPANY_URL = "https://marketplace.forgeglobal.com/marketplace/companies/replit"

def normalize_cookies(cookies_data):
    """
    Converts a list of cookies from a browser-exported JSON file
    into the format required by Playwright's context.add_cookies() method.
    """
    normalized_cookies = []
    for cookie in cookies_data:
        same_site_mapping = {
            "no_restriction": "None",
            "unspecified": "None",
            "lax": "Lax",
            "strict": "Strict"
        }
        new_cookie = {
            "name": cookie["name"],
            "value": cookie["value"],
            "domain": cookie["domain"],
            "path": cookie["path"],
            "expires": cookie.get("expirationDate", -1),
            "httpOnly": cookie.get("httpOnly", False),
            "secure": cookie.get("secure", False),
            "sameSite": same_site_mapping.get(cookie.get("sameSite", "").lower(), "Lax")
        }
        normalized_cookies.append(new_cookie)
    return normalized_cookies

def main():
    try:
        with open(COOKIES_FILE_PATH, 'r') as f:
            cookies = json.load(f)
        normalized_cookies = normalize_cookies(cookies)
        print(f"✅ Successfully loaded and normalized {len(normalized_cookies)} cookies.")
    except FileNotFoundError:
        print(f"❌ Error: The cookie file was not found at '{COOKIES_FILE_PATH}'")
        return
    except Exception as e:
        print(f"❌ Error reading or parsing the cookie file: {e}")
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=50)
        context = browser.new_context()
        print("Adding cookies to the browser context...")
        context.add_cookies(normalized_cookies)
        page = context.new_page()

        try:
            # --- MODIFIED LOGIC ---
            # 1. Navigate directly to the target page
            print(f"Navigating directly to company page: {COMPANY_URL}...")
            page.goto(COMPANY_URL, wait_until="domcontentloaded", timeout=60000)

            print("Scraping Forge Price Valuation...")

            # 2. THE NEW, ACCURATE SELECTOR
            # First, locate the parent chart container using its stable 'data-testid'.
            # Then, find the <p> element inside it that contains a "$" sign.
            # This is highly specific and robust.
            price_element = page.locator('div[data-testid="forge-price-line-chart"] p:has-text("$")')

            # 3. Wait for the element to be visible. Data might load asynchronously.
            expect(price_element).to_be_visible(timeout=30000)

            # 4. Extract the text content
            price_text = price_element.inner_text()
            print(f"Found raw price text: '{price_text}'")

            # Clean the text to get just the value
            found_price = price_text.replace('$', '').strip()
            
            if found_price:
                 print(f"✅ Scraped Price: ${found_price}")
            else:
                 print("❌ Could not parse the price from the element.")

        except Exception as e:
            print(f"❌ An error occurred during scraping: {e}")
            page.screenshot(path="debug_scraping_failed.png")
            print("   - Saved a screenshot to 'debug_scraping_failed.png' for analysis.")
        finally:
            print("Closing browser in 10 seconds...")
            time.sleep(10)
            browser.close()

if __name__ == "__main__":
    main()