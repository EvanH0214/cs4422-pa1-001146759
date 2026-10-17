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
import hashlib
from datetime import datetime, timezone
from collections import Counter

# Configurations
REQUEST_TIMEOUT = 10
MAX_REDIRECTS = 5
POLITENESS_DELAY = 1 
MAX_PAGES = 0 
SHINGLE_SIZE = 5
NEAR_DUPE_THRESHOLD = 0.80

# Create visited, blocked, host, and threads list.
visited = []
in_progress = []
blocked = []
host_list = []
host_threads = []
dupes_list = []


# Create locks for threading
host_lock = threading.Lock()
visited_lock = threading.Lock()
blocked_lock = threading.Lock()
threadList_lock = threading.Lock()
pages_lock = threading.Lock()
crawl_lock = threading.Lock()
stats_lock = threading.Lock()
dupe_lock = threading.Lock()
in_link_lock = threading.Lock()


# Create header for requests
headers = {
    "User-Agent": "KSU CS4422-Crawler/1.0"
}


# Tracking variables for artifacts
pages_crawled = 0
pages_fetched = 0
urls_seen = 0
wall_clock_seconds = 0
robots_skips = 0
random_seed = 0
in_links = Counter()


#  Output paths for artifacts
pages_path = Path(__file__).parent.parent/"artifacts"/"pages.jsonl"
pages_path.parent.mkdir(parents=True, exist_ok=True)

crawl_path = Path(__file__).parent.parent/"artifacts"/"crawl.log"
crawl_path.parent.mkdir(parents=True, exist_ok=True)

stats_path = Path(__file__).parent.parent/"artifacts"/"stats.json"
stats_path.parent.mkdir(parents=True, exist_ok=True)


# Clear corpus from previous crawl
pages_path.write_text("", encoding="utf-8")
crawl_path.write_text("", encoding="utf-8")
stats_path.write_text("", encoding="utf-8")


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

    # Check if the host of the url has already been seen
    try: 
        host_match = None

        # Search each host object for the hostname of the url
        for host in host_list:
            if host.get_hostname() == urlparse(url).hostname:
                host_match = host

    # Lock & release before the delay
    finally: 
        host_lock.release()

    # No existing host found for url, error has occured
    if host_match is None:
        return False

    # Fetch the robots.txt for the current host
    rp =  host_match.get_robots_txt()

    # If there is no robot.txt, assume crawl is allowed
    if rp is None:
        time.sleep(host_match.get_delay())
        return True

    # If robots.txt exists and allows crawler
    if rp.can_fetch(url, "KSU CS4422-Crawler/1.0"):
        time.sleep(host_match.get_delay())  
        return True

    # If robots.txt exists and does not allow crawler
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
        # Send an http request for the robots.txt file of the current url host
        r = requests.get("https://" + urlparse(url).hostname + "/robots.txt", timeout = REQUEST_TIMEOUT, headers=headers)

        # Request succeeded 
        if r.status_code == 200:
            return Protego.parse(r.text)

        # Robots.txt was not found
        elif r.status_code == 404:
            return None

        # Catch statement for other status codes
        return None
    
    # Catch statements for errors
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

        # Detect and handle redirect loops
        if current_url in redirect_urls:
            print(f"Redirect loop detected at: {current_url}")
            return None
        redirect_urls.append(current_url)
        try:

            # Sends request and waits 10 seconds before timeout
            response = requests.get(current_url, timeout = REQUEST_TIMEOUT, headers=headers, allow_redirects=False)

            # Status for pages.jsonl
            status = response.status_code

            if response.status_code == 200:
                return response.text, status
            
            # Handle HTTP redirects
            if response.status_code in (301, 302, 303, 307, 308):
                redirect_count+=1

                # Gets the new url
                location = response.headers.get("Location")
                if not location:
                    print(f"Redirect without Location header at: {current_url}")
                    return None, 0
                current_url = urljoin(current_url, location)
                continue

            # Retry if response code is retryable
            if response.status_code == 429 or response.status_code == 503:
                return retry(current_url), status
            
            # Print response code
            print(f"HTTP {response.status_code} while fetching: {current_url}")
            return None, status
        
        # Catch statements for errors
        except requests.exceptions.Timeout:
            print(f"Timeout while fetching, at: {current_url}")
            dump_crawl_log(datetime.now(timezone.utc).isoformat(), "error", current_url, "Timeout", None)
            return None, 0
        except requests.exceptions.SSLError:
            print(f"TLS/SSL error while fetching, at: {current_url}")
            dump_crawl_log(datetime.now(timezone.utc).isoformat(), "error", current_url, "TLS/SSL error", None)
            return None, 0
        except requests.exceptions.ConnectionError:
            print(f"Connection failure while fetching, at: {current_url}")
            dump_crawl_log(datetime.now(timezone.utc).isoformat(), "error", current_url, "Connection error", None)
            return None, 0
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e} while fetching at: {current_url}")
            dump_crawl_log(datetime.now(timezone.utc).isoformat(), "error", current_url, "Request error", None)
            return None, 0


