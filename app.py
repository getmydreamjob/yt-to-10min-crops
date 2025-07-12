import streamlit as st
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError
import subprocess
import os
import traceback
import whisper
import json
from tempfile import NamedTemporaryFile

st.set_page_config(
    page_title="🎬 YouTube Highlights Generator",
    page_icon="🎬",
    layout="centered"
)

DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

st.title("🎬 YouTube Downloader with Highlight Detection")

video_url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...")
option = st.radio("Select action:", ["Download Original", "Download Mirrored", "Generate Highlights (~10 mins)"])

cookies_file = st.sidebar.file_uploader("Upload your YouTube cookies.txt (Optional)", type=["txt"])
cookie_path = None
if cookies_file:
    cookie_path = os.path.join(DOWNLOAD_FOLDER, "cookies.txt")
    with open(cookie_path, "wb") as f:
        f.write(cookies_file.getbuffer())

if st.button("Run"):
    if not video_url.strip():
        st.warning("Please enter a valid YouTube URL.")
        st.stop()

    with st.spinner("Downloading video..."):
        try:
            ydl_opts = {
                'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
                'format': 'best[ext=mp4]/bestvideo[ext=mp4]+bestaudio[ext=m4a]/best',
                'merge_output_format': 'mp4',
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0',
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

            if option == "Download Original":
                with open(file_name, "rb") as f:
                    st.download_button("Download Original", f, file_name=os.path.basename(file_name))

            elif option == "Download Mirrored":
                mirrored_name = file_name.replace(".mp4", "_mirrored.mp4")
                if not os.path.exists(mirrored_name):
                    st.info("Mirroring video...")
                    subprocess.run([
                        "ffmpeg", "-y", "-i", file_name,
                        "-vf", "hflip", "-c:a", "copy", mirrored_name
                    ], check=True)
                st.success("Video mirrored!")
                st.video(mirrored_name)
                with open(mirrored_name, "rb") as f:
                    st.download_button("Download Mirrored Video", f, file_name=os.path.basename(mirrored_name))

            elif option == "Generate Highlights (~10 mins)":
                st.info("Transcribing with Whisper...")
                model = whisper.load_model("base")
                result = model.transcribe(file_name, word_timestamps=True)
                segments = result["segments"]

                def score_segment(seg):
                    txt = seg['text'].lower()
                    score = 0
                    score += txt.count("!" + txt.count("?")) * 2
                    score += sum(1 for word in ["amazing", "important", "wow", "incredible"] if word in txt)
                    score += len(txt.split()) / (seg['end'] - seg['start'] + 1)
                    return score

                scored = sorted(segments, key=score_segment, reverse=True)
                top_segments = []
                total_duration = 0
                for seg in scored:
                    duration = seg['end'] - seg['start']
                    if total_duration + duration <= 600:
                        top_segments.append(seg)
                        total_duration += duration

                clips = []
                for i, seg in enumerate(top_segments):
                    out_file = file_name.replace(".mp4", f"_clip_{i+1}.mp4")
                    subtitle = seg['text'].replace('"', '\"')
                    font_opts = "fontfile=/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf:fontsize=24:fontcolor=white:borderw=1"
                    cmd = f"ffmpeg -y -i \"{file_name}\" -ss {seg['start']} -to {seg['end']} -vf drawtext=\"text='{subtitle}':x=(w-text_w)/2:y=h-th-50:{font_opts}\" -c:a copy \"{out_file}\""
                    subprocess.run(cmd, shell=True, check=True)
                    clips.append(out_file)

                for out_file in clips:
                    st.video(out_file)
                    with open(out_file, "rb") as f:
                        st.download_button(f"Download Clip", f, file_name=os.path.basename(out_file))

        except DownloadError as de:
            st.error(f"Download failed: {de}")
        except Exception as e:
            st.error(f"Unexpected error: {e}")
            st.text(traceback.format_exc())
