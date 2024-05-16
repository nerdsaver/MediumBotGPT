import asyncio
import feedparser
import logging
import random
import json
import time
import cv2
import numpy as np
from pyppeteer import launch
from PIL import ImageGrab, Image
from io import BytesIO

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load configuration from file
CONFIG_FILE_PATH = 'config.json'

with open(CONFIG_FILE_PATH, 'r') as config_file:
    config = json.load(config_file)

EMAIL = config['EMAIL']
PASSWORD = config['PASSWORD']
LOGIN_SERVICE = config['LOGIN_SERVICE']
DRIVER = config['DRIVER']
LIKE_POSTS = config['LIKE_POSTS']
RANDOMIZE_LIKING_POSTS = config['RANDOMIZE_LIKING_POSTS']
MAX_LIKES_ON_POST = config['MAX_LIKES_ON_POST']
COMMENT_ON_POSTS = config['COMMENT_ON_POSTS']
RANDOMIZE_COMMENTING_ON_POSTS = config['RANDOMIZE_COMMENTING_ON_POSTS']
ARTICLE_BLACK_LIST = config['ARTICLE_BLACK_LIST']
FOLLOW_USERS = config['FOLLOW_USERS']
RANDOMIZE_FOLLOWING_USERS = config['RANDOMIZE_FOLLOWING_USERS']
UNFOLLOW_USERS = config['UNFOLLOW_USERS']
RANDOMIZE_UNFOLLOWING_USERS = config['RANDOMIZE_UNFOLLOWING_USERS']
UNFOLLOW_USERS_BLACK_LIST = config['UNFOLLOW_USERS_BLACK_LIST']
USE_RELATED_TAGS = config['USE_RELATED_TAGS']
ARTICLES_PER_TAG = config['ARTICLES_PER_TAG']
VERBOSE = config['VERBOSE']
TAGS = config['TAGS']

# Set the path to the manually downloaded Chromium binary
CHROMIUM_PATH = r'chrome\win64-125.0.6422.60\chrome-win64\chrome.exe'  # Update this path to where you installed Chromium

# Path to the clap button template image
CLAP_BUTTON_TEMPLATE_PATH = 'clap_button_template.png'

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

def find_clap_button(image):
    """Uses template matching to find the clap button in the image."""
    template = cv2.imread(CLAP_BUTTON_TEMPLATE_PATH, 0)
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    result = cv2.matchTemplate(gray_image, template, cv2.TM_CCOEFF_NORMED)
    _, max_val, _, max_loc = cv2.minMaxLoc(result)

    threshold = 0.8
    if max_val >= threshold:
        return max_loc
    return None

async def clap_article(page):
    try:
        screenshot = await take_screenshot(page)
        clap_button_location = find_clap_button(screenshot)

        if clap_button_location:
            logging.info("Clap button found.")
            # Click the clap button between 11 and 23 times
            times_to_clap = random.randint(11, 23)
            for _ in range(times_to_clap):
                await page.mouse.click(clap_button_location[0], clap_button_location[1])
                await asyncio.sleep(random.uniform(0.1, 0.3))  # Random delay between clicks
            logging.info(f'Clapped {times_to_clap} times')
        else:
            logging.info('Clap button not found.')
    except Exception as e:
        logging.error(f'Error while clapping: {e}')

async def read_and_clap_article(browser, url):
    page = await browser.newPage()
    await page.goto(url)
    
    # Scroll down the article
    await page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
    await asyncio.sleep(45)  # Spend 45 seconds on the page

    # Find and click the clap button
    await clap_article(page)
    await page.close()

async def main():
    browser = await launch(headless=False, executablePath=CHROMIUM_PATH)  # Use the specified Chromium path

    articleURLsVisited = []
    tags = TAGS

    for tag in tags:
        articleURLsQueued = fetch_rss_article_links(tag, articleURLsVisited)

        while articleURLsQueued:
            articleURL = articleURLsQueued.pop()
            articleURLsVisited.append(articleURL)
            await read_and_clap_article(browser, articleURL)

    await browser.close()

# Event loop setup for Windows
if __name__ == '__main__':
    asyncio.run(main())
