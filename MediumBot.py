import os
import random
import sys
import time
import json
import logging

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from bs4 import BeautifulSoup
from summarization import fetch_initial_comment, refine_comment_with_groq, refine_comment_further

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

def Launch():
    if 'chrome' not in DRIVER.lower() and 'firefox' not in DRIVER.lower() and 'phantomjs' not in DRIVER.lower():
        logging.info('Choose your browser:')
        logging.info('[1] Chrome')
        logging.info('[2] Firefox/Iceweasel')
        logging.info('[3] PhantomJS')

        while True:
            try:
                browserChoice = int(input('Choice? '))
            except ValueError:
                logging.info('Invalid choice.')
            else:
                if browserChoice not in [1, 2, 3]:
                    logging.info('Invalid choice.')
                else:
                    break

        StartBrowser(browserChoice)
    elif 'chrome' in DRIVER.lower():
        StartBrowser(1)
    elif 'firefox' in DRIVER.lower():
        StartBrowser(2)
    elif 'phantomjs' in DRIVER.lower():
        StartBrowser(3)

def StartBrowser(browserChoice):
    if browserChoice == 1:
        logging.info('Launching Chrome')
        browser = webdriver.Chrome()
    elif browserChoice == 2:
        logging.info('Launching Firefox/Iceweasel')
        browser = webdriver.Firefox()
    elif browserChoice == 3:
        logging.info('Launching PhantomJS')
        browser = webdriver.PhantomJS()

    if SignInToService(browser):
        logging.info('Success!')
        MediumBot(browser)
    else:
        soup = BeautifulSoup(browser.page_source, 'lxml')
        if soup.find('div', {'class': 'alert error'}):
            logging.error('Error! Please verify your username and password.')
        elif browser.title == '403: Forbidden':
            logging.error('Medium is momentarily unavailable. Please wait a moment, then try again.')
        else:
            logging.error('Please make sure your config is set up correctly.')

    browser.quit()

def SignInToService(browser):
    serviceToSignWith = LOGIN_SERVICE.lower()
    signInCompleted = False
    logging.info('Signing in...')

    browser.get('https://medium.com/m/signin?redirect=https%3A%2F%2Fmedium.com%2F')

    if serviceToSignWith == 'twitter':
        signInCompleted = SignInToTwitter(browser)
    elif serviceToSignWith == 'facebook':
        signInCompleted = SignInToFacebook(browser)
    else:
        logging.error(f'Unsupported login service: {serviceToSignWith}. Please choose either Facebook or Twitter.')

    return signInCompleted

def SignInToTwitter(browser):
    signInCompleted = False
    try:
        WebDriverWait(browser, 20).until(
            EC.element_to_be_clickable((By.CLASS_NAME, 'button--twitter'))
        ).click()

        WebDriverWait(browser, 20).until(
            EC.presence_of_element_located((By.XPATH, '//input[@id="username_or_email"]'))
        ).send_keys(EMAIL)

        WebDriverWait(browser, 20).until(
            EC.presence_of_element_located((By.XPATH, '//input[@id="password"]'))
        ).send_keys(PASSWORD)

        WebDriverWait(browser, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//input[@id="allow"]'))
        ).click()
        
        time.sleep(3)  # Additional wait time for any post-click actions on the website.
        signInCompleted = True
    except NoSuchElementException as e:
        logging.error(f'Element not found during Twitter sign-in: {e}')
    except TimeoutException as e:
        logging.error(f'Timeout during Twitter sign-in: {e}')
    except Exception as e:
        logging.error(f'Unexpected error during Twitter sign-in: {e}')

    return signInCompleted

def SignInToFacebook(browser):
    signInCompleted = False
    try:
        logging.info('Navigating to Facebook login page...')
        browser.get('https://medium.com/m/connect/facebook?state=facebook-%7Chttps%3A%2F%2Fmedium.com%2F%3Fsource%3Dlogin-------------------------------------%7Clogin&source=login-------------------------------------')

        logging.info('Entering email...')
        WebDriverWait(browser, 20).until(
            EC.presence_of_element_located((By.XPATH, '//input[@id="email"]'))
        ).send_keys(EMAIL)

        logging.info('Entering password...')
        WebDriverWait(browser, 20).until(
            EC.presence_of_element_located((By.XPATH, '//input[@id="pass"]'))
        ).send_keys(PASSWORD)

        logging.info('Clicking login button...')
        WebDriverWait(browser, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//button[@id="loginbutton"]'))
        ).click()
        
        logging.info('Waiting for post-login actions...')
        time.sleep(5)  # Additional wait time for any post-click actions on the website.
        signInCompleted = True
    except NoSuchElementException as e:
        logging.error(f'Element not found during Facebook sign-in: {e}')
    except TimeoutException as e:
        logging.error(f'Timeout during Facebook sign-in: {e}')
    except Exception as e:
        logging.error(f'Unexpected error during Facebook sign-in: {e}')

    return signInCompleted

