from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver import ActionChains
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from bs4 import BeautifulSoup
import os
import shutil
import random
import time
import pandas as pd
import zipfile

# Setup Selenium WebDriver to use chrome with automatic download settings
def setup_selenium(download_folder):
    print("[LOG] Setting up Selenium WebDriver...")
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)
        print(f"[LOG] Created download folder: {download_folder}")

    chrome_options = Options()
    
    prefs = {
        "download.default_directory": os.path.abspath(download_folder),  # Set the download folder
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    # Set up Chrome driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    print("driver = ",driver)
    print("[LOG] Selenium WebDriver setup complete.")
    return driver

# Function to get the next available serialized filename
def get_next_serialized_filename(download_folder):
    print(f"[LOG] Getting next serialized filename in folder: {download_folder}")
    existing_files = [f for f in os.listdir(download_folder) if f.startswith('Video_') and f.endswith('.mp4')]
    print(f"[LOG] Existing files: {existing_files}")
    if existing_files:
        last_file = max(existing_files, key=lambda x: int(x.split('_')[1].split('.')[0]))
        print(f"[LOG] Last serialized file: {last_file}")
        next_index = int(last_file.split('_')[1].split('.')[0]) + 1
    else:
        next_index = 1
    next_filename = f"Video_{next_index}.mp4"
    print(f"[LOG] Next serialized filename: {next_filename}")
    return next_filename

# Function to check if the download is complete
def is_download_complete(download_folder):
    print(f"[LOG] Checking if download is complete in folder: {download_folder}")
    temp_files = [f for f in os.listdir(download_folder) if f.endswith('.mp4')]
    if temp_files:
        print(f"[LOG] Non-MP4 files: {temp_files}")
        return True

def get_counter_value(counter_file):
    print(f"[LOG] Getting counter value from file: {counter_file}")
    if not os.path.exists(counter_file):
        print(f"[LOG] Counter file does not exist. Creating new file with initial value 1.")
        with open(counter_file, 'w', encoding='utf-8') as f:
            f.write('1')
        return 1
    with open(counter_file, 'r', encoding='utf-8') as f:
        value = int(f.read().strip())
        print(f"[LOG] Current counter value: {value}")
        return value

def increment_counter(counter_file):
    print(f"[LOG] Incrementing counter value in file: {counter_file}")
    value = get_counter_value(counter_file) + 1
    print(f"[LOG] New counter value: {value}")
    with open(counter_file, 'w', encoding='utf-8') as f:
        f.write(str(value))
    return value

def rename_and_move_downloaded_file(temp_folder, videos_folder, counter_file, reel_url, links_file):
    print(f"[LOG] Starting rename_and_move_downloaded_file for reel: {reel_url}")
    # Wait until there are no active downloads
    while not is_download_complete(temp_folder):
        print("[LOG] Waiting for download to complete...")
        time.sleep(60)  # Check every 60 seconds
    # Exclude 'null.mp4' from the list
    files = [f for f in os.listdir(temp_folder) if f.endswith('.mp4') and f != 'null.mp4']
    print(f"Files in temp folder: {files}")
    if files:
        latest_file = max(files, key=lambda x: os.path.getctime(os.path.join(temp_folder, x)))
        print(f"Latest file: {latest_file}")
        latest_file_path = os.path.join(temp_folder, latest_file)
        print(f"Latest file path: {latest_file_path}")
        counter = get_counter_value(counter_file)
        print(f"Counter value: {counter}")
        new_filename = f"Video_{counter}.mp4"
        print(f"New filename: {new_filename}")
        renamed_path = os.path.join(temp_folder, new_filename)
        print(f"Renamed path: {renamed_path}")
        shutil.move(latest_file_path, renamed_path)
        size_mb = os.path.getsize(renamed_path) / (1024 * 1024)
        print(f"File size (MB): {size_mb}")
        if size_mb > 100:
            print(f"File {renamed_path} is too large ({size_mb:.2f} MB). Removing...")
            os.remove(renamed_path)

            # Update links.txt to mark the link as "LARGE FILE"
            with open(links_file, 'r', encoding='utf-8') as file:
                lines = file.readlines()

            # Update the specific line in memory and write back once
            if reel_url in lines:
                line_index = lines.index(reel_url + '\n')
                lines[line_index] = f"{reel_url} - LARGE FILE\n"

            with open(links_file, 'w', encoding='utf-8') as file:
                file.writelines(lines)
        else:
            final_path = os.path.join(videos_folder, new_filename)
            shutil.move(renamed_path, final_path)
            print(f"File renamed and moved to: {final_path}")
        increment_counter(counter_file)
    print(f"[LOG] Completed rename_and_move_downloaded_file for reel: {reel_url}")

# Function to download Instagram reels using sssinstagram.net
def download_instagram_reels_sssinstagram(reel_url, temp_folder, videos_folder, counter_file, links_file):
    print(f"[LOG] Starting download for reel: {reel_url}")
    driver = setup_selenium(temp_folder)
    # Navigate to sssinstagram's Instagram Reel Downloader
    driver.get("https://sssinstagram.com/reels-downloader")
    time.sleep(10)
    try:
        print(f"[LOG] Attempting to find input box for reel: {reel_url}")
        # Find the input box and paste the reel URL
        input_box = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//input[@id='input']"))
        )
        print("[LOG] Input box found. Entering reel URL...")
        input_box.send_keys(reel_url)
        
        print("[LOG] Attempting to find and click the download button...")
        # Click the Download button to submit the URL
        download_button = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//button[@type='submit']"))
        )
        download_button.click()
        print("[LOG] Download button clicked. Waiting for video download link...")
        # Wait for the "Download" button to appear and click it
        # download_button = WebDriverWait(driver, 20).until(
        #     EC.element_to_be_clickable((By.XPATH, "//a[@class='button button--filled button__download']"))
        # )
        # print("[LOG] Download button found. Clicking the button...")
        # download_button.click()
        # print("[LOG] Download initiated. Waiting for the download to complete...")
        # Wait for either of the "Download Video" buttons to appear and get the href
        download_video_button = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//a[@class='button button--filled button__download']"))
        )
        print("[LOG] Download video button found. Extracting download link...")

        # Extract the href link for the video
        video_download_link = download_video_button.get_attribute("href")
        print(f"[LOG] Download link extracted: {video_download_link}")
        
        # Download the video manually using the extracted href link
        time.sleep(10)
        print("[LOG] Navigating to the video download link...")
        driver.get(video_download_link)
        print("[LOG] Waiting for the download to start...")
        time.sleep(10)  # Give time for the download to start
        
        # Rename the file after download
        print("[LOG] Attempting to rename and move the downloaded file...")
        rename_and_move_downloaded_file(temp_folder, videos_folder, counter_file, reel_url, links_file)

        print(f"[LOG] Successfully downloaded and processed reel: {reel_url}")
        driver.quit()
        return 1
        
    except Exception as e:
        print(f"[ERROR] Exception occurred: {str(e)}")
        print(f"[LOG] Failed to download reel: {reel_url}")
        driver.quit()
        return 0

