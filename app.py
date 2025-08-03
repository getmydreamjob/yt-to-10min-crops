import os
import tempfile
import streamlit as st
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from tiktok_uploader.upload import upload_video
import undetected_chromedriver as uc

# --- CONFIG ---
# packages.txt: chromium, chromium-driver
# requirements.txt: streamlit, tiktok-uploader, APScheduler, selenium, undetected-chromedriver

def create_driver():
    """Instantiate undetected_chromedriver with defaults."""
    # Let uc manage driver executable automatically
    options = uc.ChromeOptions()
    options.headless = True
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-setuid-sandbox')
    options.add_argument('--remote-debugging-port=9222')
    # Use system binary if available, else default
    if os.path.exists('/usr/bin/chromium-browser'):
        options.binary_location = '/usr/bin/chromium-browser'
    elif os.path.exists('/usr/bin/chromium'):
        options.binary_location = '/usr/bin/chromium'
    # uc.Chrome will install driver into user directory
    return uc.Chrome(options=options)


def do_upload(video_path: str, title: str, cookies_path: str) -> (bool, str):
    """Uploads video using tiktok-uploader with undetected_chromedriver."""
    driver = create_driver()
    try:
        upload_video(
            video_path,
            description=title,
            cookies=cookies_path,
            driver=driver,
        )
        driver.quit()
        return True, f"Uploaded '{title}' at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    except Exception as e:
        try:
            driver.quit()
        except:
            pass
        return False, str(e)


def upload_and_report(video_path: str, title: str, cookies_path: str):
    ok, msg = do_upload(video_path, title, cookies_path)
    if ok:
        st.success(f"✅ {msg}")
    else:
        st.error(f"❌ Upload failed: {msg}")


def schedule_jobs(video_path: str, title: str, cookies_path: str):
    scheduler = BackgroundScheduler()
    def job():
        ok, msg = do_upload(video_path, title, cookies_path)
        print("Scheduler:", "OK" if ok else "FAIL", msg)
    scheduler.add_job(job, 'interval', hours=2, id='tiktok_job')
    scheduler.start()
    return scheduler


def main():
    st.title('🎬 TikTok Scheduler')

    cookies_file = st.file_uploader(
        'Upload your TikTok cookies.txt (Netscape format)',
        type=['txt'], key='cookies'
    )
    video_file = st.file_uploader(
        'Upload your short video',
        type=['mp4', 'mov'], key='video'
    )
    title = st.text_input('Video Title', key='title')

    if st.button('Start Scheduling', key='start'):
        if cookies_file is None:
            st.error('Please upload cookies.txt')
            return
        if video_file is None or not title:
            st.error('Please upload a video and enter a title')
            return

        # Save cookies and video
        ck = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
        ck.write(cookies_file.read()); ck.flush()
        cookies_path = ck.name

        vid = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
        vid.write(video_file.read()); vid.flush()
        video_path = vid.name

        # Schedule and test
        st.session_state.scheduler = schedule_jobs(video_path, title, cookies_path)
        upload_and_report(video_path, title, cookies_path)

    if 'scheduler' in st.session_state:
        sched = st.session_state.scheduler
        job = sched.get_job('tiktok_job')
        if job:
            next_time = job.next_run_time.strftime('%Y-%m-%d %H:%M:%S')
            st.write('**Next scheduled upload:**', next_time)
            if st.button('Run Now', key='run_now'):
                ok, msg = do_upload(video_path, title, cookies_path)
                if ok:
                    st.success(f"✅ {msg}")
                else:
                    st.error(f"❌ Upload failed: {msg}")

if __name__ == '__main__':
    main()
