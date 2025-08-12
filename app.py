"""
YouTube automation demo (Streamlit app)

Files contained: this app (app.py)

Purpose:
- Demonstration / educational only.
- Search YouTube by keyword (YouTube Data API v3, read-only using API KEY).
- Choose a high-view video from results.
- Load comment lines from a Google Sheet (service account JSON + sheet id).
- Generate a local Selenium script (downloadable) that, when run locally, will: open the video, wait ~3 minutes, optionally like, comment, and subscribe using browser automation.

IMPORTANT SAFETY / TOS NOTE:
Automating likes/comments/subscriptions at scale violates YouTube Terms of Service and spam policies. Use this demo ONLY on test accounts and for educational purposes. The Streamlit app does NOT run the Selenium automation in the cloud — it only *generates* a script for you to run locally where you control the browser and credentials.

How to use:
1) Create a Google Cloud project and enable YouTube Data API v3.
   - Create an API KEY (browser-restricted recommended) for search/list operations.
2) Create a Google Service Account, grant it access to your Google Sheet and download the JSON key.
3) Run this Streamlit app (locally or deploy to Streamlit Community Cloud). Upload the service account JSON when asked.
4) After selecting video & comments, click "Generate Selenium script" and download the script.
5) Run the generated script locally (requires Chrome + chromedriver, or modify for other browsers).

Requirements (examples to put in requirements.txt):
streamlit
google-api-python-client
google-auth
gspread
selenium
pytz

"""

import streamlit as st
import json
import time
import io
from googleapiclient.discovery import build
import gspread
from google.oauth2.service_account import Credentials
from typing import List

st.set_page_config(page_title="YouTube automation demo", layout="wide")

st.title("YouTube automation demo — safe, educational generator")

with st.expander("⚠️ Warnings & Terms"):
    st.markdown(
        """
- This demo **must** be used for educational/testing purposes only.
- Automating bulk likes/comments/subscribes can violate YouTube Terms of Service and lead to account suspension. See YouTube policies.
- The Streamlit app will **not** perform the Selenium automation in this environment — it generates a script for you to download and run locally.
"""
    )

# --- Input: YouTube API key for read-only search ---
st.sidebar.header("YouTube API / Google Sheets settings")
api_key = st.sidebar.text_input("YouTube Data API key (for search)")

# --- Keyword search ---
st.header("1) Tìm video theo từ khóa")
keyword = st.text_input("Nhập từ khóa tìm chủ đề (ví dụ: 'python tutorial')")
max_results = st.slider("Số kết quả", min_value=5, max_value=25, value=10)

search_results = []

if st.button("Tìm video"):
    if not api_key:
        st.error("Bạn cần nhập YouTube Data API key trong sidebar.")
    elif not keyword:
        st.error("Nhập từ khóa đã." )
    else:
        try:
            youtube = build('youtube', 'v3', developerKey=api_key)
            req = youtube.search().list(q=keyword, part='snippet', type='video', maxResults=max_results, order='viewCount')
            res = req.execute()
            items = res.get('items', [])
            video_ids = [it['id']['videoId'] for it in items]
            # fetch statistics
            stats_res = youtube.videos().list(part='snippet,statistics', id=','.join(video_ids)).execute()
            for v in stats_res.get('items', []):
                search_results.append({
                    'videoId': v['id'],
                    'title': v['snippet']['title'],
                    'channelTitle': v['snippet']['channelTitle'],
                    'views': int(v.get('statistics', {}).get('viewCount', 0)),
                    'url': f"https://www.youtube.com/watch?v={v['id']}"
                })
            # sort by views desc just in case
            search_results.sort(key=lambda x: x['views'], reverse=True)
            st.success(f"Tìm thấy {len(search_results)} video. Hiển thị top {len(search_results)} theo views.")
        except Exception as e:
            st.exception(e)

