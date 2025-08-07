import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
from docx import Document
import tempfile
import os

def get_video_ids_from_playlist(url):
    ydl_opts = {'quiet': True, 'extract_flat': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        playlist_info = ydl.extract_info(url, download=False)
        return [entry['id'] for entry in playlist_info['entries']]

def get_video_title(video_id):
    ydl_opts = {'quiet': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            video_info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            return video_info.get('title', video_id)
        except:
            return video_id

def fetch_transcript(video_id):
    api = YouTubeTranscriptApi()
    try:
        transcript = api.fetch(video_id=video_id, languages=['en'], preserve_formatting=False)
        return " ".join([entry.text for entry in transcript])
    except Exception as e:
        return f"[{video_id}] Transcript not available: {e}"

def save_transcript_to_docx(transcript, video_title):
    doc = Document()
    doc.add_paragraph(transcript)
    safe_title = "".join(c for c in video_title if c not in "\\/:*?\"<>|")
    filename = f"{safe_title}.docx"
    temp_path = os.path.join(tempfile.gettempdir(), filename)
    doc.save(temp_path)
    return temp_path, filename

st.title("YouTube Playlist Transcript Fetcher")

playlist_url = st.text_input("Enter YouTube Playlist URL:")

if st.button("Fetch Transcripts"):
    if playlist_url:
        video_ids = get_video_ids_from_playlist(playlist_url)
        for video_id in video_ids[:1]:  # just latest episode — remove [:1] to get all
            st.write(f"Fetching transcript for https://www.youtube.com/watch?v={video_id}")
            transcript = fetch_transcript(video_id)
            video_title = get_video_title(video_id)
            st.write(transcript)
            docx_path, docx_name = save_transcript_to_docx(transcript, video_title)
            with open(docx_path, "rb") as f:
                st.download_button("Download Transcript (.docx)", f, file_name=docx_name)
    else:
        st.warning("Please enter a playlist URL.")