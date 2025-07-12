import streamlit as st
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import subprocess
import os
import traceback
import whisper
import tempfile
from datetime import timedelta

# Set download folder
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

st.set_page_config(
    page_title="YouTube Video Downloader with Options",
    page_icon="🎬",
    layout="centered"
)

st.sidebar.header("Optional: Cookies")
cookies_file = st.sidebar.file_uploader("Upload your YouTube cookies.txt", type=["txt"])
cookie_path = None
if cookies_file:
    cookie_path = os.path.join(DOWNLOAD_FOLDER, "cookies.txt")
    with open(cookie_path, "wb") as f:
        f.write(cookies_file.getbuffer())

st.title("🎬 YouTube to Video Editor")
video_url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
action = st.radio("Select Action", ["Download Original Video", "Download Mirrored Video", "Download Mirrored + Subtitled Video"])

def transcribe_audio(video_path):
    model = whisper.Whisper("base")
    result = model.transcribe(video_path)
    return result['segments']

def burn_subtitles(input_path, output_path, segments):
    drawtext_filters = []
    for i, seg in enumerate(segments):
        start = seg['start']
        end = seg['end']
        text = seg['text'].replace("'", "")
        drawtext_filters.append(
            f"drawtext=fontfile=/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf: text='{text}': fontcolor=white: fontsize=24: x=(w-text_w)/2: y=h-th-30: enable='between(t,{start},{end})'"
        )
    filter_complex = ",".join(drawtext_filters)
    subprocess.run([
        "ffmpeg", "-y", "-i", input_path,
        "-vf", filter_complex,
        "-c:a", "copy", output_path
    ], check=True)

if st.button("Start"):
    if not video_url.strip():
        st.warning("Enter a valid YouTube URL.")
    else:
        with st.spinner("Processing..."):
            try:
                ydl_opts = {
                    'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
                    'format': 'best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
                    'merge_output_format': 'mp4',
                    'http_headers': {
                        'User-Agent': 'Mozilla/5.0',
                        'Referer': 'https://www.youtube.com',
                        'Accept-Language': 'en-US,en;q=0.9',
                    },
                    'geo_bypass': True,
                    'geo_bypass_country': 'US',
                    'retries': 3,
                }
                if cookie_path:
                    ydl_opts['cookiefile'] = cookie_path

                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=False)
                    if info.get('is_live'):
                        st.warning("Live streams are not supported.")
                        st.stop()

                    info = ydl.extract_info(video_url, download=True)
                    file_name = ydl.prepare_filename(info)
                    if not file_name.endswith(".mp4"):
                        file_name += ".mp4"

                st.success("Video downloaded!")

                if action == "Download Original Video":
                    with open(file_name, "rb") as f:
                        st.download_button("Download Original Video", data=f, file_name=os.path.basename(file_name))

                elif action == "Download Mirrored Video":
                    mirrored_file = file_name.replace(".mp4", "_mirrored.mp4")
                    subprocess.run([
                        "ffmpeg", "-y", "-i", file_name, "-vf", "hflip", "-c:a", "copy", mirrored_file
                    ], check=True)
                    st.success("Video mirrored!")
                    with open(mirrored_file, "rb") as f:
                        st.download_button("Download Mirrored Video", data=f, file_name=os.path.basename(mirrored_file))

                elif action == "Download Mirrored + Subtitled Video":
                    mirrored_file = file_name.replace(".mp4", "_mirrored.mp4")
                    final_output = file_name.replace(".mp4", "_mirrored_subtitled.mp4")

                    subprocess.run([
                        "ffmpeg", "-y", "-i", file_name, "-vf", "hflip", "-c:a", "copy", mirrored_file
                    ], check=True)
                    st.info("Generating subtitles...")
                    segments = transcribe_audio(file_name)
                    st.info("Burning subtitles...")
                    burn_subtitles(mirrored_file, final_output, segments)
                    st.success("Video mirrored and subtitled!")
                    with open(final_output, "rb") as f:
                        st.download_button("Download Final Video", data=f, file_name=os.path.basename(final_output))

            except DownloadError as de:
                st.error(f"Download failed: {de}")
                st.info("403 means YouTube blocked access. Ensure your cookies.txt is from a logged-in account or the video may be private.")
            except Exception as e:
                st.error(f"Unexpected error: {e}")
                st.text(traceback.format_exc())
