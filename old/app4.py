# 🚀 FULL WEB APP: WhatsApp Bulk Sender (Flask + Frontend + Queue)

# ================= BACKEND =================

from flask import Flask, request, jsonify, render_template
import threading, time, random, urllib.parse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

app = Flask(__name__)

PROFILE_PATH = r"C:\selenium-profile"

# Anti-spam configs
MESSAGE_DELAY = (8, 20)
BATCH_SIZE = 5
BATCH_COOLDOWN = (60, 120)

status_data = {
    "sent": 0,
    "failed": 0,
    "running": False
}

# ---------------- DRIVER ---------------- #

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir={PROFILE_PATH}")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

# ---------------- HELPERS ---------------- #

def random_delay(a, b):
    time.sleep(random.randint(a, b))

# ---------------- SENDER ---------------- #

def send_bulk(data):
    global status_data

    driver = setup_driver()
    driver.get("https://web.whatsapp.com")

    WebDriverWait(driver, 60).until(
        EC.presence_of_element_located((By.ID, "pane-side"))
    )

    status_data["running"] = True

    for i, user in enumerate(data):
        try:
            msg = f"Hey {user['name']}! How are you? 😊"
            encoded = urllib.parse.quote(msg)
            url = f"https://web.whatsapp.com/send?phone={user['number']}&text={encoded}"

            driver.get(url)

            box = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]'))
            )

            time.sleep(random.uniform(1, 3))
            box.send_keys(Keys.ENTER)

            status_data["sent"] += 1
            print(f"Sent to {user['number']}")

        except Exception as e:
            status_data["failed"] += 1
            print(f"Error: {e}")

        random_delay(*MESSAGE_DELAY)

        if (i + 1) % BATCH_SIZE == 0:
            time.sleep(random.randint(*BATCH_COOLDOWN))

    driver.quit()
    status_data["running"] = False

# ---------------- ROUTES ---------------- #

@app.route('/')
def index():
    return render_template("index4.html")

@app.route('/send', methods=['POST'])
def send():
    data = request.json
    threading.Thread(target=send_bulk, args=(data,)).start()
    return jsonify({"status": "started"})

@app.route('/status')
def status():
    return jsonify(status_data)



# ================= RUN =================

if __name__ == '__main__':
    app.run(debug=True)
