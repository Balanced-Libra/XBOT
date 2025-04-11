import time
import random
import logging
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import sqlite3
from datetime import datetime
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException, ElementClickInterceptedException
import google.generativeai as genai
import openai

# Hardcoded constants
DELAY_MIN = 1
DELAY_MAX = 5
SCROLL_ATTEMPTS = 5

# Configuration
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Database")
DB_PATH = os.path.join(DB_DIR, "memories.db")

# Custom logging formatter with color and concise output
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

# Apply logging config for terminal only
logging.basicConfig(
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logging.getLogger().handlers[0].setFormatter(ConciseFormatter())

# SQLite Database Setup with Migration
def init_comments_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create the table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS comments 
                 (id INTEGER PRIMARY KEY, 
                  post_id TEXT, 
                  comment_text TEXT, 
                  commented_at TEXT)''')
    
    # Check if the 'username' column exists and add it if missing
    c.execute("PRAGMA table_info(comments)")
    columns = [col[1] for col in c.fetchall()]
    if 'username' not in columns:
        logging.info("Adding 'username' column to comments table")
        c.execute("ALTER TABLE comments ADD COLUMN username TEXT")
    
    # Ensure the UNIQUE constraint exists (SQLite doesn't support modifying constraints directly, so we recreate the table if needed)
    # Note: This step assumes the original table might not have the UNIQUE constraint; we’ll handle it safely
    c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='comments'")
    create_statement = c.fetchone()[0]
    if 'UNIQUE(post_id, comment_text)' not in create_statement:
        logging.info("Adding UNIQUE constraint to comments table")
        # Create a new table with the updated schema
        c.execute('''CREATE TABLE comments_new 
                     (id INTEGER PRIMARY KEY, 
                      post_id TEXT, 
                      username TEXT, 
                      comment_text TEXT, 
                      commented_at TEXT,
                      UNIQUE(post_id, comment_text))''')
        # Migrate data from old table to new table
        c.execute("INSERT INTO comments_new (id, post_id, comment_text, commented_at) SELECT id, post_id, comment_text, commented_at FROM comments")
        # Drop the old table and rename the new one
        c.execute("DROP TABLE comments")
        c.execute("ALTER TABLE comments_new RENAME TO comments")
    
    conn.commit()
    conn.close()

def save_comment(post_id, username, comment_text):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO comments (post_id, username, comment_text, commented_at) VALUES (?, ?, ?, ?)", 
              (post_id, username, comment_text, datetime.now().strftime("%Y-%m-d %H:%M:%S")))
    rows_affected = conn.total_changes
    conn.commit()
    conn.close()
    return rows_affected > 0

def get_comments_count_today():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM comments WHERE commented_at LIKE ?", (f"{today}%",))
    count = c.fetchone()[0]
    conn.close()
    return count

def get_previous_comments(limit=50):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT comment_text FROM comments ORDER BY commented_at DESC LIMIT ?", (limit,))
    comments = [row[0] for row in c.fetchall()]
    conn.close()
    return comments

init_comments_db()

def strip_non_bmp(text):
    return ''.join(c for c in text if ord(c) <= 65535 and not (0xFE00 <= ord(c) <= 0xFE0F))

# Configure API client based on settings
def configure_api_client(settings):
    try:
        if settings['api_type'] == 'openai':
            return openai.OpenAI(api_key=settings['api_key'])
        else:  # gemini
            genai.configure(api_key=settings['api_key'])
            return genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        logging.error(f"Failed to configure {settings['api_type']} API: {repr(e)}")
        return None

# Generate contextual comment reflecting the bot's personality
def generate_contextual_comment(post_text, poster_username, settings):
    """Generate a comment reflecting the bot's personality, tone, and settings, avoiding repetition."""
    api_client = configure_api_client(settings)
    if not api_client:
        return "Cool post, thanks for sharing!"

    tone = ", ".join(settings['tone_keywords'])
    personality = settings.get('personality_preset', 'default')
    language = settings.get('language', 'English')
    autodetect = settings.get('autodetect_language', False)
    previous_comments = get_previous_comments()  # Fetch previous comments to avoid repetition

    if autodetect:
        try:
            from langdetect import detect
            detected_lang = detect(post_text)
            lang_map = {
                'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
                'it': 'Italian', 'pt': 'Portuguese', 'nl': 'Dutch', 'ru': 'Russian',
                'zh-cn': 'Chinese', 'ja': 'Japanese'
            }
            language = lang_map.get(detected_lang, settings.get('language', 'English'))
            logging.info(f"Detected language '{detected_lang}' for post '{post_text}', using '{language}'")
        except Exception as e:
            logging.warning(f"Language detection failed: {repr(e)}, using default '{language}'")

    prompt = (
        f"You are {settings['personality_description']} with a {tone} tone. "
        f"Generate a short Twitter comment (max 280 characters) responding to this post by @{poster_username}: '{post_text}' in {language}. "
        f"Use 1-2 hashtags from {', '.join(settings['hashtags'])}. "
        f"Optionally include a phrase from {', '.join(settings['custom_phrases'])}, "
        f"and add an emoji from {', '.join(settings['emoji_list'])} if {settings['use_emojis']} and random chance < {settings['emoji_frequency']}%."
        f"Avoid repeating these previous comments: {', '.join(previous_comments)}."
    )

    try:
        if settings['api_type'] == 'openai':
            response = api_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": "Generate a comment."}],
                max_tokens=150,
                temperature=0.8
            )
            comment = strip_non_bmp(response.choices[0].message.content.strip())
        else:  # gemini
            response = api_client.generate_content(prompt)
            comment = strip_non_bmp(response.text.strip())

        # Remove asterisks from the generated comment
        comment = comment.replace('*', '')

        if len(comment) > 280:
            comment = comment[:277] + "..."
        if comment in previous_comments:
            logging.info(f"Generated duplicate comment: {comment}, regenerating...")
            return generate_contextual_comment(post_text, poster_username, settings)  # Recursive call to avoid duplicates
        return comment
    except Exception as e:
        logging.warning(f"{settings['api_type'].capitalize()} API failed for comment generation: {repr(e)}")
        return "Kiek mal, wie schnieke der Post is!" if personality == "BerlinerSchnauze" else "Cool post, thanks for sharing!"

def comment_on_posts(driver, settings):
    """Comment on posts based on user-defined keywords, respecting daily limit."""
    success = False
    try:
        current_comment_count = get_comments_count_today()
        daily_limit = settings.get('daily_comment_limit', 10)
        if current_comment_count >= daily_limit:
            logging.info(f"Daily comment limit ({daily_limit}) reached: {current_comment_count} comments today")
            return False

        search_keywords = settings.get('search_keywords', ["Berlin", "News", "Tech"])
        logging.info(f"Available search keywords: {search_keywords}")
        keyword = random.choice(search_keywords)
        logging.info(f"Selected keyword for this run: {keyword}")
        try:
            search_bar = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, '//input[@placeholder="Search"]'))
            )
            search_bar.click()
            search_bar.send_keys(Keys.CONTROL + "a")
            search_bar.send_keys(Keys.DELETE)
            search_bar.send_keys(keyword)
            search_bar.send_keys(Keys.RETURN)
            time.sleep(random.uniform(2, 4))
        except TimeoutException:
            logging.warning("Search bar not found, falling back to home page")
            driver.get("https://x.com/home")
            time.sleep(random.uniform(2, 4))

        last_height = driver.execute_script("return document.body.scrollHeight")
        logging.info("Initial scroll to load content")
        driver.execute_script("window.scrollBy(0, 1000);")
        time.sleep(random.uniform(1, 3))

        scroll_count = 0
        commented_this_run = 0
        remaining_comments = min(daily_limit - current_comment_count, 1)

        while commented_this_run < remaining_comments and scroll_count < SCROLL_ATTEMPTS:
            scroll_count += 1
            try:
                tweets = WebDriverWait(driver, 15).until(
                    EC.presence_of_all_elements_located((By.XPATH, "//article[@data-testid='tweet']"))
                )
                logging.info(f"Found {len(tweets)} tweets, scroll {scroll_count}")

                for tweet in tweets:
                    current_comment_count = get_comments_count_today()
                    if current_comment_count >= daily_limit:
                        logging.info(f"Daily limit ({daily_limit}) reached during run: {current_comment_count} comments")
                        success = commented_this_run > 0
                        return success

                    try:
                        # Get post ID
                        try:
                            link_elem = tweet.find_element(By.XPATH, ".//a[@role='link' and .//time]")
                            post_id = link_elem.get_attribute("href").split('/')[-1]
                        except NoSuchElementException:
                            post_id = f"tweet_{int(time.time()*1000)}"
                            logging.warning(f"Using fallback post_id: {post_id}")

                        # Extract username of the poster
                        try:
                            username_elem = tweet.find_element(By.XPATH, ".//span[starts-with(text(), '@')]")
                            poster_username = username_elem.text.lstrip('@')
                        except NoSuchElementException:
                            poster_username = "unknown"
                            logging.warning(f"Could not extract username for post {post_id}, using 'unknown'")

                        # Extract full post text
                        try:
                            text_elements = tweet.find_elements(By.XPATH, ".//div[@lang]//span")
                            post_text = " ".join([elem.text.strip() for elem in text_elements if elem.text.strip()])
                            if not post_text:
                                post_text = "[Empty or media-only post]"
                        except NoSuchElementException:
                            post_text = "[Text extraction failed]"
                            logging.warning(f"Failed to extract text for post {post_id}")
                            continue

                        # Check if already commented
                        conn = sqlite3.connect(DB_PATH)
                        c = conn.cursor()
                        c.execute("SELECT COUNT(*) FROM comments WHERE post_id = ?", (post_id,))
                        already_commented = c.fetchone()[0] > 0
                        conn.close()
                        if already_commented:
                            logging.info(f"Skipping already commented post '{post_text}' (ID: {post_id}) by @{poster_username}")
                            continue

                        # Comment button
                        try:
                            comment_button = WebDriverWait(tweet, 10).until(
                                EC.element_to_be_clickable((By.XPATH, ".//button[@data-testid='reply']"))
                            )
                        except TimeoutException:
                            logging.info(f"Post '{post_text}' (ID: {post_id}) by @{poster_username} has restricted replies, skipping")
                            continue
                        
                        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", comment_button)
                        time.sleep(random.uniform(0.5, 1.5))
                        driver.execute_script("arguments[0].click();", comment_button)
                        time.sleep(random.uniform(1, 2))

                        # Generate contextual comment using personality settings
                        comment = generate_contextual_comment(post_text, poster_username, settings)

                        # Comment box
                        comment_box = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//div[@data-testid='tweetTextarea_0' and @role='textbox']"))
                        )
                        comment_box.send_keys(comment)
                        time.sleep(random.uniform(0.5, 1.5))

                        # Reply button
                        reply_button = WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='tweetButton']"))
                        )
                        driver.execute_script("arguments[0].click();", reply_button)
                        time.sleep(random.uniform(2, 4))

                        # Save comment and log
                        if save_comment(post_id, poster_username, comment):
                            commented_this_run += 1
                            current_comment_count += 1
                            logging.info(f"Commented on post '{post_text}' (ID: {post_id}) by @{poster_username}: {comment}")
                            if commented_this_run >= remaining_comments:
                                break
                        else:
                            logging.info(f"Skipped duplicate comment on post '{post_text}' (ID: {post_id}) by @{poster_username}")

                    except (NoSuchElementException, TimeoutException, StaleElementReferenceException, ElementClickInterceptedException) as e:
                        logging.warning(f"Skipping tweet due to error: {repr(e)}")
                        continue

                if commented_this_run < remaining_comments:
                    logging.info(f"Scrolling to load more content, attempt {scroll_count}")
                    driver.execute_script("window.scrollBy(0, 1000);")
                    time.sleep(random.uniform(2, 4))
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        logging.info("No new content loaded, stopping scroll")
                        break
                    last_height = new_height

            except TimeoutException as e:
                logging.error(f"Timeout finding tweets, scroll {scroll_count}: {repr(e)}")
                driver.execute_script("window.scrollBy(0, 1000);")
                time.sleep(random.uniform(2, 4))

        success = commented_this_run > 0
        logging.info(f"Commented {commented_this_run} this run. Total today: {get_comments_count_today()}/{daily_limit}")
    except Exception as e:
        logging.error(f"Comment on posts failed entirely: {repr(e)}")
    return success

if __name__ == "__main__":
    from Login.xlogin import get_logged_in_driver
    result = get_logged_in_driver()
    if result:
        driver = result["driver"]
        settings = result["settings"]
        comment_on_posts(driver, settings)
        driver.quit()