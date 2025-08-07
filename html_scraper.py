import re
import feedparser
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

RSS_FEED = "https://omny.fm/shows/ping-proving-grounds/playlists/podcast.rss"

# Convert episode title to URL slug
def generate_episode_url(title: str) -> str:
    base_url = "https://omny.fm/shows/ping-proving-grounds/"
    slug = title.lower()
    slug = re.sub(r'[:]', '', slug)           # remove colons
    slug = re.sub(r'[^\w\s-]', '', slug)      # remove punctuation
    slug = re.sub(r'\s+', '-', slug)          # spaces to dashes
    return base_url + slug

# Get latest episode title from Apple RSS
def get_latest_episode_from_rss(feed_url=RSS_FEED):
    feed = feedparser.parse(feed_url)
    latest = feed.entries[0]
    return latest.title


def extract_transcript_segments(url: str) -> str:
    # Set up headless Chrome
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)

    try:
        driver.get(url)

        # Wait for the page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Get all text content from the page
        body = driver.find_element(By.TAG_NAME, "body")
        all_text = body.text
        
        print(f"🧱 Found {len(all_text)} characters of text.")
        
        # Extract transcript between "Transcript" and "Show full transcript"
        start_marker = "Transcript"
        end_marker = "Show full transcript"
        
        start_index = all_text.find(start_marker)
        end_index = all_text.find(end_marker)
        
        if start_index != -1 and end_index != -1:
            # Extract text between markers (skip the "Transcript" word itself)
            transcript_text = all_text[start_index + len(start_marker):end_index].strip()
            print(f"✅ Extracted transcript: {len(transcript_text)} characters")
            print(transcript_text)
            return transcript_text
        else:
            print("❌ Could not find transcript markers")
            return all_text

    except Exception as e:
        return f"❌ Error: {e}"

    finally:
        driver.quit()


# Main function
if __name__ == "__main__":
    title = get_latest_episode_from_rss()
    url = generate_episode_url(title)

    print(f"🎙️  Title: {title}")
    print(f"🔗  URL:   {url}")

    transcript = extract_transcript_segments(url)
    print(f"\n📝 Transcript Preview:\n{transcript[:1000]}...\n")
