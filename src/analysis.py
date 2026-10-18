import json
import argparse
from pathlib import Path
from collections import Counter
from urllib.parse import urlparse
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS
import re
import numpy as np
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
import math
import random

# Configurations
BOILERPLATE_THRESHOLD = 0.2
SHINGLE_SIZE = 5

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
def q1b():
    url_counter = Counter()

    with crawl_path.open("r", encoding="utf-8") as crawl_log:
        for line in crawl_log:
            record = json.loads(line)
            if "url" in record:
                urls = record["url"]
                pattern = urls[:urls.find("kennesaw.edu")]
                url_counter[pattern] += 1

    print("Top 10 domains by count:\n")
    print(url_counter.most_common(10))

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

        print(failure_counter.most_common(5))


# Q4. Which are the top 5 pages by incoming links and the top 5 by outgoing links?
def q4():
    # Incoming
    print("Incoming:")
    with stats_path.open("r", encoding="utf-8") as stats_file:
        record = json.load(stats_file)
        print(record["in_links"])

    # Outgoing
    print("\nOutgoing:")
    with stats_path.open("r", encoding="utf-8") as stats_file:
            record = json.load(stats_file)
            print(record["out_links"])


# Q5. Boilerplate identification and removal
# Q5.a How much of each page is boilerplate? Report mean words per page before and after removal, and the top 5 longest pages under each.
def generate_shingles(text, n = 5):
    words = " ".join(text.lower().split()).split()
    shingles = []
    # gets every possible group of SHINGLE_SIZE consecutive words
    for i in range(len(words) - n + 1):
        shingle = tuple(words[i:i+n])
        shingles.append(shingle)
    return shingles

def identify_boilerplate(pages, threshold = BOILERPLATE_THRESHOLD):
    shingles_counter = Counter()
    # counts each shingle only once per page
    for page in pages:
        unique_shingles = []
        for shingle in generate_shingles(page, SHINGLE_SIZE):
            if shingle not in unique_shingles:
                unique_shingles.append(shingle)
        # updates shingles count in the counter
        shingles_counter.update(unique_shingles)
    # returns empty list if there're no pages
    if len(pages)==0:
        return []
    # find how often the shingle appears across all pages, if greater than threshold (50%), add to boilerplate
    boilerplate_shingles = []
    for shingle, count in shingles_counter.items():
        fraction = count/len(pages)
        if fraction > threshold:
            boilerplate_shingles.append(shingle)
    return boilerplate_shingles


def remove_boilerplate(text, boilerplate_shingles):
    # normalizes and splits text into list of words
    words = " ".join(text.lower().split()).split()
    # list of false values that act as a mask for words
    word_removal = [False] * len(words)

    # finds words that belongs to boilerplate shingles
    for i in range(len(words) - SHINGLE_SIZE + 1):
        shingle = tuple(word.lower() for word in words[i:i + SHINGLE_SIZE])
        if shingle in boilerplate_shingles:
            for j in range(i, i + SHINGLE_SIZE):
                word_removal[j] = True

    # keeps the words that aren't in boilerplate 
    cleaned_words = []
    for i in range(len(words)):
        if not word_removal[i]:
            cleaned_words.append(words[i])
    return " ".join(cleaned_words)


