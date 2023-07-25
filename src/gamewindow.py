import re
from time import sleep

import numpy as np
import win32gui
import pyautogui
from PIL import Image
from mss import mss
import easyocr
import cv2


class GameWindow:
    def __init__(self, title):
        self.hwnd = win32gui.FindWindow(None, title)
        if not self.hwnd:
            raise ValueError(f"Window '{title}' not found!")
        win_rect = win32gui.GetWindowRect(self.hwnd)
        self.offset_x = win_rect[0] + 7
        self.offset_y = win_rect[1]
        self.reader = easyocr.Reader(['en'])

    def click(self, x, y):
        abs_x = self.offset_x + x
        abs_y = self.offset_y + y
        pyautogui.moveTo(abs_x, abs_y)
        pyautogui.click()
        sleep(0.07)

    def move_mouse(self, x, y):
        abs_x = self.offset_x + x
        abs_y = self.offset_y + y
        pyautogui.moveTo(abs_x, abs_y)

    def pixel_is_color(self, x, y, color):
        actual_color = pyautogui.pixel(self.offset_x + x, self.offset_y + y)
        return actual_color == color

    def grab_screen(self, region):
        region = {
            "top": self.offset_y + region[1],
            "left": self.offset_x + region[0],
            "width": region[2],
            "height": region[3],
        }
        with mss() as sct:
            screenshot = sct.grab(region)
        screenshot_image = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
        return screenshot_image

    def get_text_from_screen(self, region):
        screenshot_image = self.grab_screen(region)
        screenshot_image.save("screenshot.png")
        screenshot = cv2.cvtColor(np.array(screenshot_image), cv2.COLOR_RGB2BGR)
        result = self.reader.readtext(screenshot)
        return ' '.join([res[1] for res in result])

    def get_numbers_from_screen(self, region):
        text = self.get_text_from_screen(region)
        return [int(num) for num in re.findall(r'\d+', text)]
