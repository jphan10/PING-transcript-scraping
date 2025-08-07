import re
import feedparser
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import streamlit as st
from docx import Document
import tempfile
import os
import subprocess
try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False

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

# Get all episodes from RSS feed
def get_all_episodes_from_rss(feed_url=RSS_FEED):
    feed = feedparser.parse(feed_url)
    episodes = []
    for entry in feed.entries:
        episodes.append({
            'title': entry.title,
            'url': generate_episode_url(entry.title)
        })
    return episodes


def extract_transcript_segments(url: str) -> str:
    """
    Extract transcript using multiple approaches for maximum compatibility
    """
    # First try: Simple requests approach (fastest)
    try:
        response = requests.get(url)
        if response.status_code == 200:
            # Try to find transcript in static HTML
            text = response.text
            
            # Look for the transcript API URL in the page data
            import json
            if '"TranscriptUrl":"' in text:
                # Extract the transcript URL from the JSON data
                start_idx = text.find('"TranscriptUrl":"')
                if start_idx != -1:
                    start_idx += len('"TranscriptUrl":"')
                    end_idx = text.find('"', start_idx)
                    if end_idx != -1:
                        transcript_url = text[start_idx:end_idx]
                        # Replace escaped characters
                        transcript_url = transcript_url.replace('\\/', '/')
                        
                        # Try to fetch the actual transcript
                        try:
                            transcript_response = requests.get(transcript_url)
                            if transcript_response.status_code == 200:
                                transcript_data = transcript_response.json()
                                # Extract transcript segments
                                if 'segments' in transcript_data:
                                    transcript_text = ""
                                    for segment in transcript_data['segments']:
                                        if 'body' in segment:
                                            transcript_text += segment['body'] + " "
                                    if len(transcript_text.strip()) > 100:
                                        return transcript_text.strip()
                        except Exception as e:
                            print(f"Transcript API failed: {e}")
            
            # Fallback: try to extract from HTML if API fails
            if "Transcript" in text and "Show full transcript" in text:
                start_idx = text.find("Transcript")
                end_idx = text.find("Show full transcript") 
                if start_idx != -1 and end_idx != -1:
                    extracted = text[start_idx:end_idx]
                    # More aggressive HTML cleaning
                    import re
                    # Remove CSS and JavaScript
                    clean_text = re.sub(r'<style[^>]*>.*?</style>', '', extracted, flags=re.DOTALL | re.IGNORECASE)
                    clean_text = re.sub(r'<script[^>]*>.*?</script>', '', clean_text, flags=re.DOTALL | re.IGNORECASE)
                    # Remove HTML tags
                    clean_text = re.sub(r'<[^>]+>', '', clean_text)
                    # Remove CSS classes and IDs
                    clean_text = re.sub(r'\.css-[^{;]+[{;][^}]*}', '', clean_text)
                    # Clean up extra whitespace
                    clean_text = re.sub(r'\s+', ' ', clean_text)
                    if len(clean_text.strip()) > 100:
                        return clean_text.strip()
    except Exception as e:
        print(f"Requests approach failed: {e}")
    
    # Second try: Selenium with Streamlit Cloud configuration
    driver = None
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-plugins")
        options.add_argument("--remote-debugging-port=9222")
        
        # Check if we're on Streamlit Cloud (has chromium)
        try:
            # Try different chromium paths for different systems
            chromium_paths = ['/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome']
            chromedriver_paths = ['/usr/bin/chromedriver', '/usr/bin/chromium-driver']
            
            chromium_path = None
            chromedriver_path = None
            
            # Find chromium binary
            for path in chromium_paths:
                result = subprocess.run(['which', path.split('/')[-1]], capture_output=True, text=True)
                if result.returncode == 0:
                    chromium_path = path
                    break
            
            # Find chromedriver binary
            for path in chromedriver_paths:
                result = subprocess.run(['which', path.split('/')[-1]], capture_output=True, text=True)
                if result.returncode == 0:
                    chromedriver_path = path
                    break
            
            if chromium_path and chromedriver_path:
                options.binary_location = chromium_path
                service = Service(chromedriver_path)
                driver = webdriver.Chrome(service=service, options=options)
            elif WEBDRIVER_MANAGER_AVAILABLE:
                # Use webdriver-manager to auto-download ChromeDriver
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=options)
            else:
                # Local development
                driver = webdriver.Chrome(options=options)
        except Exception:
            # Final fallback
            driver = webdriver.Chrome(options=options)

        # Use the driver to get the page
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
            return transcript_text
        else:
            print("❌ Could not find transcript markers")
            return all_text

    except Exception as e:
        return f"❌ Selenium Error: {e}"

    finally:
        if driver is not None:
            driver.quit()
    
    # If all methods fail
    return "❌ Failed to extract transcript with all methods"

def save_transcript_to_docx(transcript, episode_title):
    # Add two line breaks before every '>>' except at the start
    import re
    formatted = re.sub(r"(?!^)>>", "\n\n>>", transcript)
    # Add newline before timestamps (format: 00:00, 00:04, etc.)
    formatted = re.sub(r"(?!^)(\d{2}:\d{2})", r"\n\1", formatted)
    doc = Document()
    doc.add_paragraph(formatted)
    safe_title = "".join(c for c in episode_title if c not in "\\/:*?\"<>|")
    filename = f"{safe_title}.docx"
    temp_path = os.path.join(tempfile.gettempdir(), filename)
    doc.save(temp_path)
    with open(temp_path, "rb") as f:
        file_bytes = f.read()
    return file_bytes, filename

# Streamlit App
st.title("Ping Proving Grounds Transcript Fetcher")

st.write("Episodes in podcast:")
episodes = get_all_episodes_from_rss()

for episode in episodes:
    col1, col2 = st.columns([4, 1])
    with col1:
        st.write(f"{episode['title']}")
    with col2:
        if 'download_state' not in st.session_state:
            st.session_state['download_state'] = {}
        
        episode_key = episode['title'].replace(' ', '_').replace(':', '')
        
        if st.session_state['download_state'].get(episode_key, False):
            with st.spinner('Fetching transcript and preparing download...'):
                transcript = extract_transcript_segments(episode['url'])
                file_bytes, docx_name = save_transcript_to_docx(transcript, episode['title'])
            st.success('Transcript ready!')
            st.download_button(
                label="Download Transcript (.docx)",
                data=file_bytes,
                file_name=docx_name,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                key=f"download_{episode_key}"
            )
            # Reset state after download button is shown
            st.session_state['download_state'][episode_key] = False
        else:
            if st.button(f"Download", key=episode_key):
                st.session_state['download_state'][episode_key] = True
                st.rerun()
