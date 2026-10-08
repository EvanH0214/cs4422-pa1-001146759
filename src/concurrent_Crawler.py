import requests
import json
from pathlib import Path
from bs4 import BeautifulSoup
import argparse
from urllib.parse import urlparse
from urllib.parse import urljoin
from protego import Protego
from collections import deque
import time
import w3lib.url
import threading

# Configurations
REQUEST_TIMEOUT = 10
MAX_REDIRECTS = 5
POLITENESS_DELAY = 1 
MAX_PAGES = 0 # Will be changed by user input


# Create visited, blocked, host, and threads list.
visited = []
in_progress = []
blocked = []
host_list = []
host_threads = []

# Create locks for threading
host_lock = threading.Lock()
visited_lock = threading.Lock()
blocked_lock = threading.Lock()
threadList_lock = threading.Lock()
corpus_lock = threading.Lock()


# For keeping track of # of pages crawled by threads
pages_crawled = 0

# Create header for requests
headers = {
    "User-Agent": "KSU CS4422-Crawler/1.0"
}


# Corpus file (path)
output_path = Path(__file__).parent.parent/"artifacts"/"pages.jsonl"
output_path.parent.mkdir(parents=True, exist_ok=True)

# Clear corpus from previous crawl
output_path.write_text("", encoding="utf-8")

# Host class to create host objects
class Host:
    def __init__(self, hostname, robots_txt, delay):
        self.hostname = hostname
        self.robots_txt = robots_txt
        self.delay = delay
        self.host_queue = deque()
        self.queue_lock = threading.Lock()

    def get_hostname(self):
        return self.hostname

    def get_robots_txt(self):
        return self.robots_txt

    def get_delay(self):
        return self.delay

    def pop_from_queue(self):
        self.queue_lock.acquire()
        try:
            if self.host_queue:
                return self.host_queue.popleft()
        finally:
            self.queue_lock.release()

    def push_to_queue(self, url):
        self.queue_lock.acquire()
        try:
            self.host_queue.append(url)
        finally:
            self.queue_lock.release()

    def has_urls(self):
        self.queue_lock.acquire()
        try:
            return bool(self.host_queue)
        finally:
            self.queue_lock.release()

    def contains_url(self, url):
        self.queue_lock.acquire()
        try:
            return url in self.host_queue
        finally:
            self.queue_lock.release()

# Retrieve next URL from frontier
def next_url(host):
    return host.pop_from_queue()


# Fetch robots.txt and parse
def check_robots_txt(url):
    host_lock.acquire()
    try: 
        host_match = None
        # Search each host object for the hostname of the url
        for host in host_list:
            if host.get_hostname() == urlparse(url).hostname:
                host_match = host
    finally: # lock & release before the delay
        host_lock.release()
    if host_match is None:
        return False
    rp =  host_match.get_robots_txt()
    # If there is no robot.txt, assume crawl is allowed
    if rp is None:
        time.sleep(host_match.get_delay())
        return True
    if rp.can_fetch(url, "KSU CS4422-Crawler/1.0"):
        time.sleep(host_match.get_delay())  
        return True
    else:
        return False


# Create a new host object
def create_host(url):
    # Fetch robots.txt for the host
    robots_txt =  fetch_robots_txt(url)

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
def fetch_robots_txt(url):
    try:
        r = requests.get("https://" + urlparse(url).hostname + "/robots.txt", timeout = REQUEST_TIMEOUT, headers=headers)
        if r.status_code == 200:
            return Protego.parse(r.text)

        elif r.status_code == 404:
            return None
        return None
    # Catches timeouts
    except requests.exceptions.Timeout:
        print(f"Timeout while fetching, at: {url}")
        return None
    except requests.exceptions.SSLError:
        print(f"TLS/SSL error while fetching, at: {url}")
        return None
    except requests.exceptions.ConnectionError:
        print(f"Connection failure while fetching, at: {url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e} while fetching at: {url}")
        return None
    


