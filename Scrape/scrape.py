import json
import time
from playwright.sync_api import sync_playwright, expect

# --- Configuration ---
COOKIES_FILE_PATH = "cookies.json"
WEBSITE_URL = "https://marketplace.forgeglobal.com/marketplace/dashboard"

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

        print(f"Navigating to protected page: {WEBSITE_URL}...")
        page.goto(WEBSITE_URL, wait_until="domcontentloaded", timeout=60000)

        print("Verifying login status...")
        try:
            # Using the div around the user icon for login verification
            account_button = page.locator('div[data-testid="user-menu"]')
            expect(account_button).to_be_visible(timeout=20000) # Increased timeout slightly for safety
            print("✅ Verification successful! Logged in.")
        except Exception:
            print("❌ Verification failed! Could not find the account button.")
            page.screenshot(path="debug_forge_login_failed.png")
            print("   - Saved a screenshot to 'debug_forge_login_failed.png'")
            browser.close()
            return

        try:
            print("Searching for 'Replit'...")
            search_input = page.get_by_placeholder("Search for companies")
            # Use .fill() which is often more reliable for setting input values.
            search_input.fill("Replit")

            print("Waiting for search results to appear...")
            # This is the most reliable locator. It finds a link (<a> tag) with the exact accessible name "Replit".
            search_results = page.get_by_role("link", name="Replit", exact=True)
            
            # --- THIS IS THE KEY ADDITION ---
            # Explicitly wait for the search result to be visible before trying to click it.
            # This handles any delay from the website's search API.
            expect(search_results).to_be_visible(timeout=5000)
            
            print("Clicking on the 'Replit' search result...")
            search_results.click()

            print("Scraping Forge Price Valuation...")
            price_chart_container = page.locator('div[data-testid="forge-price-line-chart"]')
            expect(price_chart_container).to_be_visible(timeout=30000)

            price_text_content = price_chart_container.inner_text()
            print(f"Found chart block text: \n---\n{price_text_content}\n---")

            found_price = None
            lines = price_text_content.split('\n')
            for i, line in enumerate(lines):
                if "Forge Price" in line and i + 1 < len(lines):
                    price_str = lines[i+1]
                    found_price = price_str.replace('$', '').strip()
                    break
            
            if found_price:
                 print(f"✅ Scraped Price: ${found_price}")
            else:
                 print("❌ Could not parse the price from the chart text.")

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