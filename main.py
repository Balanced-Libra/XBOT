import time
import logging
import sys
import os
from datetime import datetime
from modules.xlogin_core import get_logged_in_driver
from modules.headline_fetcher import fetch_and_save_headlines
from modules.posting import post_tweet
from modules.follow import follow_accounts
from modules.like_posts import like_posts
from modules.comment import comment_on_posts

# Custom logging formatter
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
        
        # Custom message replacements for readability
        msg = record.msg
        if "DevTools listening on ws://" in msg:
            return self.BLUE + f"{record.asctime} [I] Browser debugging started" + self.RESET
        elif "Created TensorFlow Lite XNNPACK delegate for CPU" in msg:
            return self.BLUE + f"{record.asctime} [I] Optimized browser processing enabled" + self.RESET
        elif "HTTP Request: POST https://api.openai.com/v1/chat/completions" in msg:
            return self.BLUE + f"{record.asctime} [I] ChatGPT responded successfully" + self.RESET
        elif "privacy-sandbox-attestations.dat" in msg:
            return ""  # Suppress Chrome cleanup errors
        
        return formatter.format(record)

# Logging filter to suppress unwanted noise
class NoiseFilter(logging.Filter):
    def filter(self, record):
        msg = record.msg
        if "Attempting to use a delegate that only supports static-sized tensors" in msg:
            return False
        if "privacy-sandbox-attestations.dat" in msg:
            return False
        return True

# Logging setup
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
log_filename = os.path.join(LOG_DIR, f"bot_log_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt")

# Create logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Clear any existing handlers to avoid duplicates
logger.handlers.clear()

# Ensure console uses UTF-8 encoding
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:  # For older Python versions or if reconfigure fails
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(ConciseFormatter())
console_handler.addFilter(NoiseFilter())
logger.addHandler(console_handler)

file_handler = logging.FileHandler(log_filename, encoding='utf-8')  # Ensure file uses UTF-8 too
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
file_handler.addFilter(NoiseFilter())
logger.addHandler(file_handler)

logger.setLevel(logging.INFO)

def main():
    while True:  # Outer loop for restarting the bot or returning to login view
        logging.info("Bot started")
        result = get_logged_in_driver()
        if result is None:  # Shutdown requested
            logging.info("Shutting down bot gracefully")
            sys.exit(0)  # Exit immediately, no loop continuation
        elif result is False:  # Logout requested
            logging.info("Logged out, returning to login view")
            continue  # Loop back to login view

        driver = result["driver"]
        settings = result["settings"]
        logging.info("Bot running")  # Removed settings from this log

        run_count = 0
        try:
            while run_count < settings['loop_count']:
                try:
                    if settings.get('research_enabled', True):
                        fetch_and_save_headlines(settings)
                    else:
                        logging.info("Research disabled, skipping headline fetch")
                    if settings['post_enabled']:
                        post_tweet(driver, settings)
                    if settings['follow_enabled']:
                        follow_accounts(driver, settings)
                    if settings['like_enabled']:
                        like_posts(driver, settings)
                    if settings['comment_enabled']:
                        comment_on_posts(driver, settings)
                    run_count += 1
                    logging.info(f"Run {run_count}/{settings['loop_count']} complete.")
                    if run_count < settings['loop_count']:
                        logging.info(f"Pausing for {settings['schedule_interval']} minutes before next run...")
                        time.sleep(settings['schedule_interval'] * 60)
                except Exception as e:
                    logging.error(f"Loop iteration crashed: {e}")
                    if "connection" in str(e).lower():
                        logging.info("Restarting driver due to connection error...")
                        driver.quit()
                        result = get_logged_in_driver()
                        if result is None:  # Shutdown during recovery
                            logging.info("Shutting down bot gracefully")
                            sys.exit(0)  # Exit immediately
                        elif result is False:  # Logout during recovery
                            logging.info("Logged out during recovery, returning to login view")
                            break  # Break inner loop to return to login view
                        driver = result["driver"]
                        settings = result["settings"]
                    time.sleep(10)

            logging.info(f"Completed {settings['loop_count']} run(s). Closing browser and restarting interface...")
            driver.quit()

        except Exception as e:
            logging.error(f"Main loop crashed unexpectedly: {e}")
            driver.quit()  # Always quit driver on crash
            time.sleep(10)
            # After crash, loop back to login view instead of exiting

if __name__ == "__main__":
    main()