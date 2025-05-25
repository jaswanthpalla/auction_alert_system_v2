import csv
import random
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
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
user_data_dir = tempfile.mkdtemp(prefix="chrome_user_data_albion_")
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
    
    driver.get("https://albionbankauctions.com/")
    driver.maximize_window()
    time.sleep(random.uniform(4, 7))  # Wait for JS to load content

    # --- Select "Upcoming" from the dropdown ---
    try:
        status_dropdown = Select(driver.find_element(By.ID, "sort"))
        status_dropdown.select_by_value("upcoming")
        time.sleep(random.uniform(2, 5))  # Wait for the page to reload with filtered data
        logger.info("Selected 'Upcoming' from dropdown.")
    except Exception as e:
        logger.error("Could not select 'Upcoming': %s", e)

    data = []
    page = 1

    while True:
        logger.info(f"Scraping page {page}...")
        time.sleep(random.uniform(2, 5))  # Random delay for page load

        cards = driver.find_elements(By.CLASS_NAME, "property-card")
        logger.info(f"Found {len(cards)} property cards.")

        for card in cards:
            try:
                auction_id = card.find_element(
                    By.XPATH, ".//p[contains(text(),'Auction ID')]/following-sibling::p"
                ).text
                heading = card.find_element(By.TAG_NAME, "h2").text
                location = card.find_element(By.CLASS_NAME, "property-location").text
                bank_name = card.find_element(
                    By.XPATH, ".//p[contains(text(),'Bank Name')]/following-sibling::div"
                ).text
                reserve_price = card.find_element(By.CLASS_NAME, "reserve_price").text
                auction_date = card.find_element(
                    By.XPATH, ".//p[contains(text(),'Auction Date')]/following-sibling::p"
                ).text

                data.append({
                    "Auction ID": auction_id,
                    "Heading": heading,
                    "Location": location,
                    "Bank Name": bank_name,
                    "Reserve Price": reserve_price,
                    "Auction Date": auction_date
                })
            except Exception as e:
                logger.error("Error parsing card: %s", e)

        # Try to click the "Next" button
        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, ".pagination a.next")
            if "disabled" in next_btn.get_attribute("class"):
                logger.info("Next button is disabled. Stopping.")
                break
            driver.execute_script("arguments[0].click();", next_btn)
            page += 1
            time.sleep(random.uniform(2, 5))  # Random delay after clicking next
        except (NoSuchElementException, ElementClickInterceptedException):
            logger.info("No more pages or cannot click next.")
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

# Write to CSV with date suffix
today_str = datetime.now().strftime('%Y%m%d')
output_file = os.path.join(DOWNLOAD_DIR, f"albion_auctions_{today_str}.csv")
with open(output_file, "w", newline='', encoding="utf-8") as csvfile:
    fieldnames = ["Auction ID", "Heading", "Location", "Bank Name", "Reserve Price", "Auction Date"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)
logger.info(f"Data saved to {output_file}")
