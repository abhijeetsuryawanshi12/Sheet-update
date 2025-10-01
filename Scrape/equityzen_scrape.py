import asyncio
import json
import random
import sys
import os
import time
import re

from playwright.async_api import async_playwright, expect

# --- Add parent directory to path to import 'app' modules ---
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.services.google_sheets import GoogleSheetsClient
from app.services.database import DatabaseClient

# --- Configuration ---
COOKIES_FILE_PATH = "Scrape/equityzen_cookies.json"

def normalize_cookies(cookies_data):
    """Converts browser-exported cookies to the format Playwright requires."""
    normalized_cookies = []
    for cookie in cookies_data:
        same_site_mapping = { "no_restriction": "None", "unspecified": "None", "lax": "Lax", "strict": "Strict" }
        new_cookie = {
            "name": cookie["name"], "value": cookie["value"], "domain": cookie["domain"], "path": cookie["path"],
            "expires": cookie.get("expirationDate", -1), "httpOnly": cookie.get("httpOnly", False),
            "secure": cookie.get("secure", False), "sameSite": same_site_mapping.get(str(cookie.get("sameSite", "")).lower(), "Lax")
        }
        normalized_cookies.append(new_cookie)
    return normalized_cookies

async def scrape_company_data(page, company_name, company_url, db_client):
    """Scrapes Overview, Investors, Market Activity, and Funding data for a single company."""
    # --- UPDATED: Use the provided URL directly ---
    base_url = company_url.rstrip('/')
    about_url = base_url
    funding_url = f"{base_url}/?tab=cap-table"
    scraped_data = {}

    try:
        # --- STAGE 1: Scrape "About" Page ---
        print(f"🚀 Navigating to {company_name}'s 'About' page...")
        await page.goto(about_url, wait_until="domcontentloaded", timeout=45000)

        time.sleep(3)
        # Check if page exists
        page_title = await page.title()
        if "Sorry, we couldn't find that page" in page_title or "EquityZen | Invest in Private Companies" in page_title:
            print(f"❌ Page not found or redirected for {company_name}. Skipping.")
            return None

        # Handle confirmation popup
        try:
            confirm_button = page.locator('button:has-text("Confirm")')
            if await confirm_button.count() > 0:
                await confirm_button.click(timeout=5000)
                print("   - ✅ 'Confirm' button clicked.")
                await page.wait_for_load_state('networkidle', timeout=10000)
        except Exception as e:
            print(f"   - ℹ️ No confirmation popup found or already handled.")

        # Check if Overview field is empty in database
        existing_overview = db_client.get_field_value(company_name, 'Overview')
        if not existing_overview or existing_overview.strip() == "":
            # Scrape Overview using SanitizedHtml
            try:
                # Try multiple selectors for overview
                overview_text = None
                
                # First try: div.SanitizedHtml
                sanitized_html = page.locator('div.SanitizedHtml').first
                if await sanitized_html.count() > 0:
                    overview_text = await sanitized_html.inner_text()
                
                # Second try: Original selector as fallback
                if not overview_text:
                    overview_locator = page.locator('div[class*="SvaSingleCompanyAboutCompanyTab--section"] div[class*="--description"]').first
                    if await overview_locator.count() > 0:
                        overview_text = await overview_locator.inner_text()
                
                if overview_text and overview_text.strip():
                    scraped_data['Overview'] = overview_text.strip()
                    print(f"   - ✅ Overview scraped ({len(overview_text)} chars).")
                else:
                    print(f"   - ⚠️ Overview selector found but no text content for {company_name}.")
            except Exception as e:
                print(f"   - ⚠️ Overview not found for {company_name}: {str(e)}")
        else:
            print(f"   - ℹ️ Overview already exists for {company_name}. Skipping.")

        # Check if Investors field is empty in database
        existing_investors = db_client.get_field_value(company_name, 'Investors')
        if not existing_investors or existing_investors.strip() == "":
            # Scrape Investors
            try:
                investors = []
                
                # Try multiple selectors for investors
                # Method 1: Original selector
                investor_locators = page.locator('div[class*="Company-Investors"] a h5')
                if await investor_locators.count() > 0:
                    investors = await investor_locators.all_inner_texts()
                
                # Method 2: Alternative selector from CompanyInvestors class
                if not investors:
                    investor_links = page.locator('div.CompanyInvestors a.CompanyInvestors--link h5')
                    if await investor_links.count() > 0:
                        investors = await investor_links.all_inner_texts()
                
                # Method 3: Try just CompanyInvestors--header
                if not investors:
                    investor_headers = page.locator('h5.CompanyInvestors--header')
                    if await investor_headers.count() > 0:
                        investors = await investor_headers.all_inner_texts()
                
                # Clean and filter investors
                investors = [inv.strip() for inv in investors if inv and inv.strip()]
                
                if investors:
                    scraped_data['Investors'] = ", ".join(investors)
                    print(f"   - ✅ Investors scraped ({len(investors)} investors).")
                else:
                    print(f"   - ⚠️ No investors found for {company_name}.")
            except Exception as e:
                print(f"   - ⚠️ Error scraping investors for {company_name}: {str(e)}")
        else:
            print(f"   - ℹ️ Investors already exist for {company_name}. Skipping.")

        # Scrape Market Activity Card (always scrape to get latest data)
        try:
            items_container = page.locator('div[class*="MarketActivityCard--items"]')
            if await items_container.count() > 0:
                all_items = items_container.locator('div[class*="MarketActivityCard--item"]')
                item_count = await all_items.count()
                
                if item_count > 0:
                    for i in range(item_count):
                        item = all_items.nth(i)
                        label_locator = item.locator('div[class*="--item-label"]')
                        value_locator = item.locator('div[class*="--item-value"]')
                        
                        if await label_locator.count() > 0 and await value_locator.count() > 0:
                            label = await label_locator.inner_text()
                            value = await value_locator.inner_text()
                            
                            if label and value and value.strip() not in ['--', '', 'N/A']:
                                scraped_data[label.strip()] = value.strip()
                    
                    print(f"   - ✅ Market Activity scraped ({len([k for k in scraped_data.keys() if k not in ['Overview', 'Investors', 'Funding History']])} fields).")
                else:
                    print(f"   - ⚠️ Market Activity card found but no items for {company_name}.")
            else:
                print(f"   - ⚠️ Market Activity card not found for {company_name}.")
        except Exception as e:
            print(f"   - ⚠️ Error scraping Market Activity for {company_name}: {str(e)}")

        # --- STAGE 2: Scrape Funding Data ---
        print(f"🚀 Navigating to {company_name}'s 'Funding' page...")
        await page.goto(funding_url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(5000)  # Wait for dynamic content


        funding_scraped = False

        # Try to scrape full funding history table (CompanyCapTable)
        try:
            table_container = page.locator("div.CompanyCapTable").first
            
            if await table_container.count() > 0:
                await expect(table_container).to_be_visible(timeout=15000)
                
                # Get headers
                all_th = table_container.locator("thead th.ant-table-cell")
                if await all_th.count() > 0:
                    headers = [text.strip() for text in await all_th.all_inner_texts() if text.strip()]
                    
                    # Get rows
                    row_locators = table_container.locator("tbody > tr.ant-table-row")
                    row_count = await row_locators.count()
                    
                    if row_count > 0 and len(headers) > 0:
                        all_rows_data = []
                        
                        for i in range(row_count):
                            row = row_locators.nth(i)
                            all_td = row.locator("td.ant-table-cell")
                            cell_texts = []
                            
                            for j in range(await all_td.count()):
                                cell_class = await all_td.nth(j).get_attribute("class") or ""
                                # Skip expand icon cells
                                if "ant-table-row-expand-icon-cell" not in cell_class:
                                    cell_text = await all_td.nth(j).inner_text()
                                    cell_texts.append(cell_text.strip())
                            
                            # Only add row if it matches header count
                            if len(headers) == len(cell_texts):
                                all_rows_data.append(dict(zip(headers, cell_texts)))
                        
                        if all_rows_data:
                            scraped_data['Funding History'] = json.dumps(all_rows_data)
                            print(f"   - ✅ Funding History table scraped ({len(all_rows_data)} rows).")
                            funding_scraped = True
                        else:
                            print(f"   - ⚠️ Funding table found but no valid rows extracted.")
                    else:
                        print(f"   - ℹ️ Funding table found but empty or no headers.")
        except Exception as e:
            print(f"   - ℹ️ Full funding history table not found: {str(e)}")

        # If funding history table not found, try simple date/value table
        if not funding_scraped:
            try:
                print(f"   - 🔄 Attempting to scrape simple funding data...")
                
                # Look for rows with level-0 class (from screenshot)
                simple_rows = page.locator("tr.ant-table-row.ant-table-row-level-0")
                row_count = await simple_rows.count()
                
                if row_count > 0:
                    simple_funding_data = []
                    
                    for i in range(row_count):
                        row = simple_rows.nth(i)
                        cells = row.locator("td.ant-table-cell")
                        cell_count = await cells.count()
                        
                        # Expect at least 2 cells: date and value
                        if cell_count >= 2:
                            date_text = await cells.nth(0).inner_text()
                            value_text = await cells.nth(1).inner_text()
                            
                            # Also try to get the amount if there's a third column
                            amount_text = ""
                            if cell_count >= 3:
                                amount_text = await cells.nth(2).inner_text()
                            
                            if date_text.strip() and value_text.strip():
                                entry = {
                                    "Date": date_text.strip(),
                                    "Value": value_text.strip()
                                }
                                if amount_text.strip():
                                    entry["Amount"] = amount_text.strip()
                                
                                simple_funding_data.append(entry)
                    
                    if simple_funding_data:
                        scraped_data['Funding History'] = json.dumps(simple_funding_data)
                        print(f"   - ✅ Simple funding data scraped ({len(simple_funding_data)} entries).")
                        funding_scraped = True
                    else:
                        print(f"   - ⚠️ Simple funding rows found but no valid data extracted.")
                else:
                    print(f"   - ℹ️ No simple funding data rows found.")
            except Exception as e:
                print(f"   - ⚠️ Error scraping simple funding data: {str(e)}")

        if not funding_scraped:
            print(f"   - ⚠️ No funding data found for {company_name}.")

        return scraped_data if scraped_data else None

    except Exception as e:
        print(f"❌ An error occurred while scraping {company_name}: {str(e)}")
        try:
            # Create a slug from the URL for the screenshot filename
            company_slug = base_url.split('/')[-1]
            await page.screenshot(path=f"error_{company_slug}.png")
            print(f"   - 📸 Screenshot saved as error_{company_slug}.png")
        except:
            pass
        return None


async def main():
    gs_client = GoogleSheetsClient()
    db_client = DatabaseClient()
    
    # --- NEW: Define companies and their URLs in this dictionary ---
    # INSTRUCTION: Add company names as keys and their full EquityZen URLs as values.
    # The script will iterate through this dictionary.
    COMPANIES_TO_SCRAPE = {
        '6sense': "https://equityzen.com/company/6sense/",
        'Abnormal AI': "https://equityzen.com/company/abnormalsecurity/",
        'Abridge': "https://equityzen.com/company/abridged1a4/",
        'Airtable': "https://equityzen.com/company/airtable/",
        'Alchemy Insights': "https://equityzen.com/company/alchemyinsights/",
        'Aledade Inc.': "https://equityzen.com/company/aledade/",
        'Algolia': "https://equityzen.com/company/algolia/",
        'AlphaSense': "https://equityzen.com/company/alphasense/",
        'Altruist': "https://equityzen.com/company/altruistcorp/",
        'Ambience Healthcare': "https://equityzen.com/company/ambiencehealthcare/",
        'Anaconda': "https://equityzen.com/company/continuumanalytics/",
        'Anysphere, Inc.': "https://equityzen.com/company/anysphere/",
        'Apptronik': "https://equityzen.com/company/apptronik/",
        'Arctic Wolf': "https://equityzen.com/company/arcticwolfnetworks/",
        'Aviatrix': "https://equityzen.com/company/aviatrix/",
        'Aviatrix Systems': "https://equityzen.com/company/aviatrixsystems/",
        'Benchling': "https://equityzen.com/company/benchling/",
        'Bitwise': "https://equityzen.com/company/bitwiseassetmanagement/",
        'Boxabl': "https://equityzen.com/company/boxabl/",
        'Celestial AI': "https://equityzen.com/company/inorganicintelligence/",
        'Cerebras Systems': "https://equityzen.com/company/cerebrassystems/",
        'Chainalysis': "https://equityzen.com/company/chainalysis123/",
        'Chronosphere': "https://equityzen.com/company/chronosphere/",
        'Cityblock Health': "https://equityzen.com/company/cityblockhealth/",
        'ClickHouse': "https://equityzen.com/company/clickhouse/",
        'Cockroach Labs': "https://equityzen.com/company/cockroachlabs/",
        'Cognition AI': "https://equityzen.com/company/cognition5bd7/",
        'Cohere': "https://equityzen.com/company/cohere82b8/",
        'Cohesity, Inc.': "https://equityzen.com/company/cohesity/",
        'Colossal': "https://equityzen.com/company/colossalbiosciences/",
        'Commonwealth Fusion Systems': "https://equityzen.com/company/commonwealthfusionsystems/",     
        'Consensys': "https://equityzen.com/company/consensussystems/",
        'Cribl': "https://equityzen.com/company/cribl/",
        'Crunchbase': "https://equityzen.com/company/crunchbase/",
        'Crusoe ': "https://equityzen.com/company/crusoe/",
        'Crusoe Energy': "https://equityzen.com/company/crusoeenergy/",
        'Crusoe Energy Systems': "https://equityzen.com/company/crusoeenergysystems/",
        'DataRobot': "https://equityzen.com/company/datarobot/",
        'Databricks': "https://equityzen.com/company/databricks/",
        'Decart': "https://equityzen.com/company/decartabcd/",
        'Deel': "https://equityzen.com/company/deel/",
        'Devo': "https://equityzen.com/company/logtrustsl/",
        'Discord': "https://equityzen.com/company/discord/",
        'DispatchHealth': "https://equityzen.com/company/dispatchhealth/",
        'Drata': "https://equityzen.com/company/drata/",
        'Dura Software': "https://equityzen.com/company/durasoftware/",
        'Eight Sleep': "https://equityzen.com/company/morphy/",
        'Eightfold AI': "https://equityzen.com/company/eightfold/",
        'ElevenLabs': "https://equityzen.com/company/elevenlabs/",
        'EliseAI': "https://equityzen.com/company/meetelise/",
        'Eon': "https://equityzen.com/company/eone96e/",
        'Epic Games': "https://equityzen.com/company/epicgames234/",
        'Epic Games Inc.': "https://equityzen.com/company/epicgames/",
        'Events.com': "https://equityzen.com/company/eventscom/",
        'Evidation Health': "https://equityzen.com/company/evidationhealth/",
        'Fever': "https://equityzen.com/company/fever/",
        'FigureAI': "https://equityzen.com/company/figureb5dc/",
        'Fivetran': "https://equityzen.com/company/fivetran/",
        'Flock Safety': "https://equityzen.com/company/flocksafety/",
        'Gecko Robotics': "https://equityzen.com/company/geckorobotics/",
        'Glean': "https://equityzen.com/company/sciotechnologies/",
        'Gusto': "https://equityzen.com/company/gusto/",
        'Helion Energy': "https://equityzen.com/company/helionenergy/",
        'Helsing': "https://equityzen.com/company/helsing/",
        'Hippocratic AI': "https://equityzen.com/company/hippocraticai/",
        'Huntress': "https://equityzen.com/company/huntress/",
        'Icertis': "https://equityzen.com/company/icertis/",
        'Illumio': "https://equityzen.com/company/illumio/",
        'Invisible Technologies': "https://equityzen.com/company/invisibletechnologies/",
        'Kalshi': "https://equityzen.com/company/kalshi/",
        'Kard': "https://equityzen.com/company/kard/",
        'Kraken': "https://equityzen.com/company/kraken/",
        'Lambda': "https://equityzen.com/company/lambdalabs/",
        'LeoLabs': "https://equityzen.com/company/leolabs/",
        'Lightmatter': "https://equityzen.com/company/lightmatterinc/",
        'Magic': "https://equityzen.com/company/magicleap/",
        'Maven': "https://equityzen.com/company/mavenlink/",
        'Medable': "https://equityzen.com/company/medableinc/",
        'Meesho': "https://equityzen.com/company/meesho/",
        'Megvii': "https://equityzen.com/company/megvii/",
        'Meter': "https://equityzen.com/company/meter5c65/",
        'MinIO': "https://equityzen.com/company/minioinc/",
        'Motive Technologies': "https://equityzen.com/company/motive/",
        'Neo4J': "https://equityzen.com/company/neotechnology/",
        'Neuralink': "https://equityzen.com/company/neuralink/",
        'Niantic, Inc.': "https://equityzen.com/company/nianticlabsgoogle/",
        'Nova Labs  (Helium)': "https://equityzen.com/company/novalabs(helium)/",
        'Nova Labs (Helium)': "https://equityzen.com/company/novalabs(helium)/",
        'Nuro': "https://equityzen.com/company/nuro2/",
        'OpenAI': "https://equityzen.com/company/openai/",
        'OpenEvidence': "https://equityzen.com/company/openevidence/",
        'Orum': "https://equityzen.com/company/orum/",
        'Persefoni AI Inc.': "https://equityzen.com/company/persefoni/",
        'Polymarket': "https://equityzen.com/company/polymarket/",
        'Postman': "https://equityzen.com/company/postman/",
        'PurpleLab': "https://equityzen.com/company/purplelab/",
        'Quantum Machines': "https://equityzen.com/company/quantummachines/",
        'Reflection AI': "https://equityzen.com/company/reflectionai/",
        'Reify Health': "https://equityzen.com/company/reifyhealth/",
        'Reka AI': "https://equityzen.com/company/rekaai/",
        'Relativity Space': "https://equityzen.com/company/relativityspace/",
        'Remote Technology': "https://equityzen.com/company/remoted596/",
        'Replit': "https://equityzen.com/company/replit/",
        'Ripple Labs Inc.': "https://equityzen.com/company/ripplelabs/",
        'SambaNova Systems': "https://equityzen.com/company/sambanovasystems/",
        'SandboxAQ': "https://equityzen.com/company/sandboxaq/",
        'Shield AI': "https://equityzen.com/company/shieldai/",
        'Sierra Space': "https://equityzen.com/company/sierraspace/",
        'Sila Nanotechnologies': "https://equityzen.com/company/silananotechnologies/",
        'Skydio': "https://equityzen.com/company/skydio/",
        'Snorkel AI': "https://equityzen.com/company/snorkelai/",
        'SpaceX': "https://equityzen.com/company/spacex/",
        'StartEngine': "https://equityzen.com/company/startengine/",
        'StockX': "https://equityzen.com/company/stockx/",
        'Talkdesk': "https://equityzen.com/company/talkdesk/",
        'Tanium': "https://equityzen.com/company/tanium/",
        'Teleport': "https://equityzen.com/company/gravitational/",
        'Thinking Machines Lab': "https://equityzen.com/company/thinkingmachineslab/",
        'Together AI': "https://equityzen.com/company/together1a7e/",
        'Vercel': "https://equityzen.com/company/vercel/",
        'Xanadu': "https://equityzen.com/company/xanadu2/",
        'Zipline': "https://equityzen.com/company/romotive/",
    }

    if not COMPANIES_TO_SCRAPE:
        print("❌ The COMPANIES_TO_SCRAPE dictionary is empty. Please add companies and their URLs to the script. Exiting.")
        return

    try:
        with open(COOKIES_FILE_PATH, 'r') as f:
            cookies = normalize_cookies(json.load(f))
    except Exception as e:
        print(f"❌ Error with cookie file: {e}")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=50)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        await context.add_cookies(cookies)
        page = await context.new_page()

        start_index = 0  # Adjust this to start from a specific company in the list
        # Convert dict items to a list to allow slicing
        companies_to_process = list(COMPANIES_TO_SCRAPE.items())[start_index:]

        for i, (company_name, company_url) in enumerate(companies_to_process):
            original_index = i + start_index
            print("-" * 50)
            print(f"Processing company {i+1}/{len(companies_to_process)} (#{original_index}): {company_name}")
            print(f"   - URL: {company_url}")
            
            all_data = await scrape_company_data(page, company_name, company_url, db_client)
            
            if all_data:
                print(f"   - ✅ Scraping successful for {company_name}. Updating stores...")
                db_client.update_scraped_data(company_name=company_name, data=all_data)
                gs_client.update_or_add_company_data(company_name=company_name, data=all_data)
                print(f"   - 💾 Data saved: {', '.join(all_data.keys())}")
            else:
                print(f"   - ❌ No data scraped for {company_name}. Not updating stores.")

            # Random delay between companies
            sleep_duration = random.uniform(5, 12)
            print(f"⏸️  Pausing for {sleep_duration:.2f} seconds before next company...")
            time.sleep(sleep_duration)

        await browser.close()
        db_client.close()
        print("\n" + "=" * 50)
        print("✅ All companies processed successfully!")
        print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())