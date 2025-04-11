import tkinter as tk
from tkinter import ttk, messagebox
from .xlogin_setup_gui import shutdown_flag, logging
from .xlogin_settings_utils import submit_settings, add_posting_time, update_posting_times_display, remove_posting_time
from .xlogin_db import load_personality, get_all_personality_presets, save_personality, delete_personality, load_api_keys, save_api_key, delete_api_key, save_credentials

# Tooltip-Klasse
class Tooltip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event):
        if self.tooltip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify="left", background="#ffffe0", relief="solid", borderwidth=1, font=("Arial", 8))
        label.pack()

    def hide_tooltip(self, event):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None

def get_settings_from_gui(loaded_credentials=None):
    global shutdown_flag
    credentials = loaded_credentials.copy() if loaded_credentials else {}
    personality_settings = {}
    save_credentials_name = None

    root = tk.Tk()
    root.title("Twitter Bot Settings")
    root.geometry("480x715")
    root.resizable(True, True)
    root.configure(bg="#2b2b2b")

    style = ttk.Style()
    style.theme_use('clam')
    style.configure("TNotebook", background="#2b2b2b", borderwidth=0)
    style.configure("TNotebook.Tab", background="#3c3c3c", foreground="#ffffff", padding=[10, 5])
    style.map("TNotebook.Tab", background=[("selected", "#4a4a4a")])

    main_frame = tk.Frame(root, bg="#2b2b2b")
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    notebook = ttk.Notebook(main_frame)
    notebook.pack(pady=10, fill="both", expand=True)

    class ToggleSwitch(tk.Canvas):
        def __init__(self, parent, variable, text, **kwargs):
            super().__init__(parent, width=60, height=24, bg="#2b2b2b", highlightthickness=0, **kwargs)
            self.var = variable
            self.text = text
            self.on_color = "#00cc00"
            self.off_color = "#666666"
            self.circle_color = "#ffffff"
            self.state = self.var.get()
            self.draw()
            self.bind("<Button-1>", self.toggle)
            self.var.trace("w", self.update_state)
            tk.Label(parent, text=self.text, bg="#2b2b2b", fg="#ffffff").pack(side="left", padx=(0, 10))

        def draw(self):
            self.delete("all")
            bg_color = self.on_color if self.state else self.off_color
            self.create_rounded_rect(2, 2, 58, 22, radius=10, fill=bg_color, outline="")
            x_pos = 38 if self.state else 18
            self.create_oval(x_pos-8, 4, x_pos+8, 20, fill=self.circle_color, outline="")

        def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
            self.create_arc(x1, y1, x1 + 2*radius, y1 + 2*radius, start=90, extent=90, style=tk.PIESLICE, **kwargs)
            self.create_arc(x2 - 2*radius, y1, x2, y1 + 2*radius, start=0, extent=90, style=tk.PIESLICE, **kwargs)
            self.create_arc(x1, y2 - 2*radius, x1 + 2*radius, y2, start=180, extent=90, style=tk.PIESLICE, **kwargs)
            self.create_arc(x2 - 2*radius, y2 - 2*radius, x2, y2, start=270, extent=90, style=tk.PIESLICE, **kwargs)
            self.create_rectangle(x1 + radius, y1, x2 - radius, y2, **kwargs)
            self.create_rectangle(x1, y1 + radius, x2, y2 - radius, **kwargs)

        def toggle(self, event):
            self.state = not self.state
            self.var.set(self.state)
            self.draw()

        def update_state(self, *args):
            self.state = self.var.get()
            self.draw()

    # Credentials Tab
    cred_frame = ttk.Frame(notebook)
    notebook.add(cred_frame, text="Credentials")
    tk.Label(cred_frame, text="Twitter Credentials", font=("Arial", 12, "bold"), bg="#2b2b2b", fg="#ffffff").pack(pady=10)
    tk.Label(cred_frame, text="Username:", bg="#2b2b2b", fg="#ffffff").pack()
    username_entry = tk.Entry(cred_frame, width=40, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
    username_entry.insert(0, credentials.get('username', ''))
    username_entry.pack(pady=5)
    Tooltip(username_entry, "Your Twitter username for login.")
    tk.Label(cred_frame, text="Password:", bg="#2b2b2b", fg="#ffffff").pack()
    password_entry = tk.Entry(cred_frame, width=40, show="*", bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
    password_entry.insert(0, credentials.get('password', ''))
    password_entry.pack(pady=5)
    Tooltip(password_entry, "Your Twitter password for login.")
    tk.Label(cred_frame, text="Email:", bg="#2b2b2b", fg="#ffffff").pack()
    email_entry = tk.Entry(cred_frame, width=40, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
    email_entry.insert(0, credentials.get('email', ''))
    email_entry.pack(pady=5)
    Tooltip(email_entry, "Your email associated with the Twitter account.")

    # API Key Management
    tk.Label(cred_frame, text="API Keys:", font=("Arial", 10, "bold"), bg="#2b2b2b", fg="#ffffff").pack(pady=5)
    api_keys = load_api_keys(credentials.get('username', ''))
    api_key_options = [key["custom_name"] for key in api_keys] if api_keys else ["No API keys saved"]
    selected_api_key_var = tk.StringVar(value=api_key_options[0] if api_key_options else "No API keys saved")
    api_key_menu = ttk.Combobox(cred_frame, textvariable=selected_api_key_var, values=api_key_options, state="readonly")
    api_key_menu.pack(pady=5)
    Tooltip(api_key_menu, "Select an API key to use for content generation.")

    api_key_frame = tk.Frame(cred_frame, bg="#2b2b2b")
    api_key_frame.pack(pady=5)

    def add_api_key():
        add_window = tk.Toplevel(root)
        add_window.title("Add API Key")
        add_window.geometry("350x250")
        add_window.configure(bg="#2b2b2b")

        tk.Label(add_window, text="Add New API Key", font=("Arial", 12, "bold"), bg="#2b2b2b", fg="#ffffff").pack(pady=10)
        tk.Label(add_window, text="Custom Name:", bg="#2b2b2b", fg="#ffffff").pack()
        custom_name_entry = tk.Entry(add_window, width=40, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
        custom_name_entry.pack(pady=5)
        tk.Label(add_window, text="API Type:", bg="#2b2b2b", fg="#ffffff").pack()
        api_type_var = tk.StringVar(value="openai")
        ttk.Combobox(add_window, textvariable=api_type_var, values=["openai", "gemini"], state="readonly").pack(pady=5)
        tk.Label(add_window, text="API Key:", bg="#2b2b2b", fg="#ffffff").pack()
        api_key_entry = tk.Entry(add_window, width=40, show="*", bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
        api_key_entry.pack(pady=5)

        def save_new_api_key():
            custom_name = custom_name_entry.get().strip()
            api_type = api_type_var.get()
            api_key = api_key_entry.get().strip()
            if not all([custom_name, api_key]):
                messagebox.showerror("Error", "Custom name and API key are required!")
                return
            if custom_name in [key["custom_name"] for key in load_api_keys(credentials.get('username', ''))]:
                messagebox.showerror("Error", f"API key name '{custom_name}' already exists!")
                return
            save_api_key(credentials.get('username', ''), custom_name, api_type, api_key)
            updated_keys = load_api_keys(credentials.get('username', ''))
            api_key_menu['values'] = [key["custom_name"] for key in updated_keys]
            selected_api_key_var.set(custom_name)
            add_window.destroy()
            messagebox.showinfo("Success", f"API key '{custom_name}' added!")

        tk.Button(add_window, text="Save", command=save_new_api_key, bg="#4a4a4a", fg="#ffffff").pack(pady=10)
        add_window.wait_window()

    def delete_api_key():
        selected_name = selected_api_key_var.get()
        if selected_name and selected_name != "No API keys saved":
            if messagebox.askyesno("Confirm Delete", f"Delete API key '{selected_name}'?"):
                delete_api_key(credentials.get('username', ''), selected_name)
                updated_keys = load_api_keys(credentials.get('username', ''))
                api_key_options = [key["custom_name"] for key in updated_keys] if updated_keys else ["No API keys saved"]
                api_key_menu['values'] = api_key_options
                selected_api_key_var.set(api_key_options[0] if api_key_options else "No API keys saved")
                messagebox.showinfo("Success", f"API key '{selected_name}' deleted!")

    tk.Button(api_key_frame, text="+ Add API Key", command=add_api_key, bg="#4a4a4a", fg="#ffffff").pack(side="left", padx=5)
    tk.Button(api_key_frame, text="Delete Selected", command=delete_api_key, bg="#ff4a4a", fg="#ffffff").pack(side="left", padx=5)

    # Personality Tab
    personality_frame = ttk.Frame(notebook)
    notebook.add(personality_frame, text="Personality")
    tk.Label(personality_frame, text="Select Personality Preset:", bg="#2b2b2b", fg="#ffffff").pack(pady=5)
    preset_var = tk.StringVar()
    presets = get_all_personality_presets()
    preset_menu = ttk.Combobox(personality_frame, textvariable=preset_var, values=presets, state="readonly" if presets else "disabled")
    preset_menu.pack(pady=5)
    Tooltip(preset_menu, "Load a saved personality preset for the bot.")
    preset_button_frame = tk.Frame(personality_frame, bg="#2b2b2b")
    preset_button_frame.pack(pady=5)

    # Define language_var and autodetect_var early so they are available for all functions
    language_var = tk.StringVar(value=personality_settings.get('language', 'English'))
    autodetect_var = tk.BooleanVar(value=personality_settings.get('autodetect_language', False))
    tk.Button(preset_button_frame, text="Load Preset", command=lambda: load_preset(preset_var, personality_settings, personality_entry, tone_entry, phrases_entry, topics_entry, keywords_entry, sources_entry, hashtags_entry, ratio_scale, post_var, follow_var, like_var, comment_var, post_limit_entry, follow_limit_entry, like_limit_entry, comment_limit_entry, loop_count_entry, schedule_entry, emoji_var, emojis_entry, emoji_scale, research_var, headless_var, posting_times_list, posting_times_frame, language_var, autodetect_var), bg="#4a4a4a", fg="#ffffff").pack(side="left", padx=5)
    tk.Button(preset_button_frame, text="Save Preset", command=lambda: save_preset(root, preset_var, personality_settings, preset_menu, personality_entry, tone_entry, phrases_entry, topics_entry, keywords_entry, sources_entry, hashtags_entry, ratio_scale, post_var, follow_var, like_var, comment_var, post_limit_entry, follow_limit_entry, like_limit_entry, comment_limit_entry, loop_count_entry, schedule_entry, emoji_var, emojis_entry, emoji_scale, research_var, headless_var, posting_times_list, language_var, autodetect_var), bg="#4a4a4a", fg="#ffffff").pack(side="left", padx=5)
    tk.Button(preset_button_frame, text="Delete Preset", command=lambda: delete_preset(preset_var, personality_settings, preset_menu), bg="#ff4a4a", fg="#ffffff").pack(side="left", padx=5)
    tk.Label(personality_frame, text="Personality Description:", font=("Arial", 10, "bold"), bg="#2b2b2b", fg="#ffffff").pack(pady=5)
    personality_entry = tk.Text(personality_frame, height=3, width=40, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
    personality_entry.insert(tk.END, personality_settings.get('personality_description', "A neutral AI sharing updates."))
    personality_entry.pack(pady=5)
    Tooltip(personality_entry, "Describe the bot's personality (e.g., 'A witty tech enthusiast').")
    tk.Label(personality_frame, text="Tone Keywords:", font=("Arial", 10, "bold"), bg="#2b2b2b", fg="#ffffff").pack(pady=5)
    tone_entry = tk.Text(personality_frame, height=2, width=40, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
    tone_entry.insert(tk.END, ", ".join(personality_settings.get('tone_keywords', ["casual", "friendly"])))
    tone_entry.pack(pady=5)
    Tooltip(tone_entry, "Keywords defining the tone of tweets/comments (e.g., 'funny, formal').")
    tk.Label(personality_frame, text="Custom Phrases:", font=("Arial", 10, "bold"), bg="#2b2b2b", fg="#ffffff").pack(pady=5)
    phrases_entry = tk.Text(personality_frame, height=2, width=40, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
    phrases_entry.insert(tk.END, ", ".join(personality_settings.get('custom_phrases', ["Check this out!", "Cool stuff!"])))
    phrases_entry.pack(pady=5)
    Tooltip(phrases_entry, "Phrases the bot can randomly use in tweets/comments.")
    tk.Label(personality_frame, text="Self-Update Topics:", font=("Arial", 10, "bold"), bg="#2b2b2b", fg="#ffffff").pack(pady=5)
    topics_entry = tk.Text(personality_frame, height=2, width=40, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
    topics_entry.insert(tk.END, ", ".join(personality_settings.get('self_update_topics', ["daily life", "interests"])))
    topics_entry.pack(pady=5)
    Tooltip(topics_entry, "Topics for self-update tweets (e.g., 'tech, hobbies').")

    # Content Tab
    content_frame = ttk.Frame(notebook)
    notebook.add(content_frame, text="Content")
    tk.Label(content_frame, text="Content Settings", font=("Arial", 12, "bold"), bg="#2b2b2b", fg="#ffffff").pack(pady=10)
    tk.Label(content_frame, text="Search Keywords:", bg="#2b2b2b", fg="#ffffff").pack()
    keywords_entry = tk.Text(content_frame, height=2, width=40, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
    keywords_entry.insert(tk.END, ", ".join(personality_settings.get('search_keywords', ["news", "tech"])))
    keywords_entry.pack(pady=5)
    Tooltip(keywords_entry, "Keywords to search for posts to like, follow, or comment on.")
    tk.Label(content_frame, text="Content Sources:", bg="#2b2b2b", fg="#ffffff").pack()
    sources_entry = tk.Text(content_frame, height=2, width=40, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
    sources_entry.insert(tk.END, ", ".join(personality_settings.get('content_sources', ["https://example.com/rss"])))
    sources_entry.pack(pady=5)
    Tooltip(sources_entry, "RSS or web URLs to fetch headlines for tweets.")
    tk.Label(content_frame, text="Hashtags:", bg="#2b2b2b", fg="#ffffff").pack()
    hashtags_entry = tk.Text(content_frame, height=2, width=40, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
    hashtags_entry.insert(tk.END, ", ".join(personality_settings.get('hashtags', ["#AI", "#Tech"])))
    hashtags_entry.pack(pady=5)
    Tooltip(hashtags_entry, "Hashtags to include in tweets.")
    tk.Label(content_frame, text="Tweet Type Ratio (Research vs Self-Update):", bg="#2b2b2b", fg="#ffffff").pack()
    ratio_scale = tk.Scale(content_frame, from_=0, to=100, orient=tk.HORIZONTAL, bg="#2b2b2b", fg="#ffffff", troughcolor="#3c3c3c", highlightthickness=0)
    ratio_scale.set(personality_settings.get('tweet_type_ratio', 50))
    ratio_scale.pack(pady=5)
    Tooltip(ratio_scale, "Balance between research-based (headlines) and self-update tweets (0 = all self-update, 100 = all research).")

    # Actions & Limits Tab
    actions_frame = ttk.Frame(notebook)
    notebook.add(actions_frame, text="Actions & Limits")
    tk.Label(actions_frame, text="Bot Actions", font=("Arial", 12, "bold"), bg="#2b2b2b", fg="#ffffff").pack(pady=10)

    post_frame = tk.Frame(actions_frame, bg="#2b2b2b")
    post_frame.pack(fill="x", pady=5)
    post_var = tk.BooleanVar(value=personality_settings.get('post_enabled', True))
    post_switch = ToggleSwitch(post_frame, post_var, "Enable Posting")
    post_switch.pack(side="left", anchor="w", padx=(0, 10))
    Tooltip(post_switch, "Enable or disable posting tweets.")
    post_limit_frame = tk.Frame(post_frame, bg="#2b2b2b")
    post_limit_frame.pack(side="right", padx=10)
    tk.Label(post_limit_frame, text="Post Limit:", bg="#2b2b2b", fg="#ffffff").pack(side="left", padx=5)
    post_limit_entry = tk.Entry(post_limit_frame, width=10, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
    post_limit_entry.insert(0, personality_settings.get('daily_post_limit', 5))
    post_limit_entry.pack(side="left")
    Tooltip(post_limit_entry, "Daily limit for posts (0 = unlimited).")
    post_limit_entry.config(state="normal" if post_var.get() else "disabled")
    post_var.trace("w", lambda *args: post_limit_entry.config(state="normal" if post_var.get() else "disabled"))

    follow_frame = tk.Frame(actions_frame, bg="#2b2b2b")
    follow_frame.pack(fill="x", pady=5)
    follow_var = tk.BooleanVar(value=personality_settings.get('follow_enabled', True))
    follow_switch = ToggleSwitch(follow_frame, follow_var, "Enable Following")
    follow_switch.pack(side="left", anchor="w", padx=(0, 10))
    Tooltip(follow_switch, "Enable or disable following accounts.")
    follow_limit_frame = tk.Frame(follow_frame, bg="#2b2b2b")
    follow_limit_frame.pack(side="right", padx=10)
    tk.Label(follow_limit_frame, text="Follow Limit:", bg="#2b2b2b", fg="#ffffff").pack(side="left", padx=5)
    follow_limit_entry = tk.Entry(follow_limit_frame, width=10, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
    follow_limit_entry.insert(0, personality_settings.get('daily_follow_limit', 10))
    follow_limit_entry.pack(side="left")
    Tooltip(follow_limit_entry, "Daily limit for following accounts (0 = unlimited).")
    follow_limit_entry.config(state="normal" if follow_var.get() else "disabled")
    follow_var.trace("w", lambda *args: follow_limit_entry.config(state="normal" if follow_var.get() else "disabled"))

    like_frame = tk.Frame(actions_frame, bg="#2b2b2b")
    like_frame.pack(fill="x", pady=5)
    like_var = tk.BooleanVar(value=personality_settings.get('like_enabled', True))
    like_switch = ToggleSwitch(like_frame, like_var, "Enable Liking")
    like_switch.pack(side="left", anchor="w", padx=(0, 10))
    Tooltip(like_switch, "Enable or disable liking posts.")
    like_limit_frame = tk.Frame(like_frame, bg="#2b2b2b")
    like_limit_frame.pack(side="right", padx=10)
    tk.Label(like_limit_frame, text="Like Limit:", bg="#2b2b2b", fg="#ffffff").pack(side="left", padx=5)
    like_limit_entry = tk.Entry(like_limit_frame, width=10, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
    like_limit_entry.insert(0, personality_settings.get('daily_like_limit', 20))
    like_limit_entry.pack(side="left")
    Tooltip(like_limit_entry, "Daily limit for liking posts (0 = unlimited).")
    like_limit_entry.config(state="normal" if like_var.get() else "disabled")
    like_var.trace("w", lambda *args: like_limit_entry.config(state="normal" if like_var.get() else "disabled"))

    comment_frame = tk.Frame(actions_frame, bg="#2b2b2b")
    comment_frame.pack(fill="x", pady=5)
    comment_var = tk.BooleanVar(value=personality_settings.get('comment_enabled', True))
    comment_switch = ToggleSwitch(comment_frame, comment_var, "Enable Commenting")
    comment_switch.pack(side="left", anchor="w", padx=(0, 10))
    Tooltip(comment_switch, "Enable or disable commenting on posts.")
    comment_limit_frame = tk.Frame(comment_frame, bg="#2b2b2b")
    comment_limit_frame.pack(side="right", padx=10)
    tk.Label(comment_limit_frame, text="Comment Limit:", bg="#2b2b2b", fg="#ffffff").pack(side="left", padx=5)
    comment_limit_entry = tk.Entry(comment_limit_frame, width=10, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
    comment_limit_entry.insert(0, personality_settings.get('daily_comment_limit', 10))
    comment_limit_entry.pack(side="left")
    Tooltip(comment_limit_entry, "Daily limit for comments (0 = unlimited).")
    comment_limit_entry.config(state="normal" if comment_var.get() else "disabled")
    comment_var.trace("w", lambda *args: comment_limit_entry.config(state="normal" if comment_var.get() else "disabled"))

    tk.Label(actions_frame, text="Number of Loops:", bg="#2b2b2b", fg="#ffffff").pack(pady=5)
    loop_count_entry = tk.Entry(actions_frame, width=10, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
    loop_count_entry.insert(0, personality_settings.get('loop_count', 5))
    loop_count_entry.pack(pady=2)
    Tooltip(loop_count_entry, "Number of times the bot runs all actions before restarting.")
    tk.Label(actions_frame, text="Schedule Interval (minutes):", bg="#2b2b2b", fg="#ffffff").pack(pady=5)
    schedule_entry = tk.Entry(actions_frame, width=10, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
    schedule_entry.insert(0, personality_settings.get('schedule_interval', 60))
    schedule_entry.pack(pady=2)
    Tooltip(schedule_entry, "Time in minutes between each loop run.")

    # Style & Behavior Tab
    style_frame = ttk.Frame(notebook)
    notebook.add(style_frame, text="Style & Behavior")
    tk.Label(style_frame, text="Style Settings", font=("Arial", 12, "bold"), bg="#2b2b2b", fg="#ffffff").pack(pady=10)

    toggle_frame = tk.Frame(style_frame, bg="#2b2b2b")
    toggle_frame.pack(fill="x", pady=5)
    emoji_var = tk.BooleanVar(value=personality_settings.get('use_emojis', True))
    emoji_switch = ToggleSwitch(toggle_frame, emoji_var, "Use Emojis")
    emoji_switch.pack(side="left", anchor="w", padx=(0, 10), pady=5)
    Tooltip(emoji_switch, "Enable or disable emojis in tweets/comments.")
    tk.Frame(toggle_frame, bg="#2b2b2b", width=50).pack(side="left")
    research_var = tk.BooleanVar(value=personality_settings.get('research_enabled', True))
    research_switch = ToggleSwitch(toggle_frame, research_var, "Enable Research")
    research_switch.pack(side="left", anchor="w", padx=(0, 10), pady=5)
    Tooltip(research_switch, "Enable fetching headlines from content sources.")
    headless_frame = tk.Frame(style_frame, bg="#2b2b2b")
    headless_frame.pack(fill="x", pady=5)
    headless_var = tk.BooleanVar(value=personality_settings.get('headless_enabled', False))
    headless_switch = ToggleSwitch(headless_frame, headless_var, "Run Headless")
    headless_switch.pack(side="left", anchor="w", padx=(0, 10), pady=5)
    Tooltip(headless_switch, "Run the bot without a visible browser window.")

    tk.Label(style_frame, text="Bot Language:", bg="#2b2b2b", fg="#ffffff").pack(pady=(10, 0))
    language_options = ["English", "Spanish", "French", "German", "Italian", "Portuguese", "Dutch", "Russian", "Chinese", "Japanese"]
    language_menu = ttk.Combobox(style_frame, textvariable=language_var, values=language_options, state="readonly")
    language_menu.pack(pady=5)
    Tooltip(language_menu, "Select the language for the bot's tweets.")

    autodetect_frame = tk.Frame(style_frame, bg="#2b2b2b")
    autodetect_frame.pack(fill="x", pady=5)
    autodetect_switch = ToggleSwitch(autodetect_frame, autodetect_var, "Autodetect Comment Language")
    autodetect_switch.pack(side="left", anchor="w", padx=(0, 10), pady=5)
    Tooltip(autodetect_switch, "If enabled, comments will match the detected language of the post.")

    tk.Label(style_frame, text="Emoji List:", bg="#2b2b2b", fg="#ffffff").pack(pady=(10, 0))
    emojis_entry = tk.Text(style_frame, height=2, width=40, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
    emojis_entry.insert(tk.END, ", ".join(personality_settings.get('emoji_list', ["😊", "👍"])))
    emojis_entry.pack(pady=5)
    Tooltip(emojis_entry, "List of emojis the bot can use.")
    tk.Label(style_frame, text="Emoji Frequency (%):", bg="#2b2b2b", fg="#ffffff").pack()
    emoji_scale = tk.Scale(style_frame, from_=0, to=100, orient=tk.HORIZONTAL, bg="#2b2b2b", fg="#ffffff", troughcolor="#3c3c3c", highlightthickness=0)
    emoji_scale.set(personality_settings.get('emoji_frequency', 50))
    emoji_scale.pack(pady=5)
    Tooltip(emoji_scale, "Percentage chance of adding an emoji to tweets/comments.")

    tk.Label(style_frame, text="Posting Times (HH:MM):", bg="#2b2b2b", fg="#ffffff").pack(pady=(10, 0))
    posting_time_entry = tk.Entry(style_frame, width=10, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
    posting_time_entry.pack(pady=2)
    Tooltip(posting_time_entry, "Specific times (HH:MM) for posting tweets.")
    tk.Button(style_frame, text="Add Time", command=lambda: add_posting_time(posting_time_entry, posting_times_list, lambda lst: update_posting_times_display(lst, posting_times_frame, remove_posting_time)), bg="#4a4a4a", fg="#ffffff").pack(pady=2)
    posting_times_frame = tk.Frame(style_frame, bg="#2b2b2b")
    posting_times_frame.pack(fill="x", pady=5)
    posting_times_list = personality_settings.get('posting_times', [])
    update_posting_times_display(posting_times_list, posting_times_frame, remove_posting_time)

    # Buttons
    button_frame = tk.Frame(main_frame, bg="#2b2b2b")
    button_frame.pack(fill="x", pady=10)
    tk.Button(button_frame, text="Start Bot", command=lambda: submit_settings(credentials, personality_settings, save_credentials_name, root, loaded_credentials, None, username_entry, password_entry, email_entry, selected_api_key_var, api_key_menu, personality_entry, tone_entry, phrases_entry, topics_entry, keywords_entry, sources_entry, hashtags_entry, ratio_scale, post_var, follow_var, like_var, comment_var, post_limit_entry, follow_limit_entry, like_limit_entry, comment_limit_entry, loop_count_entry, schedule_entry, emoji_var, emojis_entry, emoji_scale, research_var, headless_var, posting_times_list, language_var, autodetect_var), bg="#4a4a4a", fg="#ffffff", font=("Arial", 10, "bold")).pack(side="left", padx=5, fill="x", expand=True)
    tk.Button(button_frame, text="Logout", command=lambda: shutdown(root), bg="#ff4a4a", fg="#ffffff", font=("Arial", 10, "bold")).pack(side="left", padx=5, fill="x", expand=True)

    root.mainloop()

    if shutdown_flag or not credentials:
        logging.info("Shutdown flag set or no credentials, returning None")
        return None, None, None
    logging.info("Returning settings from GUI")
    return credentials, personality_settings, save_credentials_name


def submit_settings(credentials, personality_settings, save_credentials_name, root, loaded_credentials, setup_name_entry, username_entry, password_entry, email_entry, selected_api_key_var, api_key_menu, personality_entry, tone_entry, phrases_entry, topics_entry, keywords_entry, sources_entry, hashtags_entry, ratio_scale, post_var, follow_var, like_var, comment_var, post_limit_entry, follow_limit_entry, like_limit_entry, comment_limit_entry, loop_count_entry, schedule_entry, emoji_var, emojis_entry, emoji_scale, research_var, headless_var, posting_times_list, language_var, autodetect_var):
    logging.info("submit_settings called")
    # Update credentials from GUI
    credentials['username'] = username_entry.get().strip()
    credentials['password'] = password_entry.get().strip()
    credentials['email'] = email_entry.get().strip()
    logging.info(f"Updated credentials: username={credentials['username']}, email={credentials['email']}")
    
    # Get selected API key details
    selected_name = selected_api_key_var.get()
    logging.info(f"Selected API key name: {selected_name}")
    if selected_name and selected_name != "No API keys saved":
        api_keys = load_api_keys(credentials['username'])
        selected_key = next((key for key in api_keys if key["custom_name"] == selected_name), None)
        if selected_key:
            credentials['api_type'] = selected_key["api_type"]
            credentials['api_key'] = selected_key["api_key"]
            logging.info(f"Set API: type={credentials['api_type']}, key={credentials['api_key'][:5]}...")  # Only log first 5 chars of key for security
        else:
            logging.error("Selected API key not found in database")
            messagebox.showerror("Error", "Selected API key not found!")
            return
    else:
        logging.warning("No valid API key selected")
        messagebox.showerror("Error", "Please select or add an API key!")
        return

    # Update personality settings
    personality_settings['language'] = language_var.get()
    personality_settings['autodetect_language'] = autodetect_var.get()
    personality_settings['personality_description'] = personality_entry.get("1.0", tk.END).strip()
    personality_settings['tone_keywords'] = [k.strip() for k in tone_entry.get("1.0", tk.END).strip().split(',') if k.strip()]
    personality_settings['custom_phrases'] = [p.strip() for p in phrases_entry.get("1.0", tk.END).strip().split(',') if p.strip()]
    personality_settings['self_update_topics'] = [t.strip() for t in topics_entry.get("1.0", tk.END).strip().split(',') if t.strip()]
    personality_settings['search_keywords'] = [k.strip() for k in keywords_entry.get("1.0", tk.END).strip().split(',') if k.strip()]
    personality_settings['content_sources'] = [s.strip() for s in sources_entry.get("1.0", tk.END).strip().split(',') if s.strip()]
    personality_settings['hashtags'] = [h.strip() for h in hashtags_entry.get("1.0", tk.END).strip().split(',') if h.strip()]
    personality_settings['tweet_type_ratio'] = ratio_scale.get()
    personality_settings['post_enabled'] = post_var.get()
    personality_settings['follow_enabled'] = follow_var.get()
    personality_settings['like_enabled'] = like_var.get()
    personality_settings['comment_enabled'] = comment_var.get()
    personality_settings['daily_post_limit'] = int(post_limit_entry.get() or 0)
    personality_settings['daily_follow_limit'] = int(follow_limit_entry.get() or 0)
    personality_settings['daily_like_limit'] = int(like_limit_entry.get() or 0)
    personality_settings['daily_comment_limit'] = int(comment_limit_entry.get() or 0)
    personality_settings['loop_count'] = int(loop_count_entry.get() or 0)
    personality_settings['schedule_interval'] = int(schedule_entry.get() or 0)
    personality_settings['use_emojis'] = emoji_var.get()
    personality_settings['emoji_list'] = [e.strip() for e in emojis_entry.get("1.0", tk.END).strip().split(',') if e.strip()]
    personality_settings['emoji_frequency'] = emoji_scale.get()
    personality_settings['research_enabled'] = research_var.get()
    personality_settings['headless_enabled'] = headless_var.get()
    personality_settings['posting_times'] = posting_times_list[:]
    logging.info("Personality settings updated")

    # Save credentials to database (only if they’ve changed)
    if loaded_credentials != credentials:
        save_credentials(credentials['username'], credentials)
        logging.info("Credentials saved to database")

    # Close the GUI
    root.destroy()
    logging.info("Settings submitted successfully")


def load_preset(preset_var, personality_settings, personality_entry, tone_entry, phrases_entry, topics_entry, keywords_entry, sources_entry, hashtags_entry, ratio_scale, post_var, follow_var, like_var, comment_var, post_limit_entry, follow_limit_entry, like_limit_entry, comment_limit_entry, loop_count_entry, schedule_entry, emoji_var, emojis_entry, emoji_scale, research_var, headless_var, posting_times_list, posting_times_frame, language_var, autodetect_var):
    preset_name = preset_var.get()
    if preset_name:
        loaded_settings = load_personality(preset_name)
        if loaded_settings:
            personality_settings.update(loaded_settings)
            personality_entry.delete("1.0", tk.END)
            personality_entry.insert(tk.END, personality_settings.get('personality_description', ''))
            tone_entry.delete("1.0", tk.END)
            tone_entry.insert(tk.END, ", ".join(personality_settings.get('tone_keywords', [])))
            phrases_entry.delete("1.0", tk.END)
            phrases_entry.insert(tk.END, ", ".join(personality_settings.get('custom_phrases', [])))
            topics_entry.delete("1.0", tk.END)
            topics_entry.insert(tk.END, ", ".join(personality_settings.get('self_update_topics', [])))
            keywords_entry.delete("1.0", tk.END)
            keywords_entry.insert(tk.END, ", ".join(personality_settings.get('search_keywords', [])))
            sources_entry.delete("1.0", tk.END)
            sources_entry.insert(tk.END, ", ".join(personality_settings.get('content_sources', [])))
            hashtags_entry.delete("1.0", tk.END)
            hashtags_entry.insert(tk.END, ", ".join(personality_settings.get('hashtags', [])))
            ratio_scale.set(personality_settings.get('tweet_type_ratio', 50))
            post_var.set(personality_settings.get('post_enabled', True))
            follow_var.set(personality_settings.get('follow_enabled', True))
            like_var.set(personality_settings.get('like_enabled', True))
            comment_var.set(personality_settings.get('comment_enabled', True))
            language_var.set(personality_settings.get('language', 'English'))
            autodetect_var.set(personality_settings.get('autodetect_language', False))
            post_limit_entry.delete(0, tk.END)
            post_limit_entry.insert(0, personality_settings.get('daily_post_limit', 5))
            follow_limit_entry.delete(0, tk.END)
            follow_limit_entry.insert(0, personality_settings.get('daily_follow_limit', 10))
            like_limit_entry.delete(0, tk.END)
            like_limit_entry.insert(0, personality_settings.get('daily_like_limit', 20))
            comment_limit_entry.delete(0, tk.END)
            comment_limit_entry.insert(0, personality_settings.get('daily_comment_limit', 10))
            loop_count_entry.delete(0, tk.END)
            loop_count_entry.insert(0, personality_settings.get('loop_count', 5))
            schedule_entry.delete(0, tk.END)
            schedule_entry.insert(0, personality_settings.get('schedule_interval', 60))
            emoji_var.set(personality_settings.get('use_emojis', True))
            emojis_entry.delete("1.0", tk.END)
            emojis_entry.insert(tk.END, ", ".join(personality_settings.get('emoji_list', [])))
            emoji_scale.set(personality_settings.get('emoji_frequency', 50))
            research_var.set(personality_settings.get('research_enabled', True))
            headless_var.set(personality_settings.get('headless_enabled', False))
            posting_times_list.clear()
            posting_times_list.extend(personality_settings.get('posting_times', []))
            update_posting_times_display(posting_times_list, posting_times_frame, remove_posting_time)
            logging.info(f"Loaded personality preset '{preset_name}'")
            messagebox.showinfo("Success", f"Loaded preset '{preset_name}'")

def save_preset(root, preset_var, personality_settings, preset_menu, personality_entry, tone_entry, phrases_entry, topics_entry, keywords_entry, sources_entry, hashtags_entry, ratio_scale, post_var, follow_var, like_var, comment_var, post_limit_entry, follow_limit_entry, like_limit_entry, comment_limit_entry, loop_count_entry, schedule_entry, emoji_var, emojis_entry, emoji_scale, research_var, headless_var, posting_times_list, language_var, autodetect_var):
    preset_window = tk.Toplevel(root)
    preset_window.title("Save Personality Preset")
    preset_window.geometry("350x200")
    preset_window.configure(bg="#2b2b2b")

    tk.Label(preset_window, text="Save as new preset or overwrite existing:", bg="#2b2b2b", fg="#ffffff").pack(pady=5)

    tk.Label(preset_window, text="New Preset Name:", bg="#2b2b2b", fg="#ffffff").pack(pady=5)
    preset_name_entry = tk.Entry(preset_window, width=40, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
    preset_name_entry.pack(pady=5)

    tk.Label(preset_window, text="Or Overwrite Existing (leave blank for none):", bg="#2b2b2b", fg="#ffffff").pack(pady=5)
    overwrite_var = tk.StringVar()
    existing_presets = get_all_personality_presets()
    # Add empty string as the first option to allow deselection
    overwrite_menu_options = [''] + existing_presets
    overwrite_menu = ttk.Combobox(preset_window, textvariable=overwrite_var, values=overwrite_menu_options, state="readonly" if existing_presets else "disabled")
    overwrite_menu.pack(pady=5)
    if preset_var.get():
        overwrite_var.set(preset_var.get())  # Preselect current preset if one is selected
    else:
        overwrite_var.set('')  # Default to no selection if no preset is currently selected

    def save_action():
        new_name = preset_name_entry.get().strip()
        overwrite_name = overwrite_var.get()
        personality_settings['language'] = language_var.get()
        personality_settings['autodetect_language'] = autodetect_var.get()
        personality_settings['personality_description'] = personality_entry.get("1.0", tk.END).strip()
        personality_settings['tone_keywords'] = [k.strip() for k in tone_entry.get("1.0", tk.END).strip().split(',') if k.strip()]
        personality_settings['custom_phrases'] = [p.strip() for p in phrases_entry.get("1.0", tk.END).strip().split(',') if p.strip()]
        personality_settings['self_update_topics'] = [t.strip() for t in topics_entry.get("1.0", tk.END).strip().split(',') if t.strip()]
        personality_settings['search_keywords'] = [k.strip() for k in keywords_entry.get("1.0", tk.END).strip().split(',') if k.strip()]
        personality_settings['content_sources'] = [s.strip() for s in sources_entry.get("1.0", tk.END).strip().split(',') if s.strip()]
        personality_settings['hashtags'] = [h.strip() for h in hashtags_entry.get("1.0", tk.END).strip().split(',') if h.strip()]
        personality_settings['tweet_type_ratio'] = ratio_scale.get()
        personality_settings['post_enabled'] = post_var.get()
        personality_settings['follow_enabled'] = follow_var.get()
        personality_settings['like_enabled'] = like_var.get()
        personality_settings['comment_enabled'] = comment_var.get()
        personality_settings['daily_post_limit'] = int(post_limit_entry.get() or 0)
        personality_settings['daily_follow_limit'] = int(follow_limit_entry.get() or 0)
        personality_settings['daily_like_limit'] = int(like_limit_entry.get() or 0)
        personality_settings['daily_comment_limit'] = int(comment_limit_entry.get() or 0)
        personality_settings['loop_count'] = int(loop_count_entry.get() or 0)
        personality_settings['schedule_interval'] = int(schedule_entry.get() or 0)
        personality_settings['use_emojis'] = emoji_var.get()
        personality_settings['emoji_list'] = [e.strip() for e in emojis_entry.get("1.0", tk.END).strip().split(',') if e.strip()]
        personality_settings['emoji_frequency'] = emoji_scale.get()
        personality_settings['research_enabled'] = research_var.get()
        personality_settings['headless_enabled'] = headless_var.get()
        personality_settings['posting_times'] = posting_times_list[:]

        if new_name and overwrite_name:
            messagebox.showerror("Error", "Please choose either a new name or an existing preset to overwrite, not both!")
            return
        elif not new_name and not overwrite_name:
            messagebox.showerror("Error", "Please provide a new name or select a preset to overwrite!")
            return
        elif new_name:
            if new_name in existing_presets:
                messagebox.showerror("Error", f"Preset '{new_name}' already exists! Choose a different name or overwrite it.")
                return
            save_personality(new_name, personality_settings)
            preset_menu['values'] = get_all_personality_presets()
            preset_var.set(new_name)
            logging.info(f"Saved personality preset '{new_name}'")
            messagebox.showinfo("Success", f"Preset '{new_name}' saved!")
        else:  # overwrite_name is set (and not empty due to prior check)
            save_personality(overwrite_name, personality_settings)
            preset_menu['values'] = get_all_personality_presets()
            preset_var.set(overwrite_name)
            logging.info(f"Saved personality preset '{overwrite_name}'")
            messagebox.showinfo("Success", f"Preset '{overwrite_name}' overwritten!")

        preset_window.destroy()

    tk.Button(preset_window, text="Save", command=save_action, bg="#4a4a4a", fg="#ffffff").pack(pady=10)
    preset_window.wait_window()

def delete_preset(preset_var, personality_settings, preset_menu):
    preset_name = preset_var.get()
    if preset_name:
        if messagebox.askyesno("Confirm Delete", f"Delete preset '{preset_name}'?"):
            delete_personality(preset_name)
            personality_settings.clear()
            preset_menu['values'] = get_all_personality_presets()
            preset_var.set('')
            logging.info(f"Deleted personality preset '{preset_name}'")
            messagebox.showinfo("Success", f"Preset '{preset_name}' deleted!")
            personality_entry.delete("1.0", tk.END)
            personality_entry.insert(tk.END, "A neutral AI sharing updates.")
            tone_entry.delete("1.0", tk.END)
            tone_entry.insert(tk.END, "casual, friendly")
            phrases_entry.delete("1.0", tk.END)
            phrases_entry.insert(tk.END, "Check this out!, Cool stuff!")
            topics_entry.delete("1.0", tk.END)
            topics_entry.insert(tk.END, "daily life, interests")
            keywords_entry.delete("1.0", tk.END)
            keywords_entry.insert(tk.END, "news, tech")
            sources_entry.delete("1.0", tk.END)
            sources_entry.insert(tk.END, "https://example.com/rss")
            hashtags_entry.delete("1.0", tk.END)
            hashtags_entry.insert(tk.END, "#AI, #Tech")
            ratio_scale.set(50)
            post_var.set(True)
            follow_var.set(True)
            like_var.set(True)
            comment_var.set(True)
            post_limit_entry.delete(0, tk.END)
            post_limit_entry.insert(0, "5")
            follow_limit_entry.delete(0, tk.END)
            follow_limit_entry.insert(0, "10")
            like_limit_entry.delete(0, tk.END)
            like_limit_entry.insert(0, "20")
            comment_limit_entry.delete(0, tk.END)
            comment_limit_entry.insert(0, "10")
            loop_count_entry.delete(0, tk.END)
            loop_count_entry.insert(0, "5")
            schedule_entry.delete(0, tk.END)
            schedule_entry.insert(0, "60")
            emoji_var.set(True)
            emojis_entry.delete("1.0", tk.END)
            emojis_entry.insert(tk.END, "😊, 👍")
            emoji_scale.set(50)
            research_var.set(True)
            headless_var.set(False)
            posting_times_list.clear()
            update_posting_times_display(posting_times_list, posting_times_frame, remove_posting_time)

def shutdown(root):
    global shutdown_flag
    shutdown_flag = True
    root.destroy()

def logout(root):
    global shutdown_flag
    shutdown_flag = False
    root.destroy()

if __name__ == "__main__":
    from .xlogin_setup_gui import select_setup_gui
    choice = select_setup_gui()
    logging.info(f"Setup choice received: {choice}")
    if choice and choice["action"] == "new":
        credentials, personality_settings, save_name = get_settings_from_gui()
        logging.info(f"New credentials: {credentials}, Personality: {personality_settings}, Save as: {save_name}")
    elif choice and choice["action"] == "load":
        from .xlogin_db import load_credentials
        credentials = load_credentials(choice["username"])
        logging.info(f"Loaded credentials for '{choice['username']}': {credentials}")
        credentials, personality_settings, save_name = get_settings_from_gui(credentials)
        logging.info(f"Loaded credentials: {credentials}, Personality: {personality_settings}, Save as: {save_name}")