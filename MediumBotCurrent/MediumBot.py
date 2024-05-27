import asyncio
import feedparser
import logging
import random
import json
import time
import cv2
import numpy as np
import csv
from pyppeteer import launch
from PIL import Image
from PIL import ImageGrab
from io import BytesIO

# Logging Configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Loading Configuration
CONFIG_FILE_PATH = 'config.json'
VISITED_URLS_FILE_PATH = 'visited_urls.csv'

with open(CONFIG_FILE_PATH, 'r') as config_file:
    config = json.load(config_file)

EMAIL = config['EMAIL']
PASSWORD = config['PASSWORD']
TAGS = config['TAGS']

# Setting the Path for Chromium and Template Images
CHROMIUM_PATH = r'chrome\win64-125.0.6422.60\chrome-win64\chrome.exe'
CLAP_BUTTON_TEMPLATE_PATH = r'buttontemps\clap_button_template.png'
BLACK_CLAP_BUTTON_TEMPLATE_PATH = r'buttontemps\black_clap_button_template.png'
FOLLOW_BUTTON_TEMPLATE_BLACK_PATH = r'buttontemps\follow_button_template_black.png'
FOLLOW_BUTTON_TEMPLATE_WHITE_PATH = r'buttontemps\follow_button_template_white.png'

