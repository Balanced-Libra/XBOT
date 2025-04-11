import time
import random
import logging
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import sqlite3
from datetime import datetime
import os
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException

# Hardcoded constants
DELAY_MIN = 1
DELAY_MAX = 5
SCROLL_ATTEMPTS = 5

# Configuration
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Database")
DB_PATH = os.path.join(DB_DIR, "memories.db")

# SQLite Database Setup for Liked Posts
def init_likes_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS likes 
                 (id INTEGER PRIMARY KEY, post_id TEXT UNIQUE, liked_at TEXT)''')
    conn.commit()
    conn.close()

def save_like(post_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO likes (post_id, liked_at) VALUES (?, ?)", 
              (post_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    rows_affected = conn.total_changes
    conn.commit()
    conn.close()
    return rows_affected > 0

def get_likes_count_today():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM likes WHERE liked_at LIKE ?", (f"{today}%",))
    count = c.fetchone()[0]
    conn.close()
    return count

init_likes_db()

def like_posts(driver, settings):
    """Like posts based on user-defined keywords, respecting daily limit."""
    success = False
    try:
        current_like_count = get_likes_count_today()
        daily_limit = settings.get('daily_like_limit', 0)
        if current_like_count >= daily_limit and daily_limit > 0:
            logging.info(f"Daily like limit ({daily_limit}) reached: {current_like_count} likes today")
            return True
        
        if not settings.get('search_keywords'):
            logging.warning("No search keywords provided in settings, skipping like action")
            return False
        
        driver.get("https://x.com/search")  # Navigate to search page first
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

        keyword = random.choice(settings['search_keywords'])
        logging.info(f"Searching for posts with keyword: {keyword}")
        try:
            search_bar = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, '//input[@placeholder="Search"]'))
            )
            # Robustly clear the search bar
            search_bar.click()  # Ensure it's focused
            search_bar.send_keys(Keys.CONTROL + "a")  # Select all text
            search_bar.send_keys(Keys.DELETE)  # Delete selected text
            search_bar.send_keys(keyword)
            search_bar.send_keys(Keys.RETURN)
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
        except TimeoutException:
            logging.warning("Search bar not found, falling back to home page")
            driver.get("https://x.com/home")
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

        # Rest of the function remains unchanged
        last_height = driver.execute_script("return document.body.scrollHeight")
        driver.execute_script("window.scrollBy(0, 500);")
        logging.info("Initial scroll to load content")
        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

        scroll_count = 0
        liked_this_run = 0
        remaining_likes = min(daily_limit - current_like_count, 1) if daily_limit > 0 else 1

        while liked_this_run < remaining_likes and scroll_count < SCROLL_ATTEMPTS:
            scroll_count += 1
            try:
                posts = WebDriverWait(driver, 3).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//article[@data-testid='tweet']"))
                )
                logging.info(f"Found {len(posts)} posts on scroll {scroll_count}")

                for post in posts:
                    current_like_count = get_likes_count_today()
                    if current_like_count >= daily_limit and daily_limit > 0:
                        logging.info(f"Daily limit ({daily_limit}) reached during run: {current_like_count} likes")
                        success = liked_this_run > 0
                        return success

                    try:
                        try:
                            unlike_button = post.find_element(By.XPATH, ".//button[@data-testid='unlike']")
                            logging.info("Found unlike button, scrolling past already liked post")
                            driver.execute_script("arguments[0].scrollIntoView({block: 'end'});", post)
                            driver.execute_script("window.scrollBy(0, 500);")
                            time.sleep(random.uniform(0.5, 1))
                            continue
                        except NoSuchElementException:
                            pass

                        button = WebDriverWait(post, 3).until(
                            EC.element_to_be_clickable((By.XPATH, ".//button[@data-testid='like']"))
                        )
                        aria_label = button.get_attribute("aria-label")
                        if not aria_label or "Like" not in aria_label:
                            continue

                        try:
                            link_elem = post.find_element(By.XPATH, ".//a[@role='link' and .//time]")
                            post_id = link_elem.get_attribute("href").split('/')[-1]
                        except NoSuchElementException:
                            post_id = f"tweet_{int(time.time()*1000)}_{random.randint(1, 10000)}"
                            logging.warning(f"Using fallback post_id: {post_id}")

                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        c.execute("SELECT COUNT(*) FROM likes WHERE post_id = ?", (post_id,))
                        already_liked = c.fetchone()[0] > 0
                        conn.close()
                        if already_liked:
                            logging.info(f"Skipping already liked post {post_id}")
                            continue

                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
                        time.sleep(random.uniform(0.5, 1.5))
                        driver.execute_script("arguments[0].click();", button)
                        time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

                        if save_like(post_id):
                            liked_this_run += 1
                            current_like_count += 1
                            logging.info(f"Liked post with ID: {post_id}")
                            break

                    except (NoSuchElementException, StaleElementReferenceException, ElementClickInterceptedException, TimeoutException) as e:
                        logging.info(f"Skipping post due to error: {repr(e)}")
                        continue

                if liked_this_run < remaining_likes:
                    logging.info(f"Scrolling to load more content, attempt {scroll_count}")
                    driver.execute_script("window.scrollBy(0, 1000);")
                    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        logging.info("No new content loaded, stopping scroll")
                        break
                    last_height = new_height

            except TimeoutException as e:
                logging.error(f"Timeout waiting for posts on scroll {scroll_count}: {repr(e)}")
                scroll_count += 1
                driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))

        updated_count = get_likes_count_today()
        if liked_this_run == 0:
            logging.info(f"No new posts liked this run. Today's like count: {updated_count}/{daily_limit or 'infinite'}")
        else:
            logging.info(f"Like action complete. Today's like count: {updated_count}/{daily_limit or 'infinite'}")
            success = True
    except Exception as e:
        logging.error(f"Like posts failed: {repr(e)}")
    return success

if __name__ == "__main__":
    from modules.xlogin_core import get_logged_in_driver
    result = get_logged_in_driver()
    if result is not None:
        driver = result["driver"]
        settings = result["settings"]
        like_posts(driver, settings)
        driver.quit()