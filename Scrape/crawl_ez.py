import asyncio
import json
import random
import sys
import os
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# --- crawl4ai Imports ---
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    LLMExtractionStrategy,
    JsonCssExtractionStrategy,
    LLMConfig,
)

# --- Add parent directory to path to import user's existing modules ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.services.google_sheets import GoogleSheetsClient
from app.services.database import DatabaseClient

# --- Configuration & Setup ---
# 1. Cookies File: Ensure 'equityzen_cookies.json' is in the same directory.
COOKIES_FILE_PATH = "Scrape/equityzen_cookies.json"

# 2. Environment Variables: Create a '.env' file for your Gemini API key.
#    Example .env content:
#    GEMINI_API_KEY="your_google_ai_api_key_here"
from dotenv import load_dotenv
load_dotenv()


### NEW: Re-introduced your robust cookie normalization function ###
def normalize_cookies(cookies_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Converts browser-exported cookies to the format Playwright/crawl4ai requires."""
    normalized_cookies = []
    for cookie in cookies_data:
        # This mapping handles the different 'sameSite' values from browser extensions
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
            "sameSite": same_site_mapping.get(str(cookie.get("sameSite", "Lax")).lower(), "Lax")
        }
        normalized_cookies.append(new_cookie)
    return normalized_cookies


# --- Pydantic Schemas for LLM Extraction ---
class FundingRound(BaseModel):
    """Defines the structure for a single funding round."""
    date: str = Field(..., description="The date of the funding round (e.g., 'Jan 2024').")
    price_per_share: str = Field(..., description="The price per share for the round (e.g., '$12.34').")

class FundingHistory(BaseModel):
    """Defines the structure for the entire funding history table."""
    funding_rounds: List[FundingRound] = Field(..., description="A list of all funding rounds found in the table.")


# --- The Main Scraping Logic using crawl4ai (No changes in this function) ---
# --- The Main Scraping Logic using crawl4ai ---
async def scrape_company_with_crawl4ai(crawler: AsyncWebCrawler, company_name: str) -> Optional[Dict[str, Any]]:
    """
    Orchestrates a multi-step crawl for a single company using crawl4ai's session management
    and hybrid extraction strategies.
    """
    session_id = f"equityzen_session_{random.randint(1000, 9999)}"
    print(f"🚀 Starting crawl for '{company_name}' with session ID: {session_id}")
    scraped_data = {}

    try:
        # ### CHANGED: Merged Step 1 and 2 into a single, more direct action ###
        # --- STEP 1: Navigate to /welcome, search, and scrape "About" Tab ---
        print("   - Step 1: Navigating to welcome page, searching, and extracting 'About' tab...")

        about_tab_schema = {
            "name": "EquityZenAboutTab", "baseSelector": "body",
            "fields": [
                {"name": "Overview", "selector": 'div[class*="SvaSingleCompanyAboutCompanyTab--section"] div[class*="--description"]', "type": "text", "default": "Not found"},
                {"name": "Investors", "selector": 'div[class*="Company-Investors"] a h5', "type": "list", "default": []},
                {"name": "MarketActivity", "selector": 'div[class*="MarketActivityCard--item"]', "type": "list", "fields": [
                    {"name": "label", "selector": 'div[class*="--item-label"]', "type": "text"},
                    {"name": "value", "selector": 'div[class*="--item-value"]', "type": "text"}
                ], "default": []}
            ]
        }
        css_extractor = JsonCssExtractionStrategy(schema=about_tab_schema)

        # This single config now handles the entire flow to the company profile page
        navigate_and_extract_config = CrawlerRunConfig(
            session_id=session_id,
            # The JS code now starts directly with the search, as we are already on the correct page
            js_code=[
                f"document.querySelector('input#NavigationBarGlobSearch').value = '';",
                f"document.querySelector('input#NavigationBarGlobSearch').dispatchEvent(new Event('input', {{ bubbles: true }}));",
                f"document.querySelector('input#NavigationBarGlobSearch').focus();",
                f"document.querySelector('input#NavigationBarGlobSearch').type('{company_name}');",
                "await new Promise(r => setTimeout(r, 1000));", # Wait for dropdown results
                "document.querySelector('div[class*=\"SearchDropdown-item\"]').click();"
            ],
            # This wait_for confirms that the click was successful and we landed on the company page
            wait_for="css:div[class*='SvaSingleCompanyAboutCompanyTab--section']",
            wait_for_timeout=30000,
            extraction_strategy=css_extractor,
            simulate_user=True,
        )

        result_about = await crawler.arun(
            url="https://equityzen.com/welcome", # Start directly at the welcome page
            config=navigate_and_extract_config
        )

        if not result_about.success or not result_about.extracted_content:
            print(f"   - ❌ Step 1 failed for '{company_name}'. Could not find company or extract 'About' data. Error: {result_about.error_message}")
            return None

        # Process the extracted 'About' data
        about_data_list = json.loads(result_about.extracted_content)
        if about_data_list:
            about_data = about_data_list[0]
            scraped_data['Overview'] = about_data.get('Overview', '').strip()
            scraped_data['Investors'] = ", ".join(about_data.get('Investors', []))
            for item in about_data.get('MarketActivity', []):
                if item.get('label') and item.get('value') and item['value'] != '--':
                    scraped_data[item['label'].strip()] = item['value'].strip()
            print("   - ✅ 'About' tab data successfully extracted.")
        else:
            print("   - ⚠️ 'About' tab extraction yielded no data.")


        # --- STEP 2 (formerly Step 3): Navigate to "Cap Table" and Scrape Funding History ---
        print("   - Step 2: Navigating to 'Cap Table' and extracting funding history with Gemini...")
        llm_config = LLMConfig(provider="gemini/gemini-1.5-flash-latest", api_token=os.getenv("GEMINI_API_KEY"))
        llm_extractor = LLMExtractionStrategy(
            llm_config=llm_config, schema=FundingHistory.model_json_schema(),
            instruction="From the provided HTML snippet of a funding history table, extract all rows containing the date and price per share. Ignore header rows.",
            extraction_type="schema", input_format="html",
        )
        extract_funding_config = CrawlerRunConfig(
            session_id=session_id, # Use the SAME session
            js_only=True,          # Just clicking a tab
            js_code="document.querySelector('div[role=\"tab\"]:has-text(\"Cap Table\")').click();",
            wait_for="css:div.CompanyCapTable, div.CompanyCapTable-funding-history-container", wait_for_timeout=20000,
            extraction_strategy=llm_extractor, css_selector="div.CompanyCapTable, div.CompanyCapTable-funding-history-container",
        )
        result_funding = await crawler.arun(url=result_about.url, config=extract_funding_config)

        if result_funding.success and result_funding.extracted_content:
            funding_data = json.loads(result_funding.extracted_content)
            if "funding_rounds" in funding_data and funding_data["funding_rounds"]:
                scraped_data['Funding History'] = json.dumps(funding_data["funding_rounds"])
                print(f"   - ✅ Funding history extracted for {len(funding_data['funding_rounds'])} rounds.")
            else:
                 print("   - ⚠️ Gemini extraction for funding history returned no rounds.")
        else:
            print(f"   - ⚠️ Step 2 failed for '{company_name}'. Could not extract funding history. Error: {result_funding.error_message}")

        return scraped_data

    finally:
        # Clean up the browser session for this company to free up resources
        print(f"   - Cleaning up session {session_id}.")
        await crawler.crawler_strategy.kill_session(session_id)


# --- Main Orchestration ---
async def main():
    if not os.path.exists(COOKIES_FILE_PATH):
        print(f"❌ Cookie file not found at '{COOKIES_FILE_PATH}'. Please log in to EquityZen and export your cookies.")
        return

    if not os.getenv("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY environment variable not set. LLM-based extraction will fail.")
        return
        
    ### CHANGED: Pre-process cookies before configuring the crawler ###
    print("🔎 Normalizing cookies from file...")
    try:
        with open(COOKIES_FILE_PATH, 'r') as f:
            raw_cookies = json.load(f)
        
        normalized_cookies = normalize_cookies(raw_cookies)
        
        # This dictionary is what Playwright/crawl4ai expects for storage_state
        storage_state_dict = {"cookies": normalized_cookies}
        print("   - ✅ Cookies successfully normalized.")

    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"❌ Error reading or parsing cookie file: {e}")
        return

    gs_client = GoogleSheetsClient()
    db_client = DatabaseClient()
    companies_to_scrape = gs_client.get_company_list()

    if not companies_to_scrape:
        print("❌ No companies found in the Google Sheet. Exiting.")
        return

    # Configure the browser once for all crawl jobs
    browser_config = BrowserConfig(
        headless=False,
        # Pass the pre-processed cookie dictionary to storage_state
        storage_state=storage_state_dict,
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        verbose=True,
        extra_args=["--start-maximized"] 
    )

    start_index = 34
    companies_to_process = companies_to_scrape[start_index:]

    async with AsyncWebCrawler(config=browser_config) as crawler:
        for i, company_name in enumerate(companies_to_process):
            original_index = i + start_index
            print("-" * 50)
            print(f"Processing company {i+1}/{len(companies_to_process)}: {company_name} (Row {original_index + 2})")

            all_data = await scrape_company_with_crawl4ai(crawler, company_name)

            if all_data:
                print(f"   - ✅ Scraping successful for '{company_name}'. Updating data stores.")
                db_client.update_scraped_data(company_name=company_name, data=all_data)
                gs_client.update_or_add_company_data(company_name=company_name, data=all_data)
            else:
                print(f"   - ❌ No data scraped for '{company_name}'. Skipping updates.")

            sleep_duration = random.uniform(5, 12)
            print(f"--- Pausing for {sleep_duration:.2f} seconds before next company ---")
            await asyncio.sleep(sleep_duration)

    db_client.close()
    print("\n✅ All companies processed.")

if __name__ == "__main__":
    asyncio.run(main())