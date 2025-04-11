import os
import random
import logging
import sqlite3
from datetime import datetime
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

# Hardcoded constants (as fallbacks)
DELAY_MIN = 1
DELAY_MAX = 5
SCROLL_ATTEMPTS = 5
DEFAULT_KEYWORDS = ["Berlin", "Berliner Leben", "BLN News"]  # Fallback for BerlinerSchnauze
DAILY_FOLLOW_LIMIT = 20
MAX_FOLLOWS_PER_RUN = 1  # Changed to 1 to ensure only one follow per run

# Configuration
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Database")
DB_PATH = os.path.join(DB_DIR, "memories.db")

# SQLite Database Setup for Followed Accounts
def init_follow_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS followed 
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, followed_at TEXT)''')
    conn.commit()
    conn.close()

def save_followed(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO followed (username, followed_at) VALUES (?, ?)", 
              (username, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def is_account_followed(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM followed WHERE username = ?", (username,))
    exists = c.fetchone()[0] > 0
    conn.close()
    return exists

def get_followed_count_today():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM followed WHERE followed_at LIKE ?", (f"{today}%",))
    count = c.fetchone()[0]
    conn.close()
    return count

init_follow_db()

def follow_accounts(driver, settings):
    """Follow one account based on user-defined or personality-derived keywords, respecting daily limit."""
    try:
        daily_limit = settings.get('daily_follow_limit', DAILY_FOLLOW_LIMIT)
        current_follow_count = get_followed_count_today()
        if current_follow_count >= daily_limit and daily_limit > 0:
            logging.info(f"Daily follow limit ({daily_limit}) reached: {current_follow_count} follows today")
            return

        follow_keywords = settings.get("follow_keywords") or settings.get("search_keywords")
        if follow_keywords:
            if isinstance(follow_keywords, str):
                keywords = [kw.strip() for kw in follow_keywords.split(",")]
            elif isinstance(follow_keywords, list):
                keywords = [kw.strip() for kw in follow_keywords]
            else:
                raise ValueError(f"Invalid format for follow_keywords: {follow_keywords}")
        else:
            personality = settings.get('personality_preset', 'default')
            keyword_map = {
                'BerlinerSchnauze': DEFAULT_KEYWORDS,
                'default': ['news', 'trending']
            }
            keywords = keyword_map.get(personality, keyword_map['default'])
            logging.info(f"No follow_keywords in settings, using {keywords} based on personality '{personality}'")

        delay_min = settings.get('delay_min', DELAY_MIN)
        delay_max = settings.get('delay_max', DELAY_MAX)
        scroll_attempts = settings.get('scroll_attempts', SCROLL_ATTEMPTS)

        keyword = random.choice(keywords)
        logging.info(f"Searching for accounts with keyword: {keyword}")

        # Navigate to search page and use the search bar
        driver.get("https://x.com/search?f=user")  # Navigate to user search page
        time.sleep(random.uniform(delay_min, delay_max))
        search_bar = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//input[@placeholder="Search"]'))
        )
        # Robustly clear the search bar
        search_bar.click()  # Ensure it's focused
        search_bar.send_keys(Keys.CONTROL + "a")  # Select all text
        search_bar.send_keys(Keys.DELETE)  # Delete selected text
        search_bar.send_keys(keyword)
        search_bar.send_keys(Keys.RETURN)
        time.sleep(random.uniform(delay_min, delay_max))

        scroll_count = 0
        followed_count = 0
        remaining_follows = min(daily_limit - current_follow_count, MAX_FOLLOWS_PER_RUN) if daily_limit > 0 else MAX_FOLLOWS_PER_RUN

        while scroll_count < scroll_attempts and followed_count < remaining_follows:
            follow_buttons = WebDriverWait(driver, 20).until(
                EC.presence_of_all_elements_located((By.XPATH, "//button[contains(@aria-label, 'Follow')]"))
            )
            logging.info(f"Found {len(follow_buttons)} follow buttons on scroll {scroll_count + 1}")

            for button in follow_buttons:
                if followed_count >= remaining_follows or get_followed_count_today() >= daily_limit:
                    break
                try:
                    aria_label = button.get_attribute("aria-label")
                    if "Follow" in aria_label and "Following" not in aria_label:
                        driver.execute_script("arguments[0].scrollIntoView(true);", button)
                        username_elem = button.find_element(By.XPATH, "../../..//span[starts-with(text(), '@')]")
                        username = username_elem.text

                        if username == settings.get("username") or is_account_followed(username):
                            continue

                        driver.execute_script("arguments[0].click();", button)
                        save_followed(username)
                        followed_count += 1
                        logging.info(f"Followed account: {username}")
                        time.sleep(random.uniform(delay_min, delay_max))
                        break  # Exit after one follow
                except Exception as e:
                    logging.warning(f"Failed to process follow button: {e}")
                    continue

            if followed_count < remaining_follows and get_followed_count_today() < daily_limit:
                logging.info("Scrolling to find more accounts...")
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                scroll_count += 1
                time.sleep(random.uniform(delay_min, delay_max))
            else:
                break

        updated_count = get_followed_count_today()
        if followed_count == 0:
            logging.warning(f"No new accounts followed after {scroll_attempts} scrolls. Today's count: {updated_count}/{daily_limit}")
        else:
            logging.info(f"Followed {followed_count} new account this run. Today's count: {updated_count}/{daily_limit}")

    except Exception as e:
        logging.error(f"Follow accounts failed: {repr(e)}")

if __name__ == "__main__":
    from modules.xlogin_core import get_logged_in_driver
    result = get_logged_in_driver()
    if result is not None:
        driver = result["driver"]
        settings = result["settings"]
        follow_accounts(driver, settings)
        driver.quit()