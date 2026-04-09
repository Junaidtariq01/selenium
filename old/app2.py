import time
import random
import urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ================= CONFIG ================= #

CHROME_PROFILE_PATH = r"C:\Users\Junaid\AppData\Local\Google\Chrome\User Data"

numbers = [
    "916005852514",
    "919469036885"
]

message_templates = [
    "Hey! How are you? 😊",
    "Hello! Just checking in.",
    "Hi there! Hope you're doing great 👋",
]

MAX_MESSAGES_PER_BATCH = 5
BATCH_COOLDOWN = (60, 120)   # seconds
MESSAGE_DELAY = (8, 20)

# ========================================= #

def random_delay(a, b):
    delay = random.randint(a, b)
    print(f"⏳ Waiting {delay}s...")
    time.sleep(delay)

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir={CHROME_PROFILE_PATH}")
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=options)
    return driver

def wait_for_whatsapp_load(driver):
    print("📲 Waiting for WhatsApp Web to load...")
    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.ID, "pane-side"))
    )
    print("✅ WhatsApp Loaded Successfully!")

def send_message(driver, number, message):
    try:
        encoded_msg = urllib.parse.quote(message)
        url = f"https://web.whatsapp.com/send?phone={number}&text={encoded_msg}"
        driver.get(url)

        # Wait for message box
        input_box = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(
                (By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
            )
        )

        time.sleep(random.uniform(1, 3))

        input_box.send_keys(Keys.ENTER)

        print(f"✅ Message sent to {number}")
        return True

    except Exception as e:
        print(f"❌ Failed for {number}: {e}")
        return False

def main():
    driver = setup_driver()
    driver.get("https://web.whatsapp.com")

    wait_for_whatsapp_load(driver)

    sent_count = 0

    for i, number in enumerate(numbers):
        message = random.choice(message_templates)

        success = send_message(driver, number, message)

        if success:
            sent_count += 1

        # Delay between messages
        random_delay(*MESSAGE_DELAY)

        # Batch cooldown
        if sent_count % MAX_MESSAGES_PER_BATCH == 0:
            cooldown = random.randint(*BATCH_COOLDOWN)
            print(f"🛑 Batch limit reached. Cooling down for {cooldown}s...")
            time.sleep(cooldown)

    print(f"🎯 Total messages sent: {sent_count}")
    driver.quit()

if __name__ == "__main__":
    main()