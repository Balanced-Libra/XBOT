import time
import random
import logging
import os
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import sqlite3
from datetime import datetime
import pyperclip
from modules.headline_fetcher import get_unused_headlines, mark_headline_posted
import openai
import google.generativeai as genai
import re  # Added for URL detection

# Hardcoded constants
DELAY_MIN = 1
DELAY_MAX = 5
TWITTER_CHAR_LIMIT = 280  # Define as constant for clarity
TWITTER_LINK_LENGTH = 23  # Twitter shortens all URLs to 23 characters

# Logging setup (unchanged)
class ConciseFormatter(logging.Formatter):
    GREY = "\x1b[90m"
    BLUE = "\x1b[94m"
    RED = "\x1b[91m"
    GREEN = "\x1b[92m"
    RESET = "\x1b[0m"
    FORMATS = {
        logging.INFO: BLUE + "%(asctime)s [I] %(message)s" + RESET,
        logging.ERROR: RED + "%(asctime)s [E] %(message)s" + RESET,
        logging.WARNING: GREY + "%(asctime)s [W] %(message)s" + RESET
    }
    def format(self, record):
        if record.msg == "Bot started":
            log_fmt = self.GREEN + "%(asctime)s [I] %(message)s" + self.RESET
        else:
            log_fmt = self.FORMATS.get(record.levelno, "%(asctime)s [%(levelname)s] %(message)s")
        formatter = logging.Formatter(log_fmt, datefmt="%H:%M:%S")
        return formatter.format(record)

logging.basicConfig(level=logging.INFO, handlers=[logging.StreamHandler()])
logging.getLogger().handlers[0].setFormatter(ConciseFormatter())

# Configuration
DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Database")
DB_PATH = os.path.join(DB_DIR, "memories.db")

