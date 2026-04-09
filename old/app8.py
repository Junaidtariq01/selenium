# 🚀 FULL WEB APP (v5 OPTIMIZED): Search-Based Messaging + Config Dashboard

from flask import Flask, request, jsonify, render_template
import threading, time, random, urllib.parse, re, datetime, csv, requests, io
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from openpyxl import load_workbook

app = Flask(__name__)

PROFILE_PATH = r"C:\selenium-profile"
DEFAULT_COUNTRY_CODE = "91"

# 🔥 NOW CONFIGURABLE FROM FRONTEND
CONFIG = {
    "MESSAGE_DELAY_MIN": 8,
    "MESSAGE_DELAY_MAX": 20,
    "BATCH_SIZE": 5,
    "BATCH_COOLDOWN_MIN": 60,
    "BATCH_COOLDOWN_MAX": 120
}

status_data = {"sent":0,"failed":0,"skipped":0,"running":False}

# ---------------- DRIVER ---------------- #

def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument(f"user-data-dir={PROFILE_PATH}")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# ---------------- HELPERS ---------------- #

def normalize_number(num):
    num = re.sub(r"\D", "", str(num))
    if len(num) == 10:
        num = DEFAULT_COUNTRY_CODE + num
    return num


def is_valid_number(num):
    return re.fullmatch(r"\d{12,13}", num) is not None


def process_numbers(raw):
    seen = set()
    clean = []

    for r in raw:
        num = normalize_number(r.get("number"))
        name = r.get("name", "User")

        if not is_valid_number(num) or num in seen:
            status_data["skipped"] += 1
            continue

        seen.add(num)
        clean.append({"name":name, "number":num})

    return clean

# ---------------- SENDER (ULTRA OPTIMIZED) ---------------- #

def send_bulk(data, message):
    driver = setup_driver()
    driver.get("https://web.whatsapp.com")

    WebDriverWait(driver,60).until(EC.presence_of_element_located((By.ID,"pane-side")))

    status_data["running"] = True

    for i,user in enumerate(data):
        try:
            msg = message.replace("{name}", user['name'])

            # 🔥 NEW: USE SEARCH BOX (NO PAGE RELOAD)
            search_box = WebDriverWait(driver,20).until(
                EC.presence_of_element_located((By.XPATH,'//div[@contenteditable="true"][@data-tab="3"]')))

            search_box.click()
            search_box.send_keys(user['number'])
            time.sleep(2)
            search_box.send_keys(Keys.ENTER)

            # message box
            msg_box = WebDriverWait(driver,20).until(
                EC.presence_of_element_located((By.XPATH,'//div[@contenteditable="true"][@data-tab="10"]')))

            msg_box.send_keys(msg)
            time.sleep(1)
            msg_box.send_keys(Keys.ENTER)

            status_data["sent"] += 1

        except Exception as e:
            status_data["failed"] += 1

        # 🔥 dynamic delay
        delay = random.randint(CONFIG["MESSAGE_DELAY_MIN"], CONFIG["MESSAGE_DELAY_MAX"])
        time.sleep(delay)

        # batch cooldown
        if (i+1) % CONFIG["BATCH_SIZE"] == 0:
            cooldown = random.randint(CONFIG["BATCH_COOLDOWN_MIN"], CONFIG["BATCH_COOLDOWN_MAX"])
            time.sleep(cooldown)

    driver.quit()
    status_data["running"] = False

# ---------------- ROUTES ---------------- #

@app.route('/')
def index():
    return render_template("index8.html")

@app.route('/send', methods=['POST'])
def send():
    req = request.json

    # update config dynamically
    CONFIG["MESSAGE_DELAY_MIN"] = int(req.get("delay_min",8))
    CONFIG["MESSAGE_DELAY_MAX"] = int(req.get("delay_max",20))
    CONFIG["BATCH_SIZE"] = int(req.get("batch",5))
    CONFIG["BATCH_COOLDOWN_MIN"] = int(req.get("cool_min",60))
    CONFIG["BATCH_COOLDOWN_MAX"] = int(req.get("cool_max",120))

    raw = [{"name":"User","number":n.strip()} for n in req.get("numbers").split(",")]
    data = process_numbers(raw)

    threading.Thread(target=send_bulk, args=(data,req.get("message"))).start()
    return jsonify({"total":len(data)})

@app.route('/status')
def status():
    return jsonify(status_data)

# ---------------- FRONTEND ---------------- #


if __name__=='__main__':
    app.run(debug=True)
