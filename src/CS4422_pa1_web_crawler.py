# import necessary libraries
from pyclbr import Class
import requests
import json
from pathlib import Path
from bs4 import BeautifulSoup
from collections import deque
import w3lib.url
from protego import Protego
import argparse
from urllib.parse import urlparse
import time
import asyncio

# Host class to create host objects
class Host:
    def __init__(self, hostname, robots_txt, delay):
        self.hostname = hostname
        self.robots_txt = robots_txt
        self.delay = delay
        self.host_queue = deque()

    def get_hostname(self):
        return self.hostname

    def get_robots_txt(self):
        return self.robots_txt

    def get_delay(self):
        return self.delay

    def pop_from_queue(self):
        if self.host_queue:
            return self.host_queue.popleft()

    def push_to_queue(self, url):
        self.host_queue.append(url)

    def set_hostname(self, hostname):
        self.hostname = hostname

    def set_robots_txt(self, robots_txt):
        self.robots_txt = robots_txt

    def set_delay(self, delay): 
        self.delay = delay


# Configurations
REQUEST_TIMEOUT = 10
MAX_REDIRECTS = 5
POLITENESS_DELAY = 1  

# Visited Pages
visited = []

# Pages blocked by robots.txt
blocked = []

# List of host objects to store robots.txt information per host
host_list = []

# Create header for requests
headers = {
    "User-Agent": "KSU CS4422-Crawler/1.0"
}

# Corpus file (path)
output_path = Path(__file__).parent.parent/"artifacts"/"pages.jsonl"
output_path.parent.mkdir(parents=True, exist_ok=True)

# Fetch Page method
def fetch_page(url):
    current_url = url
    redirect_urls = []
    for redirect_count in range(MAX_REDIRECTS + 1):
        # Detects redirect loop
        if current_url in redirect_urls:
            print(f"Redirect loop detected at: {current_url}")
        redirect_urls.append(current_url)
        try:
            # sends request and waits 10 seconds before timeout
            response = requests.get(current_url, timeout = REQUEST_TIMEOUT, headers=headers, allow_redirects=False, stream=True)
            if response.status_code == 200:
                return response.text
        # Catches timeouts
        except requests.exceptions.Timeout:
            print(f"Timeout while fetching, at: {current_url}")
        except requests.exceptions.SSLError:
            print(f"TLS/SSL error while fetching, at: {current_url}")
        except requests.exceptions.ConnectionError:
            print(f"Connection failure while fetching, at: {current_url}")
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e} while fetching at: {current_url}")
        

# Fetch robots.txt and parse
def fetch_robots_txt(url):

    # Check if robots.txt has already been fetched for this host
    for hosts in host_list:
        if hosts.get_hostname() == urlparse(url).hostname:
            if hosts.get_robots_txt() is None:
                return True
            else:
                host = hosts
                time.sleep(host.get_delay())

    # robots.txt has not been fetched for this host -- create new host object and task with robots.txt
    else:
        r = requests.get("https://" + urlparse(url).hostname + "/robots.txt", timeout = REQUEST_TIMEOUT, headers=headers)

        # robots.txt was found
        if r.status_code == 200:
            rp = Protego.parse(r.text)

            # If robots.txt has no crawl delay
            if(rp.crawl_delay(user_agent="KSU CS4422-Crawler/1.0") is None):
                host = Host(urlparse(url).hostname, rp, POLITENESS_DELAY)
                host_list.append(host)

            # if robots.txt has a crawl delay greater than POLITENESS_DELAY
            elif (rp.crawl_delay(user_agent="KSU CS4422-Crawler/1.0") > POLITENESS_DELAY):
                host = Host(urlparse(url).hostname, rp, rp.crawl_delay(user_agent="KSU CS4422-Crawler/1.0"))
                host_list.append(host)

            # if robots.txt has a crawl delay less than the POLITENESS_DELAY
            else:
                host = Host(urlparse(url).hostname, rp, POLITENESS_DELAY)
                host_list.append(host)

            host_crawler = asyncio.create_task(crawl(host))
            asyncio.run(host_crawler)

            if rp.can_fetch(url, user_agent="KSU CS4422-Crawler/1.0"):
                return True
            else:
                return False

        # robots.txt was not found
        elif r.status_code == 404:
            host = Host(urlparse(url).hostname, None, POLITENESS_DELAY)
            host_list.append(host)
            host_crawler = asyncio.create_task(crawl(host))
            asyncio.run(host_crawler)
            return True


# Retrieve next URL from frontier
def next_url(host):

    if host.host_queue:
        temp_url = host.pop_from_queue()
        return temp_url
    return None


# dumps the page into corpus file
def dump_corpus(page):
    with output_path.open("a", encoding="utf-8") as corpus_file:
        corpus_file.write(json.dumps(page, ensure_ascii=False) + "\n")


# look here! -- make sure to save fetched page in a page object --> page = fetch_page(url), then dump this into corpus file
# Crawler Loop -- Breadth First Search 
async def crawl(host): 
    while(True):
        # Check if all host frontier is empty
        if not (host.host_queue):
            break

        # Check if max number of pages has been reached
        if len(visited) >= max_pages:
            print("Max number of pages reached.")
            break

        # Get next URL from frontier
        current = next_url(host)

        # Check if current URL has already been visisted
        if current in visited:
            continue

        # Check if current URL is allowed by robots.txt
        if fetch_robots_txt(current):
            # Fetch current page only if allowed by robots.txt
            page_content = fetch_page(current)
            # Continues only if page is successfully fetched
            if page_content is None:
                visited.append(current)
                continue
            # Dumps page content into corpus
            dump_corpus(page_content)
        else:
            print("Robots.txt did not allow this URL " + current)
            blocked.append(current)
            continue

        # Scrape current page for links
        soup = BeautifulSoup(page_content, "html.parser")
        for link in soup.select("a", href=True):

            # Normalize all links
            normalized_link = w3lib.url.canonicalize_url(str(link.get("href")))

            # Remove invalid urls
            if not normalized_link.startswith("http"):
                continue

            # Check if link is within the kennesaw.edu domain
            if "kennesaw.edu" not in normalized_link:
                continue

            # Add links to correct host frontier if not already visited or in frontier
            if normalized_link not in visited:
                if normalized_link not in host.host_queue:
                    fetch_robots_txt(normalized_link)
                else:
                    host.push_to_queue(normalized_link)

        # Add current URL to visited
        visited.append(current)

    await crawl(host)


async def main():
    await crawl(host_list[0])


# Create a parser using argparse
parser = argparse.ArgumentParser(description="seed url and max number of pages")
parser.add_argument("--seed_url", type=str, help="Seed URL")
parser.add_argument("--max_pages", type=int, help="Crawl budget")
args = parser.parse_args()


# Collect user input for seed url and max number of pages if not provided in command line
if not args.seed_url:
    args.seed_url = input("Enter seed URL: ")

if not args.max_pages:
    while True:
        try:
            args.max_pages = int(input("Enter max pages: "))
            break
        except ValueError:
            print("Invalid input")

# Set user input for seed url and max number of pages
first_host = Host(urlparse(args.seed_url).hostname, None, POLITENESS_DELAY)
host_list.append(first_host)
host_list[0].push_to_queue(args.seed_url)
max_pages = args.max_pages
asyncio.run(main())





