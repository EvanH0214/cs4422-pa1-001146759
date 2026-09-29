# import necessary libraries
import requests
import json
from pathlib import Path
from bs4 import BeautifulSoup
from collections import deque
import w3lib.url
from protego import Protego
import argparse

# Crawler Frontier
frontier = deque()

# Visited Pages
visited = []

# Create header for requests
headers = {
    "User-Agent": "KSU CS4422-Crawler/1.0"
}

# Corpus file (path)
output_path = Path("artifacts/pages.jsonl")
output_path.parent.mkdir(parents=True, exist_ok=True)


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
            args.max_pages = int(input("Enter max pages :"))
            break
        except ValueError:
            print("Invalid input")

# Set user input for seed url and max number of pages    
frontier.append(args.seed_url)
max_pages = args.max_pages

# Fetch Page method
def fetch_page(url):
    # sends request and waits 10 seconds before timeout
    response = requests.get(url, timeout = 10, headers=headers)
    if response.status_code == 200:
        return response.text
    return None

# Fetch robots.txt and parse
def fetch_robots_txt(url):
    r = requests.get(url + "/robots.txt", timeout = 10, headers=headers)
    if r.status_code == 200:
        rp = Protego.parse(r.text)
        if rp.can_fetch("*", user_agent="KSU CS4422-Crawler/1.0"):
            return True
        else:
            return False

# Retrieve next URL from frontier
def next_url():
    if frontier:
        temp_url = frontier.popleft()
        return temp_url
    return None

# dumps the page into corpus file
def dump_corpus(page):
    with output_path.open("a", encoding="utf-8") as corpus_file:
        corpus_file.write(json.dumps(page, ensure_ascii=False) + "\n")


# look here! -- make sure to save fetched page in a page object --> page = fetch_page(url), then dump this into corpus file

# Crawler Loop -- Breadth First Search  
while(True):
    # Check if frontier is empty
    if not frontier:
        break

    # Check if max number of pages has been reached
    if len(visited) >= max_pages:
        print("Max number of pages reached.")
        break

    # Get next URL from frontier
    current = next_url()

    # Check if current URL has already been visisted
    if current in visited:
        continue

    # Check if current URL is allowed by robots.txt
    if fetch_robots_txt(current):

        # Fetch current page only if allowed by robots.txt
        page_content = fetch_page(current)

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

        # Add links to frontier if not already visited or in frontier
        if link.get("href") not in visited and link.get("href") not in frontier:
            frontier.append(link.get("href"))


    # Add current URL to visited
    visited.append(current)

    print("\n\nVisited: ", visited)