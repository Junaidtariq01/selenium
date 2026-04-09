# ================= BACKEND (Flask + Selenium) =================

import os
import random
import threading
import time
import urllib.parse

from flask import Flask, jsonify, render_template_string, request
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

app = Flask(__name__)

DEFAULT_CHROME_PROFILE_PATH = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "Google",
    "Chrome",
    "User Data",
)
CHROME_PROFILE_PATH = os.environ.get(
    "CHROME_PROFILE_PATH",
    DEFAULT_CHROME_PROFILE_PATH,
)
WHATSAPP_WEB_URL = "https://web.whatsapp.com"
MESSAGE_BOX_XPATH = '//footer//div[@contenteditable="true"][@role="textbox"]'
LOGIN_TIMEOUT = 90
CHAT_LOAD_TIMEOUT = 30

# ------------------- Anti-Spam Config ------------------- #
MAX_MESSAGES_PER_BATCH = 10
BATCH_COOLDOWN = (60, 120)  # seconds
MESSAGE_DELAY = (8, 20)

message_templates = [
    "Hey {name}! How are you? 😊",
    "Hello {name}, just checking in!",
    "Hi {name}! Hope you're doing great 👋",
]

# ------------------- Driver Setup ------------------- #

def setup_driver():
    if not CHROME_PROFILE_PATH or not os.path.isdir(CHROME_PROFILE_PATH):
        raise RuntimeError(
            "Chrome profile path not found. Set CHROME_PROFILE_PATH to your Chrome "
            "user data folder before starting the app."
        )

    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir={CHROME_PROFILE_PATH}")
    options.add_argument("--start-maximized")
    return webdriver.Chrome(options=options)

# ------------------- Helpers ------------------- #

def random_delay(a, b):
    time.sleep(random.uniform(a, b))


def normalize_numbers(numbers):
    if not isinstance(numbers, list) or not numbers:
        raise ValueError("Request body must be a non-empty JSON array.")

    cleaned_numbers = []

    for index, entry in enumerate(numbers, start=1):
        if not isinstance(entry, dict):
            raise ValueError(f"Entry {index} must be a JSON object.")

        raw_number = str(entry.get("number", "")).strip()
        digits_only = "".join(char for char in raw_number if char.isdigit())
        if not digits_only:
            raise ValueError(f"Entry {index} is missing a valid phone number.")

        name = str(entry.get("name", "there")).strip() or "there"
        cleaned_numbers.append({"number": digits_only, "name": name})

    return cleaned_numbers


def simulate_typing(element, text):
    for char in text:
        element.send_keys(char)
        time.sleep(random.uniform(0.05, 0.2))


def wait_for_whatsapp_ready(driver):
    WebDriverWait(driver, LOGIN_TIMEOUT).until(
        lambda current_driver: current_driver.find_elements(By.ID, "pane-side")
        or current_driver.find_elements(By.XPATH, MESSAGE_BOX_XPATH)
    )


def wait_for_message_box(driver):
    return WebDriverWait(driver, CHAT_LOAD_TIMEOUT).until(
        EC.element_to_be_clickable((By.XPATH, MESSAGE_BOX_XPATH))
    )

# ------------------- Sender Logic ------------------- #

def send_bulk(numbers):
    driver = None

    try:
        driver = setup_driver()
        driver.get(WHATSAPP_WEB_URL)
        wait_for_whatsapp_ready(driver)

        sent = 0

        for index, entry in enumerate(numbers, start=1):
            number = entry["number"]
            name = entry["name"]
            msg = random.choice(message_templates).format(name=name)
            encoded_msg = urllib.parse.quote(msg)

            try:
                url = f"{WHATSAPP_WEB_URL}/send?phone={number}&text={encoded_msg}"
                driver.get(url)

                box = wait_for_message_box(driver)
                box.click()
                box.send_keys(Keys.CONTROL, "a")
                box.send_keys(Keys.DELETE)

                simulate_typing(box, msg)
                time.sleep(random.uniform(1, 3))
                box.send_keys(Keys.ENTER)

                sent += 1
                print(f"[{index}/{len(numbers)}] Sent to {number}")

                if sent and sent % MAX_MESSAGES_PER_BATCH == 0 and index < len(numbers):
                    cooldown = random.randint(*BATCH_COOLDOWN)
                    print(f"Cooling down for {cooldown}s...")
                    time.sleep(cooldown)

            except TimeoutException:
                print(f"Failed {number}: message box did not load in time.")
            except Exception as exc:
                print(f"Failed {number}: {exc}")

            if index < len(numbers):
                random_delay(*MESSAGE_DELAY)

    except Exception as exc:
        print(f"Bulk send stopped: {exc}")
    finally:
        if driver is not None:
            driver.quit()

# ------------------- API ------------------- #

@app.route("/")
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
        <title>WhatsApp Bulk Sender</title>
    </head>
    <body>
        <h2>Bulk WhatsApp Sender</h2>
        <textarea id="data" rows="10" cols="50" placeholder='[{"number":"9198...","name":"Junaid"}]'></textarea><br>
        <button onclick="send()">Send Messages</button>

        <script>
        async function send() {
            const response = await fetch('/send', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: document.getElementById('data').value
            });

            const data = await response.json();
            alert(data.status);
        }
        </script>
    </body>
    </html>
    """)


@app.route("/send", methods=["POST"])
def send():
    numbers = request.get_json(silent=True)

    try:
        cleaned_numbers = normalize_numbers(numbers)
    except ValueError as exc:
        return jsonify({"status": str(exc)}), 400

    thread = threading.Thread(target=send_bulk, args=(cleaned_numbers,), daemon=True)
    thread.start()
    return jsonify({"status": f"Started sending to {len(cleaned_numbers)} contact(s)."})


if __name__ == "__main__":
    app.run(debug=True)
# def send_bulk(data, message):
    driver = setup_driver()
    driver.get("https://web.whatsapp.com")

    WebDriverWait(driver,60).until(EC.presence_of_element_located((By.ID,"pane-side")))

    status_data["running"] = True

    for i,user in enumerate(data):
        try:
            msg = message.replace("{name}", user['name'])

            search_box = WebDriverWait(driver,20).until(
                EC.presence_of_element_located((By.XPATH,'//div[@contenteditable="true"][@data-tab="3"]')))

            search_box.click()
            search_box.clear()
            search_box.send_keys(user['number'])
            time.sleep(2)
            search_box.send_keys(Keys.ENTER)

            msg_box = WebDriverWait(driver,20).until(
                EC.presence_of_element_located((By.XPATH,'//div[@contenteditable="true"][@data-tab="10"]')))

            msg_box.send_keys(msg)
            time.sleep(1)
            msg_box.send_keys(Keys.ENTER)

            status_data["sent"] += 1

        except Exception as e:
            status_data["failed"] += 1

        delay = random.randint(CONFIG["DELAY_MIN"], CONFIG["DELAY_MAX"])
        time.sleep(delay)

        if (i+1) % CONFIG["BATCH"] == 0:
            cooldown = random.randint(CONFIG["COOL_MIN"], CONFIG["COOL_MAX"])
            time.sleep(cooldown)

    driver.quit()
    status_data["running"] = False