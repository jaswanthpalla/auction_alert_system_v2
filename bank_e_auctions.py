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
import shutil
import psutil
import tempfile
import logging
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Output directory
DOWNLOAD_DIR = "auction_exports"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def setup_chrome_options(user_data_dir):
    """Set up Chrome options for headless browsing."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Enable headless mode like ibbi.gov.py
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
    chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
    chrome_options.add_experimental_option('prefs', {
        "download.default_directory": os.path.abspath(DOWNLOAD_DIR),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "safebrowsing.enabled": True
    })
    return chrome_options

def cleanup_chrome_processes():
    """Kill any lingering Chrome processes."""
    chrome_processes = []
    for proc in psutil.process_iter(['name', 'pid']):
        if proc.info['name'] in ['chrome', 'chromium', 'chromedriver']:
            chrome_processes.append((proc.info['pid'], proc.info['name']))
            try:
                proc.kill()
                logger.info(f"Killed lingering process: {proc.info['name']} (PID: {proc.info['pid']})")
            except psutil.NoSuchProcess:
                logger.info(f"Process {proc.info['name']} (PID: {proc.info['pid']}) already terminated.")
    return chrome_processes

# Clean up any lingering Chrome processes before starting
logger.info("Cleaning up Chrome processes before starting...")
existing_processes = cleanup_chrome_processes()
if existing_processes:
    logger.info(f"Found and killed {len(existing_processes)} Chrome-related processes: {existing_processes}")
else:
    logger.info("No Chrome-related processes found running.")

# Verify ChromeDriver version
try:
    chromedriver_version = subprocess.check_output(["chromedriver", "--version"]).decode().strip()
    logger.info(f"ChromeDriver version: {chromedriver_version}")
except Exception as e:
    logger.error(f"Failed to check ChromeDriver version: {e}")

# Create a temporary user data directory
user_data_dir = tempfile.mkdtemp(prefix="chrome_user_data_bank_e_")
logger.info(f"Created temporary user data directory: {user_data_dir}")

# Verify the directory is empty
if os.path.exists(user_data_dir):
    dir_contents = os.listdir(user_data_dir)
    if dir_contents:
        logger.warning(f"User data directory {user_data_dir} is not empty: {dir_contents}")
    else:
        logger.info(f"User data directory {user_data_dir} is empty as expected.")
else:
    logger.error(f"User data directory {user_data_dir} was not created!")
    exit(1)

# Initialize the WebDriver
chrome_options = setup_chrome_options(user_data_dir)
driver = None
try:
    logger.info("Starting Chrome WebDriver...")
    driver = webdriver.Chrome(options=chrome_options)
    logger.info("Chrome WebDriver started successfully.")
    
    driver.get("https://www.bankeauctions.com/")

    # Wait for the table to be present
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
        logger.info("Table loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load initial page: {e}")
        raise

    all_data = []
    page_count = 0
    max_pages = 200  # Safety limit
    previous_page_hash = None
    max_retries = 3

    while True:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        table = soup.find("table")
        
        if not table:
            logger.error(f"No table found on page {page_count + 1}. Stopping.")
            break
        
        current_page_data = []
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            data = [cell.get_text(strip=True) for cell in cells]
            if data:
                current_page_data.append(data)
        
        current_page_hash = hashlib.md5(str(current_page_data).encode()).hexdigest()
        
        if current_page_hash == previous_page_hash and page_count > 0:
            logger.info(f"Data unchanged on page {page_count + 1}. Stopping.")
            break
        
        all_data.extend(current_page_data)
        previous_page_hash = current_page_hash
        
        try:
            next_button = WebDriverWait(driver, 15).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Next')]"))
            )
            btn_class = next_button.get_attribute("class") or ""
            if "disabled" in btn_class.lower():
                logger.info("Next button is disabled. Stopping.")
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
                    logger.info(f"Successfully loaded new content on attempt {attempt + 1}")
                    break
                except Exception as e:
                    logger.error(f"Attempt {attempt + 1} failed to load new content: {e}")
                    if attempt == max_retries - 1:
                        logger.info("Max retries reached. Stopping and saving data.")
                        break
            
            else:
                break
            
            page_count += 1
            logger.info(f"Scraped page {page_count}")
            
            if page_count >= max_pages:
                logger.info("Reached max_pages limit. Stopping.")
                break
        
        except Exception as e:
            logger.info(f"No Next button found or error occurred: {e}. Stopping.")
            break

finally:
    if driver:
        driver.quit()
        logger.info("Browser closed")
    # Additional cleanup
    cleanup_chrome_processes()
    if user_data_dir and os.path.exists(user_data_dir):
        try:
            shutil.rmtree(user_data_dir)
            logger.info("Cleaned up user data directory: %s", user_data_dir)
        except Exception as e:
            logger.warning("Failed to clean up user data directory: %s", e)

# Process and save the data with date suffix
if all_data:
    headers = all_data[0]
    rows = [row for row in all_data[1:] if row != headers]
    df = pd.DataFrame(rows, columns=headers)
    df = df.dropna(how="all")
    today_str = datetime.now().strftime('%Y%m%d')
    output_file = os.path.join(DOWNLOAD_DIR, f"bank_e_auctions_{today_str}.csv")
    df.to_csv(output_file, index=False)
    logger.info(f"Data saved to {output_file} with {len(df)} rows")
else:
    logger.info("No data found.")
