import time
import argparse
from colorama import init as colorama_init, Fore, Style
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    WebDriverException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
)

colorama_init(autoreset=True)


MODAL_XPATH = "//*[contains(@class, 'modal') and contains(@class, 'eHuW')]"
BLUR_XPATH = "//*[contains(@class, 'tabBlurOverlay')]"
CONTROLS_BLUR_XPATH = "//*[contains(@class, 'controlsBlurOverlay')]"

DEFAULT_POLL_INTERVAL = 0.05
IFRAME_SELECTOR = None

MAX_CONSECUTIVE_ERRORS = 5

JS_WATCHER = r"""
(function() {
  if (window.__pauseBypasserInstalled) return;
  window.__pauseBypasserInstalled = true;

  function findModal(root) {
    var el = root.querySelector("[class*='modal'][class*='eHuW']");
    if (!el || el.dataset.pbHandled === '1') return null;
    return el;
  }

  function findBlur(root) {
    return root.querySelector("[class*='tabBlurOverlay']");
  }

  function findControlsBlur(root) {
    return root.querySelector("[class*='controlsBlurOverlay']");
  }

  function hideFully(el) {
    try {
      el.style.setProperty('display', 'none', 'important');
      el.style.setProperty('visibility', 'hidden', 'important');
      el.style.setProperty('pointer-events', 'none', 'important');
    } catch (e) {}
  }

  function tapPlayPauseTwice() {
    var btn = document.getElementById('control-play');
    if (!btn) return;
    btn.click();
    setTimeout(function() {
      var btn2 = document.getElementById('control-play');
      if (btn2) btn2.click();
    }, 150);
  }

  function handle() {
    var blur = findBlur(document);
    var controlsBlur = findControlsBlur(document);
    if (blur) hideFully(blur);
    if (controlsBlur) hideFully(controlsBlur);

    var modal = findModal(document);
    if (modal) {
      modal.dataset.pbHandled = '1';
      hideFully(modal);
      tapPlayPauseTwice();
    }
  }

  var observer = new MutationObserver(handle);
  observer.observe(document.documentElement, {
    childList: true, subtree: true, attributes: true, attributeFilter: ['class']
  });

  handle();
})();
"""


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
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument", {"source": JS_WATCHER}
        )
    except WebDriverException as e:
        print(Fore.YELLOW + f"Note: couldn't install CDP auto-injection ({e}). "
                             f"Falling back to Python-only polling." + Style.RESET_ALL)
    return driver


def inject_watcher(driver):
    try:
        driver.execute_script(JS_WATCHER)
    except WebDriverException:
        pass


def _search_current_context(driver) -> bool:
    found_something = False

    for xpath, label in ((BLUR_XPATH, "blur overlay"), (CONTROLS_BLUR_XPATH, "controls blur overlay")):
        elements = driver.find_elements(By.XPATH, xpath)
        elements = [e for e in elements if e.is_displayed()]
        if elements:
            try:
                driver.execute_script(
                    "arguments[0].style.setProperty('display','none','important');"
                    "arguments[0].style.setProperty('visibility','hidden','important');"
                    "arguments[0].style.setProperty('pointer-events','none','important');",
                    elements[0],
                )
                print(f"Hid the {label}.")
                found_something = True
            except (StaleElementReferenceException, WebDriverException):
                pass

    modals = driver.find_elements(By.XPATH, MODAL_XPATH)
    modals = [m for m in modals if m.is_displayed()]
    if modals:
        modal = modals[0]

        try:
            driver.execute_script(
                "arguments[0].style.setProperty('display','none','important');"
                "arguments[0].style.setProperty('visibility','hidden','important');"
                "arguments[0].style.setProperty('pointer-events','none','important');",
                modal,
            )
            print("Hid the modal.")
            found_something = True
        except (StaleElementReferenceException, WebDriverException):
            pass

        try:
            play_button = driver.find_element(By.ID, "control-play")
            play_button.click()
            time.sleep(0.15)
            play_button = driver.find_element(By.ID, "control-play")
            play_button.click()
            print("Double-tapped the play/pause button.")
            found_something = True
        except (NoSuchElementException, ElementClickInterceptedException, ElementNotInteractableException, StaleElementReferenceException, WebDriverException):
            pass

    return found_something


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
    consecutive_errors = 0

    try:
        while True:
            try:
                try_click_continue(driver)
                consecutive_errors = 0

            except StaleElementReferenceException as e:
                print(Fore.YELLOW + f"(ignored, page shifted): {e}" + Style.RESET_ALL)

            except WebDriverException as e:
                print(Fore.RED + Style.BRIGHT +
                      "Browser window seems to have closed or crashed. Stopping. "
                      "Try running the script again!" + Style.RESET_ALL)
                break

            except Exception as e:
                consecutive_errors += 1
                print(Fore.RED + f"Poll error ({consecutive_errors}/{MAX_CONSECUTIVE_ERRORS}): {e}" + Style.RESET_ALL)
                if consecutive_errors >= MAX_CONSECUTIVE_ERRORS:
                    print(Fore.RED + Style.BRIGHT +
                          "Too many errors in a row, stopping to avoid spamming your console. "
                          "Try running the script again!" + Style.RESET_ALL)
                    break

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
        help=f"Python-side fallback poll interval, in seconds (default: {DEFAULT_POLL_INTERVAL})."
    )
    args = parser.parse_args()

    driver = get_driver()
    driver.get("https://songsterr.com")
    inject_watcher(driver)

    watch_loop(driver, poll_interval=args.poll_interval)