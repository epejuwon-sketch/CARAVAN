import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests

ARTIFACT_DIR = "/home/antigravity/.gemini/jetski/brain/v1/default/jetski_remote_agents_3p_devbox/2e1bdfcb-9db7-4326-874b-6bb647a515fb"
BASE_URL = "https://caravan-juwon2.vercel.app"

def get_auth_token():
    email = f"screenshot_user_{int(time.time())}@caravan-demo.africa"
    password = "AureliaPassword2026!"
    payload = {
        "email": email,
        "password": password,
        "full_name": "Hadiza Danjuma",
        "organization_name": "Savannah Harvest Technologies",
        "entity_type": "STARTUP",
        "country": "Nigeria",
        "state_location": "Kano",
        "sector": "Agriculture & AgTech",
        "stage": "GROWTH",
    }
    res = requests.post(f"{BASE_URL}/api/v1/auth/register", json=payload, timeout=10)
    data = res.json()
    return data["access_token"], data.get("user", {}), email, password

def capture_screenshots():
    token, user, email, password = get_auth_token()
    print(f"Obtained auth token for: {email}")

    # 1. Desktop Screenshot
    print("Capturing Desktop Screenshot (1280x800)...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1280,800")

    driver = webdriver.Chrome(options=chrome_options)
    try:
        # Load the base page
        driver.get(f"{BASE_URL}/login")
        time.sleep(2)

        # Inject auth token into localStorage
        driver.execute_script(f"""
            localStorage.setItem('caravan_token', '{token}');
            localStorage.setItem('token', '{token}');
        """)
        
        # Navigate to Copilot / AURELIA Page
        driver.get(f"{BASE_URL}/#copilot")
        time.sleep(5)

        desktop_path = os.path.join(ARTIFACT_DIR, "aurelia_desktop_journey.png")
        driver.save_screenshot(desktop_path)
        print(f"Saved desktop screenshot to {desktop_path}")
    finally:
        driver.quit()

    # 2. Mobile Screenshot
    print("Capturing Mobile Screenshot (390x844)...")
    mobile_options = Options()
    mobile_options.add_argument("--headless=new")
    mobile_options.add_argument("--no-sandbox")
    mobile_options.add_argument("--disable-dev-shm-usage")
    mobile_options.add_argument("--disable-gpu")
    mobile_options.add_argument("--window-size=390,844")

    driver = webdriver.Chrome(options=mobile_options)
    try:
        driver.get(f"{BASE_URL}/login")
        time.sleep(2)

        driver.execute_script(f"""
            localStorage.setItem('caravan_token', '{token}');
            localStorage.setItem('token', '{token}');
        """)
        
        driver.get(f"{BASE_URL}/#copilot")
        time.sleep(5)

        mobile_path = os.path.join(ARTIFACT_DIR, "aurelia_mobile_journey.png")
        driver.save_screenshot(mobile_path)
        print(f"Saved mobile screenshot to {mobile_path}")
    finally:
        driver.quit()

if __name__ == "__main__":
    capture_screenshots()
