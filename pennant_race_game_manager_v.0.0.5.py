import pygame
import psycopg2
import sys
from psycopg2.extras import DictCursor

# Constants for screen dimensions and colors
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 800
MENU_WIDTH = 350
BG_COLOR = (30, 30, 30)
TEXT_COLOR = (23, 127, 100)

# Initialize Pygame
pygame.init()
pygame.mixer.init()  # Initialize mixer for sound playback
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Pennant Race!")
clock = pygame.time.Clock()

# Load click sound
click_sound = pygame.mixer.Sound(r'C:\Users\vadim\Documents\Code\_pennant_race\gui\button_click.mp3')

# Load the splash image
splash_image = pygame.image.load(r'C:\Users\vadim\Documents\Code\_football_game\screen.png')
splash_image = pygame.transform.scale(splash_image, (SCREEN_WIDTH - MENU_WIDTH, SCREEN_HEIGHT))

# Define button dimensions and spacing
BUTTON_WIDTH, BUTTON_HEIGHT = MENU_WIDTH - 40, 60
BUTTON_SPACING = 5  # Space between each button

# Load button images for each state and scale to consistent size
button_normal = pygame.transform.scale(pygame.image.load(r'C:\Users\vadim\Documents\Code\_pennant_race\gui\main_screen_button_normal.png').convert_alpha(), (BUTTON_WIDTH, BUTTON_HEIGHT))
button_hover = pygame.transform.scale(pygame.image.load(r'C:\Users\vadim\Documents\Code\_pennant_race\gui\main_screen_button_hover.png').convert_alpha(), (BUTTON_WIDTH, BUTTON_HEIGHT))
button_click = pygame.transform.scale(pygame.image.load(r'C:\Users\vadim\Documents\Code\_pennant_race\gui\main_screen_button_click.png').convert_alpha(), (BUTTON_WIDTH, BUTTON_HEIGHT))

# Define the menu options
menu_options = [
    "Exhibition Game",
    "League Play",
    "League Utilities",
    "Reports",
    "Schedule Editor",
    "Player Editor",
    "Manager Profile",
    "General Manager Utilities",
    "Game Options",
    "System Settings",
    "Exit"
]

# Button class to handle three-state buttons
class Button:
    def __init__(self, x, y, images, text, font, text_color, click_sound):
        self.images = images  # Dictionary with button states
        self.text = text
        self.font = font
        self.text_color = text_color
        self.click_sound = click_sound
        self.image = images['normal']  # Default to the normal image
        self.rect = self.image.get_rect(topleft=(x, y))
        self.state = 'normal'
    
    def update(self, mouse_pos, mouse_click):
        # Check if the mouse is over the button
        if self.rect.collidepoint(mouse_pos):
            if mouse_click[0]:  # If left mouse button is pressed
                if self.state != 'hover':  # Only play sound once per click
                    self.click_sound.play()  # Play click sound
                self.state = 'click'
            else:
                self.state = 'hover'
        else:
            self.state = 'normal'

        # Update the button image based on the current state
        self.image = self.images[self.state]

    def draw(self, surface):
        # Draw the button image
        surface.blit(self.image, self.rect)
        
        # Render and draw the text on top of the button
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)  # Center the text on the button
        surface.blit(text_surf, text_rect)

# Initialize font
font = pygame.font.Font(None, 24)  # Choose a font and size

# Main menu screen class with button functionality
class MainMenuScreen:
    def __init__(self, screen_manager):
        self.screen_manager = screen_manager
        self.buttons = []
        self.create_buttons()

    def create_buttons(self):
        # Starting position for buttons
        x = 870
        y = 20  # Starting vertical position for the first button
        
        # Initialize buttons with images and text
        for i, option in enumerate(menu_options):
            button = Button(
                x, y + i * (BUTTON_HEIGHT + BUTTON_SPACING),  # Position each button with consistent vertical spacing
                {'normal': button_normal, 'hover': button_hover, 'click': button_click},  # Button images
                option,  # Button text
                font,  # Font for the text
                TEXT_COLOR,  # Text color
                click_sound
            )
            self.buttons.append(button)

    def handle_events(self, event):
        if event.type == pygame.MOUSEMOTION:
            # Update button hover state based on mouse position
            mouse_pos = event.pos
            for button in self.buttons:
                button.update(mouse_pos, pygame.mouse.get_pressed())
        
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Check for button clicks
            if event.button == 1:  # Left mouse button
                mouse_pos = pygame.mouse.get_pos()
                for i, button in enumerate(self.buttons):
                    if button.rect.collidepoint(mouse_pos):
                        self.activate_option(i)

    def activate_option(self, option_index):
        selected_option_text = menu_options[option_index]
        if selected_option_text == "Exit":
            pygame.quit()
            sys.exit()
        else:
            # Load the screen corresponding to the selected option
            self.screen_manager.set_screen(PlaceholderScreen(self.screen_manager, selected_option_text))

    def update(self):
        pass  # Placeholder to meet the expected update method requirement

    def draw(self, surface):
        # Draw the splash image and menu background box
        surface.blit(splash_image, (0, 0))

        # Draw each button on the screen
        for button in self.buttons:
            button.draw(surface)

# Placeholder screen for each menu option
class PlaceholderScreen:
    def __init__(self, screen_manager, title):
        self.screen_manager = screen_manager
        self.title = title
    
    def handle_events(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.screen_manager.set_screen(MainMenuScreen(self.screen_manager))

    def update(self):
        pass

    def draw(self, surface):
        font = pygame.font.Font(None, 48)
        title_text = font.render(self.title, True, TEXT_COLOR)
        surface.blit(title_text, (SCREEN_WIDTH // 2 - title_text.get_width() // 2, 100))

        # Display back instruction
        back_font = pygame.font.Font(None, 32)
        back_text = back_font.render("Press ESC to return to Main Menu", True, TEXT_COLOR)
        surface.blit(back_text, (SCREEN_WIDTH // 2 - back_text.get_width() // 2, 200))

# Screen Manager to handle transitions
class ScreenManager:
    def __init__(self, db_helper):
        self.current_screen = None
        self.db_helper = db_helper

    def set_screen(self, screen):
        self.current_screen = screen

    def handle_events(self, event):
        if self.current_screen:
            self.current_screen.handle_events(event)

    def update(self):
        if self.current_screen:
            self.current_screen.update()

    def draw(self, surface):
        if self.current_screen:
            surface.fill(BG_COLOR)  # Clear the screen
            self.current_screen.draw(surface)
            pygame.display.flip()

# Database Helper (unchanged)
class DatabaseHelper:
    def __init__(self, db_params):
        self.connection = psycopg2.connect(**db_params)
    
    def get_teams(self):
        with self.connection.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("SELECT id, name FROM teams;")
            return cursor.fetchall()

    def get_team_details(self, team_id):
        with self.connection.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute("SELECT player_id, player_name, rating, position FROM players WHERE team_id = %s;", (team_id,))
            return cursor.fetchall()

# Database connection parameters
db_params = {
    "dbname": "pennant_race",
    "user": "vadim",
    "password": "bacon",
    "host": "localhost"
}

# Initialize DatabaseHelper and ScreenManager
db_helper = DatabaseHelper(db_params)
screen_manager = ScreenManager(db_helper)
screen_manager.set_screen(MainMenuScreen(screen_manager))

# Main game loop
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        else:
            screen_manager.handle_events(event)

    screen_manager.update()
    screen_manager.draw(screen)
    clock.tick(30)

pygame.quit()
sys.exit()
