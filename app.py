# app.py
import streamlit as st
import tempfile
from apscheduler.schedulers.background import BackgroundScheduler
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from TikTokApi import TikTokApi

# --- CONFIG ---
# YouTube OAuth2 client secrets (download from Google Cloud Console)
CLIENT_SECRETS_FILE = "client_secrets.json"
YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# TikTok credentials placeholder
TIKTOK_USERNAME = "greatone.02"
TIKTOK_PASSWORD = "hebhor-xacgy0-hegtAp"

def get_youtube_service():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, YOUTUBE_SCOPES)
    creds = flow.run_console()
    return build("youtube", "v3", credentials=creds)

def upload_to_youtube(video_path: str, title: str, youtube):
    body = {
        "snippet": {"title": title, "description": "", "categoryId": "22"},
        "status": {"privacyStatus": "public"}
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"YouTube upload: {int(status.progress() * 100)}%")
    print(f"✅ YouTube video ID: {resp['id']}")

def upload_to_tiktok(video_path: str, title: str):
    api = TikTokApi.get_instance()
    # NOTE: you may need to authenticate via cookies/session rather than username/password
    api.login(username=TIKTOK_USERNAME, password=TIKTOK_PASSWORD)
    upload_resp = api.upload_video(video_path)
    api.post_video(video_file=upload_resp, title=title)
    print("✅ Uploaded to TikTok")

def schedule_jobs(video_path: str, title: str):
    youtube = get_youtube_service()
    scheduler = BackgroundScheduler()
    def job():
        upload_to_youtube(video_path, title, youtube)
        upload_to_tiktok(video_path, title)
    scheduler.add_job(job, "interval", hours=2)
    scheduler.start()

def main():
    st.title("🎬 YouTube Shorts & TikTok Scheduler")
    uploaded = st.file_uploader("Upload your short video", type=["mp4", "mov"], help="Max 60 s")
    title = st.text_input("Video Title")
    if st.button("Start Scheduling"):
        if not uploaded or not title:
            st.error("Please upload a video and enter a title.")
        else:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            tmp.write(uploaded.read())
            tmp.flush()
            schedule_jobs(tmp.name, title)
            st.success("✅ Scheduled uploads every 2 hours!")

if __name__ == "__main__":
    main()
