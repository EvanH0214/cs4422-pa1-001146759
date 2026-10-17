# Analysis 

## Q1) URL pattern identification

### Q1a) Which URL patterns consumed the most of your crawl budget?

  The URL patterns that consumed most of the crawl budget are digitalcommons.kennesaw.edu, cpe.kennesaw.edu,   facultyweb.kennesaw.edu, calender.kennesaw.edu, campus.kennesaw.edu, and kennesaw.edu using a total of 367 of the 500 URL limit.

### Q1b) Could any of them be unlimited?

  The digitalcommons.kennesaw.edu URL pattern may be unlimited due to our crawler discovering over 30k URL just from this  host.

### Q1c) What did you do about it, and why?

  To circumvent this, we attempted to update our duplicate detection method, however even after the changes our crawler still recognized each of these as a unique URL.

## Q2) Duplicate-content census

### Q2a) How much of what you fetched was duplicate content: byte-identical, near-duplicate, or self-declared duplicate via <link rel="canonical">?

### Q2b) Give three concrete example URL pairs from your crawl, one per category, and say what caused each duplication.


## Q3) What were the five most common ways your fetches failed, ranked by count?

('Exact duplicate', 88), ('Blocked by robots.txt', 61), ('Near duplicate', 11), ('Connection error', 4), ('TLS/SSL error', 2)

## Q4) Which are the top 5 pages by incoming links and the top 5 by outgoing links?


## Q5) Boilerplate identification and removal

### Q5a) How much of each page is boilerplate? Report mean words per page before and after removal, and the top 5 longest pages under each.

  The mean words per page before removal was 1,354.14 and the mean words per page after removal is 1,245.04, the words reduced by approximately 8.05% per page. From the results, it can be seen that the word count for the top 3 longest pages before and after removal was unaffected, while the bottom 2 (4 and 5 from the top 5-- events.kennesaw.edu and csm.kennesaw.edu/chemistry-biochemistry/...) showed reductions of 183 and 307 words, respectively.

## Q6) Text statistics

### Q6a) What are the 30 most frequent words before/after stopwords are removed? Describe the difference.

### Q6b) Does the word-frequency distribution follow Zipf's law? What is the fitted exponent, and where does the distribution depart from it?


## Q7) For 5 randomly sampled pages, what are the top 5 TF-IDF keywords each — and where they come out badly, why, and what fixes it?


## Q8) Politeness evidence

### Q8a) Did your delay constraint actually hold across the run, on every host?

  Yes, the crawl delay held on every host across the entire crawl. This is seen from the stats page which tracks the minimum delay that a thread waited between requests.

### Q8b) How many URLs did robots.txt stop you from fetching, and on which hosts? Pick two of them and quote the rule line that blocked each.

  Robots.txt files stopped our crawler from crawling 61 pages, half of which came from calendar.kennesaw.edu.
  
  https://digitalcommons.kennesaw.edu/do/discipline_browser/disciplines   was blocked by:
  
  Disallow: /disciplines.cgi

  https://ksuweb.kennesaw.edu/~vclincy/    was blocked by:
  
  Disallow: /

### Q8c) What was your overall request rate and total wall-clock time?

  The request rate for our crawler was 1.98 pages per second, and the total wall clock time was 254.93 seconds
