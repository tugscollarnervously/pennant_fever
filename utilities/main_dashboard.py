import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os

CONFIG_FILE = "default_directories.json"

class BaseballDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Baseball Game Dashboard")
        self.geometry("400x400")
        self.default_directories = self.load_default_directories()
        self.create_widgets()

    def create_widgets(self):
        # Title
        title_label = tk.Label(self, text="Baseball Game Dashboard", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=10)

        # Buttons for main menu options
        self.create_button("Load Away Team", self.load_away_team).pack(pady=5)
        self.create_button("Load Home Team", self.load_home_team).pack(pady=5)
        self.create_button("Select Manager", self.select_manager).pack(pady=5)
        self.create_button("Set Game Rules", self.set_game_rules).pack(pady=5)
        self.create_button("Set Default Directories", self.set_default_directories).pack(pady=5)
        self.create_button("Start Game", self.start_game).pack(pady=20)

    def create_button(self, text, command):
        return tk.Button(self, text=text, font=("Helvetica", 12), width=20, command=command)

    def load_away_team(self):
        messagebox.showinfo("Load Away Team", "This will load the away team data.")

    def load_home_team(self):
        messagebox.showinfo("Load Home Team", "This will load the home team data.")

    def select_manager(self):
        messagebox.showinfo("Select Manager", "This will open the manager selection screen.")

    def set_game_rules(self):
        GameRulesWindow(self, self.default_directories["Config"])

    def set_default_directories(self):
        DefaultDirectoriesWindow(self, self.default_directories)

    def start_game(self):
        messagebox.showinfo("Start Game", "Starting the game with the selected options.")

    def load_default_directories(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        else:
            return {
                "Config": os.getcwd(),
                "Teams": os.getcwd(),
                "Saved Games": os.getcwd(),
                "Stats": os.getcwd()
            }

    def save_default_directories(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.default_directories, f, indent=4)

class GameRulesWindow(tk.Toplevel):
    def __init__(self, parent, config_dir):
        super().__init__(parent)
        self.title("Set Game Rules")
        self.geometry("300x400")
        self.config_dir = config_dir
        self.create_widgets()
        self.load_settings()

    def create_widgets(self):
        self.options = {
            "Computer vs Computer": tk.StringVar(),
            "Visiting Team": tk.StringVar(),
            "Home Team": tk.StringVar(),
            "League Type": tk.StringVar(),
            "Designated Hitter": tk.StringVar(),
            "Game Type": tk.StringVar(),
            "Month": tk.StringVar(),
            "Time of Day": tk.StringVar(),
            "Start Game": tk.StringVar(),
            "Use Injuries": tk.StringVar(),
            "Use Left/Right Split Stats": tk.StringVar(),
            "Use Days Rest Data": tk.StringVar(),
            "Use Manager Profile": tk.StringVar(),
            "Use Weather Effects": tk.StringVar(),
            "Pitcher Era": tk.StringVar()
        }

        self.comboboxes = {}
        for option in self.options.keys():
            ttk.Label(self, text=option, font=("Helvetica", 12)).pack(anchor=tk.W, padx=10, pady=2)
            combobox = ttk.Combobox(self, values=["Yes", "No"], state="readonly", textvariable=self.options[option])
            combobox.pack(anchor=tk.W, padx=20)
            self.comboboxes[option] = combobox

        ttk.Button(self, text="Save Settings As", command=self.save_settings).pack(pady=20)

    def load_settings(self):
        try:
            with open(os.path.join(self.config_dir, "game_rules.json"), "r") as f:
                settings = json.load(f)
                for option, value in settings.items():
                    if option in self.options:
                        self.options[option].set(value)
        except FileNotFoundError:
            # Set default values if the file doesn't exist
            for option in self.options.keys():
                self.options[option].set("Yes")

    def save_settings(self):
        settings = {option: var.get() for option, var in self.options.items()}
        save_path = self.config_dir
        os.makedirs(save_path, exist_ok=True)  # Ensure the directory exists
        with open(os.path.join(save_path, "game_rules.json"), "w") as f:
            json.dump(settings, f, indent=4)
        messagebox.showinfo("Save Settings", "Game rules have been saved.")
        self.destroy()

class DefaultDirectoriesWindow(tk.Toplevel):
    def __init__(self, parent, directories):
        super().__init__(parent)
        self.title("Set Default Directories")
        self.geometry("400x300")
        self.directories = directories
        self.create_widgets()

    def create_widgets(self):
        self.entries = {}
        for key in self.directories.keys():
            label = ttk.Label(self, text=key, font=("Helvetica", 12))
            label.pack(anchor=tk.W, padx=10, pady=2)
            entry = ttk.Entry(self, width=50)
            entry.pack(anchor=tk.W, padx=20, pady=2)
            entry.insert(0, self.directories[key])
            self.entries[key] = entry
            browse_button = ttk.Button(self, text="Browse", command=lambda k=key: self.browse_directory(k))
            browse_button.pack(anchor=tk.W, padx=20, pady=2)

        ttk.Button(self, text="Save Directories", command=self.save_directories).pack(pady=20)

    def browse_directory(self, key):
        directory = filedialog.askdirectory(initialdir=self.directories[key])
        if directory:
            self.entries[key].delete(0, tk.END)
            self.entries[key].insert(0, directory)

    def save_directories(self):
        for key, entry in self.entries.items():
            self.directories[key] = entry.get()
        self.master.save_default_directories()
        messagebox.showinfo("Save Directories", "Default directories have been saved.")
        self.destroy()

if __name__ == "__main__":
    app = BaseballDashboard()
    app.mainloop()