# Loading and Saving Visited URLs
def load_visited_urls():
    """Load visited URLs from a CSV file."""
    visited_urls = set()
    try:
        with open(VISITED_URLS_FILE_PATH, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.reader(file)
            for row in reader:
                visited_urls.add(row[0])
        logging.info(f"Loaded {len(visited_urls)} visited URLs from {VISITED_URLS_FILE_PATH}")
    except FileNotFoundError:
        logging.info('Visited URLs file not found. A new one will be created.')
    return visited_urls

def save_visited_urls(visited_urls):
    """Save visited URLs to a CSV file."""
    try:
        with open(VISITED_URLS_FILE_PATH, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            for url in visited_urls:
                writer.writerow([url])
        logging.info(f"Visited URLs successfully saved to {VISITED_URLS_FILE_PATH}")
    except Exception as e:
        logging.error(f"Error saving visited URLs to {VISITED_URLS_FILE_PATH}: {e}")
        print(f"Error saving visited URLs to {VISITED_URLS_FILE_PATH}: {e}")

# Fetching RSS Article Links
def fetch_rss_article_links(tag, articleURLsVisited):
    logging.info(f'Fetching articles for tag: {tag}')
    feed_url = f'https://medium.com/feed/tag/{tag.replace(" ", "-").lower()}'
    feed = feedparser.parse(feed_url)
    article_urls = []

    if 'entries' not in feed:
        logging.error(f'No entries found in the RSS feed for tag: {tag}')
        return article_urls

    for entry in feed.entries:
        link = entry.link
        if link not in articleURLsVisited:
            logging.info(f'Found new article: {link}')
            article_urls.append(link)

    return article_urls

# Taking a Screenshot
async def take_screenshot(page=None):
    """Takes a screenshot of the current page or the entire screen if page is None."""
    if page is None:
        screenshot = ImageGrab.grab()
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGR2GRAY)
    else:
        screenshot = await page.screenshot(fullPage=True)
        return np.array(Image.open(BytesIO(screenshot)))

# Finding the Follow Button
def find_follow_button(image, template_paths, threshold=0.6):
    """Uses template matching to find the follow button in the image."""
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    for template_path in template_paths:
        template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
        result = cv2.matchTemplate(gray_image, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        logging.info(f"Template matching value for {template_path}: {max_val}")

        if max_val >= threshold:
            return max_loc
    return None

# Clapping on an Article
def find_clap_button(image, template_path):
    """Uses template matching to find the clap button in the image."""
    template = cv2.imread(template_path, 0)
    result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)
    
    logging.info(f"Template matching value for {template_path}: {max_val}")
    
    threshold = 0.51  # Adjusted threshold
    if max_val >= threshold:
        return max_loc
    return None

async def clap_article(page):
    try:
        for attempt in range(5):  # Try up to 5 times
            screenshot = await take_screenshot()

            black_clap_button_location = find_clap_button(screenshot, BLACK_CLAP_BUTTON_TEMPLATE_PATH)
            if black_clap_button_location:
                logging.info("Black clap button found, waiting and clapping once, then skipping to next article.")
                await asyncio.sleep(random.uniform(3, 5))
                template = cv2.imread(BLACK_CLAP_BUTTON_TEMPLATE_PATH, 0)
                h, w = template.shape
                center_x = black_clap_button_location[0] + w // 2
                center_y = black_clap_button_location[1] + h // 2
                await page.mouse.click(center_x, center_y)
                await asyncio.sleep(5)
                return

            clap_button_location = find_clap_button(screenshot, CLAP_BUTTON_TEMPLATE_PATH)
            if clap_button_location:
                logging.info("Clap button found.")
                template = cv2.imread(CLAP_BUTTON_TEMPLATE_PATH, 0)
                h, w = template.shape
                center_x = clap_button_location[0] + w // 2
                center_y = clap_button_location[1] + h // 2

                times_to_clap = random.randint(11, 22)
                for _ in range(times_to_clap):
                    await page.mouse.click(center_x, center_y)
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                logging.info(f'Clapped {times_to_clap} times')
                return
            else:
                logging.info('Clap button not found, scrolling and retrying...')
                await page.evaluate('window.scrollBy(0, window.innerHeight / 2)')
                await asyncio.sleep(2)
        logging.info('Failed to find the clap button after 5 attempts.')
    except Exception as e:
        logging.error(f'Error while clapping: {e}')

# Detecting the Follow Button using Template Matching
async def detect_follow_button(page):
    screenshot = await take_screenshot(page)
    follow_button_location = find_follow_button(screenshot, [FOLLOW_BUTTON_TEMPLATE_BLACK_PATH, FOLLOW_BUTTON_TEMPLATE_WHITE_PATH])
    return follow_button_location

# Detecting the Follow Button using CSS Selector
async def detect_follow_button_css(page):
    try:
        await page.waitForSelector('button.follow', timeout=5000)
        logging.info("Follow button found using CSS selector.")
        return True
    except Exception as e:
        logging.info("Follow button not found using CSS selector.")
        return False

# Clicking the Follow Button
async def click_follow_button(page, location):
    """Simulates a click on the detected 'Follow' button."""
    template = cv2.imread(FOLLOW_BUTTON_TEMPLATE_BLACK_PATH, cv2.IMREAD_GRAYSCALE)
    h, w = template.shape
    center_x = location[0] + w // 2
    center_y = location[1] + h // 2
    viewport_size = await page.evaluate('({ width: window.innerWidth, height: window.innerHeight })')
    logging.info(f"Viewport size: {viewport_size}")

    # Ensure the button is within the viewport
    if 0 <= center_x <= viewport_size['width'] and 0 <= center_y <= viewport_size['height']:
        await page.mouse.click(center_x, center_y)
        logging.info(f"Clicked Follow button at coordinates: ({center_x}, {center_y})")
    else:
        logging.info("Follow button is not within the viewport.")

# Reading and Clapping Articles
async def read_and_clap_article(browser, url, visited_urls):
    page = await browser.newPage()
    await page.goto(url)
    
    await asyncio.sleep(random.uniform(3, 5))

    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    await asyncio.sleep(45)

    await clap_article(page)
    await page.close()

    visited_urls.add(url)
    save_visited_urls(visited_urls)
    logging.info(f'Visited and clapped article: {url}')

# Reading and Following Articles
async def read_and_follow_article(browser, url, visited_urls):
    page = await browser.newPage()
    await page.goto(url)
    await asyncio.sleep(random.uniform(5, 15))  # Add delay of 5-15 seconds before finding and clicking 'Follow'
    
    follow_button_location = await detect_follow_button(page)
    if follow_button_location:
        await click_follow_button(page, follow_button_location)
    else:
        logging.info("Follow button not found using template matching.")

    css_detected = await detect_follow_button_css(page)
    if css_detected:
        logging.info("Follow button found and clicked using CSS selector.")
    else:
        logging.info("Follow button not found using CSS selector.")
    
    await page.close()
    visited_urls.add(url)
    save_visited_urls(visited_urls)
    logging.info(f'Visited and followed article: {url}')

# Logging into Medium via Facebook
async def login_to_medium(page):
    facebook_login_url = (
        "https://www.facebook.com/login.php?skip_api_login=1&api_key=542599432471018&kid_directed_site=0&app_id=542599432471018"
        "&signed_next=1&next=https%3A%2F%2Fwww.facebook.com%2Fv5.0%2Fdialog%2Foauth%3Fclient_id%3D542599432471018%26redirect_uri"
        "%3Dhttps%253A%252F%252Fmedium.com%252Fm%252Fcallback%252Fv2%252Ffacebook%26scope%3Dpublic_profile%252Cemail%26state%3D"
        "facebook-%257Chttps%253A%252F%252Fmedium.com%252F%253Fsource%253Dlogin-------------------------------------%257Clogin%257C9ffcfc83a831949427d0923d0ce8cced"
        "%257Ca6b0fc52708cb75331731cb67d9bb9bf811ca3bad40a361abbd1d2a45c6c79a0%26response_type%3Dtoken%26ret%3Dlogin%26fbapp_pres%3D0%26logger_id%3D56023d27-5a6a-48c7-8a3f-ab12dbd7f8f1%26tp%3Dunspecified"
        "&cancel_url=https%3A%2F%2Fmedium.com%2Fm%2Fcallback%2Fv2%2Ffacebook%3Ferror%3Daccess_denied%26error_code%3D200%26error_description%3DPermissions%2Berror%26error_reason%3Duser_denied%26state%3Dfacebook"
        "-%257Chttps%253A%252F%252Fmedium.com%252F%253Fsource%253Dlogin-------------------------------------%257Clogin%257C9ffcfc83a831949427d0923d0ce8cced%257Ca6b0fc52708cb75331731cb67d9bb9bf811ca3bad40a361abbd1d2a45c6c79a0%23_%3D_&display=page&locale=en_US&pl_dbl=0"
    )
    await page.goto(facebook_login_url)
    logging.info('Logging in to Facebook...')
    
    await page.type('#email', EMAIL)
    await page.type('#pass', PASSWORD)
    await page.click('#loginbutton')

    await page.waitForNavigation()
    logging.info('Logged in successfully.')

# Main Function
async def main():
    browser = await launch(headless=False, executablePath=CHROMIUM_PATH)
    page = await browser.newPage()
    
    await login_to_medium(page)
    
    visited_urls = load_visited_urls()
    articleURLsVisited = list(visited_urls)
    tags = TAGS

    for tag in tags:
        articleURLsQueued = fetch_rss_article_links(tag, articleURLsVisited)

        while articleURLsQueued:
            articleURL = articleURLsQueued.pop()
            if articleURL not in visited_urls:
                await read_and_clap_article(browser, articleURL, visited_urls)
                await read_and_follow_article(browser, articleURL, visited_urls)

    await browser.close()

# Handling Event Loop in Windows
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if str(e) == 'Event loop is closed':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(main())
