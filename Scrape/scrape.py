import json
import time
from playwright.sync_api import sync_playwright, expect

# --- Configuration ---
COOKIES_FILE_PATH = "cookies.json"
# The main logged-in interface for Forge is the marketplace dashboard.
WEBSITE_URL = "https://marketplace.forgeglobal.com/marketplace/dashboard"

def normalize_cookies(cookies_data):
    """
    Converts a list of cookies from a browser-exported JSON file
    into the format required by Playwright's context.add_cookies() method.
    """
    normalized_cookies = []
    for cookie in cookies_data:
        # Map the 'sameSite' value to the format Playwright expects.
        # Browser exports use 'no_restriction', 'lax', etc.
        # Playwright needs 'None', 'Lax', 'Strict'.
        same_site_mapping = {
            "no_restriction": "None",
            "unspecified": "None",
            "lax": "Lax",
            "strict": "Strict"
        }
        
        # Create the new cookie object with the required keys
        new_cookie = {
            "name": cookie["name"],
            "value": cookie["value"],
            "domain": cookie["domain"],
            "path": cookie["path"],
            # RENAME 'expirationDate' to 'expires'. Playwright uses 'expires'.
            # Use .get() to avoid errors if the key is missing, default to -1 for session cookies.
            "expires": cookie.get("expirationDate", -1),
            "httpOnly": cookie.get("httpOnly", False),
            "secure": cookie.get("secure", False),
            # Use the mapping to get the correct sameSite value, defaulting to Lax.
            "sameSite": same_site_mapping.get(cookie.get("sameSite", "").lower(), "Lax")
        }
        normalized_cookies.append(new_cookie)
        
    return normalized_cookies

def main():
    # Step 1: Load and normalize the cookies from the file
    try:
        with open(COOKIES_FILE_PATH, 'r') as f:
            cookies = json.load(f)
        
        normalized_cookies = normalize_cookies(cookies)
        print(f"✅ Successfully loaded and normalized {len(normalized_cookies)} cookies.")
    
    except FileNotFoundError:
        print(f"❌ Error: The cookie file was not found at '{COOKIES_FILE_PATH}'")
        print("   Please ensure the file is in the same directory as the script.")
        return
    except Exception as e:
        print(f"❌ Error reading or parsing the cookie file: {e}")
        return

    # Step 2: Launch Playwright and use the cookies
    with sync_playwright() as p:
        # Launch browser. Set headless=False to watch it work, True for automation.
        browser = p.chromium.launch(headless=False, slow_mo=50)
        context = browser.new_context()

        # THIS IS THE KEY STEP: Add the normalized cookies to the browser context
        print("Adding cookies to the browser context...")
        context.add_cookies(normalized_cookies)

        page = context.new_page()

        # Step 3: Navigate to the target page
        print(f"Navigating to protected page: {WEBSITE_URL}...")
        page.goto(WEBSITE_URL, wait_until="domcontentloaded", timeout=60000)

        # Step 4: Verify that the login was successful
        # A good verification is to check for an element that ONLY exists when logged in.
        # On Forge, the user account button has a specific 'data-testid'.
        print("Verifying login status...")
        try:
            account_button = page.locator('button[data-testid="profile-menu-button"]')
            # Wait up to 15 seconds for the button to appear
            expect(account_button).to_be_visible(timeout=15000)
            print("✅ Verification successful! Logged in to Forge Global marketplace.")
        except Exception:
            print("❌ Verification failed! Could not find the account button.")
            print("   - The cookies might be expired or invalid.")
            print("   - You may need to generate a fresh 'cookies.json' file.")
            # Take a screenshot to help with debugging
            page.screenshot(path="debug_forge_login_failed.png")
            print("   - Saved a screenshot to 'debug_forge_login_failed.png' for analysis.")
        finally:
            # Keep browser open for a few seconds to see the result
            print("Closing browser in 5 seconds...")
            time.sleep(5)
            browser.close()

if __name__ == "__main__":
    main()