# Retry method
def retry(url):
    try:
        print("retrying fetch: " + url)
        # Request a page
        response = requests.get(url, timeout=REQUEST_TIMEOUT, headers=headers, allow_redirects=False)

        # Successful request
        if response.status_code == 200:
            return response.text

        # Retryable http error codes
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

            # Retry unsuccessful 
            print(f"Retry failed for {url} with status code {response.status_code}")
            dump_crawl_log(datetime.now(timezone.utc).isoformat(), "error", url, "Retry failed", response.status_code)
            return None
        return None

    # Catch statements for errors
    except requests.exceptions.Timeout:
        print(f"Timeout while retrying: {url}")
    except requests.exceptions.SSLError:
        print(f"TLS/SSL error while retrying: {url}")
    except requests.exceptions.ConnectionError:
        print(f"Connection failure while retrying: {url}")
    except requests.exceptions.RequestException as e:
        print(f"Request error while retrying {url}: {e}")


# Detect duplicates method
def detect_exact_dupes(page_content):
    # normalizes and hashes current page text
    normalized_text = " ".join(page_content.lower().split())
    current_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    # compares current page hash with the hash in the records in pages.jsonl for exact match
    pages_lock.acquire()
    try:
        with pages_path.open("r", encoding="utf-8") as corpus_file:
            for line in corpus_file:
                record = json.loads(line)
                if record["content_hash"] == current_hash:
                    return True
    finally:
        pages_lock.release()
    return False

# Generates n-gram shingles where n = SHINGLE_SIZE
def generate_shingles(text, n = SHINGLE_SIZE):
    words = " ".join(text.lower().split()).split()
    shingles = []
    # gets every possible group of SHINGLE_SIZE consecutive words
    for i in range(len(words) - n + 1):
        shingle = tuple(words[i:i+n])
        shingles.append(shingle)
    return shingles

# Computes jaccard similarity
def jaccard_similarity(shingles_a, shingles_b):
    intersection = list(set(shingles_a) & set(shingles_b)) # shared (same) shingles between the two
    union = list(set(shingles_a) | set(shingles_b)) # total unique shingles 
    if not union:
        return 0
    return len(intersection)/len(union)

# detects near duplicates -- true if jaccard similarity of the compared shingles is above the threshold
def detect_near_dupes(page_content):
    # generate shingles for current page
    current_shingles = generate_shingles(page_content, n = SHINGLE_SIZE)

    # hashes normalized text and compares for skipping exact dupes
    normalized_text = " ".join(page_content.lower().split())
    current_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    
    if not current_shingles:
        return False
    # goes through each record, generates shingle, computes and compares jaccard similarity with the threshold
    pages_lock.acquire()
    try:
        with pages_path.open("r", encoding="utf-8") as corpus_file:
                for line in corpus_file:
                    # skips exact dupes
                    record = json.loads(line)
                    if record["content_hash"] == current_hash:
                        continue
                    # prevents error if jsonl contains blank line
                    if not line.strip():
                        continue
                    record = json.loads(line)
                    stored_shingles = generate_shingles(record["text"])
                    similarity = jaccard_similarity(current_shingles, stored_shingles)
                    if similarity >= NEAR_DUPE_THRESHOLD:
                        return True
    finally:
        pages_lock.release()
    return False

# Dump pages into corpus file
def dump_pages(url_canonical, status, fetched_at, title, text, out_links, delay):
    word_count = len(text.split())
    normalized_text = " ".join(text.lower().split())
    # generate sha-256 hash as hexadecimal string
    content_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()
    canonical_link = None

    record = {"url_canonical": url_canonical, "status": status, "fetched_at": fetched_at, "title": title, "text": text, "word_count": word_count, "out_links": out_links, "content_hash": content_hash, "canonical_link": canonical_link, "delay": delay}

    pages_lock.acquire()
    try:
        with pages_path.open("a", encoding="utf-8") as pages_file:
            pages_file.write(json.dumps(record, ensure_ascii=False) + "\n")
    finally:
        pages_lock.release()


