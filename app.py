import streamlit as st
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import subprocess
import os
import traceback
import whisper
import pysubs2
import uuid

# Set download folder
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

st.set_page_config(
    page_title="YouTube Auto Shorts Maker",
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

st.title("🎬 YouTube Auto Shorts Maker with Mirroring, Subtitles, and Highlights")
video_url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")

if st.button("Download and Process"):
    if not video_url.strip():
        st.warning("Enter a valid YouTube URL.")
    else:
        with st.spinner("Downloading and processing..."):
            try:
                ydl_opts = {
                    'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
                    'format': 'best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
                    'merge_output_format': 'mp4',
                    'http_headers': {
                        'User-Agent': (
                            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                            'AppleWebKit/537.36 (KHTML, like Gecko) '
                            'Chrome/115.0.0.0 Safari/537.36'
                        ),
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

                st.success("Download completed!")
                st.write(f"**Title:** {info.get('title','Unknown')}")

                size_mb = os.path.getsize(file_name) / (1024 * 1024)
                st.write(f"**Original File Size:** {size_mb:.1f} MB")

                with open(file_name, "rb") as f:
                    st.download_button("Download Original", data=f, file_name=os.path.basename(file_name))

                try:
                    st.video(file_name)
                except:
                    st.warning("Preview not available.")

                # Step 1: Mirror video
                mirrored_file = file_name.replace(".mp4", "_mirrored.mp4")
                if not os.path.exists(mirrored_file):
                    subprocess.run([
                        "ffmpeg", "-y", "-i", file_name,
                        "-vf", "hflip",
                        "-c:a", "copy",
                        mirrored_file
                    ], check=True)

                st.success("Mirrored version ready!")
                st.video(mirrored_file)
                with open(mirrored_file, "rb") as f:
                    st.download_button("Download Mirrored", data=f, file_name=os.path.basename(mirrored_file))

                # Step 2: Transcribe audio using Whisper
                model = whisper.load_model("base")
                result = model.transcribe(mirrored_file, word_timestamps=True)
                segments = result.get("segments", [])

                # Step 3: Create .ass subtitles with styling
                subs = pysubs2.SSAFile()
                subs.styles["Default"].fontname = "Noto Sans"
                subs.styles["Default"].fontsize = 24
                subs.styles["Default"].alignment = pysubs2.Alignment.BOTTOM_CENTER
                for seg in segments:
                    line = pysubs2.SSAEvent(
                        start=int(seg["start"] * 1000),
                        end=int(seg["end"] * 1000),
                        text=seg["text"].strip()
                    )
                    subs.append(line)

                subtitle_file = os.path.join(DOWNLOAD_FOLDER, f"{uuid.uuid4().hex}.ass")
                subs.save(subtitle_file)

                # Step 4: Burn subtitles onto mirrored video
                subtitled_file = mirrored_file.replace(".mp4", "_subtitled.mp4")
                subprocess.run([
                    "ffmpeg", "-y",
                    "-i", mirrored_file,
                    "-vf", f"ass={subtitle_file}",
                    "-c:a", "copy",
                    subtitled_file
                ], check=True)

                st.success("Final video with subtitles is ready!")
                st.video(subtitled_file)
                with open(subtitled_file, "rb") as f:
                    st.download_button("Download Subtitled Video", data=f, file_name=os.path.basename(subtitled_file))

            except DownloadError as de:
                st.error(f"Download failed: {de}")
                st.info("403 means YouTube blocked access. Ensure your cookies.txt is from a logged-in account and try again.")
            except Exception as e:
                st.error(f"Unexpected error: {e}")
                st.text(traceback.format_exc())