# SQLite Database Setup (unchanged)
def init_tweet_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tweets 
                 (id INTEGER PRIMARY KEY, headline TEXT, text TEXT, timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS self_updates 
                 (id INTEGER PRIMARY KEY, text TEXT UNIQUE, timestamp TEXT)''')
    conn.commit()
    conn.close()

def save_tweet(headline, tweet):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO tweets (headline, text, timestamp) VALUES (?, ?, ?)", 
              (headline, tweet, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def save_self_update(tweet):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO self_updates (text, timestamp) VALUES (?, ?)", 
              (tweet, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

def get_recent_tweets(limit=50):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT headline, text FROM tweets ORDER BY timestamp DESC LIMIT ?", (limit,))
    recent = c.fetchall()
    conn.close()
    return recent

def get_used_self_updates(limit=50):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT text FROM self_updates ORDER BY timestamp DESC LIMIT ?", (limit,))
    used = [row[0] for row in c.fetchall()]
    conn.close()
    return used

def get_posts_count_today():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    c.execute("SELECT COUNT(*) FROM tweets WHERE timestamp LIKE ?", (f"{today}%",))
    count = c.fetchone()[0]
    conn.close()
    return count

init_tweet_db()

# Tweet Generation
def strip_non_bmp(text):
    return ''.join(c for c in text if ord(c) <= 65535 and not (0xFE00 <= ord(c) <= 0xFE0F))

def calculate_twitter_length(text):
    """Calculate the Twitter-effective length of text, accounting for URLs and emojis."""
    # Detect URLs using a simple regex
    url_pattern = re.compile(r'https?://\S+')
    urls = url_pattern.findall(text)
    length = len(text)
    
    # Adjust for URLs: each URL counts as 23 characters
    for url in urls:
        length = length - len(url) + TWITTER_LINK_LENGTH
    
    # Twitter counts most emojis as 2 characters
    # This is a simplification; some complex emojis might differ, but this covers most cases
    for char in text:
        if ord(char) > 65535:  # Surrogate pairs or astral plane characters (most emojis)
            length += 1  # Add 1 to make it count as 2 instead of 1
    
    return length

def truncate_to_twitter_limit(text):
    """Truncate text to fit within Twitter's 280-character limit, considering URLs and emojis."""
    if calculate_twitter_length(text) <= TWITTER_CHAR_LIMIT:
        return text
    
    # Truncate and add ellipsis, ensuring we stay under the limit
    truncated = text
    while calculate_twitter_length(truncated + "...") > TWITTER_CHAR_LIMIT:
        truncated = truncated[:-1]
    return truncated + "..."

def generate_self_update(api_client, used_self_updates, settings, attempt=1, max_attempts=3):
    """Generate a fresh self-update tweet with selected API, retrying for uniqueness."""
    if attempt > max_attempts:
        logging.warning("Max attempts reached for unique self-update, returning fallback")
        return "Just vibing today! #LetsGetIt"
    
    tone = ", ".join(settings['tone_keywords'])
    topic = random.choice(settings['self_update_topics'])
    language = settings.get('language', 'English')
    prompt = f"You are {settings['personality_description']} with a {tone} tone. Generate a unique tweet under 280 characters about {topic} in {language}. Avoid these previous tweets: {', '.join(used_self_updates)}. Use 1-2 hashtags from {', '.join(settings['hashtags'])}, optionally a phrase from {', '.join(settings['custom_phrases'])}, and an emoji from {', '.join(settings['emoji_list'])} if {settings['use_emojis']} and random chance < {settings['emoji_frequency']}%."
    
    try:
        if settings['api_type'] == 'openai':
            response = api_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "system", "content": prompt}, {"role": "user", "content": "Generate a tweet."}],
                max_tokens=150,
                temperature=1.0
            )
            tweet = strip_non_bmp(response.choices[0].message.content.strip())
        else:  # gemini
            response = api_client.generate_content(prompt)
            tweet = strip_non_bmp(response.text.strip())
        
        # Remove asterisks from the generated tweet
        tweet = tweet.replace('*', '')

        # Truncate if necessary to ensure it fits within Twitter's limit
        tweet = truncate_to_twitter_limit(tweet)
        
        if tweet in used_self_updates:
            logging.info(f"Generated duplicate self-update on attempt {attempt}: {tweet}, retrying...")
            return generate_self_update(api_client, used_self_updates, settings, attempt + 1, max_attempts)
        return tweet
    except Exception as e:
        logging.error(f"{settings['api_type'].capitalize()} generation failed on attempt {attempt}: {e}")
        if attempt < max_attempts:
            return generate_self_update(api_client, used_self_updates, settings, attempt + 1, max_attempts)
        return "Just vibing today! #LetsGetIt"

def generate_tweet(settings):
    try:
        if settings['api_type'] == 'openai':
            api_client = openai.OpenAI(api_key=settings['api_key'])
        else:  # gemini
            genai.configure(api_key=settings['api_key'])
            api_client = genai.GenerativeModel('gemini-1.5-flash')

        headlines = get_unused_headlines() if settings.get('research_enabled', True) else []
        used_self_updates = get_used_self_updates()
        recent_tweets = get_recent_tweets()
        used_texts = {text for _, text in recent_tweets}

        tweet_type_chance = settings['tweet_type_ratio'] / 100
        tone = ", ".join(settings['tone_keywords'])
        language = settings.get('language', 'English')

        if headlines and random.random() < tweet_type_chance and settings.get('research_enabled', True):
            numbered_headlines = "\n".join(f"{i}: {h}" for i, h in enumerate(headlines))
            prompt = f"You’re {settings['personality_description']}. Pick the most interesting headline from this numbered list based on your personality. Return only the number.\nHeadlines:\n{numbered_headlines}"
            if settings['api_type'] == 'openai':
                response = api_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": prompt}],
                    max_tokens=10,
                    temperature=0.7
                )
                chosen_index = int(response.choices[0].message.content.strip())
            else:  # gemini
                response = api_client.generate_content(prompt)
                chosen_index = int(response.text.strip())
            headline = headlines[chosen_index]
            logging.info(f"{settings['api_type'].capitalize()} picked headline {chosen_index}: {headline}")

            prompt = f"You are {settings['personality_description']} with a {tone} tone. Generate a tweet under 280 characters about the headline: '{headline}' in {language}. Use 1-2 hashtags from {', '.join(settings['hashtags'])}. Optionally use a phrase from {', '.join(settings['custom_phrases'])}, and add an emoji from {', '.join(settings['emoji_list'])} if {settings['use_emojis']} and random chance < {settings['emoji_frequency']}%."
            if settings['api_type'] == 'openai':
                response = api_client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "system", "content": prompt}, {"role": "user", "content": "Generate a tweet."}],
                    max_tokens=150,
                    temperature=0.8
                )
                tweet = strip_non_bmp(response.choices[0].message.content.strip())
            else:  # gemini
                response = api_client.generate_content(prompt)
                tweet = strip_non_bmp(response.text.strip())
            headline_used = headline
        else:
            tweet = generate_self_update(api_client, used_self_updates, settings)
            headline_used = "Self-Update"
            save_self_update(tweet)

        # Remove asterisks from the generated tweet
        tweet = tweet.replace('*', '').strip('"')
        
        # Truncate tweet to ensure it fits within Twitter's limit
        tweet = truncate_to_twitter_limit(tweet)
        
        if tweet in used_texts:
            logging.warning(f"Duplicate tweet detected: {tweet}, generating new self-update")
            tweet = generate_self_update(api_client, used_self_updates, settings)
            headline_used = "Self-Update (Duplicate Avoided)"
            save_self_update(tweet)
            tweet = truncate_to_twitter_limit(tweet)
        
        save_tweet(headline_used, tweet)
        if "Self-Update" not in headline_used:
            mark_headline_posted(headline_used)
        return tweet

    except Exception as e:
        logging.error(f"Tweet generation failed: {e}, falling back to self-update")
        if settings['api_type'] == 'openai':
            api_client = openai.OpenAI(api_key=settings['api_key'])
        else:
            genai.configure(api_key=settings['api_key'])
            api_client = genai.GenerativeModel('gemini-1.5-flash')
        used_self_updates = get_used_self_updates()
        tweet = generate_self_update(api_client, used_self_updates, settings)
        tweet = truncate_to_twitter_limit(tweet)
        save_tweet("Self-Update (Fallback)", tweet)
        save_self_update(tweet)
        return tweet

def post_to_x(driver, tweet):
    for attempt in range(3):
        try:
            logging.info(f"Loading X home page, attempt {attempt + 1}")
            driver.get("https://x.com/home")
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
            text_area = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, "//div[@data-testid='tweetTextarea_0']"))
            )
            logging.info("Text area found")
            text_area.click()
            time.sleep(0.5)
            clean_tweet = strip_non_bmp(tweet)
            if clean_tweet != tweet:
                logging.info(f"Stripped non-BMP from tweet: {tweet} -> {clean_tweet}")
                tweet = clean_tweet
            # Double-check length before posting
            tweet = truncate_to_twitter_limit(tweet)
            try:
                text_area.send_keys(tweet)
                logging.info("Tweet text entered")
            except Exception as e:
                logging.warning(f"send_keys failed: {e}, trying clipboard")
                pyperclip.copy(tweet)
                text_area.send_keys(Keys.CONTROL + "v")
                logging.info("Tweet text pasted via clipboard")
            time.sleep(random.uniform(1, 3))
            post_button = WebDriverWait(driver, 30).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@data-testid='tweetButtonInline']"))
            )
            logging.info("Post button found")
            driver.execute_script("arguments[0].click();", post_button)
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//article[@data-testid='tweet']"))
            )
            logging.info(f"Posted tweet: {tweet}")
            return
        except Exception as e:
            logging.error(f"Posting attempt {attempt + 1} failed: {e}")
            driver.refresh()
            time.sleep(5)
    raise Exception("All posting attempts failed")

def post_tweet(driver, settings):
    try:
        if not settings['post_enabled']:
            logging.info("Posting is disabled in settings")
            return
        
        current_post_count = get_posts_count_today()
        if settings['daily_post_limit'] > 0 and current_post_count >= settings['daily_post_limit']:
            logging.info(f"Daily post limit ({settings['daily_post_limit']}) reached: {current_post_count} posts today")
            return
        
        tweet = generate_tweet(settings)
        logging.info(f"Generated tweet: {tweet} ({calculate_twitter_length(tweet)} chars)")
        post_to_x(driver, tweet)
        logging.info(f"Posted successfully. Today's post count: {get_posts_count_today()}/{settings['daily_post_limit'] or 'infinite'}")
    except Exception as e:
        logging.error(f"Post tweet failed: {e}, falling back to self-update")
        if settings['api_type'] == 'openai':
            api_client = openai.OpenAI(api_key=settings['api_key'])
        else:
            genai.configure(api_key=settings['api_key'])
            api_client = genai.GenerativeModel('gemini-1.5-flash')
        used_self_updates = get_used_self_updates()
        tweet = generate_self_update(api_client, used_self_updates, settings)
        tweet = truncate_to_twitter_limit(tweet)
        save_tweet("Self-Update (Posting Failure Fallback)", tweet)
        save_self_update(tweet)
        logging.info(f"Fallback tweet generated: {tweet}")
        post_to_x(driver, tweet)

if __name__ == "__main__":
    from modules.xlogin_core import get_logged_in_driver
    result = get_logged_in_driver()
    if result is not None:
        driver = result["driver"]
        settings = result["settings"]
        post_tweet(driver, settings)
        driver.quit()