def MediumBot(browser):
    tagURLsQueued = []
    tagURLsVisitedThisLoop = []
    articleURLsVisited = []

    while True:
        tagURLsQueued = ScrapeUsersFavoriteTagsUrls(browser)

        while tagURLsQueued:
            articleURLsQueued = []
            shuffle(tagURLsQueued)
            tagURL = tagURLsQueued.pop()
            tagURLsVisitedThisLoop.extend(tagURL)

            tagURLsQueued.extend(NavigateToURLAndScrapeRelatedTags(browser, tagURL, tagURLsVisitedThisLoop))
            articleURLsQueued = ScrapeArticlesOffTagPage(browser, articleURLsVisited)

            while articleURLsQueued:
                if len(articleURLsVisited) > 530000000:
                    articleURLsVisited = []

                logging.info(f'Tags in Queue: {len(tagURLsQueued)} Articles in Queue: {len(articleURLsQueued)}')
                articleURL = articleURLsQueued.pop()
                articleURLsVisited.extend(articleURL)
                LikeCommentAndFollowOnPost(browser, articleURL)

                if UNFOLLOW_USERS:
                    if not RANDOMIZE_UNFOLLOWING_USERS:
                        UnFollowUser(browser)
                    elif random.choice([True, False]):
                        UnFollowUser(browser)

        logging.info('Pause for 1 hour to wait for new articles to be posted')
        tagURLsVisitedThisLoop = []  # Reset the tags visited
        time.sleep(3 + (random.randrange(0, 10)) * 5)

def ScrapeUsersFavoriteTagsUrls(browser):
    browser.get('https://medium.com/me/following/tags')
    time.sleep(5)
    soup = BeautifulSoup(browser.page_source, 'lxml')
    tagURLS = []
    logging.info('Gathering your favorited tags')

    try:
        for div in soup.find_all('div', class_='u-tableCell u-verticalAlignMiddle'):
            for a in div.find_all('a'):
                if a['href'] not in tagURLS:
                    tagURLS.append(a['href'])
                    if VERBOSE:
                        logging.info(a['href'])
    except Exception as e:
        logging.error(f'Exception thrown in ScrapeUsersFavoriteTagsUrls(): {e}')

    if not tagURLS or USE_RELATED_TAGS:
        if not tagURLS:
            logging.info('No favorited tags found. Grabbing the suggested tags as a starting point.')

        try:
            for div in soup.find_all('div', class_='u-sizeFull u-paddingTop10 u-paddingBottom10 u-borderBox'):
                for a in div.find_all('a'):
                    if a['href'] not in tagURLS:
                        tagURLS.append(a['href'])
                        if VERBOSE:
                            logging.info(a['href'])
        except Exception as e:
            logging.error(f'Exception thrown in ScrapeArticlesOffTagPage(): {e}')

    logging.info('')
    return tagURLS

def NavigateToURLAndScrapeRelatedTags(browser, tagURL, tagURLsVisitedThisLoop):
    browser.get(tagURL)
    tagURLS = []

    if USE_RELATED_TAGS and tagURL:
        logging.info(f'Gathering tags related to : {tagURL}')
        soup = BeautifulSoup(browser.page_source, 'lxml')

        try:
            for ul in soup.find_all('ul', class_='tags--postTags'):
                for li in ul.find_all('li'):
                    a = li.find('a')
                    if 'followed' not in a['href'] and a['href'] not in tagURLsVisitedThisLoop:
                        tagURLS.append(a['href'])
                        if VERBOSE:
                            logging.info(a['href'])
        except Exception as e:
            logging.error(f'Exception thrown in NavigateToURLAndScrapeRelatedTags(): {e}')
        logging.info('')

    return tagURLS

