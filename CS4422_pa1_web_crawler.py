# import necessary libraries

# Crawler Frontier
frontier = []

# Visited Pages
visited = []

# Set Seed URL and add to frontier


# Fetch Page method
def fetch_page():
    return None

# Retrieve next URL from frontier
def next_url():
    if not frontier.isEmpty():
        temp_url = frontier.pop(0)
        return temp_url
    return None


# Crawler Loop -- Breadth First Search  -- probably place into a method
while(True):
    # Check if frontier is empty
    if frontier.isEmpty():
        break

    # Get next URL from frontier
    #current = next_url()

    # Check if current URL has already been visisted

    # Scrape current page for links

    # Normalize all links and add to frontier

    # Remove current URL from frontier and add to visited