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
import tempfile  # Added for temporary directories

options = Options()
# options.add_argument("--headless")  # Uncomment to run headless

# Output directory
DOWNLOAD_DIR = "auction_exports"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

def cleanup_chrome_processes():
    """Kill any lingering Chrome processes."""
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] in ['chrome', 'chromedriver']:
            try:
                proc.kill()
                print(f"Killed lingering process: {proc.info['name']}")
            except psutil.NoSuchProcess:
                pass

# Clean up any lingering Chrome processes before starting
cleanup_chrome_processes()

# Create a temporary user data directory
user_data_dir = tempfile.mkdtemp(prefix="chrome_user_data_albion_")
options.add_argument(f"--user-data-dir={user_data_dir}")

driver = None
try:
    driver = webdriver.Chrome(options=options)
    driver.get("https://albionbankauctions.com/")
    driver.maximize_window()
    time.sleep(random.uniform(4, 7))  # Wait for JS to load content

    # --- Select "Upcoming" from the dropdown ---
    try:
        status_dropdown = Select(driver.find_element(By.ID, "sort"))
        status_dropdown.select_by_value("upcoming")
        time.sleep(random.uniform(2, 5))  # Wait for the page to reload with filtered data
    except Exception as e:
        print("Could not select 'Upcoming':", e)

    data = []
    page = 1

    while True:
        print(f"Scraping page {page}...")
        time.sleep(random.uniform(2, 5))  # Random delay for page load

        cards = driver.find_elements(By.CLASS_NAME, "property-card")
        print(f"Found {len(cards)} property cards.")

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
                print("Error parsing card:", e)

        # Try to click the "Next" button
        try:
            next_btn = driver.find_element(By.CSS_SELECTOR, ".pagination a.next")
            if "disabled" in next_btn.get_attribute("class"):
                break
            driver.execute_script("arguments[0].click();", next_btn)
            page += 1
            time.sleep(random.uniform(2, 5))  # Random delay after clicking next
        except (NoSuchElementException, ElementClickInterceptedException):
            print("No more pages or cannot click next.")
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

# Write to CSV with date suffix
today_str = datetime.now().strftime('%Y%m%d')
output_file = os.path.join(DOWNLOAD_DIR, f"albion_auctions_{today_str}.csv")
with open(output_file, "w", newline='', encoding="utf-8") as csvfile:
    fieldnames = ["Auction ID", "Heading", "Location", "Bank Name", "Reserve Price", "Auction Date"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(data)
print(f"Data saved to {output_file}")
