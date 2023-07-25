import logging
import math
from time import sleep, time

import keyboard
import pyautogui

from gamewindow import GameWindow

# Initialize logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

ALL_MONSTER_COORDINATES = \
    [(292, 236), (468, 236),
     (292, 360),
     (292, 424), (468, 424),
     (292, 547), (468, 547),
     (468, 611),
     (292, 734), (468, 734)]
DPS_MONSTER_COORDINATES = [(468, 611)]
WAVE_REGION = (49, 44, 111, 30)


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
                self.do_prestige_if_slow_progress: 30,
                self.do_boss_rush_if_available: 30,
                self.do_upgrades_if_available: 60
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

    def handle_monsters(self):
        self.close_tower_info_if_open()
        for (x, y) in DPS_MONSTER_COORDINATES:
            if self.window.pixel_is_color(x, y, (255, 255, 0)) and self.window.pixel_is_color(x, y-3, (255, 255, 0)):  # If yellow, no monster present on tile
                continue
            self.window.click(x, y)  # Click monster
            self.level_up_monster_if_available()
            self.evolve_monster_if_available()

    def level_up_monster_if_available(self):
        if self.window.pixel_is_color(675, 1050, (143, 204, 84)):  # Check if level up button is green
            self.window.click(599, 1044)  # Level up

    def evolve_monster_if_available(self):
        if self.window.pixel_is_color(131, 934, (206, 149, 12)):  # Check if exclamation mark on tower info
            logging.info("Evolution available, clicking")
            self.window.click(131, 934)  # Open Tower Info
            self.window.click(303, 1063)  # Open Evolution Tab
            self.window.click(380, 960)  # Click Evolve
            keyboard.press_and_release('esc')  # Close Tower Info

    def close_tower_info_if_open(self):
        if self.window.pixel_is_color(657, 186, (237, 68, 76)):
            self.window.click(657, 186)

    def click_active_play_bonus_if_available(self):
        if self.window.pixel_is_color(712, 1034, (206, 149, 12)):  # Check if exclamation mark on active bonus
            logging.info("Active bonus available, clicking")
            self.window.click(705, 1024)  # Click active bonus
            keyboard.press_and_release('esc')  # Close active bonus window

    def check_for_new_highest_wave(self):
        numbers = self.window.get_numbers_from_screen(WAVE_REGION)
        if numbers:
            wave = max(numbers) - 1  # Subtract 1 because the wave number is shown at the start of the wave
            wave = 10 * math.floor(wave / 10)  # Round down to nearest 10
            if wave > self.highest_wave_this_prestige[0]:
                current_time = time()
                logging.debug(f"New highest wave: {wave} after {((current_time - self.highest_wave_this_prestige[1])/60):.1f} minutes")
                self.highest_wave_this_prestige = (wave, current_time)

    def do_prestige_if_slow_progress(self):
        if time() - self.highest_wave_this_prestige[1] > 3 * 60:
            logging.info("Long time without progress, doing prestige at wave " + str(self.highest_wave_this_prestige[0]))
            self.do_prestige_and_start_new_round()
            self.highest_wave_this_prestige = (0, time())

    def do_prestige_and_start_new_round(self):
        self.window.click(31, 169)  # Click blue prestige button on left menu
        self.window.move_mouse(377, 1000)
        pyautogui.scroll(-50)  # Scroll down
        self.window.click(377, 1000)  # Click green prestige button
        sleep(6)  # Wait for prestige to finish

        # Check for "Rate Game" popup
        if self.window.pixel_is_color(560, 940, (237, 68, 76)):
            self.window.click(560, 940)  # Click "Maybe later" button

        self.window.click(30, 1050)  # Click loadout button
        self.window.click(350, 757)  # Load loadout 1
        self.do_boss_rush_if_available()
        self.window.click(30, 974)  # Click play

    def do_mob_if_available(self):
        text = self.window.get_text_from_screen((5, 270, 52, 16))
        if "read" in text.lower():  # 'y' is sometimes read as 'v', so we check for only 'read'
            logging.info("Mob available, starting")
            self.window.click(31, 235)  # Click Mob button
            self.window.click(377, 888)  # Click start button
            self.window.click(629, 322)  # Close Mob menu

    def do_tank_if_available(self):
        text = self.window.get_text_from_screen((5, 345, 52, 16))
        if "read" in text.lower():  # 'y' is sometimes read as 'v', so we check for only 'read'
            logging.info("Tank available, starting")
            self.window.click(31, 310)  # Click Tank button on left menu
            self.window.click(377, 1053)  # Click start button
            self.window.click(629, 174)  # Close Mob menu

    def do_necromancer_if_available(self):
        text = self.window.get_text_from_screen((5, 418, 52, 16))
        if "read" in text.lower():  # 'y' is sometimes read as 'v', so we check for only 'read'
            logging.info("Necromancer available, starting")
            self.window.click(31, 392)  # Click Necro button on left menu
            self.window.click(377, 903)  # Click start button

    def do_upgrades_if_available(self):
        if self.window.pixel_is_color(261, 1109, (206, 149, 12)):  # Check if exclamation mark on upgrades button
            logging.info("Upgrades available, entering upgrades menu")
            self.window.click(254, 1099)  # Open upgrades menu
            self.do_artifact_upgrade_if_available()
            keyboard.press_and_release('esc')  # Close upgrades menu

    def do_artifact_upgrade_if_available(self):
        if self.window.pixel_is_color(268, 1047, (206, 149, 12)):
            logging.info("Artifact upgrades available, entering artifact upgrades menu")
            self.window.click(268, 1047)  # Click artifact tab
            self.window.move_mouse(625, 320)
            pyautogui.scroll(100)  # Scroll up
            self.window.click(625, 320)  # Click Unlock! button
            self.window.click(625, 320)  # Close popup

    def do_prestige_upgrade_if_available(self):
        if self.window.pixel_is_color(268, 1047, (206, 149, 12)):
            logging.info("Prestige upgrades available, entering prestige upgrades menu")
            self.window.click(469, 1048)  # Click prestige tab
            self.window.move_mouse(620, 360)
            pyautogui.scroll(100)  # Scroll up
            self.window.click(620, 360)  # Click Unlock! button
            self.window.click(620, 360)  # Close popup

    def do_boss_rush_if_available(self):
        text = self.window.get_text_from_screen((12, 558, 52, 16))
        if "rush" in text.lower():
            logging.info("Boss Rush available, starting")
            self.window.click(30, 544)  # Click Boss Rush button on left menu
            self.window.click(576, 691)  # Click Mini Boss Rush button