def ScrapeArticlesOffTagPage(browser, articleURLsVisited):
    articleURLS = []
    logging.info(f'Gathering your articles for the tag : {browser.current_url}')

    WebDriverWait(browser, 20).until(
        EC.element_to_be_clickable((By.XPATH, '//a[contains(text(),"Latest stories")]'))
    ).click()
    time.sleep(2)

    for _ in range(1, ARTICLES_PER_TAG // 10):
        ScrollToBottomAndWaitForLoad(browser)

    try:
        for a in browser.find_elements(By.XPATH, '//div[@class="postArticle postArticle--short js-postArticle js-trackedPost"]/div[2]/a'):
            if a.get_attribute('href') not in articleURLsVisited:
                if VERBOSE:
                    logging.info(a.get_attribute('href'))
                articleURLS.append(a.get_attribute('href'))
    except Exception as e:
        logging.error(f'Exception thrown in ScrapeArticlesOffTagPage(): {e}')

    logging.info('')
    return articleURLS

def LikeCommentAndFollowOnPost(browser, articleURL):
    browser.get(articleURL)

    if browser.title not in ARTICLE_BLACK_LIST:
        if FOLLOW_USERS:
            if not RANDOMIZE_FOLLOWING_USERS:
                FollowUser(browser)
            elif random.choice([True, False]):
                FollowUser(browser)

        ScrollToBottomAndWaitForLoad(browser)

        if LIKE_POSTS:
            if not RANDOMIZE_LIKING_POSTS:
                LikeArticle(browser)
            elif random.choice([True, False]):
                LikeArticle(browser)

        if COMMENT_ON_POSTS:
            if not RANDOMIZE_COMMENTING_ON_POSTS:
                CommentOnArticle(browser)
            elif random.choice([True, False]):
                CommentOnArticle(browser)

        logging.info('')

def LikeArticle(browser):
    likeButtonXPath = '//div[@data-source="post_actions_footer"]/button'
    numLikes = 0

    try:
        numLikesElement = browser.find_element(By.XPATH, likeButtonXPath + '/following-sibling::button')
        numLikes = int(numLikesElement.text)
    except Exception as e:
        logging.error(f'Exception thrown when trying to get number of likes: {e}')

    try:
        likeButton = browser.find_element(By.XPATH, likeButtonXPath)
        buttonStatus = likeButton.get_attribute('data-action')

        if likeButton.is_displayed() and buttonStatus == 'upvote':
            if numLikes < MAX_LIKES_ON_POST:
                logging.info(f'Liking the article: "{browser.title}"')
                likeButton.click()
            else:
                logging.info(f'Article "{browser.title}" has more likes than your threshold.')
        else:
            logging.info(f'Article "{browser.title}" is already liked.')
    except Exception as e:
        logging.error(f'Exception thrown when trying to like the article: {browser.current_url} Error: {e}')

def CommentOnArticle(browser):
    usersName = browser.find_element(By.XPATH, '//div[@class="avatar"]/img').get_attribute('alt')
    alreadyCommented = False

    try:
        alreadyCommented = browser.find_element(By.XPATH, f'//a[text()[contains(.,"{usersName}")]]').is_displayed()
    except Exception as e:
        logging.error(f'Exception thrown when checking if already commented: {e}')

    if 'medium.com' in browser.current_url:
        if not alreadyCommented:
            post_content = extract_post_content(browser)
            try:
                summary = fetch_initial_comment()
                refined_summary = refine_comment_with_groq(summary)
                final_summary = refine_comment_further(refined_summary)
                logging.info(f'Summary: {final_summary}')

                logging.info(f'Commenting "{final_summary}" on the article: "{browser.title}"')
                commentButton = browser.find_element(By.XPATH, '//button[@data-action="respond"]')
                commentButton.click()
                time.sleep(5)
                browser.find_element(By.XPATH, '//div[@role="textbox"]').send_keys(final_summary)
                time.sleep(20)
                browser.find_element(By.XPATH, '//button[@data-action="publish"]').click()
                time.sleep(5)
            except Exception as e:
                logging.error(f'Exception thrown when trying to comment on the article: {browser.current_url} Error: {e}')
        else:
            logging.info(f'We have already commented on this article: {browser.title}')
    else:
        logging.info(f'Cannot comment on an article that is not hosted on Medium.com')

def extract_post_content(browser):
    try:
        post_content = browser.find_element(By.XPATH, '//article').text
        return post_content
    except Exception as e:
        logging.error(f'Exception thrown when trying to extract post content: {e}')
        return ''

def FollowUser(browser):
    '''
    Follow the user whose article you have already currently navigated to.
    browser: selenium webdriver used to interact with the browser.
    '''
    try:
        logging.info(f'Following the user: {browser.find_element(By.XPATH, "//a[@rel='author cc:attributionUrl']").text}')
        browser.find_element(By.XPATH, '//button[@data-action="toggle-subscribe-user"]').click()
    except Exception as e:
        logging.error(f'Exception thrown when trying to follow the user: {e}')

def UnFollowUser(browser):
       # ... (rest of the code)

       time.sleep(3)
       try:
           user_name = WebDriverWait(browser, 10).until(
               EC.presence_of_element_located((By.XPATH, "//h1[@class='hero-title']"))
           ).text
           logging.info(f'Unfollowing the user: {user_name}') 
           browser.find_element(By.XPATH, '//button[@data-action="toggle-subscribe-user"]').click()
       except Exception as e:
           logging.error(f'Exception thrown when trying to unfollow a user: {e}') 


def ScrollToBottomAndWaitForLoad(browser):
    '''
    Scroll to the bottom of the page and wait for the page to perform its lazy loading.
    browser: selenium webdriver used to interact with the browser.
    '''
    browser.execute_script('window.scrollTo(0, document.body.scrollHeight);')
    time.sleep(4)

if __name__ == '__main__':
    Launch()