def q5():
    pages = []
    urls = []
    with pages_path.open("r", encoding="utf-8") as corpus_file:
        # appends records in json to the corresponding pages/urls list
        for line in corpus_file:
            record = json.loads(line)
            pages.append(record["text"])
            urls.append(record["url_canonical"])
        # finds the boilerplate shingles
        boilerplate_shingles = identify_boilerplate(pages)
        # counts words in each page before boilerplate removal, tied to url
        before_counts = {url: len(text.split()) for url, text in zip(urls, pages)}
        # calls remove_boilerplate on every page
        cleaned_pages = [remove_boilerplate(text, boilerplate_shingles) for text in pages]
        # counts words in each page after boilerplate removal, tied to url
        after_counts = {url: len(text.split()) for url, text in zip(urls, cleaned_pages)}
        print("Total pages:", len(pages))
        print("Boilerplate shingles found:", len(boilerplate_shingles))
        print("Total words removed:", sum(before_counts.values()) - sum(after_counts.values()))
        print("Mean words before removal: ", sum(before_counts.values())/len(before_counts))
        print("Mean words after removal: ", sum(after_counts.values())/len(after_counts))
        # sorts before and after lists of dict based on count, in descending order
        sorted_before = [{"url": url, "count": count} for url, count in sorted(before_counts.items(), key=lambda x: x[1], reverse=True)]
        sorted_after = [{"url": url, "count": count} for url, count in sorted(after_counts.items(), key=lambda x: x[1], reverse=True)]

        # prints top 5 longest pages before & after removal
        print(f"\nTop 5 longest pages before removal:\n"
              f"1. {sorted_before[0]}\n"
              f"2. {sorted_before[1]}\n"
              f"3. {sorted_before[2]}\n"
              f"4. {sorted_before[3]}\n"
              f"5. {sorted_before[4]}"
              )
        
        print(f"\nTop 5 longest pages after removal:\n"
                      f"1. {sorted_after[0]}\n"
                      f"2. {sorted_after[1]}\n"
                      f"3. {sorted_after[2]}\n"
                      f"4. {sorted_after[3]}\n"
                      f"5. {sorted_after[4]}"
                      )

# Q6. Text statistics
# Q6.a What are the 30 most frequent words before/after stopwords are removed? Describe the difference.
# Q6.b Does the word-frequency distribution follow Zipf's law? What is the fitted exponent, and where does the distribution depart from it?

def remove_stopwords(words, stopwords):
    # Boolean mask-- same method as q5
    word_removal = [False] * len(words)

    # mark stop words in words
    for i in range(len(words)):
        if words[i] in stopwords:
            word_removal[i] = True

    # keeps the non-stopwords
    cleaned_words = []
    for i in range(len(words)):
        if not word_removal[i]:
            cleaned_words.append(words[i])
    return cleaned_words

def q6a():
    pages = []
    urls = []
    with pages_path.open("r", encoding="utf-8") as corpus_file:
        for line in corpus_file:
            record = json.loads(line)
            pages.append(record["text"])
            urls.append(record["url_canonical"])

    # counts words before and after removal
    before_counter = Counter()
    after_counter = Counter()
    stopwords = set(ENGLISH_STOP_WORDS)
    for page in pages:
        # extract lowercase words containing at least 2 characters
        words = re.findall(r"\b[a-z]{2,}\b", page.lower())

        # count original words
        before_counter.update(words)

        # removes stopwords 
        cleaned_words = remove_stopwords(words, stopwords)

        # count the cleaned words
        after_counter.update(cleaned_words)

    print("\nTop 30 words before stopword removal:")
    print(before_counter.most_common(30))

    print("\nTop 30 words after stopword removal:")
    print(after_counter.most_common(30))

def q6b():
    word_counter = Counter()

    with pages_path.open("r", encoding="utf-8") as corpus_file:
        for line in corpus_file:
            record = json.loads(line)
            text = record.get("text", "")

            # uses the same word extraction as Q6a
            words = re.findall(r"\b[a-z]{2,}\b", text.lower())
            word_counter.update(words)

    # sorts frequencies from highest to lowest
    frequencies = np.array(sorted(word_counter.values(), reverse=True))

    # assign ranks to the sorted frequencies: 1 = most frequent word
    ranks = np.arange(1, len(frequencies) + 1)

    # fit log10(frequency) = intercept + slope * log10(rank)
    log_ranks = np.log10(ranks)
    log_frequencies = np.log10(frequencies)

    slope, intercept = np.polyfit(log_ranks, log_frequencies, 1)
    # fitted exponent = negative slope
    exponent = -slope


    print("\nQ6b: Zipf's Law Analysis")
    print("Total word occurrences:", int(frequencies.sum()))
    print("Distinct words:", len(frequencies))
    print(f"Fitted exponent: {exponent:.4f}")

    # plots frequencies and the fitted line
    fitted_frequencies = 10 ** (intercept + slope * log_ranks)

    plt.figure(figsize=(9, 6))
    plt.loglog(ranks, frequencies, label="Observed word frequencies")
    plt.loglog(ranks, fitted_frequencies, "--", label=f"Zipf line (s = {exponent:.3f})")

    plt.xlabel("Word rank")
    plt.ylabel("Word frequency")
    plt.title("Word Frequency Distribution (Zipf's Law)")
    plt.legend()
    plt.grid(True, which="both", alpha=0.2)
    plt.tight_layout()
    plt.savefig("zipf_distribution.png", dpi=150)
    plt.show()

