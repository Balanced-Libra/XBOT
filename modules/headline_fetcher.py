import requests
from bs4 import BeautifulSoup
import time
import random
import logging
import os
import sqlite3
from datetime import datetime
import feedparser

# Custom logging formatter (unchanged)
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

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Database")
DB_PATH = os.path.join(DB_DIR, "memories.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS headlines 
                 (id INTEGER PRIMARY KEY, 
                  headline TEXT UNIQUE, 
                  source_url TEXT, 
                  run_number INTEGER, 
                  timestamp TEXT, 
                  posted INTEGER DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS run_counter 
                 (id INTEGER PRIMARY KEY CHECK (id = 1), 
                  count INTEGER DEFAULT 0)''')
    c.execute("INSERT OR IGNORE INTO run_counter (id, count) VALUES (1, 0)")
    conn.commit()
    conn.close()
    logging.info(f"Initialized/Updated database at {DB_PATH}")

def get_and_increment_run_counter():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT count FROM run_counter WHERE id = 1")
    run_counter = c.fetchone()[0]
    new_run_counter = run_counter + 1
    c.execute("UPDATE run_counter SET count = ? WHERE id = 1", (new_run_counter,))
    conn.commit()
    conn.close()
    return new_run_counter

def headline_exists(headline):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM headlines WHERE headline = ?", (headline,))
    exists = c.fetchone()[0] > 0
    conn.close()
    return exists

def save_headlines(headlines, source_url, run_number):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    new_count = 0
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for headline in headlines:
        if not headline_exists(headline):
            c.execute("INSERT INTO headlines (headline, source_url, run_number, timestamp, posted) VALUES (?, ?, ?, ?, ?)",
                      (headline, source_url, run_number, timestamp, 0))
            new_count += 1
    conn.commit()
    conn.close()
    return new_count

def fetch_and_save_headlines(settings):
    init_db()
    run_counter = get_and_increment_run_counter()
    total_new = 0

    if not settings['content_sources']:
        logging.info("No content sources provided, skipping headline fetch.")
        return

    logging.info(f"Run {run_counter}: Fetching headlines...")
    for url in settings['content_sources']:
        fetched = 0
        new_headlines = []
        max_items = 100
        skip_count = 0

        # Try RSS first
        try:
            logging.info(f"Run {run_counter}: Attempting RSS fetch from {url}")
            feed = feedparser.parse(url)
            if feed.entries:
                total_items = len(feed.entries)
                for entry in feed.entries[:min(max_items, total_items)]:
                    headline = entry.title.strip()
                    if headline_exists(headline):
                        skip_count += 1
                        continue
                    new_headlines.append(headline)
                    fetched += 1
                    if fetched >= 10:
                        break
                logging.info(f"Run {run_counter}: Fetched {fetched} new headlines from RSS {url} (skipped {skip_count} duplicates, checked {fetched + skip_count}/{total_items} items)")
            else:
                raise Exception("No RSS entries found, falling back to scraping")
        except Exception as e:
            logging.info(f"Run {run_counter}: RSS fetch failed for {url} ({e}), trying web scraping")

            # Enhanced web scraping with retries and better HTML parsing
            for attempt in range(3):
                try:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    }
                    response = requests.get(url, headers=headers, timeout=10)
                    response.raise_for_status()
                    soup = BeautifulSoup(response.content, 'html.parser')  # Use html.parser for modern sites

                    # Look for common headline tags
                    headline_tags = soup.find_all(['h1', 'h2', 'h3', 'a'], class_=['title', 'headline', 'post-title', 'entry-title', 'news-title'])
                    if not headline_tags:
                        # Fallback to any text in article-like elements
                        headline_tags = soup.select('article h1, article h2, .post h1, .post h2, .entry h1, .entry h2')
                    
                    total_items = len(headline_tags)
                    for tag in headline_tags[:min(max_items, total_items)]:
                        headline = tag.get_text(strip=True)
                        if not headline or len(headline) < 10:  # Skip empty or too-short headlines
                            continue
                        if headline_exists(headline):
                            skip_count += 1
                            continue
                        new_headlines.append(headline)
                        fetched += 1
                        if fetched >= 10:
                            break
                    
                    total_checked = fetched + skip_count
                    logging.info(f"Run {run_counter}: Fetched {fetched} new headlines from {url} via scraping (skipped {skip_count} duplicates, checked {total_checked}/{total_items} items)")
                    
                    if fetched == 0 and total_checked >= total_items:
                        logging.warning(f"Run {run_counter}: No new headlines from {url}, exhausted {total_items} items")
                    elif fetched == 0 and total_checked >= max_items:
                        logging.warning(f"Run {run_counter}: No new headlines from {url} after checking {max_items} items")
                    
                    break
                except Exception as e:
                    logging.error(f"Run {run_counter}: Scraping attempt {attempt + 1} failed for {url}: {e}")
                    time.sleep(random.uniform(5, 10))
                    if attempt == 2:
                        logging.error(f"Run {run_counter}: All scraping attempts failed for {url}")

        if new_headlines:
            new_saved = save_headlines(new_headlines, url, run_counter)
            total_new += new_saved
            logging.info(f"Run {run_counter}: Saved {new_saved} new headlines from {url} to {DB_PATH}")

    if total_new == 0:
        logging.info(f"Run {run_counter}: No new headlines saved across all sources")
    else:
        logging.info(f"Run {run_counter}: Total saved {total_new} new headlines to {DB_PATH}")

def get_unused_headlines(limit=50):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT headline FROM headlines WHERE posted = 0 ORDER BY timestamp DESC LIMIT ?", (limit,))
    headlines = [row[0] for row in c.fetchall()]
    conn.close()
    return headlines

def mark_headline_posted(headline):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE headlines SET posted = 1 WHERE headline = ?", (headline,))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    logging.info("Starting headline fetcher in standalone mode...")
    init_db()
    test_settings = {
        'content_sources': ["https://www.morgenpost.de/feed.rss", "https://www.visitberlin.de/en/whats-on-berlin"]
    }
    fetch_and_save_headlines(test_settings)