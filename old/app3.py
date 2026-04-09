import time
import random
import urllib.parse

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from webdriver_manager.chrome import ChromeDriverManager

# ================= CONFIG ================= #

# ⚠️ CREATE THIS FOLDER MANUALLY
# C:\selenium-profile
PROFILE_PATH = r"C:\selenium-profile"

numbers = [
    {"number": "916005852514", "name": "Junaid"},
    {"number": "919469036885", "name": "Faisal"}
]

message_templates = [
    "Hey {name}! How are you? 😊",
    "Hello {name}, just checking in!",
    "Hi {name}! Hope you're doing great 👋",
]

# Anti-spam settings
MESSAGE_DELAY = (8, 20)
BATCH_SIZE = 5
BATCH_COOLDOWN = (60, 120)

# ========================================= #

def setup_driver():
    options = webdriver.ChromeOptions()

    # 🔥 CRITICAL FIXES
    options.add_argument(f"user-data-dir={PROFILE_PATH}")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    return driver

def random_delay(a, b):
    delay = random.randint(a, b)
    print(f"⏳ Waiting {delay}s...")
    time.sleep(delay)

def wait_for_whatsapp(driver):
    print("📲 Opening WhatsApp Web...")
    driver.get("https://web.whatsapp.com")

    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.ID, "pane-side"))
    )

    print("✅ WhatsApp is ready!")

def send_message(driver, number, name):
    try:
        message = random.choice(message_templates).format(name=name)
        encoded_msg = urllib.parse.quote(message)

        url = f"https://web.whatsapp.com/send?phone={number}&text={encoded_msg}"
        driver.get(url)

        # Wait for input box
        input_box = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(
                (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
            )
        )

        time.sleep(random.uniform(1, 3))

        input_box.send_keys(Keys.ENTER)

        print(f"✅ Sent to {name} ({number})")

        return True

    except Exception as e:
        print(f"❌ Failed for {number}: {e}")
        return False

def main():
    driver = setup_driver()

    wait_for_whatsapp(driver)

    sent_count = 0

    for i, entry in enumerate(numbers):
        number = entry["number"]
        name = entry["name"]

        success = send_message(driver, number, name)

        if success:
            sent_count += 1

        # Delay between messages
        random_delay(*MESSAGE_DELAY)

        # Batch cooldown
        if sent_count % BATCH_SIZE == 0:
            cooldown = random.randint(*BATCH_COOLDOWN)
            print(f"🛑 Cooling down for {cooldown}s...")
            time.sleep(cooldown)

    print(f"🎯 Total messages sent: {sent_count}")
    driver.quit()

if __name__ == "__main__":
    main()