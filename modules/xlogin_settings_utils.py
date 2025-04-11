import tkinter as tk
from tkinter import messagebox
from .xlogin_setup_gui import shutdown_flag, logging
from .xlogin_db import save_credentials

def submit_settings(credentials, personality_settings, save_credentials_name, root, loaded_credentials, setup_name_entry, username_entry, password_entry, email_entry, api_type_var, api_key_entry, personality_entry, tone_entry, phrases_entry, topics_entry, keywords_entry, sources_entry, hashtags_entry, ratio_scale, post_var, follow_var, like_var, comment_var, post_limit_entry, follow_limit_entry, like_limit_entry, comment_limit_entry, loop_count_entry, schedule_entry, emoji_var, emojis_entry, emoji_scale, research_var, headless_var, posting_times_list, language_var, autodetect_var):
    # Update credentials from GUI
    credentials['username'] = username_entry.get().strip()
    credentials['password'] = password_entry.get().strip()
    credentials['email'] = email_entry.get().strip()
    credentials['api_type'] = api_type_var.get()
    credentials['api_key'] = api_key_entry.get().strip()

    # Update personality settings from GUI
    personality_settings['personality_description'] = personality_entry.get("1.0", tk.END).strip()
    personality_settings['tone_keywords'] = [k.strip() for k in tone_entry.get("1.0", tk.END).strip().split(',') if k.strip()]
    personality_settings['custom_phrases'] = [p.strip() for p in phrases_entry.get("1.0", tk.END).strip().split(',') if p.strip()]
    personality_settings['self_update_topics'] = [t.strip() for t in topics_entry.get("1.0", tk.END).strip().split(',') if t.strip()]
    personality_settings['search_keywords'] = [k.strip() for k in keywords_entry.get("1.0", tk.END).strip().split(',') if k.strip()]
    personality_settings['content_sources'] = [s.strip() for s in sources_entry.get("1.0", tk.END).strip().split(',') if s.strip()]
    personality_settings['hashtags'] = [h.strip() for h in hashtags_entry.get("1.0", tk.END).strip().split(',') if h.strip()]
    personality_settings['tweet_type_ratio'] = int(ratio_scale.get())
    personality_settings['post_enabled'] = post_var.get()
    personality_settings['follow_enabled'] = follow_var.get()
    personality_settings['like_enabled'] = like_var.get()
    personality_settings['comment_enabled'] = comment_var.get()
    personality_settings['language'] = language_var.get()
    personality_settings['autodetect_language'] = autodetect_var.get()

    try:
        personality_settings['daily_post_limit'] = int(post_limit_entry.get().strip()) if post_limit_entry.get().strip() else 0
        personality_settings['daily_follow_limit'] = int(follow_limit_entry.get().strip()) if follow_limit_entry.get().strip() else 0
        personality_settings['daily_like_limit'] = int(like_limit_entry.get().strip()) if like_limit_entry.get().strip() else 0
        personality_settings['daily_comment_limit'] = int(comment_limit_entry.get().strip()) if comment_limit_entry.get().strip() else 0
        if any(limit < 0 for limit in [personality_settings['daily_post_limit'], personality_settings['daily_follow_limit'], personality_settings['daily_like_limit'], personality_settings['daily_comment_limit']]):
            raise ValueError
    except ValueError:
        messagebox.showerror("Error", "Daily limits must be non-negative numbers (0 for infinite)!")
        return

    try:
        personality_settings['loop_count'] = int(loop_count_entry.get().strip())
        if personality_settings['loop_count'] <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Error", "Number of loops must be a positive number!")
        return

    try:
        personality_settings['schedule_interval'] = int(schedule_entry.get().strip())
        if personality_settings['schedule_interval'] <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Error", "Schedule interval must be a positive number!")
        return

    personality_settings['use_emojis'] = emoji_var.get()
    personality_settings['emoji_list'] = [e.strip() for e in emojis_entry.get("1.0", tk.END).strip().split(',') if e.strip()]
    personality_settings['emoji_frequency'] = int(emoji_scale.get())
    personality_settings['research_enabled'] = research_var.get()
    personality_settings['headless_enabled'] = headless_var.get()
    personality_settings['posting_times'] = posting_times_list

    for time_str in personality_settings['posting_times']:
        try:
            h, m = map(int, time_str.split(':'))
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
        except ValueError:
            messagebox.showerror("Error", f"Invalid posting time '{time_str}'. Use HH:MM (e.g., 14:30) with 0-23 hours and 0-59 minutes!")
            return

    if not all([credentials['username'], credentials['password'], credentials['email'], credentials['api_key'], personality_settings['personality_description'], personality_settings['search_keywords']]):
        messagebox.showerror("Error", "Username, password, email, API key, personality, and keywords are required!")
        return

    # Save credentials only if they are new (i.e., no loaded_credentials)
    if not loaded_credentials:
        save_credentials_name = credentials['username']  # Default to username for new credentials
        save_credentials(save_credentials_name, credentials)
    # Otherwise, assume credentials are already saved and only update if explicitly requested elsewhere (e.g., during signup)

    root.destroy()

def add_posting_time(posting_time_entry, posting_times_list, update_posting_times_display):
    time_str = posting_time_entry.get().strip()
    if time_str:
        try:
            h, m = map(int, time_str.split(':'))
            if 0 <= h <= 23 and 0 <= m <= 59:
                formatted_time = f"{h:02d}:{m:02d}"
                if formatted_time not in posting_times_list:
                    posting_times_list.append(formatted_time)
                    update_posting_times_display(posting_times_list)
                    posting_time_entry.delete(0, tk.END)
                else:
                    messagebox.showinfo("Info", f"Time '{formatted_time}' is already added!")
            else:
                messagebox.showerror("Error", "Hours must be 0-23 and minutes 0-59!")
        except ValueError:
            messagebox.showerror("Error", "Invalid format! Use HH:MM (e.g., 14:30)")
    else:
        messagebox.showerror("Error", "Please enter a posting time!")

def update_posting_times_display(posting_times_list, posting_times_frame=None, remove_posting_time=None):
    if posting_times_frame:
        for widget in posting_times_frame.winfo_children():
            widget.destroy()
        for time_str in posting_times_list:
            frame = tk.Frame(posting_times_frame, bg="#2b2b2b")
            frame.pack(fill="x", pady=2)
            tk.Label(frame, text=time_str, bg="#2b2b2b", fg="#ffffff").pack(side="left")
            tk.Button(frame, text="Remove", command=lambda t=time_str: remove_posting_time(t, posting_times_list, update_posting_times_display), bg="#ff4a4a", fg="#ffffff", font=("Arial", 8)).pack(side="right")

def remove_posting_time(time_str, posting_times_list, update_posting_times_display):
    posting_times_list.remove(time_str)
    update_posting_times_display(posting_times_list)