# Fetch a page and return the content
def fetch_page(url):
    current_url = url
    redirect_urls = []
    redirect_count = 0
    while redirect_count < MAX_REDIRECTS:
        # Detects redirect loop
        if current_url in redirect_urls:
            print(f"Redirect loop detected at: {current_url}")
            return None
        redirect_urls.append(current_url)
        try:
            # Sends request and waits 10 seconds before timeout
            response = requests.get(current_url, timeout = REQUEST_TIMEOUT, headers=headers, allow_redirects=False)
            if response.status_code == 200:
                return response.text
            # Handle HTTP redirects
            if response.status_code in (301, 302, 303, 307, 308):
                redirect_count+=1
                # Gets the new url
                location = response.headers.get("Location")
                if not location:
                    print(f"Redirect without Location header at: {current_url}")
                    return None
                current_url = urljoin(current_url, location)
                continue
            print(f"HTTP {response.status_code} while fetching: {current_url}")
            return None
        # Catches timeouts
        except requests.exceptions.Timeout:
            print(f"Timeout while fetching, at: {current_url}")
            return None
        except requests.exceptions.SSLError:
            print(f"TLS/SSL error while fetching, at: {current_url}")
            return None
        except requests.exceptions.ConnectionError:
            print(f"Connection failure while fetching, at: {current_url}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e} while fetching at: {current_url}")
            return None

# Retry method
def retry(url):
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT, headers=headers, allow_redirects=False)
        if response.status_code == 200:
            return response.text
        if response.status_code == 429 or response.status_code == 503:
            retry_after = response.headers.get("Retry-After")
            # Sleeps for retry-after
            if retry_after:
                try:
                    time.sleep(int(retry_after))
                except ValueError:
                    time.sleep(10)
            else:
                time.sleep(10)
            # Retry the URL once
            response = requests.get(url, timeout=REQUEST_TIMEOUT, headers=headers, allow_redirects=False, stream=True)
            if response.status_code == 200:
                return response.text
            print(f"Retry failed for {url} with status code {response.status_code}")
            return None
        return None
    except requests.exceptions.Timeout:
        print(f"Timeout while retrying: {url}")
    except requests.exceptions.SSLError:
        print(f"TLS/SSL error while retrying: {url}")
    except requests.exceptions.ConnectionError:
        print(f"Connection failure while retrying: {url}")
    except requests.exceptions.RequestException as e:
        print(f"Request error while retrying {url}: {e}")

# Dumps the page into corpus file
def dump_corpus(page):
    corpus_lock.acquire()
    try:
        with output_path.open("a", encoding="utf-8") as corpus_file:
            corpus_file.write(json.dumps(page, ensure_ascii=False) + "\n")
    finally:
        corpus_lock.release()


# Scrape page for links and add to host queue
def scrape_page(page_content):
    soup = BeautifulSoup(page_content, "html.parser")

    for link in soup.find_all("a", href=True):
        # Checks if max pages is hit before getting links
        visited_lock.acquire()
        try:
            if pages_crawled >= MAX_PAGES:
                break
        finally:
            visited_lock.release()
        # Normalize link and check if link is valid
        normalized =  normalize_url(link)

        if normalized is None:
            continue
        # Check if normalized url belongs to an existing host-- Critical Section
        host_lock.acquire()
        try:
            existing_host = None
            for host in host_list:
                if host.get_hostname() ==  urlparse(normalized).hostname:
                    existing_host = host
                    break
            # Add url to existing host queue
            if existing_host is not None:
                existing_host.push_to_queue(normalized)
        finally: 
            host_lock.release()
        if existing_host is not None:
            continue
        # Don't create new hosts/threads once page limit is reached
        visited_lock.acquire()
        try:
            if pages_crawled >= MAX_PAGES:
                break
        finally:
            visited_lock.release()
        
        # Create a new host and add normalized url-- only gets here if host didn't exist
        new_host = create_host(normalized)
        host_lock.acquire()
        try:
            existing_host = None
            # Checks again just in case another thread already created it
            for host in host_list:
                if host.get_hostname() == urlparse(normalized).hostname:
                    existing_host = host
                    break
            if existing_host is not None:
                existing_host.push_to_queue(normalized)
            else:
                # adds this new host to the list + create thread
                host_list.append(new_host)
                new_host.push_to_queue(normalized)
                create_thread(new_host)
        finally:
            host_lock.release()



