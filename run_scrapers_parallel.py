# run_scrapers_parallel.py

from concurrent.futures import ThreadPoolExecutor
import subprocess
import os

# List your scraper script filenames here
scrapers = [
    "ibbi.gov.py",
    "albion_bank.py",
    "bank_e_auctions.py",
    "web3_scrape.py"
]

def run_script(script_name):
    # Create a unique Chrome user data directory for this scraper
    scraper_name = script_name.replace(".py", "")
    chrome_dir = f"/tmp/chrome_user_data_{scraper_name}"
    os.makedirs(chrome_dir, exist_ok=True)

    print(f"Running {script_name} with Chrome user data dir: {chrome_dir}...")
    env = os.environ.copy()
    env["CHROME_USER_DATA_DIR"] = chrome_dir  # Pass the directory to the scraper via environment variable

    try:
        result = subprocess.run(
            ["python", script_name],
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"Finished {script_name}\nOutput:\n{result.stdout}")
        return f"Success: {script_name}"
    except subprocess.CalledProcessError as e:
        error_msg = f"Error in {script_name}\nSTDERR:\n{e.stderr}\nSTDOUT:\n{e.stdout}"
        print(error_msg)
        raise Exception(error_msg)  # Re-raise the exception to ensure the workflow fails if a scraper fails

if __name__ == "__main__":
    # Run all scrapers in parallel with ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(run_script, scrapers))

    # Print a summary of results
    print("\n=== Scraper Execution Summary ===")
    for result in results:
        print(result)
