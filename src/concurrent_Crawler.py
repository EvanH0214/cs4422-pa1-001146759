import asyncio
import requests
import json
from pathlib import Path
from bs4 import BeautifulSoup
import argparse
from urllib.parse import urlparse
from protego import Protego
from collections import deque
import w3lib.url

# Configurations
REQUEST_TIMEOUT = 10
MAX_REDIRECTS = 5
POLITENESS_DELAY = 1 


# Create visited, blocked, and host object lists
visited = []
blocked = []
host_list = []


# Create header for requests
headers = {
    "User-Agent": "KSU CS4422-Crawler/1.0"
}


# Corpus file (path)
output_path = Path(__file__).parent.parent/"artifacts"/"pages.jsonl"
output_path.parent.mkdir(parents=True, exist_ok=True)


# Host class to create host objects
class Host:
    async def __init__(self, hostname, robots_txt, delay):
        self.hostname = hostname
        self.robots_txt = robots_txt
        self.delay = delay
        self.host_queue = deque()

    async def get_hostname(self):
        return self.hostname

    async def get_robots_txt(self):
        return self.robots_txt

    async def get_delay(self):
        return self.delay

    async def pop_from_queue(self):
            if self.host_queue:
                return self.host_queue.popleft()

    async def push_to_queue(self, url):
            self.host_queue.append(url)


# Add a url to the visited list
async def append_to_visited(url):
    visited.append(url)


# Add a url to the blocked list
async def append_to_blocked(url):
    blocked.append(url)


# Retrieve next URL from frontier
async def next_url(host):
    if host.host_queue:
        temp_url = await host.pop_from_queue()
        return temp_url
    return None


# Fetch robots.txt and parse
async def check_robots_txt(url):

    # Search each host object for the hostname of the url
    for host in host_list:
        if host.get_hostname() == urlparse(url).hostname:
            rp = await host.get_robots_txt()
            if rp.can_fetch(url, user_agent="KSU CS4422-Crawler/1.0"):
                await asyncio.sleep(host.get_delay())  
                return True
            else:
                return False


# Create a new host object
async def create_host(url):
    # Fetch robots.txt for the host
    robots_txt = await fetch_robots_txt(url)

    if robots_txt is not None:
        # If robots.txt has no crawl delay
        if robots_txt.crawl_delay(user_agent="KSU CS4422-Crawler/1.0") is None:
            host = Host(urlparse(url).hostname, robots_txt, POLITENESS_DELAY)

        # If robots.txt has a crawl delay greater than POLITENESS_DELAY
        elif (robots_txt.crawl_delay(user_agent="KSU CS4422-Crawler/1.0") > POLITENESS_DELAY):
            host = Host(urlparse(url).hostname, robots_txt, robots_txt.crawl_delay(user_agent="KSU CS4422-Crawler/1.0"))
            
        # If robots.txt has a crawl delay less than the POLITENESS_DELAY
        else:
            host = Host(urlparse(url).hostname, robots_txt, POLITENESS_DELAY)

    # Robots.txt was not found
    else:
        host = Host(urlparse(url).hostname, None, POLITENESS_DELAY)

    return host


# Fetch robots.txt for a host
async def fetch_robots_txt(url):
    r = requests.get("https://" + urlparse(url).hostname + "/robots.txt", timeout = REQUEST_TIMEOUT, headers=headers)
    if r.status_code == 200:
        return Protego.parse(r.text)

    elif r.status_code == 404:
        return None


# Fetch a page and return the content
async def fetch_page(url):
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


# Dumps the page into corpus file
async def dump_corpus(page):
    with output_path.open("a", encoding="utf-8") as corpus_file:
        corpus_file.write(json.dumps(page, ensure_ascii=False) + "\n")


# Scrape page for links and add to host queue
async def scrape_page(page_content, host):
    soup = BeautifulSoup(page_content, "html.parser")
    for link in await soup.find_all("a", href=True):

        # Normalize link and check if link is valid
        normalized = await normalize_url(link)

        if normalized is None:
            continue

        else:
            # Check if normalized url belongs to an existing host
            for host in host_list:
                if host.get_hostname == await urlparse(normalized).hostname:
                    host.push_to_queue(normalized)
                    return True

            # Create a new host and add normalized url
            new_host = create_host(normalized)
            host_list.append(new_host)
            new_host.push_to_queue(normalized)
            asyncio.create_task(new_host)
            return False



# Normalize url and validate conditions
async def normalize_url(url):

    # Normalize url
    normalized_link = w3lib.url.canonicalize_url(str(url.get("href")))

    # Check if url is in visited or blocked lists
    if normalized_link in visited:
        return None

    if normalized_link in blocked:
        return None

    # Check if url is in any host queue
    for host in host_list:
        if normalized_link in host.host_queue:
            return None

    # Remove invalid urls
    if not normalized_link.startswith("http"):
        return None

    # Check if link is within the kennesaw.edu domain
    if "kennesaw.edu" not in normalized_link:
        return None

    return normalized_link


# Main crawler loop
async def crawl(host):
    while host.host_queue:

        # Check if the max number of pages has been reached
        if len(visited) >= max_pages:
            print("Max number of pages reached.")
            break

        # fetch the next URL from the host's queue
        current = next_url(host)

        # Check if current URL has already been visisted
        if current in visited:
            continue

        # Check if current URL is allowed by robots.txt
        if  await check_robots_txt(current):

            # Fetch current page only if allowed by robots.txt
            page_content = await fetch_page(current)

            # Check if page content is empty
            if page_content is None:
                await visited.append(current)
                continue

            # Dumps page content into corpus
            await dump_corpus(page_content)

        else:
            print("Robots.txt did not allow this URL: " + current)
            await blocked.append(current)
            continue 

        # Scrape current page for links and add to host frontier
        if await scrape_page(page_content, host) is False:
            continue

        else:
            visited.append(current)


async def main():
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
    max_pages = args.max_pages
    seed_url = args.seed_url
    host = await create_host(seed_url)
    await host_list.append(host)

    print("Created host, " + host.get_hostname())

    await crawl(host_list[0])


asyncio.run(main())