import asyncio
import json
from pathlib import Path
import os

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig

# --- Configuration ---
# Ensure your cookies file is in the same directory
COOKIES_FILE_PATH = "hiive_cookies.json"
COMPANY_TO_SEARCH = "Replit"

def normalize_cookies_for_playwright(cookies_data: list) -> list:
    """
    Converts cookies from a browser-exported JSON file into the format
    strictly required by Playwright's context.add_cookies() method,
    specifically fixing the `sameSite` attribute.
    """
    normalized_cookies = []
    same_site_mapping = {
        "no_restriction": "None",
        "unspecified": "None",
        "lax": "Lax",
        "strict": "Strict",
        "": "Lax"
    }
    for cookie in cookies_data:
        original_same_site = str(cookie.get("sameSite", "")).lower()
        new_cookie = {
            "name": cookie["name"],
            "value": cookie["value"],
            "domain": cookie["domain"],
            "path": cookie["path"],
            "expires": cookie.get("expirationDate", -1),
            "httpOnly": cookie.get("httpOnly", False),
            "secure": cookie.get("secure", False),
            "sameSite": same_site_mapping.get(original_same_site, "Lax")
        }
        normalized_cookies.append(new_cookie)
    return normalized_cookies

def prepare_storage_state_from_cookies(cookie_file_path: str) -> None:
    """
    Checks the cookie file, normalizes the cookies for Playwright compatibility,
    and saves it back in the `storage_state` format.
    """
    if not os.path.exists(cookie_file_path):
        print(f"❌ Error: Cookie file not found at '{cookie_file_path}'.")
        print("Please log into Hiive, export your cookies as JSON, and save the file here.")
        raise FileNotFoundError(f"Cookie file not found: {cookie_file_path}")

    with open(cookie_file_path, 'r') as f:
        try:
            data = json.load(f)
            if isinstance(data, list):
                cookie_list = data
            elif isinstance(data, dict) and "cookies" in data:
                cookie_list = data["cookies"]
            else:
                raise json.JSONDecodeError("Unrecognized cookie format.", "", 0)

            normalized_cookies = normalize_cookies_for_playwright(cookie_list)
            storage_state = {"cookies": normalized_cookies, "origins": []}
            with open(cookie_file_path, 'w') as sf:
                json.dump(storage_state, sf, indent=2)
            print(f"🍪 Cookie file '{cookie_file_path}' has been normalized for Playwright.")

        except json.JSONDecodeError:
            print(f"❌ Error: The cookie file at '{cookie_file_path}' is not a valid JSON file or has an unknown format.")
            raise

async def scrape_hiive_with_crawl4ai():
    """
    Uses crawl4ai to log in, search for a company, and scrape its data.
    """
    try:
        prepare_storage_state_from_cookies(COOKIES_FILE_PATH)
    except (FileNotFoundError, json.JSONDecodeError):
        return

    # 1. Configure Browser
    browser_config = BrowserConfig(
        headless=False,
        storage_state=COOKIES_FILE_PATH,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    # 2. Define the interaction and scraping logic.
    # This script places the result in `localStorage`
    javascript_step_1_workflow = f"""
    async () => {{
        // Helper functions
        async function waitForElement(selector, timeout = 30000) {{
            const startTime = Date.now();
            while (Date.now() - startTime < timeout) {{
                if (document.querySelector(selector)) {{ return document.querySelector(selector); }}
                await new Promise(resolve => setTimeout(resolve, 500));
            }}
            throw new Error(`Timeout waiting for element: ${{selector}}`);
        }}
        const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

        try {{
            // Step 1: Search for the company
            const searchInput = await waitForElement('input[placeholder="Search company"]');
            searchInput.click();
            await sleep(500);

            for (const char of "{COMPANY_TO_SEARCH}") {{
                searchInput.value += char;
                searchInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                await sleep(100 + Math.random() * 150);
            }}
            await sleep(3000);
            searchInput.dispatchEvent(new KeyboardEvent('keydown', {{ 'key': 'Enter', bubbles: true }}));

            // Step 2: Wait for the company page to load
            await waitForElement('h2:has-text("{COMPANY_TO_SEARCH}")');
            await sleep(3000);

            // Step 3: Scrape the data
            const labels = document.querySelectorAll("p.chakra-text.css-dhvn65");
            const values = document.querySelectorAll("span.chakra-text.css-esew9");

            if (labels.length === 0 || values.length === 0) {{
                localStorage.setItem('scrapedHiiveData', JSON.stringify({{ error: "Could not find data labels or values." }}));
                return "Scraping failed: data elements not found.";
            }}
            
            const scrapedData = {{}};
            for (let i = 0; i < labels.length; i++) {{
                const key = labels[i]?.innerText.trim();
                const val = values[i]?.innerText.trim();
                if (key) {{ scrapedData[key] = val; }}
            }}
            
            // Store the result as a JSON string in localStorage
            localStorage.setItem('scrapedHiiveData', JSON.stringify(scrapedData));
            return "Workflow completed successfully.";
        }} catch (e) {{
            console.error("Error during JS workflow:", e);
            localStorage.setItem('scrapedHiiveData', JSON.stringify({{ error: e.toString() }}));
            return "Workflow failed with an error.";
        }}
    }}
    """

    # 2.1. Define the second script to retrieve the data from localStorage.
    javascript_step_2_retrieve_data = "return JSON.parse(localStorage.getItem('scrapedHiiveData'));"

    # 3. Configure the Crawler Run with the list of two scripts.
    crawler_config = CrawlerRunConfig(
        js_code=[
            javascript_step_1_workflow,
            javascript_step_2_retrieve_data
        ],
        page_timeout=90000,
    )

    # 4. Execute the Crawl
    async with AsyncWebCrawler(config=browser_config) as crawler:
        print("🚀 Starting Crawl4ai workflow on Hiive...")
        result = await crawler.arun(
            url="https://app.hiive.com/dashboard",
            config=crawler_config
        )

        if result.success and result.js_execution_result:
            workflow_status = result.js_execution_result.get("script_0")
            scraped_data = result.js_execution_result.get("script_1") # Data comes from the second script

            print(f"\nJavaScript workflow status: {workflow_status}")

            if scraped_data and not scraped_data.get("error"):
                print("\n✅ Scraping successful!")
                print(json.dumps(scraped_data, indent=2))
            elif scraped_data and scraped_data.get("error"):
                print(f"❌ Scraping logic failed inside the browser: {scraped_data['error']}")
            else:
                print("❌ JavaScript did not return the scraped data correctly.")
                print(f"   Raw result from second script: {scraped_data}")

        elif result.success:
            print("❌ Crawl was successful, but the JavaScript execution did not return any results.")
        else:
            print(f"❌ Crawl failed: {result.error_message}")
            
if __name__ == "__main__":
    asyncio.run(scrape_hiive_with_crawl4ai())