import getpass
import json
import os
import pickle
import re
import time
from html.parser import HTMLParser
from typing import Optional

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from tqdm import tqdm

UNIQ_FILENAME = "uniq_urls.pickle"
GRAPH_FILENAME = "friend_graph.pickle"

# Facebook credentials
try:
    facebook_credentials_file = open("facebook_credentials.json")
    credentials: dict = json.load(facebook_credentials_file)
    username = credentials["username"]
    password = credentials["password"]
except:
    username = input("Facebook username:")
    password = getpass.getpass("Password:")

chrome_options = webdriver.ChromeOptions()
prefs = {"profile.default_content_setting_values.notifications": 2}
chrome_options.add_experimental_option("prefs", prefs)
driver = webdriver.Chrome(options=chrome_options)

driver.get("https://www.facebook.com/")

# authenticate to facebook account
elem = driver.find_element(By.ID, "email")
elem.send_keys(username)
elem = driver.find_element(By.ID, "pass")
elem.send_keys(password)
elem.send_keys(Keys.RETURN)
time.sleep(5)

SCROLL_PAUSE_TIME = 2


def get_fb_page(url: str):
    time.sleep(2)
    driver.get(url)

    # Get scroll height
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        # Wait to load page
        time.sleep(SCROLL_PAUSE_TIME)

        # Calculate new scroll height and compare with last scroll height
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height
    html_source = driver.page_source
    return html_source


def find_friend_from_url(url: str) -> Optional[str]:
    if re.search("/friends_mutual", url) is not None:
        return re.search(
            r"https://www.facebook.com/([^/?]+)/friends_mutual", url
        ).group(1)
    else:
        return re.search(r"https://www.facebook.com/([^/?]+)", url).group(1)


class MyHTMLParser(HTMLParser):
    urls = []

    def error(self, message):
        pass

    def handle_starttag(self, tag, attrs):
        # Only parse the 'anchor' tag.
        if tag == "a":
            # Check the list of defined attributes.
            for name, value in attrs:
                # If href is defined, print it.
                if name == "href":
                    if re.search("https://www.facebook.com/", value) is not None:
                        if (
                            re.search(
                                "facebook.com/pages|facebook.com/stories|facebook.com/events|facebook.com/groups|facebook.com/notifications|profile.php",
                                value,
                            )
                            is None
                        ):
                            self.urls.append(value)


my_url = f"https://www.facebook.com/{username}/friends"

if os.path.isfile(UNIQ_FILENAME):
    with open(UNIQ_FILENAME, "rb") as f:
        uniq_urls = pickle.load(f)
    print(f"We loaded {uniq_urls} unique friends")
else:
    friends_page = get_fb_page(my_url)
    parser = MyHTMLParser()
    parser.feed(friends_page)
    uniq_urls = set(parser.urls)

    print(f"We found {len(uniq_urls)} friends pages, saving them in a file")

    if uniq_urls:
        with open(UNIQ_FILENAME, "wb") as f:
            pickle.dump(uniq_urls, f)

friend_graph = {}

if os.path.isfile(GRAPH_FILENAME):
    with open(GRAPH_FILENAME, "rb") as f:
        friend_graph = pickle.load(f)
    print(f"Loaded existing graph, found {len(friend_graph.keys())} keys")


for url in tqdm(uniq_urls):
    friend_username = find_friend_from_url(url)
    print(f"Found friend: {friend_username}")

    if friend_username in friend_graph.keys():
        continue

    friend_graph[friend_username] = [username]
    mutual_url = f"https://www.facebook.com/{friend_username}/friends_mutual"
    mutual_page = get_fb_page(mutual_url)

    parser = MyHTMLParser()
    parser.urls = []
    parser.feed(mutual_page)
    mutual_friends_urls = set(parser.urls)
    print("Found {} urls".format(len(mutual_friends_urls)))

    for mutual_url in mutual_friends_urls:
        mutual_friend = find_friend_from_url(mutual_url)
        friend_graph[friend_username].append(mutual_friend)

    with open(GRAPH_FILENAME, "wb") as f:
        pickle.dump(friend_graph, f)

driver.quit()
