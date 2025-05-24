from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import pandas as pd
import hashlib
from datetime import datetime
import os
import shutil  # Added for directory cleanup
import psutil  # Added for process cleanup

# Set up Chrome options for headless mode
chrome_options = Options()
# chrome_options.add_argument("--headless")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Output directory
DOWNLOAD_DIR = "auction_exports"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# Specify a unique user data directory
user_data_dir = os.path.join(DOWNLOAD_DIR, "chrome_user_data_bank_e")
chrome_options.add_argument(f"--user-data-dir={user_data_dir}")

def cleanup_chrome_processes():
    """Kill any lingering Chrome processes."""
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] in ['chrome', 'chromedriver']:
            try:
                proc.kill()
                print(f"Killed lingering process: {proc.info['name']}")
            except psutil.NoSuchProcess:
                pass

# Initialize the WebDriver
driver = None
try:
    driver = webdriver.Chrome(options=chrome_options)
    driver.get("https://www.bankeauctions.com/")

    # Wait for the table to be present
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
    except Exception as e:
        print(f"Failed to load initial page: {e}")
        driver.quit()
        exit()

    all_data = []
    page_count = 0
    max_pages = 200  # Safety limit
    previous_page_hash = None
    max_retries = 3

    while True:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        table = soup.find("table")
        
        if not table:
            print(f"No table found on page {page_count + 1}. Stopping.")
            break
        
        current_page_data = []
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            data = [cell.get_text(strip=True) for cell in cells]
            if data:
                current_page_data.append(data)
        
        current_page_hash = hashlib.md5(str(current_page_data).encode()).hexdigest()
        
        if current_page_hash == previous_page_hash and page_count > 0:
            print(f"Data unchanged on page {page_count + 1}. Stopping.")
            break
        
        all_data.extend(current_page_data)
        previous_page_hash = current_page_hash
        
        try:
            next_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Next')]"))
            )
            btn_class = next_button.get_attribute("class") or ""
            if "disabled" in btn_class.lower():
                print("Next button is disabled. Stopping.")
                break
            
            current_table_text = soup.find("table").get_text(strip=True)
            
            for attempt in range(max_retries):
                try:
                    next_button.click()
                    time.sleep(10)
                    WebDriverWait(driver, 30).until(
                        lambda d: BeautifulSoup(d.page_source, "html.parser").find("table").get_text(strip=True) != current_table_text
                    )
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located((By.TAG_NAME, "table"))
                    )
                    print(f"Successfully loaded new content on attempt {attempt + 1}")
                    break
                except Exception as e:
                    print(f"Attempt {attempt + 1} failed to load new content: {e}")
                    if attempt == max_retries - 1:
                        print("Max retries reached. Stopping and saving data.")
                        break
            
            else:
                break
            
            page_count += 1
            print(f"Scraped page {page_count}")
            
            if page_count >= max_pages:
                print("Reached max_pages limit. Stopping.")
                break
        
        except Exception as e:
            print(f"No Next button found or error occurred: {e}. Stopping.")
            break

finally:
    if driver:
        driver.quit()
        print("Browser closed")
    # Additional cleanup
    cleanup_chrome_processes()
    if user_data_dir and os.path.exists(user_data_dir):
        try:
            shutil.rmtree(user_data_dir)
            print("Cleaned up user data directory:", user_data_dir)
        except Exception as e:
            print("Failed to clean up user data directory:", e)

# Process and save the data with date suffix
if all_data:
    headers = all_data[0]
    rows = [row for row in all_data[1:] if row != headers]
    df = pd.DataFrame(rows, columns=headers)
    df = df.dropna(how="all")
    today_str = datetime.now().strftime('%Y%m%d')
    output_file = os.path.join(DOWNLOAD_DIR, f"bank_e_auctions_{today_str}.csv")
    df.to_csv(output_file, index=False)
    print(f"Data saved to {output_file} with {len(df)} rows")
else:
    print("No data found.")
