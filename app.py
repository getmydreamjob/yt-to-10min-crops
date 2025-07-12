import streamlit as st
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import subprocess
import os
import traceback
import whisper
import uuid
from datetime import timedelta

# Constants
DOWNLOAD_FOLDER = "downloads"
FINAL_FOLDER = "final"
FONT_PATH = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"

# Ensure folders exist
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
os.makedirs(FINAL_FOLDER, exist_ok=True)

st.set_page_config(
    page_title="YouTube to Mirrored + Cropped Subtitled Shorts",
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

st.title("🎬 YouTube to Mirrored Subtitled Clips")

video_url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
mode = st.radio("Choose what to generate:", ["Original Video", "Mirrored Video", "Mirrored + Subtitled Crops"])

def format_timestamp(seconds):
    td = timedelta(seconds=round(seconds))
    return str(td)

def create_crop_clips(file_path, segments, font_path):
    clips = []
    for i, seg in enumerate(segments[:5]):  # Take top 5 segments (adjust as needed)
        start = max(0, seg["start"] - 1)
        end = seg["end"] + 1
        text = seg["text"].replace('\n', ' ').replace('"', '')

        cropped_name = os.path.join(FINAL_FOLDER, f"crop_{i}_{uuid.uuid4().hex[:4]}.mp4")

        drawtext = (
            f"drawtext=fontfile={font_path}:text='{text}':fontcolor=white:fontsize=24:"
            f"x=(w-text_w)/2:y=h-th-50:box=1:boxcolor=black@0.5:boxborderw=5"
        )

        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-to", str(end),
            "-i", file_path,
            "-vf", f"hflip,{drawtext}",
            "-c:a", "copy",
            cropped_name
        ]
        subprocess.run(cmd, check=True)
        clips.append(cropped_name)
    return clips

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
                    'geo_bypass_country': 'US',
                    'retries': 3,
                }
                if cookie_path:
                    ydl_opts['cookiefile'] = cookie_path

                with YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=False)
                    if info.get('is_live'):
                        st.warning("Live streams not supported.")
                        st.stop()

                    info = ydl.extract_info(video_url, download=True)
                    file_name = ydl.prepare_filename(info)
                    if not file_name.endswith(".mp4"):
                        file_name += ".mp4"

                st.success("Video downloaded!")
                st.video(file_name)

                if mode == "Original Video":
                    with open(file_name, "rb") as f:
                        st.download_button("Download Original Video", f, file_name=os.path.basename(file_name))

                elif mode == "Mirrored Video":
                    mirrored_file = file_name.replace(".mp4", "_mirrored.mp4")
                    st.info("Mirroring video...")
                    subprocess.run([
                        "ffmpeg", "-y", "-i", file_name,
                        "-vf", "hflip", "-c:a", "copy", mirrored_file
                    ], check=True)
                    with open(mirrored_file, "rb") as f:
                        st.download_button("Download Mirrored Video", f, file_name=os.path.basename(mirrored_file))
                    st.video(mirrored_file)

                elif mode == "Mirrored + Subtitled Crops":
                    st.info("Transcribing with Whisper...")
                    model = whisper.load_model("base") 
                    result = model.transcribe(file_name)
                    st.success("Transcription done.")

                    st.info("Creating subtitle clips...")
                    clips = create_crop_clips(file_name, result["segments"], FONT_PATH)
                    for clip_path in clips:
                        with open(clip_path, "rb") as f:
                            st.download_button(f"Download Clip", f, file_name=os.path.basename(clip_path))
                        st.video(clip_path)

            except DownloadError as de:
                st.error(f"Download failed: {de}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")
                st.text(traceback.format_exc())
