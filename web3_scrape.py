from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import pandas as pd
from selenium.common.exceptions import TimeoutException
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
    chrome_options.add_argument("--headless")  # Enable headless mode
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
user_data_dir = tempfile.mkdtemp(prefix="chrome_user_data_web3_")
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
    
    wait = WebDriverWait(driver, 15)
    driver.get("https://eauction.gov.in/eAuction/app?page=FrontEndEauctionByDate&service=page")
    time.sleep(5)

    try:
        closing_tab = driver.find_element(By.ID, "closingWeekTab")
        closing_tab.click()
        time.sleep(5)
        logger.info("Clicked 'Closing within 7 days' tab.")
    except Exception as e:
        logger.error("Could not click 'Closing within 7 days' tab: %s", e)

    results = []
    page_num = 1

    while True:
        logger.info(f"Scraping page {page_num}...")
        search_links = driver.find_elements(By.XPATH, "//a[starts-with(@id, 'view_')]")
        popup_urls = [link.get_attribute("href") for link in search_links]

        for url in popup_urls:
            driver.execute_script("window.open(arguments[0]);", url)
            driver.switch_to.window(driver.window_handles[-1])
            time.sleep(5)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            data = {}

            def get_value(label):
                td = soup.find('td', string=lambda s: s and label in s)
                if td and td.find_next_sibling('td'):
                    return td.find_next_sibling('td').get_text(strip=True)
                return ""

            data['Organisation Chain'] = get_value("Organisation Chain")
            data['Auction ID'] = get_value("Auction ID")
            data['EMD Amount'] = get_value("EMD Amount in ₹")
            data['Starting Price'] = get_value("Starting Price in ₹")
            data['Submission Start Date'] = get_value("Submission Start Date")
            data['Submission End Date'] = get_value("Submission End Date")
            data['Auction Start Date'] = get_value("Auction Start Date")
            data['Product Category'] = get_value("Product Category") 

            results.append(data)
            driver.close()
            driver.switch_to.window(driver.window_handles[0])

        try:
            next_btn = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="linkFwd"]')))
            driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
            time.sleep(1)
            next_btn.click()
            time.sleep(3)
            page_num += 1
        except TimeoutException:
            logger.info("No more pages or next button not clickable (timeout).")
            break
        except Exception as e:
            logger.info("No more pages or next button not found: %s", e)
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

df = pd.DataFrame(results)
today_str = datetime.now().strftime('%Y%m%d')
output_file = os.path.join(DOWNLOAD_DIR, f"web3_auctions_{today_str}.csv")
df.to_csv(output_file, index=False)
logger.info(f"Saved to {output_file}")
