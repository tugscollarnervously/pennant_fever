import tkinter as tk
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText
import customtkinter as ctk
import subprocess

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Baseball Simulation Game")
        self.geometry("1200x800")

        # Header
        header_frame = ctk.CTkFrame(self, height=50, corner_radius=0)
        header_frame.pack(side="top", fill="x")

        title_label = ctk.CTkLabel(header_frame, text="BBS 0.0.3", font=("Helvetica", 20))
        title_label.pack(pady=10)

        # Sidebar
        sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        sidebar_frame.pack(side="left", fill="y")

        buttons = [
            ("Home", self.load_home),
            ("Team", self.load_roster_management),
            ("Stats", self.load_stats),
            ("League", self.league_management),
            ("Play Game", self.play_game),
            ("Quit Game", self.quit_game)
        ]

        for (text, command) in buttons:
            button = ctk.CTkButton(sidebar_frame, hover_color="gray", text=text, command=command)
            button.pack(padx=5, pady=5)

        # Main Content Area
        self.content_frame = ctk.CTkFrame(self)
        self.content_frame.pack(side="right", expand=True, fill="both")

        # Load initial content
        self.load_home()

    def load_home(self):
            self.clear_content()
            
            # Set up a 9x9 grid
            for i in range(9):
                self.content_frame.grid_columnconfigure(i, weight=1)
                self.content_frame.grid_rowconfigure(i, weight=1)
            
            standings_label = ctk.CTkLabel(self.content_frame, bg_color="grey", text="Standings", text_color="white", font=("Helvetica", 14))
            standings_label.grid(row=0, column=0, rowspan=2, columnspan=3, sticky="nsew", padx=5, pady=5)
            
            league_leaders_label = ctk.CTkLabel(self.content_frame, bg_color="blue", text="League Leaders", font=("Helvetica", 14))
            league_leaders_label.grid(row=0, column=3, rowspan=2, columnspan=3, sticky="nsew", padx=5, pady=5)
            
            '''
            transactions_label = ctk.CTkLabel(self.content_frame, bg_color="red", text="Transactions", font=("Helvetica", 14))
            transactions_label.grid(row=0, column=6, rowspan=3, columnspan=3, sticky="nsew", padx=5, pady=5)
            
            
            news_label = ctk.CTkLabel(self.content_frame, bg_color="grey", text_color="white",text="Important News", font=("Helvetica", 14))
            news_label.grid(row=3, column=6, rowspan=1, columnspan=3, sticky="nsew", padx=5, pady=5)
            '''

            standings_content = ctk.CTkLabel(self.content_frame, bg_color="dodger blue", text="Standings content goes here")
            standings_content.grid(row=2, column=0, rowspan=6, columnspan=3, sticky="nsew", padx=5, pady=5)

            extra_content = ctk.CTkLabel(self.content_frame, bg_color="honeydew4", text="extra content")
            extra_content.grid(row=8, column=0, rowspan=1, columnspan=3, sticky="nsew", padx=5, pady=5)
            
            league_leaders_content = ctk.CTkLabel(self.content_frame, bg_color="green", text="League leaders content goes here")
            league_leaders_content.grid(row=2, column=3, rowspan=2, columnspan=3, sticky="nsew", padx=5, pady=5)
            
            transactions_content = ctk.CTkLabel(self.content_frame, bg_color="orange", text="Transactions content goes here")
            transactions_content.grid(row=0, column=6, rowspan=4, columnspan=3, sticky="nsew", padx=5, pady=5)
            
            # Placeholder for news content with ScrolledText
            news_frame = ctk.CTkFrame(self.content_frame)
            news_frame.grid(row=4, column=3, rowspan=5, columnspan=3, sticky="nsew", padx=5, pady=5)

            self.news_content_left = tk.Text(news_frame, borderwidth=10, background="gray", width=15, font="Helvetica", wrap="word", height=10)
            self.news_content_left.pack(side="left", fill="both", expand=True)

            # Customized scrollbar
            news_scrollbar = ttk.Scrollbar(news_frame, orient="vertical", command=self.news_content_left.yview)
            news_scrollbar.pack(side="right", fill="y")
            self.news_content_left.configure(yscrollcommand=news_scrollbar.set)

            # Apply custom style to the scrollbar
            style = ttk.Style()
            style.configure("TScrollbar", background="grey", troughcolor="white", bordercolor="grey", arrowcolor="black")

            # Fetch and display news content
            self.load_news()

            news_content_right = ctk.CTkLabel(self.content_frame, bg_color="sienna3", text="Important news content goes here")
            news_content_right.grid(row=4, column=6, rowspan=5, columnspan=3, sticky="nsew", padx=5, pady=5)
        

        
    def load_roster_management(self):
        self.clear_content()
        tab_control = ttk.Notebook(self.content_frame)

        tab1 = ttk.Frame(tab_control)
        tab2 = ttk.Frame(tab_control)
        tab3 = ttk.Frame(tab_control)
        tab4 = ttk.Frame(tab_control)

        tab_control.add(tab1, text='Team Info')
        tab_control.add(tab2, text='View Roster')
        tab_control.add(tab3, text='Schedule')
        tab_control.add(tab4, text='Edit Roster')

        tab_control.pack(expand=1, fill="both")

        # Add content to tabs as needed
        ttk.Label(tab1, text="Team Info").pack(pady=20)
        ttk.Label(tab2, text="View Roster").pack(pady=20)
        ttk.Label(tab1, text="Schedule").pack(pady=20)
        ttk.Label(tab2, text="Edit Roster").pack(pady=20)

    def load_stats(self):
        self.clear_content()
        stats_label = ctk.CTkLabel(self.content_frame, text="Stats Module", font=("Helvetica", 16))
        stats_label.pack(pady=20)

        # Further development for stats functionality
    
    def league_management(self):
        self.clear_content()

    def play_game(self):
        subprocess.Popen(["python", "bbs_v.0.0.3e.py"])
        self.destroy()
        in_game_label = ctk.CTkLabel(self.content_frame, text="In-Game Play Module", font=("Helvetica", 16))
        in_game_label.pack(pady=20)

        # Further development for in-game play functionality
    
    def quit_game(self):
        self.destroy()

    def clear_content(self):
        for widget in self.content_frame.winfo_children():
            widget.destroy()

    def load_news(self):
        try:
            with open("news.txt", "r") as file:
                news_content = file.read()
                self.news_content_left.configure(state="normal")
                self.news_content_left.delete(1.0, tk.END)
                self.news_content_left.insert(tk.END, news_content)
                self.news_content_left.configure(state="disabled")
        except FileNotFoundError:
            self.news_content_left.configure(state="normal")
            self.news_content_left.delete(1.0, tk.END)
            self.news_content_left.insert(tk.END, "No news available.")
            self.news_content_left.configure(state="disabled")


if __name__ == "__main__":
    app = App()
    app.mainloop()
