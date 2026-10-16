import json
import argparse
from pathlib import Path
from collections import Counter


#  Output paths for artifacts
pages_path = Path(__file__).parent.parent/"artifacts"/"pages.jsonl"
pages_path.parent.mkdir(parents=True, exist_ok=True)

crawl_path = Path(__file__).parent.parent/"artifacts"/"crawl.log"
crawl_path.parent.mkdir(parents=True, exist_ok=True)

stats_path = Path(__file__).parent.parent/"artifacts"/"stats.json"
stats_path.parent.mkdir(parents=True, exist_ok=True)


# Analysis stage to answer analysis questions

# Q1. URL pattern identification
# Q1.a Which URL patterns consumed the most of your crawl budget?
def q1a():
    pattern_counter = Counter()

    with pages_path.open("r", encoding="utf-8") as pages_file:
        for line in pages_file:
            record = json.loads(line)
            if "url_canonical" in record:
                urls = record["url_canonical"]
                pattern = urls[:urls.find("kennesaw.edu")]
                pattern_counter[pattern] += 1

        print(pattern_counter)

# Q1.b Could any of them be unlimited?
# Q1.c What did you do about it, and why?


# Q2. Duplicate-content census
# Q2.a How much of what you fetched was duplicate content: byte-identical, near-duplicate, or self-declared duplicate via <link rel="canonical">?
# Q2.b Give three concrete example URL pairs from your crawl, one per category, and say what caused each duplication.


# Q3. What were the five most common ways your fetches failed, ranked by count?
def q3():
    failure_counter = Counter()

    with crawl_path.open("r", encoding="utf-8") as crawl_log:
        for line in crawl_log:
            record = json.loads(line)
            if "failure_reason" in record:
                if record["failure_reason"] == "Max pages reached":
                    continue
                if record["failure_reason"] == "Successfully fetched":
                    continue
                failure_counter[record["failure_reason"]] += 1

        print(failure_counter)


# Q4. Which are the top 5 pages by incoming links and the top 5 by outgoing links?


# Q5. Boilerplate identification and removal
# Q5.a How much of each page is boilerplate? Report mean words per page before and after removal, and the top 5 longest pages under each.
# Generates n-gram shingles where n = 5
def generate_shingles(text, n = 5):
    words = " ".join(text.lower().split()).split()
    shingles = []
    # gets every possible group of SHINGLE_SIZE consecutive words
    for i in range(len(words) - n + 1):
        shingle = tuple(words[i:i+n])
        shingles.append(shingle)
    return shingles

def identify_boilerplate():
    shingles_counter = Counter()
    
    return None

def remove_boilerplate():
    return None

# Q6. Text statistics
# Q6.a What are the 30 most frequent words before/after stopwords are removed? Describe the difference.
# Q6.b Does the word-frequency distribution follow Zipf's law? What is the fitted exponent, and where does the distribution depart from it?


# Q7. For 5 randomly sampled pages, what are the top 5 TF-IDF keywords each — and where they come out badly, why, and what fixes it?


# Q8. Politeness evidence
# Q8.a Did your delay constraint actually hold across the run, on every host?
# Q8.b How many URLs did robots.txt stop you from fetching, and on which hosts? Pick two of them and quote the rule line that blocked each.

# Q8.c What was your overall request rate and total wall-clock time?


print("Running q1:\n")
q1a()