# Q7. For 5 randomly sampled pages, what are the top 5 TF-IDF keywords each — and where they come out badly, why, and what fixes it?
# finds tf-idf using the textbook formula
def q7():
    pages = []
    urls = []

    # load the corpus
    with pages_path.open("r", encoding="utf-8") as corpus_file:
        for line in corpus_file:
            record = json.loads(line)
            pages.append(record.get("text", ""))
            urls.append(record.get("url_canonical", "Unknown URL"))

    if not pages:
        print("No pages found.")
        return

    # tokenize each page 
    tokenized_pages = []
    for text in pages:
        words = re.findall(r"\b[a-z]{2,}\b", text.lower())
        tokenized_pages.append(words)

    # counts how many documents (pages) contain each term (doc frequency)
    document_frequency = Counter()
    for words in tokenized_pages:
        document_frequency.update(set(words))
    total_pages = len(tokenized_pages)

    # calculates the tf-idf scores for every document
    tfidf_scores = []
    for words in tokenized_pages:
        term_counts = Counter(words)
        total_terms = len(words)
        scores = {}

        if total_terms > 0:
            for term, count in term_counts.items():
                # calculates term frequency
                tf = count / total_terms
                # document frequency
                df = document_frequency[term]
                # calculates inverse document frequency (idf)
                idf = math.log10(total_pages / df)
                # tf-idf score = tf * idf
                scores[term] = tf * idf
        tfidf_scores.append(scores)

    # takes random sample with random seed 42
    rng = random.Random(42)
    rsample_pages = rng.sample(range(len(pages)),min(5, len(pages)))

    print("\nQ7: TF-IDF using the textbook formula")
    # prints the top 5 tf-idf keywords for the random sample pages
    for index in rsample_pages:
        top_terms = sorted(tfidf_scores[index].items(),key=lambda item: item[1],reverse=True)[:5]
        print(f"\nURL: {urls[index]}")
        print("Top 5 keywords:")
        for term, score in top_terms:
            print(f"  {term}: {score:.3f}")


# Q8. Politeness evidence
# Q8.a Did your delay constraint actually hold across the run, on every host?
def q8a():
    with stats_path.open("r", encoding="utf-8") as stats_file:
            record = json.load(stats_file)
            print("Min delay: " + str(record["Min crawl delay"]))


# Q8.b How many URLs did robots.txt stop you from fetching, and on which hosts? Pick two of them and quote the rule line that blocked each.
def q8b():
    robots_skips_counter = Counter()

    # Count the number of urls seen, fetched, and skipped
    with crawl_path.open("r", encoding="utf-8") as crawl_log:
        for line in crawl_log:
            record = json.loads(line) 
            if record:
                if record["failure_reason"] == "Blocked by robots.txt":
                    robots_skips_counter[urlparse(record["url"]).hostname] +=1
                    robots_skips_counter[record["url"]] +=1

        print(robots_skips_counter)
        print("Total skips: " + str(robots_skips_counter.total()))

# Q8.c What was your overall request rate and total wall-clock time?
def q8c():
    with stats_path.open("r", encoding="utf-8") as stats_file:
            record = json.load(stats_file)
            print("Crawl time: " + str(record["Crawl_time"]))
            

print("Running q1a:\n")
#q1a()

print("\n\nRunning q1b:\n")
#q1b()

print("\n\nRunning q3:\n")
#q3()

print("\n\nRunning q4:\n")
#q4()

print("\n\nRunning q5:\n")
#q5()

print("\n\nRunning q6a:\n")
#q6a()

print("\n\nRunning q6b:\n")
#q6b()

print("\n\nRunning q7:\n")
q7()

print("\n\nRunning q8a:\n")
#q8a()

print("\n\nRunning q8b:\n")
#q8b()

print("\n\nRunning q8c:\n")
#q8c()