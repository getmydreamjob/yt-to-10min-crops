import streamlit as st
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import subprocess
import os
import traceback
import whisper as openai_whisper
import uuid

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

st.set_page_config(
    page_title="YouTube to Mirrored Video with Subtitles",
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

if st.button("Start Processing"):
    if not video_url.strip():
        st.warning("Enter a valid YouTube URL.")
    else:
        with st.spinner("Downloading video..."):
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
                st.video(file_name)

                # Mirror the video
                mirrored_file = file_name.replace(".mp4", "_mirrored.mp4")
                subprocess.run(["ffmpeg", "-y", "-i", file_name, "-vf", "hflip", "-c:a", "copy", mirrored_file], check=True)
                st.success("Video mirrored!")

                # Transcribe audio
                st.info("Transcribing with Whisper...")
                model = openai_whisper.load_model("base")
                result = model.transcribe(mirrored_file)

                # Create .srt subtitle file
                srt_path = mirrored_file.replace(".mp4", ".srt")
                with open(srt_path, "w", encoding="utf-8") as srt_file:
                    for i, segment in enumerate(result["segments"], start=1):
                        start = segment["start"]
                        end = segment["end"]
                        text = segment["text"]
                        srt_file.write(f"{i}\n")
                        srt_file.write(f"{int(start // 3600):02}:{int(start % 3600 // 60):02}:{int(start % 60):02},000 --> {int(end // 3600):02}:{int(end % 3600 // 60):02}:{int(end % 60):02},000\n")
                        srt_file.write(f"{text.strip()}\n\n")

                st.success("Subtitles generated!")

                # Burn subtitles
                output_file = mirrored_file.replace(".mp4", "_subtitled.mp4")
                font_path = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"
                ffmpeg_cmd = [
                    "ffmpeg", "-y", "-i", mirrored_file, "-vf",
                    f"subtitles={srt_path}:force_style='FontName=Noto Sans,FontSize=24,Alignment=2'",
                    output_file
                ]
                subprocess.run(ffmpeg_cmd, check=True)
                st.success("Subtitled video created!")

                with open(output_file, "rb") as f:
                    st.download_button("Download Final Video", data=f, file_name=os.path.basename(output_file))
                st.video(output_file)

            except DownloadError as de:
                st.error(f"Download failed: {de}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")
                st.text(traceback.format_exc())
