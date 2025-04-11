import time
import random
import logging
import os
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from .xlogin_setup_gui import select_setup_gui, shutdown_flag
from .xlogin_settings_gui import get_settings_from_gui
from .xlogin_db import init_setup_db, load_credentials
from tkinter import messagebox

# Hardcoded constants
DELAY_MIN = 1
DELAY_MAX = 5

# Logging setup
class ConciseFormatter(logging.Formatter):
    GREY = "\x1b[90m"
    BLUE = "\x1b[94m"
    RED = "\x1b[91m"
    RESET = "\x1b[0m"
    FORMATS = {
        logging.INFO: BLUE + "%(asctime)s [I] %(message)s" + RESET,
        logging.ERROR: RED + "%(asctime)s [E] %(message)s" + RESET,
        logging.WARNING: GREY + "%(asctime)s [W] %(message)s" + RESET
    }
    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno, "%(asctime)s [%(levelname)s] %(message)s")
        formatter = logging.Formatter(log_fmt, datefmt="%H:%M:%S")
        return formatter.format(record)

logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
logging.getLogger().handlers[0].setFormatter(ConciseFormatter())

# Configuration
CHROMEDRIVER_PATH = os.path.join(os.path.dirname(__file__), "..", "drivers", "chromedriver.exe")
logging.info(f"Computed CHROMEDRIVER_PATH: {CHROMEDRIVER_PATH}")

def init_browser(headless=False):
    if not os.path.exists(CHROMEDRIVER_PATH):
        raise FileNotFoundError(f"ChromeDriver not found at: {CHROMEDRIVER_PATH}. Please ensure it is in the 'drivers' folder.")
    try:
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
        service = Service(executable_path=CHROMEDRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logging.info(f"Browser initialized successfully {'in headless mode' if headless else ''}")
        return driver
    except Exception as e:
        logging.error(f"Failed to initialize browser: {e}")
        raise

def login_to_x(driver, username, password, email, max_attempts=3):
    for attempt in range(max_attempts):
        try:
            logging.info(f"Starting login attempt {attempt + 1} of {max_attempts}")
            driver.get("https://x.com/login")
            logging.info("Navigated to X login page")
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

            username_field = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//input[@autocomplete='username']"))
            )
            username_field.clear()
            username_field.send_keys(username, Keys.ENTER)
            logging.info(f"Entered username: {username}")
            time.sleep(random.uniform(1, 3))

            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'phone number or email') or contains(text(), 'Phone or Email')]"))
                )
                active_element = driver.switch_to.active_element
                active_element.clear()
                active_element.send_keys(email)
                active_element.send_keys(Keys.ENTER)
                time.sleep(random.uniform(1, 3))
            except Exception:
                logging.info("Email input not needed")

            password_field = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//input[@autocomplete='current-password']"))
            )
            password_field.clear()
            password_field.send_keys(password, Keys.ENTER)
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//div[@data-testId='primaryColumn']"))
            )
            logging.info("Login successful")
            return True
        except Exception as e:
            logging.error(f"Login attempt {attempt + 1} failed: {e}")
            if attempt < max_attempts - 1:
                driver.refresh()
                time.sleep(random.uniform(5, 7))
            else:
                raise Exception("Login failed after maximum attempts")

def get_logged_in_driver():
    init_setup_db()
    while True:
        setup_choice = select_setup_gui()
        if setup_choice is None:
            logging.info("Shutdown requested from setup selection")
            return None

        logging.info(f"Setup choice received: {setup_choice}")

        if setup_choice["action"] == "load":
            loaded_credentials = load_credentials(setup_choice["username"])
            if not loaded_credentials:
                messagebox.showerror("Error", "Credentials not found for this username! Please try again.")
                logging.warning(f"Credentials for '{setup_choice['username']}' not found.")
                continue
            if loaded_credentials["password"] != setup_choice["password"]:
                messagebox.showerror("Error", "Incorrect password! Please try again.")
                logging.warning(f"Incorrect password for '{setup_choice['username']}'.")
                continue
        else:  # "new"
            loaded_credentials = load_credentials(setup_choice["username"])
            if not loaded_credentials:
                messagebox.showerror("Error", "Failed to load newly created credentials! Please try again.")
                logging.error(f"New credentials for '{setup_choice['username']}' not found after signup.")
                continue

        logging.info(f"Loaded credentials for '{setup_choice['username']}': {loaded_credentials}")

        credentials, personality_settings, save_credentials_name = get_settings_from_gui(loaded_credentials)
        if credentials is None:
            if shutdown_flag:
                logging.info("Shutdown requested from settings GUI")
                return None
            else:
                logging.info("Logout requested, returning to login screen")
                return False

        settings = {**credentials, **personality_settings}
        driver = init_browser(headless=settings.get('headless_enabled', False))
        try:
            if login_to_x(driver, settings['username'], settings['password'], settings['email']):
                logging.info(f"Logged in with username: {settings['username']}")
                return {"driver": driver, "settings": settings}
            else:
                driver.quit()
                logging.error("Login failed unexpectedly")
                raise Exception("Failed to log in")
        except Exception as e:
            driver.quit()
            logging.error(f"Login attempt failed: {e}")
            messagebox.showerror("Error", f"Login failed: {e}. Please retry.")
            continue

if __name__ == "__main__":
    try:
        result = get_logged_in_driver()
        if result is None:
            print("Program shutdown gracefully")
        elif result is False:
            print("Logged out, returning to login view")
        else:
            driver = result["driver"]
            settings = result["settings"]
            print(f"Logged in successfully! Settings: {settings}")
            time.sleep(10)
            driver.quit()
    except Exception as e:
        print(f"Error: {e}")