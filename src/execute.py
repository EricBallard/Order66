from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as ec
from selenium import webdriver

from win32api import GetSystemMetrics

import threading
import keyboard
import time

######################### CONFIG #########################
reddit_username = "username"
reddit_password = "password"

driver_path = r"C:\path\to\chromedriver.exe"

##########################################################

# Formatted URL ripped literally from the website's login buton
# Goes to login page, if success redirects to user's profile page
reddit_url = (
    "https://www.reddit.com/login/?dest=https%3A%2F%2Fwww.reddit.com%2Fuser%2F"
    + reddit_username
)

deleted_comments = 0

deleted_posts = 0

stopping = False


def get_screen_size():
    return (GetSystemMetrics(0), GetSystemMetrics(1))


def login(driver):
    try:
        user_input = driver.find_element(By.ID, "loginUsername")
        pass_input = driver.find_element(By.ID, "loginPassword")

        submit_input = driver.find_element(
            By.XPATH, "//*[contains(@class, 'AnimatedForm__submitButton')]"
        )
    except Exception as e:
        print("Failed to find element due to ", e)
        return False

    user_input.send_keys(reddit_username)
    pass_input.send_keys(reddit_password)

    submit_input.submit()
    return True


def get_delete_btn(driver):
    menu_items = driver.find_elements(By.XPATH, "//button[@role = 'menuitem']")
    items_len = len(menu_items)
    return menu_items[items_len - 1]


def get_confirm_btn(driver):
    confirm_btn = driver.find_element(By.XPATH, "//button[text()='Delete']")
    return confirm_btn


def get_chrome_driver():
    # Define browser options, disable intrusive notifications
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--disable-notifications")

    # Open browser
    driver = webdriver.Chrome(service=Service(
        driver_path), options=chrome_options)

    # Size broser window
    driver.set_window_size(800, 600)

    # Get native screen size (windows only)
    screen_size = get_screen_size()
    print("Screen Size: ", screen_size)

    # Center browser window on screen
    driver.set_window_position(
        screen_size[0] / 2 - 400, screen_size[1] / 2 - 300)

    return driver


def purge_reddit_profile(driver):
    global deleted_comments
    global stopping

    try:
        # Navigate to page, wait for load
        print("Loading Reddit Profile...")
        current_url = driver.current_url
        driver.get(reddit_url)

        wait = WebDriverWait(driver, 5)
        wait.until(ec.url_changes(current_url))
        current_url = driver.current_url

        print("Logging in...")
        success = login(driver)
        bad_cred = False

        # Attempted to login
        if success:
            # Validate
            print("Verifing success...")

            try:
                wait.until(ec.url_changes(current_url))
            except Exception:
                # Timeout - bad login
                bad_cred = True
                success = False

            # Logged In!
            if success:
                print("Logged In!")
                driver.execute_script("document.title = 'PRESS ESC TO STOP'")
                driver.execute_script(
                    "window.history.pushState(null, document.title, 'PRESS_ESC_TO_STOP')"
                )

                # Profile interest pop up every time even if I configure it, idk close it
                pop_up = wait.until(
                    ec.presence_of_element_located(
                        (By.CSS_SELECTOR, "[aria-label=Close]")
                    )
                )

                # Close pop up, if found
                if pop_up is not None:
                    print("Detected profile pop-up, closing...")
                    pop_up.click()
                    time.sleep(1)

                driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                
                # Query for comments on profile page
                comment_info = driver.find_elements(
                    By.CSS_SELECTOR, "div[data-testid='comment-top-meta']"
                )

                cmnts_len = len(comment_info)
                print("Found {} comments".format(cmnts_len))

                actions = ActionChains(driver)

                # Iterate comments
                for i in range(cmnts_len):
                    comment = comment_info[i]
                    info = comment.get_attribute("innerText")

                    if info is None:
                        pass

                    # Process string, find author
                    info = info.replace("\n", " ")
                    name_len = len(reddit_username)

                    # Validate this comment is from us
                    if info[:name_len] == reddit_username:
                        # YES - Trim user name from string
                        info = info[name_len:]

                        # Remove occasional 'Op' in info, further clean
                        info = info.lower().replace("op", "").replace("· ", "")

                        # Partition 'cleaned' string
                        head, sep, tail = info.partition("point")

                        # Extract points, cast to int for compare
                        points = int(head)

                        # Delete comments with low/negative kArMa
                        if points < 5:
                            # Clean comment info string
                            posted = (
                                tail[1:].strip(
                                ) if tail[:1] == "s" else tail.strip()
                            )
                            print(
                                f"Deleting comment from {posted} ({points} karama) ")

                            # Query for the "options" button on each deletable comment/post on profile
                            parent_div = comment.find_element(By.XPATH, "./..")
                            more_options = parent_div.find_element(
                                By.XPATH,
                                ".//button[contains(@aria-label, 'more options')]",
                            )

                            # Cache default button color, temporarily change to orange to hightlight focus
                            color = more_options.value_of_css_property(
                                "background-color"
                            )
                            driver.execute_script(
                                "arguments[0].style.backgroundColor = 'orange';",
                                more_options,
                            )

                            print(more_options.location)

                            # Scroll element into focus and click via js
                            try:
                                actions.move_to_element(more_options).perform()
                            except Exception:
                                print(
                                    "Failed to scroll to element... forcing with javascript.")
                                driver.execute_script(
                                    "arguments[0].scrollIntoView(true);", more_options)

                            driver.execute_script(
                                "arguments[0].click();", more_options)

                            # Wait in seconds - allow user to iterrupt
                            wait_time = 0

                            while wait_time > 0:
                                if stopping:
                                    raise Exception()

                                wait_time -= 1
                                time.sleep(1)

                            # Click delete
                            del_btn = get_delete_btn(driver)
                            driver.execute_script(
                                "arguments[0].click();", del_btn)

                            # time.sleep(1)

                            conf_btn = get_confirm_btn(driver)
                            driver.execute_script(
                                "arguments[0].click();", conf_btn)
                            deleted_comments += 1

                            # Reset color of button
                            driver.execute_script(
                                "arguments[0].style.backgroundColor = '" +
                                color + "';",
                                more_options,
                            )

        # Print info
        if success:
            print(f"Deleted {deleted_comments} comments!")
        else:
            print("Failed to logged in - closing browser...")

            if bad_cred:
                print("Check the configured username and password.")
            else:
                print("Check for errors, the website may have been updated.")

    except Exception as e:
        if not stopping:
            print("Error while processing: ", e)
    finally:
        driver.quit()
        stopping = True


def listen_for_key(driver):
    global stopping

    while True:
        try:
            if keyboard.is_pressed("esc"):
                print("USER INTERRUPTED | Stopping...")
                stopping = True
                driver.quit()
                break
            elif stopping:
                break
        except:
            break


# Main()
if __name__ == "__main__":
    driver = get_chrome_driver()

    browser_thread = threading.Thread(
        target=purge_reddit_profile, args=(driver,))
    browser_thread.start()

    key_thread = threading.Thread(target=listen_for_key, args=(driver,))
    key_thread.start()
