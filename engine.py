import os
import threading
import time
import random
import re
import csv
from datetime import datetime
from flask import request, jsonify
from flask_login import login_required
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from openpyxl import load_workbook

# --- CONFIGURATION ---
# Change from Windows path to a Linux-compatible path
# For local testing, you can use a conditional check
if os.name == 'nt':  # Windows
    PROFILE_PATH = r"C:\selenium-profile"
else:  # Linux (Render/Railway/Vercel)
    PROFILE_PATH = "/opt/render/project/src/selenium-profile" # Or simply "./selenium-profile"

# PROFILE_PATH = r"C:\selenium-profile"
DEFAULT_COUNTRY_CODE = "91"
TEMP_FILE = "data.xlsx"

status_data = {
    "sent": 0, "failed": 0, "skipped": 0, "total": 0,
    "aborted": False, "running": False, "paused": False,
    "scheduled_for": None, "countdown": 0, "current_action": "Idle",
    "typing_speed": 0
}

# ---------------- HELPERS ---------------- #

def smart_sleep(seconds, action_text="Waiting"):
    global status_data
    status_data["countdown"] = int(seconds)
    status_data["current_action"] = action_text
    while status_data["countdown"] > 0:
        if status_data["aborted"]:
            status_data["countdown"] = 0
            return
        while status_data["paused"]:
            if status_data["aborted"]: return
            status_data["current_action"] = "Paused"
            time.sleep(0.5)
        time.sleep(1)
        status_data["countdown"] -= 1
    status_data["countdown"] = 0

def setup_driver():
    options = webdriver.ChromeOptions()
    
    # Use a relative path for the profile on Linux
    linux_profile = os.path.join(os.getcwd(), "selenium-profile")
    options.add_argument(f"user-data-dir={linux_profile}")
    
    # Required Cloud Settings
    options.add_argument("--headless=new") # Run without a window
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")
    
    # User Agent mimicry to avoid bot detection
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def normalize_number(num):
    if not num: return ""
    num = str(num).strip()
    if num.startswith('+'): num = num[1:]
    num = re.sub(r"\D", "", num) # Remove spaces, dashes, dots
    if num.startswith('00'): num = num[2:]
    if len(num) == 11 and num.startswith('0'): num = num[1:]
    if len(num) == 10: num = DEFAULT_COUNTRY_CODE + num
    return num

def is_valid_number(num):
    return re.fullmatch(r"\d{11,15}", num) is not None

def process_numbers(raw):
    global status_data
    seen, clean = set(), []
    skipped_count = 0
    for r in raw:
        num = normalize_number(r.get("number"))
        if not is_valid_number(num) or num in seen:
            skipped_count += 1
            continue
        seen.add(num)
        clean.append({"name": r.get("name", "User"), "number": num})
    status_data["skipped"] = skipped_count
    return clean

def is_safe_hour():
    hour = datetime.now().hour
    return 9 <= hour < 21

def spin_message(text):
    pattern = r'\{([^{}|]+\|[^{}]+)\}'
    while True:
        match = re.search(pattern, text)
        if not match: break
        options = match.group(1).split('|')
        text = text.replace(match.group(0), random.choice(options), 1)
    return text

# ---------------- SENDER ENGINE ---------------- #

