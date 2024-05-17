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
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration from file
CONFIG_FILE_PATH = 'config.json'
VISITED_URLS_FILE_PATH = 'visited_urls.csv'  # File path for storing visited URLs

with open(CONFIG_FILE_PATH, 'r') as config_file:
    config = json.load(config_file)

EMAIL = config['EMAIL']
PASSWORD = config['PASSWORD']
TAGS = config['TAGS']

# Set the path to the manually downloaded Chromium binary
CHROMIUM_PATH = r'chrome\win64-125.0.6422.60\chrome-win64\chrome.exe'  # Update this path to where you installed Chromium

# Path to the clap button template images
CLAP_BUTTON_TEMPLATE_PATH = 'clap_button_template.png'
BLACK_CLAP_BUTTON_TEMPLATE_PATH = 'black_clap_button_template.png'

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

def fetch_rss_article_links(tag, articleURLsVisited):
    logging.info(f'Fetching articles for tag: {tag}')
    feed_url = f'https://medium.com/feed/tag/{tag.replace(" ", "-").lower()}'  # Convert spaces to hyphens and to lower case
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

async def take_screenshot(page):
    """Takes a screenshot of the current page."""
    screenshot = await page.screenshot(fullPage=True)
    return np.array(Image.open(BytesIO(screenshot)))

def find_clap_button(image, template_path, threshold=0.51):
    """Uses template matching to find the clap button in the image."""
    template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    result = cv2.matchTemplate(gray_image, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    logging.info(f"Template matching value for {template_path}: {max_val}")

    if max_val >= threshold:
        return max_loc
    return None

async def clap_article(page):
    try:
        for attempt in range(5):  # Try up to 5 times
            screenshot = await take_screenshot(page)
            
            # Check for black clap button first
            black_clap_button_location = find_clap_button(screenshot, BLACK_CLAP_BUTTON_TEMPLATE_PATH)
            if black_clap_button_location:
                logging.info("Black clap button found, waiting and clapping once, then skipping to next article.")
                await asyncio.sleep(random.uniform(3, 5))  # Wait between 3 and 5 seconds
                template = cv2.imread(BLACK_CLAP_BUTTON_TEMPLATE_PATH, 0)
                h, w = template.shape
                center_x = black_clap_button_location[0] + w // 2
                center_y = black_clap_button_location[1] + h // 2
                await page.mouse.click(center_x, center_y)
                await asyncio.sleep(5)  # Wait for 5 seconds before moving to the next article
                return

            # If black clap button is not found, look for the regular clap button
            clap_button_location = find_clap_button(screenshot, CLAP_BUTTON_TEMPLATE_PATH)
            if clap_button_location:
                logging.info("Clap button found.")
                # Calculate the center of the clap button
                template = cv2.imread(CLAP_BUTTON_TEMPLATE_PATH, 0)
                h, w = template.shape
                center_x = clap_button_location[0] + w // 2
                center_y = clap_button_location[1] + h // 2

                # Click the clap button between 11 and 22 times
                times_to_clap = random.randint(11, 22)
                for _ in range(times_to_clap):
                    await page.mouse.click(center_x, center_y)
                    await asyncio.sleep(random.uniform(0.1, 0.3))  # Random delay between clicks
                logging.info(f'Clapped {times_to_clap} times')
                return
            else:
                logging.info('Clap button not found, scrolling and retrying...')
                # Scroll down slightly
                await page.evaluate('window.scrollBy(0, window.innerHeight / 2)')
                await asyncio.sleep(2)  # Wait for 2 seconds before retrying
        logging.info('Failed to find the clap button after 5 attempts.')
    except Exception as e:
        logging.error(f'Error while clapping: {e}')

async def read_and_clap_article(browser, url, visited_urls):
    page = await browser.newPage()
    await page.goto(url)
    
    # Wait for a few seconds to ensure the page has fully loaded
    await asyncio.sleep(random.uniform(3, 5))  # Adjust the delay as needed

    # Scroll down the article
    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    await asyncio.sleep(45)  # Spend 45 seconds on the page

    # Find and click the clap button
    await clap_article(page)
    await page.close()

    # Add the URL to the visited list and save immediately
    visited_urls.add(url)
    save_visited_urls(visited_urls)
    logging.info(f'Visited and clapped article: {url}')

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

async def main():
    browser = await launch(headless=False, executablePath=CHROMIUM_PATH)  # Use the specified Chromium path
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

    await browser.close()

# Handle event loop issue in Windows
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if str(e) == 'Event loop is closed':
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(main())