# Dump crawl log into corpus 
def dump_crawl_log(ts, event, url, failure_reason, status):

    record = {"ts": ts, "event": event, "url": url, "failure_reason": failure_reason, "status": status}

    crawl_lock.acquire()
    try:
        with crawl_path.open("a", encoding="utf-8") as crawl_file:
            crawl_file.write(json.dumps(record, ensure_ascii=False) + "\n")
    finally:
        crawl_lock.release()


# Dump stats into corpus
def dump_stats(seed_url, page_budget, pages_fetched, urls_seen, max_delay, min_delay, wall_clock_seconds, robots_skips, duplicate_skips, in_links):

    record = {"Seed URL": seed_url, "Page budget": page_budget, "URLS seen": urls_seen, "Max crawl delay": max_delay, "Min crawl delay": min_delay,"Pages_fetched": pages_fetched, "Crawl_time":wall_clock_seconds, "robots_skips": robots_skips, "duplicate_skips": duplicate_skips, "in_links": in_links.most_common(5)}

    stats_lock.acquire()
    try:
        with stats_path.open("a", encoding="utf-8") as stats_file:
            stats_file.write(json.dumps(record, ensure_ascii=False, indent=4) + "\n")
    finally:
        stats_lock.release()


# Scrape page for links and add to host queue
def scrape_page(page_content):
    soup = BeautifulSoup(page_content, "html.parser")

    out_links = 0

    # Parse each link from the raw html
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

        # Check if normalized link is empty
        if normalized is None:
            continue

        in_link_lock.acquire()
        in_links[normalized] += 1
        in_link_lock.release()
        out_links +=1
        
        # Check if normalized url belongs to an existing host-- Critical Section
        host_lock.acquire()
        try:
            existing_host = None

            # Check each host object in host_list
            for host in host_list:
                if host.get_hostname() ==  urlparse(normalized).hostname:
                    existing_host = host
                    break

            # Add url to existing host queue
            if existing_host is not None:
                existing_host.push_to_queue(normalized)
        finally: 
            host_lock.release()

        # If host exists, move to next url
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

            # Checks host again if another thread already created host
            for host in host_list:
                if host.get_hostname() == urlparse(normalized).hostname:
                    existing_host = host
                    break

            # If host already exists, add link to that host
            if existing_host is not None:
                existing_host.push_to_queue(normalized)

            # If host does not already exist, add new_host to host_list and create thread for it
            else:
                # adds this new host to the list + create thread
                host_list.append(new_host)
                new_host.push_to_queue(normalized)
                create_thread(new_host)
        finally:
            host_lock.release()

    return out_links


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

    # Check if url is in dupe list
    dupe_lock.acquire()
    if any(dupe["url"] == normalized_link for dupe in dupes_list):
        dupe_lock.release()
        return None
    dupe_lock.release()

    # Check if url is in any host queue
    host_lock.acquire()
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


