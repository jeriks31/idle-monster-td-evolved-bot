import re
from time import sleep
import scipy

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

    def click(self, x, y, randomize_radius=3):
        self.move_mouse(x, y, randomize_radius)
        pyautogui.click()
        sleep(0.1)

    def move_mouse(self, x, y, randomize_radius=3):
        abs_x = self.offset_x + x + np.random.randint(-randomize_radius, randomize_radius)
        abs_y = self.offset_y + y + np.random.randint(-randomize_radius, randomize_radius)
        pyautogui.moveTo(abs_x, abs_y)

    def scroll_up(self, amount, x=260, y=600, randomize_radius=3):
        self.scroll(amount, x, y, randomize_radius)

    def scroll_down(self, amount, x=260, y=600, randomize_radius=3):
        self.scroll(-amount, x, y, randomize_radius)

    def scroll(self, amount, x=260, y=600, randomize_radius=3):
        abs_x = self.offset_x + x + np.random.randint(-randomize_radius, randomize_radius)
        abs_y = self.offset_y + y + np.random.randint(-randomize_radius, randomize_radius)
        pyautogui.moveTo(abs_x, abs_y)
        for _ in range(abs(amount)):
            pyautogui.scroll(1 if amount > 0 else -1, abs_x, abs_y)

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
        screenshot = cv2.cvtColor(np.array(screenshot_image), cv2.COLOR_RGB2BGR)
        result = self.reader.readtext(screenshot)
        return ' '.join([res[1] for res in result])

    def get_numbers_from_screen(self, region):
        text = self.get_text_from_screen(region)
        return [int(num) for num in re.findall(r'\d+', text)]

    def get_clusters_of_color(self, color, region, min_cluster_size=7, gap_size=6):
        # Grab the screenshot
        screenshot_image = self.grab_screen(region)
        screenshot = np.array(screenshot_image)

        # Create a boolean mask where the pixels match the specified color
        mask = np.all(screenshot == color, axis=2)

        # Define a structuring element with 8-connectivity
        s = [[1, 1, 1],
             [1, 1, 1],
             [1, 1, 1]]

        # Perform a binary closing operation on the mask to fill in small gaps
        closed_mask = scipy.ndimage.binary_closing(mask, structure=s, iterations=gap_size)

        # Label connected components in the closed mask
        labeled_mask, num_labels = scipy.ndimage.label(closed_mask, structure=s)

        cluster_centers = []
        for i in range(1, num_labels + 1):
            # Get the coordinates of the pixels in this cluster
            cluster_coords = np.argwhere(labeled_mask == i)

            # If the cluster is large enough, calculate its center and add it to the list
            if cluster_coords.shape[0] >= min_cluster_size:
                center_y, center_x = np.mean(cluster_coords, axis=0)
                # Convert to coordinates relative to the window
                center_x += region[0]
                center_y += region[1]
                cluster_centers.append((int(center_x), int(center_y)))

        return cluster_centers