# show results if any
if search_results:
    st.markdown("### Kết quả tìm kiếm (theo lượt xem)")
    for i, v in enumerate(search_results):
        st.write(f"**{i+1}.** [{v['title']}]({v['url']}) — {v['channelTitle']} — {v['views']:,} views")

    sel_index = st.selectbox("Chọn video để thao tác", options=list(range(len(search_results))), format_func=lambda i: f"{search_results[i]['title']} ({search_results[i]['views']:,} views)")
    chosen = search_results[sel_index]
    st.markdown(f"**Video đã chọn:** [{chosen['title']}]({chosen['url']}) — {chosen['views']:,} views")

    # --- Load Google Sheet comments ---
    st.markdown("---\n2) Lấy data comment từ Google Sheet")
    st.markdown("Upload *service account* JSON key (file) *or* paste the JSON content in the box. The sheet must be shared with this service account email.")
    sa_file = st.file_uploader("Upload service account JSON (optional)", type=['json'])
    sa_text = st.text_area("Hoặc dán nội dung JSON của service account key ở đây", height=120)
    sheet_id = st.text_input("Google Sheet ID (phần giữa của URL: https://docs.google.com/spreadsheets/d/THIS_IS_THE_ID/edit)")
    sheet_range = st.text_input("Tên sheet và range (ví dụ: Sheet1!A:A)", value='Sheet1!A:A')

    comments_list: List[str] = []
    if st.button("Load comments from Sheet"):
        if not (sa_file or sa_text):
            st.error("Bạn cần upload service account JSON hoặc dán nội dung JSON.")
        elif not sheet_id:
            st.error("Cung cấp Sheet ID.")
        else:
            try:
                if sa_file:
                    sa_json = json.load(sa_file)
                else:
                    sa_json = json.loads(sa_text)
                creds = Credentials.from_service_account_info(sa_json, scopes=['https://www.googleapis.com/auth/spreadsheets','https://www.googleapis.com/auth/drive'])
                gc = gspread.authorize(creds)
                sh = gc.open_by_key(sheet_id)
                worksheet_title = sheet_range.split('!')[0] if '!' in sheet_range else sheet_range
                ws = sh.worksheet(worksheet_title)
                col = sheet_range.split('!')[1] if '!' in sheet_range else 'A:A'
                # simple: read all values in first column of the provided range
                vals = ws.get(sheet_range)
                # flatten
                for row in vals:
                    if row and row[0] and row[0].strip():
                        comments_list.append(row[0].strip())
                st.success(f"Lấy được {len(comments_list)} bình luận từ sheet.")
            except Exception as e:
                st.exception(e)

    if comments_list:
        st.markdown("### Mẫu comment (hiển thị 10)")
        for c in comments_list[:10]:
            st.write(f"- {c}")

    # --- Generate Selenium script for local execution ---
    st.markdown("---\n3) Tạo script Selenium (tải về và chạy *cục bộ*)")
    run_like = st.checkbox("Enable: like video (script sẽ bấm nút Like)", value=False)
    run_comment = st.checkbox("Enable: post comments (script sẽ đăng comment từ Google Sheet)", value=False)
    run_sub = st.checkbox("Enable: subscribe channel (script sẽ bấm Subscribe)", value=False)
    watch_seconds = st.number_input("Số giây xem trước khi like (mặc định 180)", value=180, min_value=5)

    if st.button("Generate Selenium script"):
        if not comments_list and run_comment:
            st.error("Bạn bật 'post comments' nhưng chưa có comment nào từ sheet.")
        else:
            # produce script text
            script = generate_selenium_script(chosen['url'], comments_list, watch_seconds, run_like, run_comment, run_sub)
            b = io.BytesIO(script.encode('utf-8'))
            st.download_button("Tải script Selenium (chạy cục bộ)", data=b, file_name='yt_auto_script.py', mime='text/x-python')
            st.info("Script tải về. Chạy nó trên máy local có Chrome + chromedriver. Thay đổi logic nếu bạn dùng Firefox/geckodriver.")


# --- helper to generate selenium script ---

def generate_selenium_script(video_url: str, comments: List[str], watch_seconds: int, like: bool, do_comment: bool, subscribe: bool) -> str:
    # This script is intentionally simple and requires manual sign-in to YouTube (so cookies are used).
    # It uses Chrome and expects chromedriver in PATH.
    comments_safe = [c.replace('"', '\\"') for c in comments]
    script = f"""#!/usr/bin/env python3
"""This is an auto-generated Selenium script. Run locally only.
Preconditions:
- Install: pip install selenium
- Have Chrome and chromedriver in PATH (or modify the script to point to chromedriver).
- Manually log into YouTube in the browser profile used by chromedriver, or modify to open a browser and prompt you to login.

Generated actions:
- open video
- wait {watch_seconds} seconds
- like: {like}
- comment: {do_comment} (up to {len(comments)} comments)
- subscribe: {subscribe}

WARNING: Using this script to automate actions at scale may violate YouTube Terms of Service.
"""

    script += "\nfrom selenium import webdriver\nfrom selenium.webdriver.common.by import By\nfrom selenium.webdriver.common.keys import Keys\nfrom selenium.webdriver.chrome.options import Options\nimport time\n\noptions = Options()\n# NOTE: remove headless to make the browser visible and allow manual login if needed\n# options.add_argument('--headless')\n# use a user-data-dir to persist login (adjust path as needed)\n# options.add_argument('--user-data-dir=./profile')\n\ndriver = webdriver.Chrome(options=options)\ntry:\n    driver.get(\"{video_url}\")\n    print('Opened video, waiting for page load...')\n    time.sleep(5)\n    print('Watching for {watch_seconds} seconds...')\n    time.sleep({watch_seconds})\n"

    if like:
        script += "\n    try:\n        like_btn = driver.find_element(By.XPATH, '//ytd-toggle-button-renderer[1]//a')\n        like_btn.click()\n        print('Liked the video')\n    except Exception as e:\n        print('Like failed:', e)\n"
    if subscribe:
        script += "\n    try:\n        sub_btn = driver.find_element(By.XPATH, '//ytd-subscribe-button-renderer//tp-yt-paper-button')\n        if sub_btn.text.lower().strip() not in ['subscribed','đã đăng ký']:\n            sub_btn.click()\n            print('Subscribed')\n        else:\n            print('Already subscribed')\n    except Exception as e:\n        print('Subscribe failed:', e)\n"
    if do_comment and comments:
        script += "\n    try:\n        # scroll to comment box\n        driver.execute_script('window.scrollTo(0, 1000)')\n        time.sleep(2)\n        comment_area = driver.find_element(By.CSS_SELECTOR, 'ytd-comment-simplebox-renderer')\n        comment_area.click()\n        time.sleep(1)\n        # switch to actual editable area\n        editable = driver.find_element(By.CSS_SELECTOR, '#contenteditable-root')\n        for c in [\n"
        for c in comments:
            script += f"            \"{c}\",\n"
        script += "        ]:\n            try:\n                editable.send_keys(c)\n                time.sleep(1)\n                post_btn = driver.find_element(By.XPATH, '//ytd-button-renderer[@id="submit-button"]/a')\n                post_btn.click()\n                print('Posted comment: ', c[:60])\n                time.sleep(5)\n            except Exception as e:\n                print('Posting comment failed for:', c, e)\n    except Exception as e:\n        print('Comment section failed:', e)\n"

    script += "\nfinally:\n    print('Done. Quitting in 5 seconds...')\n    time.sleep(5)\n    driver.quit()\n"
    return script

# show footer
st.sidebar.markdown("\n---\nDemo generator created by assistant. Read the warnings above carefully.")

