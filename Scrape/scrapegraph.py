import json
import time
from playwright.sync_api import sync_playwright
from scrapegraphai.graphs import SmartScraperGraph

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

def get_authenticated_page_content():
    """
    Uses Playwright to log in with cookies and return the page HTML.
    """
    try:
        with open(COOKIES_FILE_PATH, 'r') as f:
            cookies = json.load(f)
        normalized_cookies = normalize_cookies(cookies)
    except FileNotFoundError:
        print(f"Error: The cookie file was not found at '{COOKIES_FILE_PATH}'")
        return None
    except Exception as e:
        print(f"Error reading or parsing the cookie file: {e}")
        return None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        context.add_cookies(normalized_cookies)
        page = context.new_page()

        try:
            page.goto(COMPANY_URL, wait_until="domcontentloaded", timeout=60000)
            # You might need to add waits here for dynamic content to load
            time.sleep(5) # Example wait
            return page.content()
        except Exception as e:
            print(f"An error occurred during Playwright navigation: {e}")
            return None
        finally:
            browser.close()

def main():
    # 1. Get the HTML content of the logged-in page
    page_html = get_authenticated_page_content()

    if page_html:
        # 2. Use ScrapeGraphAI to extract information from the HTML
        graph_config = {
            "llm": {
                "api_key": "sgai-b0466adc-00ec-41e1-b077-a1823b233775",
                "model": "openai/gpt-3.5-turbo",
            },
        }

        smart_scraper_graph = SmartScraperGraph(
            prompt="Extract the 'Forge Price Valuation' from the page.",
            source=page_html,  # Pass the HTML content here
            config=graph_config
        )

        result = smart_scraper_graph.run()
        print(result)

if __name__ == "__main__":
    main()