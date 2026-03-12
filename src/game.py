import math
import time
import constants
import keyboard
import numpy as np
from gamewindow import GameWindow
from logger import setup_logger

logger = setup_logger()


class Game:
    running: bool
    paused: bool
    highest_wave_this_prestige: tuple[int, float]
    last_execution_times: dict[str, float]

    def __init__(self, title):
        self.last_mob_time = time.time()
        self.running = True
        self.paused = False
        self.highest_wave_this_prestige = (0, time.time())
        self.last_execution_times = {}
        self.current_map = 'haunted_dungeon'
        #self.current_map = 'eerie_cemetery'
        self.dps_monster_index = 7
        keyboard.on_press_key('z', self.stop_execution)
        keyboard.on_press_key('x', self.toggle_paused)
        self.window = GameWindow(title)

    def run(self):
        while self.running:
            if self.paused:
                time.sleep(1)
                continue
            # Define functions and their intervals (in seconds)
            tasks = {
                self.do_prestige_if_defeat: 1,
                self.click_active_play_bonus_if_available: 10,
                self.do_mob_if_available: 10,
                self.do_tank_if_available: 10,
                self.handle_dps_monster: 1,
                self.do_boss_rush_if_available: 10,
                self.press_play_if_paused: 30,  # failsafe in case something made the game pause
                self.handle_all_monsters: 30,
                self.handle_mission_rewards: 60,
                self.random_break: 60
            }

            for task, interval in tasks.items():
                if time.time() - self.last_execution_times.get(task.__name__, 0) > interval:
                    task()
                    self.last_execution_times[task.__name__] = time.time()

            time.sleep(1)

    def stop_execution(self, e):
        self.running = False

    def toggle_paused(self, e):
        logger.info("Unpausing..." if self.paused else "Pausing...")
        self.paused = not self.paused

    def is_defeat_screen(self):
        letter_d_visible = self.window.pixel_is_color(253, 329, (255, 255, 255))
        letter_t_visible = self.window.pixel_is_color(473, 329, (255, 255, 255))
        return letter_d_visible and letter_t_visible

    def handle_dps_monster(self):
        self.close_menu_if_open()
        (x, y) = constants.MONSTER_COORDS[self.current_map][self.dps_monster_index]
        self.window.click(x, y)
        self.level_up_monster_if_available()
        self.handle_evolution_or_pet()

    def handle_all_monsters(self):
        self.close_menu_if_open()
        for (x, y) in constants.MONSTER_COORDS[self.current_map]:
            self.window.click(x, y)
            self.handle_evolution_or_pet()

    def level_all_monsters(self):
        self.close_menu_if_open()
        for (x, y) in constants.MONSTER_COORDS[self.current_map]:
            self.window.click(x, y)
            self.level_up_monster_if_available()

    def level_up_monster_if_available(self):
        """
        Levels up the currently selected monster, if enough gold
        """
        if self.window.pixel_is_color(675, 1050, constants.COLORS['green_button']):
            self.window.click(615, 1030)  # Level up

    def handle_evolution_or_pet(self):
        """
        Checks the currently selected monster for evolution or pet upgrade and handles it if available
        """
        if self.window.pixel_is_color(131, 934, constants.COLORS['exclamation_mark']):  # Check if exclamation mark on tower info
            logger.debug("Evolution or pet upgrade available")
            self.window.click(*constants.MONSTER['open_tower_info_button_coords'])
            self.window.click(*constants.MONSTER['open_evolution_tab_button_coords'])
            if self.window.pixel_is_color(275, 980, constants.COLORS['green_button']):
                monster_name = self.window.get_text_from_screen(constants.MONSTER['evolve_name_region'])
                logger.info("Evolving " + monster_name)
                self.window.click(*constants.MONSTER['evolve_button_coords'])
            else:
                self.window.click(*constants.MONSTER['open_pets_tab_button_coords'])
                self.window.scroll_up(150, 660, 650)
                for i in range(70):
                    if self.window.pixel_is_color(660, 650, constants.COLORS['green_button_darker']):
                        pet_name = self.window.get_text_from_screen(constants.MONSTER['upgrade_pet_name_region'])
                        logger.info(f'Upgrading pet {pet_name}')
                        self.window.click(556, 670)  # Upgrade pet
                        break
                    self.window.scroll_down(1, 660, 650)
            keyboard.press_and_release('esc')  # Close Tower Info

    def close_menu_if_open(self):
        if self.window.pixel_is_color(14, 1033, (32, 44, 65)):  # Check if loadout button is dark
            keyboard.press_and_release('esc')  # Close menu

    def click_active_play_bonus_if_available(self):
        if self.window.pixel_is_color(712, 1034, constants.COLORS['exclamation_mark']):  # Check if exclamation mark on active bonus
            logger.info("Active bonus available, clicking")
            self.window.click(705, 1024)  # Click active bonus
            keyboard.press_and_release('esc')  # Close active bonus window

    def check_for_new_highest_wave(self):
        """
        Reads the current wave from the top left of the game window and updates self.highest_wave_this_prestige accordingly
        """
        numbers = self.window.get_numbers_from_screen(constants.WAVE_REGION)
        if numbers:
            wave = max(numbers) - 1  # Subtract 1 because the wave number is shown at the start of the wave
            wave = 10 * math.floor(wave / 10)  # Round down to nearest 10
            if wave > self.highest_wave_this_prestige[0]:
                current_time = time.time()
                logger.debug(f"New highest wave: {wave} after {(current_time - self.highest_wave_this_prestige[1]):.1f} seconds")
                self.highest_wave_this_prestige = (wave, current_time)

    def do_prestige_if_defeat(self):
        """
        Does prestige if the defeat screen is visible and it was not caused by a mob
        """
        defeat_caused_by_mob = time.time() - self.last_mob_time < 60
        if not defeat_caused_by_mob and self.is_defeat_screen():
            logger.info("Doing prestige after defeat at wave " + str(self.window.get_numbers_from_screen(constants.WAVE_REGION)))
            self.do_prestige_and_start_new_round()
            self.highest_wave_this_prestige = (0, time.time())

    def do_prestige_and_start_new_round(self):
        if self.current_map in constants.MONSTER_COORDS:  # todo: add support for more maps
            self.level_all_monsters()  # Dump gold before prestige, for monster level achievement
        self.window.click(*constants.PRESTIGE['open_menu_button_coords'])
        self.window.scroll_down(40, *constants.PRESTIGE['prestige_button_coords'])
        self.window.click(*constants.PRESTIGE['prestige_button_coords'])
        time.sleep(7)  # Wait for prestige to finish

        # Check for "Rate Game" popup
        if self.window.pixel_is_color(560, 940, (237, 68, 76)):
            self.window.click(560, 940)  # Click "Maybe later" button

        self.window.click(30, 1050)  # Click loadout button
        self.window.scroll_up(50, 350, 850)
        self.window.click(350, 757)  # Load loadout 1
        self.do_boss_rush_if_available()
        self.press_play_if_paused()

    def do_mob_if_available(self):
        text = self.window.get_text_from_screen(constants.MOB['ready_text_region'])
        if "read" in text.lower():  # 'y' is sometimes read as 'v', so we check for only 'read'
            self.last_mob_time = time.time()
            logger.info("Summoning Peasant Mob")
            self.window.click(*constants.MOB['open_menu_button_coords'])
            self.window.click(*constants.MOB['start_button_coords'])
            self.window.click(*constants.MOB['close_menu_button_coords'])

    def do_tank_if_available(self):
        text = self.window.get_text_from_screen(constants.TANK['ready_text_region'])
        if "read" in text.lower():  # 'y' is sometimes read as 'v', so we check for only 'read'
            logger.info("Summoning Tank Swordsman")
            self.window.click(*constants.TANK['open_menu_button_coords'])
            self.window.click(*constants.TANK['start_button_coords'])
            self.window.click(*constants.TANK['close_menu_button_coords'])

    def do_boss_rush_if_available(self, type="mini"):
        text = self.window.get_text_from_screen(constants.BOSS_RUSH['rush_text_region'])
        if "rush" in text.lower():
            logger.debug(f"Enabling Boss Rush ({type})")
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
            logger.info(f'Random break for {(sleep_time/60):.1f} minutes')
            time.sleep(sleep_time)

    def handle_mission_rewards(self):
        if self.window.pixel_is_color(471, 1109, constants.COLORS['exclamation_mark']):
            logger.debug("Mission reward available, entering missions menu")
            self.window.click(431, 1123)
            if self.window.pixel_is_color(306, 1047, constants.COLORS['exclamation_mark']):
                logger.info("Daily Missions rewards available, claiming")
                self.window.click(258, 1063)
                claim_locations = self.window.get_clusters_of_color(constants.COLORS['green_button'], constants.MENU_RIGHT_SIDE_REGION)
                for (x, y) in claim_locations:
                    logger.debug("Claiming reward at " + str((x, y)))
                    self.window.click(x, y)
            if self.window.pixel_is_color(185, 1047, constants.COLORS['exclamation_mark']):
                logger.info("Achievement rewards available, claiming")
                self.window.click(137, 1063)
                self.window.scroll_up(40, 260, 600)
                for _ in range(3):
                    claim_locations = self.window.get_clusters_of_color(constants.COLORS['green_button'], constants.MENU_RIGHT_SIDE_REGION)
                    for (x, y) in claim_locations:
                        logger.debug("Claiming reward at " + str((x, y)))
                        self.window.click(x, y)
                    self.window.scroll_down(25, 260, 600)
            keyboard.press_and_release('esc')
