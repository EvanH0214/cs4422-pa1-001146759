# PA1-WebCrawling
## 0. Overview
### First Stage
If running from commandline, enter "python" followed by the filename "CS4422_pa1_web_crawler.py followed by seed url and max pages parameters with the "--seed_url" and "--max_pages" designations given

EX: python CS4422_pa1_web_crawler.py --seed_url https://www.kennesaw.edu --max_pages 500

If parameters are not given, terminal will prompt for them one by one
If running from terminal, run file and enter seed url and max pages when prompted
Crawler should take between 250 and 400 seconds, but may be longer
Once crawler is finished, artifacts available under artifacts folder

### Second Stage
Run analysis.py and wait for results to be printed
This stage may take several minutes -- it is not broken, just slow
## 1. Group Members
Name: Evan Horn - netid: 001146759 - EvanH0214


Name: Darren Ni - netid: 001153212 - WiseChimera


Name: Sedat Sekizkardes- netid: 001124578 - Sedat8kk 

## 2. Contributions
Evan Horn - q1, q3, q8, artifacts, host class, URL normalization/canonicalization, page scraping, per-host delay, user-agent, robots.txt fetching, main crawler loop

Darren Ni - q2, q5, q6, q7, threading/parallelization, retry, duplicate detection/removal, error handling, boilerplate removal, main crawler loop

Sedat Sekizkardes - q4

## 3. Instructions
### 3.1 Architecture Overview
#### Query-Parameter Policy
Parameters created to store each URL seen by the crawler exactly once. URLs are either visited successfully, blocked by robots.txt, duplicate content, encountered an error, or left in the frontier once page limit is reached.
#### Trailing-Slash Policy
URLs with a trailing slash are treated the same as the URL without a traling slash
### 3.2 How to run the crawler
Python Version:
3.14.7

Install packages:

#### Stage One - Crawling
requests, json, Path from pathlib, BeautifulSoup from bs4, argparse, urlparse from urllib.parse, urljoin from urllib.parse, Protego from protego, deque from collections, time, w3lib.url, threading, hashlib, datetime from datetime, timezone from datetime, Counter from collections
#### Stage Two - Analysis
json, argparse, Path from pathlib, Counter from collections, urlparse from urllib.parse, ENGLISH_STOP_WORDS from sklearn.feature_extraction.text, re, numpy as np, plt from matplotlib.pyplot, BeautifulSoup from bs4
