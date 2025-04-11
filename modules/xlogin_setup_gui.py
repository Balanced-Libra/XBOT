import tkinter as tk
from tkinter import ttk, messagebox
import logging
from .xlogin_db import get_all_usernames, init_setup_db, load_credentials, save_credentials

shutdown_flag = False

def select_setup_gui():
    """Create a GUI for signing in to an existing account or signing up with new credentials."""
    global shutdown_flag
    shutdown_flag = False
    init_setup_db()
    usernames = get_all_usernames()

    root = tk.Tk()
    root.title("Twitter Bot Login")
    root.geometry("400x350")
    root.configure(bg="#2b2b2b")

    style = ttk.Style()
    style.theme_use('clam')
    style.configure("TLabel", background="#2b2b2b", foreground="#ffffff")
    style.configure("TButton", background="#4a4a4a", foreground="#ffffff")

    main_frame = tk.Frame(root, bg="#2b2b2b")
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    tk.Label(main_frame, text="Sign In or Sign Up", font=("Arial", 12, "bold"), bg="#2b2b2b", fg="#ffffff").pack(pady=10)

    tk.Label(main_frame, text="Username:", bg="#2b2b2b", fg="#ffffff").pack(pady=5)
    username_var = tk.StringVar()
    username_menu = ttk.Combobox(main_frame, textvariable=username_var, values=usernames, state="readonly" if usernames else "disabled")
    username_menu.pack(pady=5)

    tk.Label(main_frame, text="Password:", bg="#2b2b2b", fg="#ffffff").pack(pady=5)
    password_entry = tk.Entry(main_frame, width=40, show="*", bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
    password_entry.pack(pady=5)

    def login():
        username = username_var.get()
        password = password_entry.get().strip()
        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password!")
            return None
        root.destroy()
        return {"action": "load", "username": username, "password": password}  # Include password

    def signup():
        signup_window = tk.Toplevel(root)
        signup_window.title("Sign Up")
        signup_window.geometry("400x450")
        signup_window.configure(bg="#2b2b2b")

        tk.Label(signup_window, text="Create New Profile", font=("Arial", 12, "bold"), bg="#2b2b2b", fg="#ffffff").pack(pady=10)

        tk.Label(signup_window, text="Username:", bg="#2b2b2b", fg="#ffffff").pack(pady=5)
        signup_username_entry = tk.Entry(signup_window, width=40, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
        signup_username_entry.pack(pady=5)

        tk.Label(signup_window, text="Password:", bg="#2b2b2b", fg="#ffffff").pack(pady=5)
        signup_password_entry = tk.Entry(signup_window, width=40, show="*", bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
        signup_password_entry.pack(pady=5)

        tk.Label(signup_window, text="Email:", bg="#2b2b2b", fg="#ffffff").pack(pady=5)
        signup_email_entry = tk.Entry(signup_window, width=40, bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
        signup_email_entry.pack(pady=5)

        tk.Label(signup_window, text="API Type:", bg="#2b2b2b", fg="#ffffff").pack(pady=5)
        api_type_var = tk.StringVar(value="openai")
        ttk.Combobox(signup_window, textvariable=api_type_var, values=["openai", "gemini"], state="readonly").pack(pady=5)

        tk.Label(signup_window, text="API Key:", bg="#2b2b2b", fg="#ffffff").pack(pady=5)
        api_key_entry = tk.Entry(signup_window, width=40, show="*", bg="#3c3c3c", fg="#ffffff", insertbackground="#ffffff")
        api_key_entry.pack(pady=5)

        def create_profile():
            username = signup_username_entry.get().strip()
            password = signup_password_entry.get().strip()
            email = signup_email_entry.get().strip()
            api_type = api_type_var.get()
            api_key = api_key_entry.get().strip()
            if not all([username, password, email, api_key]):
                messagebox.showerror("Error", "All fields are required!")
                return
            if username in usernames:
                messagebox.showerror("Error", "Username already exists! Choose a different one.")
                return
            credentials = {
                "username": username,
                "password": password,
                "email": email,
            }
            save_credentials(username, credentials)
            save_api_key(username, f"{api_type.capitalize()} Default", api_type, api_key)  # Save initial API key with a default name
            signup_window.destroy()
            root.destroy()
            return {"action": "new", "username": username, "password": password}

        tk.Button(signup_window, text="Create Profile", command=lambda: setattr(root, "result", create_profile()), bg="#4a4a4a", fg="#ffffff", font=("Arial", 10, "bold")).pack(pady=20)

        signup_window.wait_window()
        return getattr(root, "result", None)

    def shutdown():
        global shutdown_flag
        shutdown_flag = True
        root.destroy()
        return None

    button_frame = tk.Frame(main_frame, bg="#2b2b2b")
    button_frame.pack(fill="x", pady=20)
    tk.Button(button_frame, text="Sign In", command=lambda: setattr(root, "result", login()), bg="#4a4a4a", fg="#ffffff", font=("Arial", 10, "bold")).pack(side="left", padx=5, fill="x", expand=True)
    tk.Button(button_frame, text="Sign Up", command=lambda: setattr(root, "result", signup()), bg="#4a4a4a", fg="#ffffff", font=("Arial", 10, "bold")).pack(side="left", padx=5, fill="x", expand=True)
    tk.Button(button_frame, text="Shutdown", command=shutdown, bg="#ff4a4a", fg="#ffffff", font=("Arial", 10, "bold")).pack(side="left", padx=5, fill="x", expand=True)

    root.mainloop()

    if shutdown_flag:
        return None
    return getattr(root, "result", {"action": "new", "username": None})

if __name__ == "__main__":
    choice = select_setup_gui()
    print(f"Setup choice: {choice}")