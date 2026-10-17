Q1)

  Q1a)

  The URL patterns that consumed most of the crawl budget are digitalcommons.kennesaw.edu, cpe.kennesaw.edu,   facultyweb.kennesaw.edu, calender.kennesaw.edu, campus.kennesaw.edu, and kennesaw.edu using a total of 367 of the 500 URL limit.

  Q1b)

  The digitalcommons.kennesaw.edu URL pattern may be unlimited due to our crawler discovering over 30k URL just from this  host.

  Q1c)

  To circumvent this, we attempted to update our duplicate detection method, however even after the changes our crawler still recognized each of these as a unique URL.

Q2)

  Q2a)

  Q2b)


Q3)

('Exact duplicate', 88), ('Blocked by robots.txt', 61), ('Near duplicate', 11), ('Connection error', 4), ('TLS/SSL error', 2)

Q4)


Q5)


Q6)

  Q6a)

  Q6b)


Q7)


Q8)

  Q8a)

  Yes, the crawl delay held on every host across the entire crawl. This is seen from the stats page which tracks the minimum delay that a thread waited between requests.

  Q8b)

  Robots.txt files stopped our crawler from crawling 61 pages, half of which came from calendar.kennesaw.edu.
  
  https://digitalcommons.kennesaw.edu/do/discipline_browser/disciplines   was blocked by:
  
  Disallow: /disciplines.cgi

  https://ksuweb.kennesaw.edu/~vclincy/    was blocked by:
  
  Disallow: /

  Q8c)

  The request rate for our crawler was 1.98 pages per second, and the total wall clock time was 254.93 seconds
