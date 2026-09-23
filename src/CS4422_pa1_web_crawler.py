# import necessary libraries
import requests
import json
from pathlib import Path

# Crawler Frontier
frontier = []

# Visited Pages
visited = []

# Corpus file (path)
output_path = Path("artifacts/pages.jsonl")
output_path.parent.mkdir(parents=True, exist_ok=True)

# Max number of pages
max_pages = 500

# Set Seed URL and add to frontier
seed_url = "https://www.kennesaw.edu/"
frontier.append(seed_url)

# Fetch Page method
def fetch_page(url):
    # sends request and waits 10 seconds before timeout
    response = requests.get(url, timeout = 10)
    if response.status_code == 200:
        return response.text
    return None

# Retrieve next URL from frontier
def next_url():
    if frontier:
        temp_url = frontier.pop(0)
        return temp_url
    return None

# dumps the page into corpus file
def dump_corpus(page):
    with output_path.open("a", encoding="utf-8") as corpus_file:
        corpus_file.write(json.dumps(page, ensure_ascii=False) + "\n")


# look here! -- make sure to save fetched page in a page object --> page = fetch_page(url), then dump this into corpus file

# Crawler Loop -- Breadth First Search  -- probably place into a method
while(True):
    # Check if frontier is empty
    if not frontier:
        break

    # Check if max number of pages has been reached
    if len(visited) >= max_pages:
        break

    # Get next URL from frontier
    #current = next_url()

    # Check if current URL has already been visisted

    # Scrape current page for links

    # Normalize all links and add to frontier

    # Remove current URL from frontier and add to visited