# Create thread method
def create_thread(host):
    threadList_lock.acquire()
    try:
        # Assign an identifier and create a new thread to crawl a new host
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

        # Pages.jsonl variables
        url_canonical = None
        status = 0
        title = None
        text = None
        out_links = 0

        # Fetch the next URL from the host's queue
        current = next_url(host)

        url_canonical = current

        if current is None:
            break

        # Check if current url is in visited list or already being crawled or max pages has been reached
        visited_lock.acquire()
        try:
            # Check if the max number of pages has been reached
            if pages_crawled >= MAX_PAGES:
                break

            # Check if current URL has already been visited or in progress - release lock if so
            if current in visited or current in in_progress:
                continue

            in_progress.append(current)
        finally:
            visited_lock.release()

        # Check if current URL is allowed by robots.txt
        if check_robots_txt(current):

            # Fetch current page only if allowed by robots.txt
            page_content, status = fetch_page(current)
            if page_content is None:
                visited_lock.acquire()
                try:
                    in_progress.remove(current)
                finally:
                    visited_lock.release()
                continue

            soup = BeautifulSoup(page_content, "html.parser")
            # stores title extracted from HTML
            title = soup.title.get_text(strip=True) if soup.title else ""
            # stores text extracted from HTML
            text = soup.get_text(" ", strip=True)
            # checks for exact duplicates
            if detect_exact_dupes(text):
                visited_lock.acquire()
                try:
                    dupes_list.append({"url": current, "reason": "exact duplicate"})
                    in_progress.remove(current)
                finally:
                    visited_lock.release()
                    dump_crawl_log(datetime.now(timezone.utc).isoformat(), "skip", current, "Exact duplicate", None)
                continue

            # checks for near duplicates
            if detect_near_dupes(text):
                visited_lock.acquire()
                try:
                    dupes_list.append({"url": current, "reason": "near duplicate"})
                    in_progress.remove(current)
                finally:
                    visited_lock.release()
                    dump_crawl_log(datetime.now(timezone.utc).isoformat(), "skip", current, "Near duplicate", None)
                continue

            # Successfully crawled a page
            visited_lock.acquire()
            try:
                pages_crawled += 1
            finally:
                visited_lock.release()
            

        # URL blocked by robots.txt
        else:
            print("Robots.txt did not allow this URL: " + current)

            # Dump urls which are skipped due to robots.txt
            dump_crawl_log(datetime.now(timezone.utc).isoformat(), "skip", current, "Blocked by robots.txt", None)

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
        out_links = scrape_page(page_content)

        # Remove url from in_progress and append to visited when done
        visited_lock.acquire() 
        in_progress.remove(current)
        visited.append(current)
        visited_lock.release()

        # Dump links which are successfully fetched
        dump_crawl_log(datetime.now(timezone.utc).isoformat(), "fetch", current, "Successfully fetched", status)

        # Dump visited page into pages.jsonl
        dump_pages(url_canonical, status, datetime.now(timezone.utc).isoformat(), title, text, out_links, host.get_delay())

    print(f"{threading.current_thread().name} finished.")

# Main method where code execution starts
def main():
    global MAX_PAGES
    # Tracks the time it takes to run
    start_time = time.perf_counter()

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

    # Create the first host using the seed url
    host =  create_host(seed_url)
    host_list.append(host)
    host.push_to_queue(seed_url)
    print("Created host, " + host.get_hostname())

    # Create first thread with first host
    thread = create_thread(host_list[0])

    # Waits for all created threads to finish-- dynamically joins the growing list of threads
    while True:
        threadList_lock.acquire()
        try:
            # Takes a snapshot of the thread list
            threads = list(host_threads)
        finally:
            threadList_lock.release()

        # Joins the current snapshot list of threads
        for thread in threads:  
            thread.join()

        # Check if all threads have finished, exit loop if so
        threadList_lock.acquire()
        try:
            if all(not thread.is_alive() for thread in host_threads):
                break
        finally:
            threadList_lock.release()

    print("visited: ", visited)
    print(f"number of visited: {len(visited)}")
    elapsed = time.perf_counter() - start_time
    print(f"Crawl finished in {elapsed:.1f} seconds")

    print("dupes list:")
    print(dupes_list)

    # Add links in queues to crawl log with enqueue status
    for host in host_list:
        while host.has_urls():
            dump_crawl_log(datetime.now(timezone.utc).isoformat(), "enqueue", host.pop_from_queue(), "Max pages reached", None)

    # Create stats.json artifact file
    fetched_counter = 0
    seen_counter = 0
    robots_skips_counter = 0
    duplicate_skips_counter = 0

    # Count the number of urls seen, fetched, and skipped
    with crawl_path.open("r", encoding="utf-8") as crawl_log:
        for line in crawl_log:
            record = json.loads(line) 
            if record:
                seen_counter += 1
                if record["event"] == "fetch":
                    fetched_counter += 1
                if record["event"] == "skip":
                    if record["failure_reason"] == "Blocked by robots.txt":
                        robots_skips_counter += 1
                    else:
                        duplicate_skips_counter += 1

    # Record the minimum and maximum delay times
    with pages_path.open("r", encoding="utf-8") as pages_file:
        max_delay = 0
        min_delay = 100
        for line in pages_file:
            record = json.loads(line)
            if record["delay"] > max_delay:
                max_delay = record["delay"]
            if record["delay"] < min_delay:
                min_delay = record["delay"]

    print("Dumping Stats")
    dump_stats(seed_url, MAX_PAGES, fetched_counter, seen_counter, max_delay, min_delay, elapsed, robots_skips_counter, duplicate_skips_counter, in_links)
    # seed_url, page_budget, pages_fetched, urls_seen, max_delay, wall_clock_seconds, robots_skips
main()
