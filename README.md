# 🤖 Twitter Automation Bot — Smart, Stylish & AI-Powered

Welcome to your new favorite social media assistant!  
This bot isn't just a script — it’s a full-blown AI-powered automation system designed to **grow your presence**, **engage your audience**, and **save you hours** every week.

Whether you're a creator, brand, or just someone who wants to stay relevant without living on Twitter — this bot’s got your back. 💪

---

## 🚀 What It Does

This bot automates every essential Twitter task — powered by your settings, and infused with your **unique voice** through personality-based AI generation.

### ✍️ Smart Tweeting
- Writes tweets with **GPT-3.5-turbo** or **Gemini 1.5 Flash**
- Mix of **AI self-updates** & **research-based content**
- Pulls from **RSS feeds** or website headlines
- Custom hashtags, tone, emoji, language detection — all adjustable!

### 🤝 Auto-Following
- Follows accounts based on keywords or personality themes (e.g. `"Berlin"` for local vibes 🇩🇪)
- Avoids repeats and tracks activity in a built-in database

### ❤️ Liking & 💬 Commenting
- Finds tweets matching your vibe
- Likes & comments automatically with **AI-generated replies** (in the tweet’s language if needed!)
- Keeps engagement natural and consistent

### 🧠 Fully Configurable Personality
- Define your tone, favorite phrases, emojis, posting style, and even tweet timing
- Save multiple **personality presets** for different campaigns or moods

### 📅 Schedules & Loops
- Set specific posting times or run in smart loops (e.g. every hour)
- All actions respect daily limits and avoid duplicates

### 🛠️ Interface & Control
- Easy-to-use GUI for login, API setup, and all settings
- Designed for non-techies and devs alike 😄

---

## 🖼️ Screenshots

> - Login screen
> - ![Screenshot 2025-04-21 144232](https://github.com/user-attachments/assets/591fb9f7-606e-4460-942c-d9fb38113a09)

> - Settings panel (personality config)  
> - Console output with color-coded logs  

---

## 📦 How to Use (Coming Soon)

This project is currently in **active development** — once finalized, you'll be able to:
- 🔧 Run it locally with a simple setup  
- ☁️ Deploy it in the cloud (Replit, Docker, or your own server)  
- 🛒 License it for your business or personal brand  

Stay tuned — or [contact me](#) if you're interested in early access, collaboration, or white-label versions!

---

## 🧰 Tech Stack & Dependencies

- **Python** (Selenium, Tkinter, SQLite, Requests, BeautifulSoup, Feedparser)
- **OpenAI API** or **Gemini API** for tweet/comment generation
- **ChromeDriver** for browser automation
- **SQLite** for persistent memory (tweets, follows, likes, comments, headlines)

To install dependencies:
```bash
pip install selenium requests beautifulsoup4 feedparser openai google-generativeai pyperclip langdetect
```

> ⚠️ Requires matching `chromedriver` version for your browser. Place it in `drivers/chromedriver.exe`.

---

## 📁 Project Structure

```bash
TwitterBot/
├── main.py                  # Master script — runs all actions
├── modules/                 # All bot features (post, follow, like, comment)
├── logs/                    # Color-coded runtime logs
├── Database/                # SQLite memory (tweets, follows, etc.)
├── drivers/                 # ChromeDriver goes here
```

---

## 🌱 Status

✅ Features mostly implemented  
🧪 Still being refined and tested  
📤 Deployment options in progress  
💬 Open to feedback, collabs & testers!

---

## 💌 Contact

Want a custom version? Interested in licensing?  
Let’s talk — email me at `guyjamesjulius@gmail.com`

---

## ⭐ Support This Project

If you like what you see, consider starring 🌟 the repo or sharing it!  
This project is a labor of love — feedback and encouragement are always welcome.
