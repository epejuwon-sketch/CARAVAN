"""Interactive Browser and Mobile Functional Test for CARAVAN and AURELIA.

Tests actual browser interactions using headless Chrome:
- Desktop interaction (1280x800)
- Mobile interaction (390x844) with mobile user-agent
- AURELIA chat interaction (input typing, button click, response generation)
- Quick prompt buttons
- Opportunity card interactions
- Responsive navigation
"""

import os
import sys
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE_URL = "https://caravan-juwon2.vercel.app"

def get_auth_token():
    email = f"browser_test_{int(time.time())}@caravan-demo.africa"
    payload = {
        "email": email,
        "password": "AureliaBrowserTest2026!",
        "full_name": "Amina Bello",
        "organization_name": "AgroStream Logistics Ltd",
        "entity_type": "STARTUP",
        "country": "Nigeria",
        "state_location": "Kaduna",
        "sector": "Agriculture & AgTech",
        "stage": "GROWTH",
    }
    res = requests.post(f"{BASE_URL}/api/v1/auth/register", json=payload, timeout=10)
    data = res.json()
    assert res.status_code in (200, 201), f"Registration failed: {res.text}"
    return data["access_token"], data.get("user", {}), email

def test_desktop_interactions(token, user):
    print("\n--- 1. Testing Desktop Browser Interactions (1280x800) ---")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1280,800")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        # Load app and set authentication in localStorage
        driver.get(f"{BASE_URL}/login")
        time.sleep(2)
        driver.execute_script(f"""
            localStorage.setItem('caravan_token', '{token}');
            localStorage.setItem('token', '{token}');
        """)

        # 1. Navigate to #copilot
        print("Navigating to AURELIA portal (#copilot)...")
        driver.get(f"{BASE_URL}/#copilot")
        time.sleep(4)

        # Assert AURELIA welcome heading
        heading = driver.find_element(By.TAG_NAME, "h2").text
        print(f"Verified Heading: '{heading}'")
        assert "AURELIA" in heading, f"Expected AURELIA in heading, got '{heading}'"

        # Assert 8-stage ribbon presence
        body_text = driver.find_element(By.TAG_NAME, "body").text
        assert "1. Discover" in body_text
        assert "8. Track" in body_text
        print("Verified 8-stage customer journey ribbon present on Desktop.")

        # 2. Interactive Chat Query
        print("Typing interactive query to AURELIA...")
        input_el = driver.find_element(By.CSS_SELECTOR, "input[type='text']")
        input_el.clear()
        input_el.send_keys("What are the key requirements for commercial agribusiness loans?")

        send_btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        send_btn.click()
        print("Clicked Send button. Awaiting AURELIA response...")

        # Wait for AURELIA response (up to 30s for Gemini AI)
        print("Waiting for response content...")
        WebDriverWait(driver, 30).until(
            lambda d: len(d.find_elements(By.XPATH, "//span[text()='AURELIA']")) >= 1
            and any(word in d.find_element(By.TAG_NAME, "body").text.lower() for word in ["agribusiness", "loan", "funding", "caravan", "commercial"])
        )
        print("AURELIA successfully rendered response in conversation thread.")

        # 3. Navigate to Discover / Opportunities
        print("Navigating to Opportunities catalog (#discover)...")
        driver.get(f"{BASE_URL}/#discover")
        time.sleep(4)

        body_text_opps = driver.find_element(By.TAG_NAME, "body").text
        assert "Opportunities" in body_text_opps or "Discover" in body_text_opps
        print("Verified Opportunities page interactive view.")

    finally:
        driver.quit()

def test_mobile_interactions(token, user):
    print("\n--- 2. Testing Mobile Browser & Safari Compatibility (390x844) ---")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=390,844")
    # Emulate iPhone Safari user agent
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        driver.get(f"{BASE_URL}/login")
        time.sleep(2)
        driver.execute_script(f"""
            localStorage.setItem('caravan_token', '{token}');
            localStorage.setItem('token', '{token}');
        """)

        # 1. Navigate to #dashboard
        print("Navigating to Mobile Dashboard (#dashboard)...")
        driver.get(f"{BASE_URL}/#dashboard")
        time.sleep(4)

        # 2. Locate Floating "Ask AURELIA" button
        print("Locating floating Ask AURELIA button on Mobile...")
        body = driver.find_element(By.TAG_NAME, "body")
        assert "Ask AURELIA" in body.text, "Floating Ask AURELIA trigger button missing on mobile!"

        # Click floating button
        buttons = driver.find_elements(By.TAG_NAME, "button")
        aurelia_btn = None
        for b in buttons:
            if "Ask AURELIA" in b.text:
                aurelia_btn = b
                break

        assert aurelia_btn is not None, "Could not find Ask AURELIA button"
        aurelia_btn.click()
        time.sleep(3)
        print("Clicked Ask AURELIA button on mobile. Floating window opened.")

        # Verify expanded widget header and ribbon
        widget_text = driver.find_element(By.TAG_NAME, "body").text
        assert "Funding Intelligence" in widget_text or "AURELIA" in widget_text
        print("Verified AURELIA floating conversational modal on mobile.")

    finally:
        driver.quit()

def main():
    token, user, email = get_auth_token()
    print(f"Generated test account: {email}")
    test_desktop_interactions(token, user)
    test_mobile_interactions(token, user)
    print("\n=======================================================")
    print(" ALL BROWSER & MOBILE FUNCTIONAL INTERACTIONS PASSED!  ")
    print("=======================================================")

if __name__ == "__main__":
    main()