# Normalize url and validate conditions
def normalize_url(url):

    # Normalize url
    normalized_link = w3lib.url.canonicalize_url(str(url.get("href")))

    # Check if url is in visited list
    visited_lock.acquire()
    try:
        if normalized_link in visited:
            return None
    finally:
        visited_lock.release()

    # Check if url is in blocked list
    blocked_lock.acquire()
    if normalized_link in blocked:
        blocked_lock.release()
        return None
    blocked_lock.release()

    host_lock.acquire()
    # Check if url is in any host queue
    try:
        for host in host_list:
            if host.contains_url(normalized_link):
                return None
    finally:
        host_lock.release()

    # Remove invalid urls
    if not normalized_link.startswith("http"):
        return None

    # Check if link is within the kennesaw.edu domain
    if "kennesaw.edu" not in normalized_link:
        return None

    return normalized_link

def create_thread(host):
    threadList_lock.acquire()
    try:
        thread_number = len(host_threads) + 1
        thread = threading.Thread(target=crawl, args=(host,), name=f"HostThread-{thread_number}")
        host_threads.append(thread)
    finally:
        threadList_lock.release()
        thread.start()
        print(f"Created {thread.name} for host: {host.get_hostname()}")
        return thread


# Main crawler loop
def crawl(host):
    global MAX_PAGES
    global pages_crawled
    while True:
        # fetch the next URL from the host's queue
        current = next_url(host)
        if current is None:
            break

        visited_lock.acquire()
        try:
            # Check if the max number of pages has been reached
            if pages_crawled >= MAX_PAGES:
                break

            # Check if current URL has already been visited or in progress- release lock if so
            if current in visited or current in in_progress:
                continue

            in_progress.append(current)
        finally:
            visited_lock.release()
        # Check if current URL is allowed by robots.txt
        if check_robots_txt(current):

            # Fetch current page only if allowed by robots.txt
            page_content = fetch_page(current)
            if page_content is None:
                visited_lock.acquire()
                try:
                    in_progress.remove(current)
                finally:
                    visited_lock.release()
                continue

            # Successfully crawled a page
            visited_lock.acquire()
            try:
                pages_crawled += 1
            finally:
                visited_lock.release()
            # Dumps page content into corpus
            dump_corpus(page_content)

        else:
            print("Robots.txt did not allow this URL: " + current)
            blocked_lock.acquire()
            try:
                blocked.append(current)
            finally:
                blocked_lock.release()
            visited_lock.acquire()
            try:
                in_progress.remove(current)
            finally:
                visited_lock.release()
            continue 

        # Scrape current page for links and add to host frontier
        scrape_page(page_content)
        visited_lock.acquire() # remove url from in_progress and append to visited when done
        in_progress.remove(current)
        visited.append(current)
        visited_lock.release()
    print(f"{threading.current_thread().name} finished.")


def main():
    global MAX_PAGES
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
    MAX_PAGES = args.max_pages
    seed_url = args.seed_url
    host =  create_host(seed_url)
    host_list.append(host)
    host.push_to_queue(seed_url)
    print("Created host, " + host.get_hostname())

    thread = create_thread(host_list[0])
    # Waits for all created threads to finish-- dynamically joins the growing list of threads
    while True:
        threadList_lock.acquire()
        try:
            # Takes a snapshot of the thread list
            threads = list(host_threads)
        finally:
            threadList_lock.release()

        for thread in threads: # joins the current snapshot list of threads 
            thread.join()

        threadList_lock.acquire()
        try:
            # exits loop only if all threads are done
            if all(not thread.is_alive() for thread in host_threads):
                break
        finally:
            threadList_lock.release()

    print("visited: ", visited)


main()