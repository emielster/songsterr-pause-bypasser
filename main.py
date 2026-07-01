"""
Quick bypass script I wrote for Songsterr,
a famous tab provider. This will close the
pause frame whenever it pops up so you can
continue playing. Thank me later.
"""

import time
import argparse
from colorama import init as colorama_init, Fore, Style
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementNotInteractableException,
    StaleElementReferenceException,
)

colorama_init(autoreset=True)


MODAL_XPATH = "//*[contains(@class, 'modal') and contains(@class, 'eHuW')]"


DEFAULT_POLL_INTERVAL = 0.005 # How lower, how faster the window closes. This is like a "brake" for the polling.
IFRAME_SELECTOR = None


def print_intro():
    banner = r"""
   _____                       __
  / ___/____  ____  ____ ______/ /____  __________
  \__ \/ __ \/ __ \/ __ `/ ___/ __/ _ \/ ___/ ___/ 
 ___/ / /_/ / / / / /_/ (__  ) /_/  __/ /  / /  
/____/\____/_/ /_/\__, /____/\__/\___/_/  /_/  
                  /____/    Pause Bypasser
"""
    print(Fore.MAGENTA + Style.BRIGHT + banner)
    print(Fore.CYAN + Style.BRIGHT + "Songsterr Pause Bypasser" + Style.RESET_ALL)
    print(Fore.YELLOW + "-" * 55 + Style.RESET_ALL)
 

def get_driver():
    options = webdriver.ChromeOptions()
    driver = webdriver.Chrome(options=options)
    return driver


def _search_current_context(driver) -> bool:
    modals = driver.find_elements(By.XPATH, MODAL_XPATH)
    modals = [m for m in modals if m.is_displayed()]
    if not modals:
        return False
 
    modal = modals[0]
    try:

        modal.send_keys(Keys.ESCAPE)
        print("Sent ESC to dismiss the modal.")
        return True
    except (ElementNotInteractableException, StaleElementReferenceException) as e:
        try:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            return True
        except Exception as e2:
            return False


def try_click_continue(driver) -> bool:

    driver.switch_to.default_content()

    if IFRAME_SELECTOR:
        try:
            iframe = driver.find_element(By.CSS_SELECTOR, IFRAME_SELECTOR)
            driver.switch_to.frame(iframe)
        except NoSuchElementException:
            return False

    return _search_current_context(driver)


def watch_loop(driver, poll_interval: float = DEFAULT_POLL_INTERVAL):
    print(f"Watching for modal matching '{MODAL_XPATH}' ... (Ctrl+C to stop)")
    try:
        while True:
            try:
                try_click_continue(driver)
            except Exception as e:
                print(Fore.LIGHTBLUE_EX + Style.BRIGHT + "Bye!" + Style.RESET_ALL) 
                exit()
            time.sleep(poll_interval)
    except KeyboardInterrupt:
        print("Stopped watching.")


if __name__ == "__main__":
    print_intro()
    parser = argparse.ArgumentParser(
        description="Bypass the 'Pause' popup with ease"
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=DEFAULT_POLL_INTERVAL,
        help=f"How often to poll for the model, in seconds (default: {DEFAULT_POLL_INTERVAL}). How lower, how faster the frame closes but how laggier it gets."
    )
    args = parser.parse_args()



    driver = get_driver()
    driver.get("https://songsterr.com")

    watch_loop(driver, poll_interval=args.poll_interval)