import streamlit as st
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import subprocess
import os
import traceback
import whisper
import pysubs2

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

st.set_page_config(
    page_title="Auto Subtitled TikTok Generator",
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

st.title("🎬 YouTube to Mirrored Video with Subtitles")

video_url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")

if st.button("Download and Process"):
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
                    'retries': 3,
                }
                if cookie_path:
                    ydl_opts['cookiefile'] = cookie_path

                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=True)
                    file_name = ydl.prepare_filename(info)
                    if not file_name.endswith(".mp4"):
                        file_name += ".mp4"

                st.success("Video downloaded!")

                # Mirror the video
                mirrored_file = file_name.replace(".mp4", "_mirrored.mp4")
                subprocess.run([
                    "ffmpeg", "-y", "-i", file_name,
                    "-vf", "hflip", "-c:a", "copy", mirrored_file
                ], check=True)

                st.success("Video mirrored!")

                # Transcribe with whisper
                model = whisper.load_model("base")
                result = model.transcribe(mirrored_file, word_timestamps=True)

                # Generate subtitles with pysubs2
                subs = pysubs2.SSAFile()
                subs.styles["Default"].fontname = "Noto Sans"
                subs.styles["Default"].fontsize = 24
                subs.styles["Default"].alignment = pysubs2.Alignment.BOTTOM_CENTER

                for segment in result["segments"]:
                    start = segment["start"]
                    end = segment["end"]
                    line = pysubs2.SSAEvent(start=start*1000, end=end*1000, text=segment["text"])
                    subs.append(line)

                subtitle_file = mirrored_file.replace(".mp4", ".ass")
                subs.save(subtitle_file)

                # Burn subtitles with ffmpeg
                final_file = mirrored_file.replace(".mp4", "_subtitled.mp4")
                subprocess.run([
                    "ffmpeg", "-y", "-i", mirrored_file,
                    "-vf", f"ass={subtitle_file}",
                    "-c:a", "copy", final_file
                ], check=True)

                st.success("Subtitles burned!")

                st.video(final_file)
                with open(final_file, "rb") as f:
                    st.download_button("Download Final Video", data=f, file_name=os.path.basename(final_file))

            except DownloadError as de:
                st.error(f"Download failed: {de}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")
                st.text(traceback.format_exc())
