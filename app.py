"""
YouTube automation demo (Streamlit app)
... (header comments remain unchanged)
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

# ... other parts unchanged

def generate_selenium_script(video_url: str, comments: List[str], watch_seconds: int, like: bool, do_comment: bool, subscribe: bool) -> str:
    comments_safe = [c.replace('"', '\\"') for c in comments]
    header = f"""#!/usr/bin/env python3
# This is an auto-generated Selenium script. Run locally only.
... (header text remains unchanged)
"""
    script = header
    script += f"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import time

options = Options()
# options.add_argument('--headless')

with webdriver.Chrome(options=options) as driver:
    driver.get("{video_url}")
    print('Opened video, waiting for page load...')
    time.sleep(5)
    print('Watching for {watch_seconds} seconds...')
    time.sleep({watch_seconds})
"""
    if like:
        script += (
            "    try:\n"
            "        driver.find_element(By.XPATH, '//ytd-toggle-button-renderer[1]//a').click()\n"
            "        print('Liked the video')\n"
            "    except Exception as e:\n"
            "        print('Like failed:', e)\n"
        )
    if subscribe:
        script += (
            "    try:\n"
            "        sub_btn = driver.find_element(By.XPATH, '//ytd-subscribe-button-renderer//tp-yt-paper-button')\n"
            "        if sub_btn.text.lower().strip() not in ['subscribed','đã đăng ký']:\n"
            "            sub_btn.click()\n"
            "            print('Subscribed')\n"
            "        else:\n"
            "            print('Already subscribed')\n"
            "    except Exception as e:\n"
            "        print('Subscribe failed:', e)\n"
        )
    if do_comment and comments:
        script += (
            "    try:\n"
            "        driver.execute_script('window.scrollTo(0, 1000)')\n"
            "        time.sleep(2)\n"
            "        driver.find_element(By.CSS_SELECTOR, 'ytd-comment-simplebox-renderer').click()\n"
            "        time.sleep(1)\n"
            "        editable = driver.find_element(By.CSS_SELECTOR, '#contenteditable-root')\n"
        )
        for c in comments_safe:
            script += (
                f"        editable.send_keys(\"{c}\")\n"
                "        time.sleep(1)\n"
                "        driver.find_element(By.XPATH, '//ytd-button-renderer[@id=\"submit-button\"]/a').click()\n"
                f"        print('Posted comment: {c[:60]}')\n"
                "        time.sleep(5)\n"
            )
        script += (
            "    except Exception as e:\n"
            "        print('Comment section failed:', e)\n"
        )
    return script

# ... rest of the code unchanged
