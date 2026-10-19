# PA1-WebCrawling
## 0. Overview
This project tasks us with creating a web crawler that retrieves pages within the Kennesaw State University domain, processing the pages into a document store. The objective is to scrape 500 web pages, beginning with a selection of seed URLs of your choosing.

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
If running from commandline, enter "python" followed by the filename "CS4422_pa1_web_crawler.py followed by seed url and max pages parameters with the "--seed_url" and "--max_pages" designations given

EX: python CS4422_pa1_web_crawler.py --seed_url https://www.kennesaw.edu --max_pages 500

If parameters are not given, terminal will prompt for them one by one
If running from terminal, run file and enter seed url and max pages when prompted
Crawler should take between 250 and 400 seconds, but may be longer
Once crawler is finished, artifacts available under artifacts folder
#### Stage Two - Analysis
Run analysis.py and wait for results to be printed
This stage may take several minutes -- it is not broken, just slow