def send_bulk(data, message, config, schedule_delay=0):
    global status_data
    status_data.update({"aborted": False, "paused": False, "sent": 0, "failed": 0, "total": len(data), "running": True})

    if schedule_delay > 0:
        smart_sleep(schedule_delay, "Scheduling")

    driver = None
    try:
        options = webdriver.ChromeOptions()
        options.add_argument(f"user-data-dir={PROFILE_PATH}")
        options.add_argument("--remote-debugging-port=9222")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get("https://web.whatsapp.com")
        wait = WebDriverWait(driver, 60)
        status_data["current_action"] = "Waiting for WhatsApp Login..."
        wait.until(EC.presence_of_element_located((By.ID, "pane-side")))

        for i, user in enumerate(data):
            if status_data["aborted"]: break
            while status_data["paused"]:
                if status_data["aborted"]: break
                time.sleep(1)

            if config.get("SAFE_HOURS") and not is_safe_hour():
                smart_sleep(900, "Outside Safe Hours")
                continue

            phone, msg = user['number'], message.replace("{name}", user['name'])
            if config.get("SPINTAX"): msg = spin_message(msg)
            
            try:
                status_data["current_action"] = f"Sending to {phone}"
                driver.get(f"https://web.whatsapp.com/send?phone={phone}")
                # msg_box = wait.until(EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')))                
              
                # We wait for either the typing box (Success) OR the "Invalid number" pop-up (Skip)
                try:
                    # Combined XPATH: Look for the chat box OR the 'invalid' error text
                    element = WebDriverWait(driver, 15).until(
                        EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="10"] | //div[contains(text(), "invalid")] | //div[contains(text(), "not on WhatsApp")]'))
                    )
                    
                    # Check if the found element is the error pop-up
                    if "invalid" in element.text.lower() or "not on whatsapp" in element.text.lower():
                        status_data["skipped"] += 1
                        status_data["current_action"] = f"Skipped: {phone} (Not on WhatsApp)"
                        # Click the "OK" button to clear the overlay
                        try:
                            ok_btn = driver.find_element(By.XPATH, '//div[@role="button"][contains(., "OK")]')
                            ok_btn.click()
                        except: pass
                        continue # Skip to next number
                    
                    # If it's the message box, proceed
                    msg_box = element
                except:
                    # If it times out, the number likely doesn't exist or loading failed
                    status_data["failed"] += 1
                    continue
                # --- TYPING & SENDING ---
                if config.get("TYPING"):
                    for char in msg:
                        if status_data["aborted"]: break
                        # Select the random speed and save it to status_data
                        speed = random.uniform(0.03, 0.14)
                        status_data["typing_speed"] = round(speed * 1000, 0) # Convert to milliseconds
                        msg_box.send_keys(char)
                        time.sleep(speed)
                    status_data["typing_speed"] = 0
                else:
                    msg_box.send_keys(msg)
                
                time.sleep(1.5) # Buffer before enter
                msg_box.send_keys(Keys.ENTER)
                time.sleep(3) # Wait for send tick
                status_data["sent"] += 1
            except Exception as e:
                print(f"Error sending to {phone}: {e}")
                status_data["failed"] += 1
            # Delays and Cooldowns
            if i < len(data) - 1:
                delay = random.randint(config["DELAY_MIN"], config["DELAY_MAX"])
                if (i + 1) % config["BATCH"] == 0:
                    delay = random.randint(config["COOL_MIN"], config["COOL_MAX"])
                    smart_sleep(delay, "Batch Cooldown")
                else:
                    smart_sleep(delay, "Next Delay")
    finally:
        if driver: driver.quit()
        status_data.update({"running": False, "current_action": "Completed", "countdown": 0})
        if status_data["sent"] > 0 and os.path.exists(TEMP_FILE):
            try: os.remove(TEMP_FILE)
            except: pass

# ---------------- API ENDPOINTS ---------------- #

@login_required
def get_status():
    return jsonify(status_data)

@login_required
def upload_excel():
    f = request.files['file']
    f.save(TEMP_FILE)
    wb = load_workbook(TEMP_FILE)
    sheet = wb.active
    raw = [{"name": str(r[0] or "User"), "number": str(r[1])} for r in sheet.iter_rows(min_row=2, values_only=True) if r[1]]
    data = process_numbers(raw)
    return jsonify({"count": len(data)})

@login_required
def upload_csv():
    f = request.files['file']
    f.save("data.csv")
    raw = []
    with open("data.csv", mode='r', encoding='utf-8') as infile:
        reader = csv.DictReader(infile)
        for row in reader:
            raw.append({"name": row.get("name", "User"), "number": row.get("number")})
    data = process_numbers(raw)
    return jsonify({"count": len(data)})

@login_required
def start_campaign():
    req = request.json
    manual_input = req.get("numbers", "").strip()
    
    # Priority 1: Manual Input
    if manual_input:
        # Split by comma or newline
        raw_list = re.split(r'[,\n]+', manual_input)
        raw = [{"name": "User", "number": n.strip()} for n in raw_list if n.strip()]
        data = process_numbers(raw)
    # Priority 2: Excel File
    elif os.path.exists(TEMP_FILE):
        wb = load_workbook(TEMP_FILE)
        sheet = wb.active
        raw = [{"name": str(r[0] or "User"), "number": str(r[1])} for r in sheet.iter_rows(min_row=2, values_only=True) if r[1]]
        data = process_numbers(raw)
    else:
        return jsonify({"error": "No contacts found. Please upload file or enter numbers."}), 400

    if not data:
        return jsonify({"error": "No valid numbers after normalization."}), 400

    config = {
        "DELAY_MIN": int(req.get("dmin", 15)),
        "DELAY_MAX": int(req.get("dmax", 45)),
        "BATCH": int(req.get("batch", 5)),
        "COOL_MIN": int(req.get("cmin", 2)) * 60,
        "COOL_MAX": int(req.get("cmin", 2)) * 60 + 60,
        "TYPING": req.get("typing", True),
        "SPINTAX": req.get("spintax", True),
        "SAFE_HOURS": req.get("safe_hours", False)
    }

    schedule_delay = 0
    sched_time_str = req.get("schedule_time")
    if sched_time_str:
        try:
            sched_time = datetime.strptime(sched_time_str, "%Y-%m-%dT%H:%M")
            now = datetime.now()
            if sched_time > now:
                schedule_delay = (sched_time - now).total_seconds()
                status_data["scheduled_for"] = sched_time_str
        except: pass

    threading.Thread(target=send_bulk, args=(data, req.get("message"), config, schedule_delay)).start()
    return jsonify({"status": "started", "total": len(data)})

@login_required
def pause_campaign():
    status_data["paused"] = True
    return jsonify({"status": "paused"})

@login_required
def resume_campaign():
    status_data["paused"] = False
    return jsonify({"status": "resumed"})

@login_required
def abort_campaign():
    status_data.update({"aborted": True, "running": False, "paused": False, "scheduled_for": None})
    return jsonify({"status": "stopping"})