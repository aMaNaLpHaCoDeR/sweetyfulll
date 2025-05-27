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
    if not os.path.exists(download_folder):
        os.makedirs(download_folder)

    chrome_options = Options()
    chrome_options.binary_location = "/usr/bin/brave-browser"  # now it will work
    prefs = {
        "download.default_directory": os.path.abspath(download_folder),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_argument("--headless=new")  # Use headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    print("driver = ", driver)
    
    return driver

# Function to get the next available serialized filename
def get_next_serialized_filename(download_folder):
    existing_files = [f for f in os.listdir(download_folder) if f.startswith('Video_') and f.endswith('.mp4')]
    if existing_files:
        last_file = max(existing_files, key=lambda x: int(x.split('_')[1].split('.')[0]))
        next_index = int(last_file.split('_')[1].split('.')[0]) + 1
    else:
        next_index = 1
    return f"Video_{next_index}.mp4"

# Function to check if the download is complete
def is_download_complete(download_folder):
    temp_files = [f for f in os.listdir(download_folder) if f.endswith('.crdownload') or f.endswith('.tmp')]
    return len(temp_files) == 0

def get_counter_value(counter_file):
    if not os.path.exists(counter_file):
        with open(counter_file, 'w') as f:
            f.write('1')
        return 1
    with open(counter_file, 'r') as f:
        return int(f.read().strip())

def increment_counter(counter_file):
    value = get_counter_value(counter_file) + 1
    with open(counter_file, 'w') as f:
        f.write(str(value))
    return value

def split_file_binary(input_path, output_path1, output_path2):
    try:
        with open(input_path, 'rb') as f:
            data = f.read()
        half = len(data) // 2
        with open(output_path1, 'wb') as f1:
            f1.write(data[:half])
        with open(output_path2, 'wb') as f2:
            f2.write(data[half:])
        return True
    except Exception as e:
        print(f"Binary split failed: {e}")
        return False

def rename_and_move_downloaded_file(temp_folder, videos_folder, counter_file, reel_url, links_file):
    # Wait until there are no active downloads
    while not is_download_complete(temp_folder):
        print("Waiting for download to complete...")
        time.sleep(5)  # Check every 5 seconds
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
            with open(links_file, 'r') as file:
                lines = file.readlines()

            # Update the specific line in memory and write back once
            if reel_url in lines:
                line_index = lines.index(reel_url + '\n')
                lines[line_index] = f"{reel_url} - LARGE FILE\n"

            with open(links_file, 'w') as file:
                file.writelines(lines)
        else:
            final_path = os.path.join(videos_folder, new_filename)
            shutil.move(renamed_path, final_path)
            print(f"File renamed and moved to: {final_path}")
        increment_counter(counter_file)

# Function to download Instagram reels using sssinstagram.net
def download_instagram_reels_sssinstagram(reel_url, temp_folder, videos_folder, counter_file, links_file):
    driver = setup_selenium(temp_folder)
    # Navigate to sssinstagram's Instagram Reel Downloader
    driver.get("https://sssinstagram.com/reels-downloader")
    time.sleep(10)
    try:
        # Find the input box and paste the reel URL
        input_box = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//input[@id='input']"))
        )
        input_box.send_keys(reel_url)
        
        # Click the Download button to submit the URL
        download_button = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//button[@type='submit']"))
        )
        download_button.click()
        time.sleep(10)

    
        # Wait for either of the "Download Video" buttons to appear and get the href
        download_video_button = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//a[@class='button button--filled button__download']"))
        )

        # Extract the href link for the video
        video_download_link = download_video_button.get_attribute("href")
        print(f"Download link: {video_download_link}")
        
        # Download the video manually using the extracted href link
        driver.get(video_download_link)
        time.sleep(30)  # Give time for the download to start
    
        # Rename the file after download
        rename_and_move_downloaded_file(temp_folder, videos_folder, counter_file, reel_url,links_file)

        # print(f"Download attempt finished for: {reel_url}")
        driver.quit() 
        return 1
        
    except Exception as e:
        print(f"Error clicking the download button or fetching video link: {str(e)}")
        driver.quit() 
        return 0
    
# Add this function to handle retries
def download_with_retry(reel_url, temp_folder, videos_folder, counter_file, links_file, max_retries=7):
    attempt = 0
    success = False

    while attempt < max_retries and not success:
        print("attempt Reel= ",attempt)
        number = download_instagram_reels_sssinstagram(reel_url, temp_folder, videos_folder, counter_file, links_file)
        if number == 1:
            success = True
            break
        else:
            attempt += 1
            time.sleep(5)  # Wait for a few seconds before retrying
            
    if not success:
        print(f"Failed to download reel after {max_retries} attempts: {reel_url}")
                  
# Main function to automate the process
def main():
    temp_folder = "temp"
    videos_folder = "VIDEOS"
    counter_file = "counter.txt"
    links_file = "links.txt"
    
    # Read reel links from the .txt file
    with open(links_file, 'r') as file:
        reel_links = [line.strip() for line in file.readlines()]
        for reel_link in reel_links:
            print(f"Downloading reel: {reel_link}")
            download_with_retry(reel_link, temp_folder, videos_folder, counter_file, links_file)

if __name__ == "__main__":
    main()