# Add this function to handle retries
def download_with_retry(reel_url, temp_folder, videos_folder, counter_file, links_file, max_retries=7):
    print(f"[LOG] Starting download_with_retry for reel: {reel_url}")
    attempt = 0
    success = False

    while attempt < max_retries and not success:
        print(f"[LOG] Attempt {attempt + 1} for reel: {reel_url}")
        number = download_instagram_reels_sssinstagram(reel_url, temp_folder, videos_folder, counter_file, links_file)
        if number == 1:
            success = True
            print(f"[LOG] Successfully downloaded reel after {attempt + 1} attempts: {reel_url}")
            break
        else:
            attempt += 1
            print(f"[LOG] Retry {attempt} for reel: {reel_url}")
            time.sleep(5)  # Wait for a few seconds before retrying
    if not success:
        print(f"[LOG] Failed to download reel after {max_retries} attempts: {reel_url}")

# Main function to automate the process
def main():
    print("[LOG] Starting main function...")
    temp_folder = "temp"
    videos_folder = "VIDEOS"
    counter_file = "counter.txt"
    links_file = "links.txt"
    
    # Read reel links from the .txt file
    with open(links_file, 'r', encoding='utf-8') as file:
        reel_links = [line.strip() for line in file.readlines()]
        for reel_link in reel_links:
            print(f"Downloading reel: {reel_link}")
            download_with_retry(reel_link, temp_folder, videos_folder, counter_file, links_file)
    print("[LOG] Completed main function.")

if __name__ == "__main__":
    main()
