from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging
import os
import glob
from datetime import datetime  # Added for date suffix

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Output directory
DOWNLOAD_DIR = "auction_exports"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def setup_chrome_options():
    """Set up Chrome options for headless browsing."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")
    chrome_options.add_experimental_option('prefs', {
        "download.default_directory": os.path.abspath(DOWNLOAD_DIR),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "plugins.always_open_pdf_externally": True,
        "safebrowsing.enabled": True
    })
    return chrome_options

def scrape_auctions():
    """Scrape auction data from IBBI website and download Excel file."""
    driver = None
    try:
        # Setup Chrome driver
        chrome_options = setup_chrome_options()
        logger.info("Download directory set to: %s", os.path.abspath(DOWNLOAD_DIR))
        driver = webdriver.Chrome(options=chrome_options)
        
        # Open IBBI auction site
        driver.get("https://ibbi.gov.in/en/liquidation-auction-notices/lists")
        logger.info("Waiting for page to load...")
        time.sleep(5)  # Wait for JavaScript to render
        
        # Click EXPORT button
        wait = WebDriverWait(driver, 30)
        export_button = wait.until(EC.element_to_be_clickable((By.NAME, "export_excel")))
        export_button.click()
        logger.info("EXPORT button clicked!")
        
        # Wait for file to download
        timeout = 120
        start_time = time.time()
        downloaded_file = None
        while time.time() - start_time < timeout:
            excel_files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.xls"))
            partial_files = glob.glob(os.path.join(DOWNLOAD_DIR, "*.crdownload"))
            logger.info("Files in directory: %s", os.listdir(DOWNLOAD_DIR))
            logger.info("Excel files found: %s", excel_files)
            logger.info("Partial downloads: %s", partial_files)
            if excel_files:
                downloaded_file = excel_files[0]
                break
            time.sleep(1)
        
        if downloaded_file:
            # Rename the downloaded file with date suffix
            today_str = datetime.now().strftime('%Y%m%d')
            new_filename = os.path.join(DOWNLOAD_DIR, f"ibbi_auctions_{today_str}.xls")
            os.rename(downloaded_file, new_filename)
            logger.info("Excel file renamed to: %s", new_filename)
            return new_filename
        else:
            logger.error("No Excel file found in %s after %d seconds", DOWNLOAD_DIR, timeout)
            return None
    
    except Exception as e:
        logger.error("Scraping failed: %s", e)
        return None
    
    finally:
        if driver:
            driver.quit()
            logger.info("Browser closed")

if __name__ == "__main__":
    scrape_auctions()