
import streamlit as st
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
from docx import Document
import tempfile
import os

PLAYLIST_URL = "https://www.youtube.com/playlist?list=PLerJdr1xhGiUKMPq3_uhO3HeIGE98CgTy"


def get_playlist_videos(url):
    ydl_opts = {'quiet': True, 'extract_flat': True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        playlist_info = ydl.extract_info(url, download=False)
        # Return list of dicts with id and title
        return [
            {'id': entry['id'], 'title': entry.get('title', entry['id'])}
            for entry in playlist_info['entries']
        ]


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
        transcript = api.fetch(video_id=video_id, languages=['en'], preserve_formatting=True)
        return " ".join([entry.text for entry in transcript])
    except Exception as e:
        return f"[{video_id}] Transcript not available: {e}"


def save_transcript_to_docx(transcript, video_title):
    # Add two line breaks after every line starting with '>>'
    formatted = "\n\n".join([line for line in transcript.splitlines() if line.strip().startswith('>>')])
    # If there are lines not starting with '>>', keep them as is
    other_lines = [line for line in transcript.splitlines() if not line.strip().startswith('>>')]
    if formatted:
        # Add the rest of the transcript after the formatted lines
        formatted += "\n\n" + "\n".join(other_lines)
    else:
        formatted = transcript
    doc = Document()
    doc.add_paragraph(formatted)
    safe_title = "".join(c for c in video_title if c not in "\\/:*?\"<>|")
    filename = f"{safe_title}.docx"
    temp_path = os.path.join(tempfile.gettempdir(), filename)
    doc.save(temp_path)
    return temp_path, filename


st.title("YouTube Playlist Transcript Fetcher")

st.write("Episodes in playlist:")
videos = get_playlist_videos(PLAYLIST_URL)

for video in videos:
    col1, col2 = st.columns([4, 1])
    with col1:
        st.write(f"{video['title']}")
    with col2:
        if st.button(f"Download", key=video['id']):
            transcript = fetch_transcript(video['id'])
            docx_path, docx_name = save_transcript_to_docx(transcript, video['title'])
            with open(docx_path, "rb") as f:
                st.download_button("Download Transcript (.docx)", f, file_name=docx_name)