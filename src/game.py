import logging
import math
from time import sleep, time
import constants
import keyboard
import pyautogui
import numpy as np


from gamewindow import GameWindow

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DPS_MONSTER_COORDINATES = [(468, 611)]
#DPS_MONSTER_COORDINATES = [(293, 705)]  # cemetery


class Game:
    running: bool
    paused: bool
    highest_wave_this_prestige: tuple[int, float]
    last_execution_times: dict[str, float]

    def __init__(self, title):
        self.running = True
        self.paused = False
        self.highest_wave_this_prestige = (0, time())
        self.last_execution_times = {}
        self.current_map = 'enchanted_forest'
        keyboard.on_press_key('z', self.stop_execution)
        keyboard.on_press_key('x', self.toggle_paused)
        self.window = GameWindow(title)

    def run(self):
        while self.running:
            if self.paused:
                sleep(1)
                continue
            # Define functions and their intervals (in seconds)
            tasks = {
                self.click_active_play_bonus_if_available: 10,
                self.do_mob_if_available: 10,
                self.do_tank_if_available: 10,
                self.handle_monsters: 1,
                self.check_for_new_highest_wave: 10,
                self.do_prestige_if_slow_progress: 10,
                self.do_boss_rush_if_available: 10,
                self.press_play_if_paused: 30,  # failsafe in case something made the game pause
                self.random_break: 60
            }

            for task, interval in tasks.items():
                if time() - self.last_execution_times.get(task.__name__, 0) > interval:
                    task()
                    self.last_execution_times[task.__name__] = time()

            sleep(1)

    def stop_execution(self, e):
        self.running = False

    def toggle_paused(self, e):
        logging.info("Unpausing..." if self.paused else "Pausing...")
        self.paused = not self.paused

    def handle_monsters(self, dps_only=True):
        self.close_menu_if_open()
        for (x, y) in DPS_MONSTER_COORDINATES if dps_only else constants.MONSTER_COORDS[self.current_map]:
            if self.window.pixel_is_color(x, y, (255, 255, 0)) and self.window.pixel_is_color(x, y-3, (255, 255, 0)):  # If yellow, no monster present on tile
                continue
            self.window.click(x, y)  # Click monster
            self.level_up_monster_if_available()
            self.handle_evolution_or_pet()

    def level_up_monster_if_available(self):
        if self.window.pixel_is_color(675, 1050, constants.COLORS['green_button']):
            self.window.click(615, 1030)  # Level up

    def handle_evolution_or_pet(self):
        if self.window.pixel_is_color(131, 934, constants.COLORS['exclamation_mark']):  # Check if exclamation mark on tower info
            logging.info("Evolution or pet upgrade available, clicking")
            self.window.click(*constants.MONSTER['open_tower_info_button_coords'])
            self.window.click(*constants.MONSTER['open_evolution_tab_button_coords'])
            if self.window.pixel_is_color(275, 980, constants.COLORS['green_button']):
                logging.info("Evolution available, clicking")
                self.window.click(*constants.MONSTER['evolve_button_coords'])
            else:
                self.window.click(*constants.MONSTER['open_pets_tab_button_coords'])
                self.window.move_mouse(660, 650)
                pyautogui.scroll(150)
                for i in range(70):
                    if self.window.pixel_is_color(660, 650, constants.COLORS['green_button_darker']):
                        logging.info(f'Found pet upgrade after scrolling {i} times')
                        self.window.click(556, 670)  # Upgrade pet
                        break
                    pyautogui.scroll(-1)
            keyboard.press_and_release('esc')  # Close Tower Info

    def close_menu_if_open(self):
        if self.window.pixel_is_color(14, 1033, (32, 44, 65)):  # Check if loadout button is dark
            keyboard.press_and_release('esc')  # Close menu

    def click_active_play_bonus_if_available(self):
        if self.window.pixel_is_color(712, 1034, constants.COLORS['exclamation_mark']):  # Check if exclamation mark on active bonus
            logging.info("Active bonus available, clicking")
            self.window.click(705, 1024)  # Click active bonus
            keyboard.press_and_release('esc')  # Close active bonus window

    def check_for_new_highest_wave(self):
        numbers = self.window.get_numbers_from_screen(constants.WAVE_REGION)
        if numbers:
            wave = max(numbers) - 1  # Subtract 1 because the wave number is shown at the start of the wave
            wave = 10 * math.floor(wave / 10)  # Round down to nearest 10
            if wave > self.highest_wave_this_prestige[0]:
                current_time = time()
                logging.debug(f"New highest wave: {wave} after {(current_time - self.highest_wave_this_prestige[1]):.1f} seconds")
                self.highest_wave_this_prestige = (wave, current_time)

    def do_prestige_if_slow_progress(self):
        if time() - self.highest_wave_this_prestige[1] > 2 * 60:
            logging.info("Long time without progress, doing prestige at wave " + str(self.highest_wave_this_prestige[0]))
            self.do_prestige_and_start_new_round()
            self.highest_wave_this_prestige = (0, time())

    def do_prestige_and_start_new_round(self):
        if self.current_map == 'enchanted_forest':  # todo: add support for other maps
            self.handle_monsters(dps_only=False)  # Dump gold before prestige, for mosnter level achievementx
        self.window.click(*constants.PRESTIGE['open_menu_button_coords'])
        self.window.move_mouse(*constants.PRESTIGE['prestige_button_coords'])
        pyautogui.scroll(-50)  # Scroll down
        self.window.click(*constants.PRESTIGE['prestige_button_coords'])
        sleep(7)  # Wait for prestige to finish

        # Check for "Rate Game" popup
        if self.window.pixel_is_color(560, 940, (237, 68, 76)):
            self.window.click(560, 940)  # Click "Maybe later" button

        self.window.click(30, 1050)  # Click loadout button
        self.window.move_mouse(350, 850)
        pyautogui.scroll(50)  # Scroll up
        self.window.click(350, 757)  # Load loadout 1
        self.do_boss_rush_if_available()
        self.press_play_if_paused()

    def do_mob_if_available(self):
        text = self.window.get_text_from_screen(constants.MOB['ready_text_region'])
        if "read" in text.lower():  # 'y' is sometimes read as 'v', so we check for only 'read'
            logging.info("Mob available, starting")
            self.window.click(*constants.MOB['open_menu_button_coords'])
            self.window.click(*constants.MOB['start_button_coords'])
            self.window.click(*constants.MOB['close_menu_button_coords'])

    def do_tank_if_available(self):
        text = self.window.get_text_from_screen(constants.TANK['ready_text_region'])
        if "read" in text.lower():  # 'y' is sometimes read as 'v', so we check for only 'read'
            logging.info("Tank available, starting")
            self.window.click(*constants.TANK['open_menu_button_coords'])
            self.window.click(*constants.TANK['start_button_coords'])
            self.window.click(*constants.TANK['close_menu_button_coords'])

    def do_boss_rush_if_available(self, type="mini"):
        text = self.window.get_text_from_screen(constants.BOSS_RUSH['rush_text_region'])
        if "rush" in text.lower():
            logging.info("Boss Rush available, starting")
            self.window.click(*constants.BOSS_RUSH['open_menu_button_coords'])
            self.window.click(*constants.BOSS_RUSH[f'{type}_button_coords'])

    def press_play_if_paused(self):
        if self.window.pixel_is_color(41, 960, constants.COLORS['green_button']):
            self.window.click(31, 972)

    def random_break(self):
        if np.random.random() < 0.05:
            self.close_menu_if_open()
            self.press_play_if_paused()
            sleep_time = np.random.randint(60, 60*15)
            logging.info(f'Random break for {(sleep_time/60):.1f} minutes')
            sleep(sleep_time)
