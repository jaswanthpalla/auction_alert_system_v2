import pandas as pd
import glob
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_and_combine():
    combined_data = []

    # Source 1: ibbi.gov.py (reads .xls file)
    ibbi_files = glob.glob("auction_exports/ibbi_auctions_*.xls")
    if ibbi_files:
        try:
            latest_ibbi = max(ibbi_files, key=os.path.getctime)
            ibbi_gov = pd.read_csv(latest_ibbi, sep="\t", encoding="utf-8")
            # Rename columns as per combine.ipynb
            ibbi_gov.rename(columns={
                'CIN No.': 'Auction ID',
                'Last date of Submission': 'last_date_of_submission',
                'Name of Corporate Debtor': 'Bank/Organisation Name'
            }, inplace=True)
            # Add missing columns with default value "-"
            ibbi_gov["City/District/Location"] = "-"
            ibbi_gov["EMD"] = "-"
            ibbi_gov["Category"] = "-"
            ibbi_gov["Source"] = "IBBI"
            # Select required columns
            ibbi_gov = ibbi_gov[["Auction ID", 'Bank/Organisation Name', "City/District/Location", 'last_date_of_submission', 'Reserve Price', "EMD", "Category", "Source"]]
            # Standardize last_date_of_submission (already in DD-MM-YYYY, e.g., 02-06-2025)
            ibbi_gov['last_date_of_submission'] = pd.to_datetime(
                ibbi_gov['last_date_of_submission'], format='%d-%m-%Y', errors='coerce'
            )
            if ibbi_gov['last_date_of_submission'].isna().any():
                logger.warning("Some dates in ibbi.gov last_date_of_submission could not be parsed.")
            combined_data.append(ibbi_gov)
        except Exception as e:
            logger.error(f"Failed to process ibbi.gov data: {e}")

    # Source 2: albion_bank.py
    albion_files = glob.glob("auction_exports/albion_auctions_*.csv")
    if albion_files:
        try:
            latest_albion = max(albion_files, key=os.path.getctime)
            albion_data = pd.read_csv(latest_albion)
            # Rename columns as per combine.ipynb
            albion_data.rename(columns={
                "Bank Name": "Bank/Organisation Name",
                "Auction Date": "last_date_of_submission",
                "Location": "City/District/Location"
            }, inplace=True)
            # Get the first word from each Heading for Category
            first_words = albion_data["Heading"].str.split().str[0]
            albion_data['Category'] = first_words.values
            albion_data["EMD"] = "-"
            # Select required columns
            albion_data = albion_data[["Auction ID", 'Bank/Organisation Name', 'City/District/Location', 'last_date_of_submission', 'Reserve Price', "EMD", "Category"]]
            # Add source column
            albion_data["Source"] = "Albion"
            # Standardize last_date_of_submission (format: DD/MM/YYYY, e.g., 24/07/2025)
            albion_data['last_date_of_submission'] = pd.to_datetime(
                albion_data['last_date_of_submission'], format='%d/%m/%Y', errors='coerce'
            )
            if albion_data['last_date_of_submission'].isna().any():
                logger.warning("Some dates in albion_bank last_date_of_submission could not be parsed.")
            combined_data.append(albion_data)
        except Exception as e:
            logger.error(f"Failed to process albion_bank data: {e}")

    # Source 3: bank_e_auctions.py
    bank_e_files = glob.glob("auction_exports/bank_e_auctions_*.csv")
    if bank_e_files:
        try:
            latest_bank_e = max(bank_e_files, key=os.path.getctime)
            bank_e = pd.read_csv(latest_bank_e)
            # Drop unnecessary columns as per combine.ipynb
            cols_to_drop = [
                'Unnamed: 0', 'DRT Name', 'Unnamed: 10', 'Unnamed: 11',
                'Unnamed: 12', 'Unnamed: 14', 'Event Type', "Asset on Auction"
            ]
            bank_e.drop(columns=[col for col in cols_to_drop if col in bank_e.columns], inplace=True)
            # Rename columns as per combine.ipynb
            bank_e.rename(columns={
                'Unnamed: 13': 'Category',
                'Sealed Bid Submission last date': 'last_date_of_submission',
                "City/District": "City/District/Location"
            }, inplace=True)
            # Select required columns
            bank_e = bank_e[["Auction ID", 'Bank/Organisation Name', 'City/District/Location', 'last_date_of_submission', 'Reserve Price', "EMD", "Category"]]
            # Add source column
            bank_e['Source'] = 'link_of_e_auction'
            # Standardize last_date_of_submission (format: DD Mon YYYY, e.g., 21 May 2025)
            bank_e['last_date_of_submission'] = pd.to_datetime(
                bank_e['last_date_of_submission'], format='%d %b %Y', errors='coerce'
            )
            if bank_e['last_date_of_submission'].isna().any():
                logger.warning("Some dates in bank_e_auctions last_date_of_submission could not be parsed.")
            combined_data.append(bank_e)
        except Exception as e:
            logger.error(f"Failed to process bank_e_auctions data: {e}")

    # Source 4: web3_scrape.py
    web3_files = glob.glob("auction_exports/web3_auctions_*.csv")
    if web3_files:
        try:
            latest_web3 = max(web3_files, key=os.path.getctime)
            web3_data = pd.read_csv(latest_web3)
            # Derive Bank/Organisation Name and Location as per combine.ipynb
            web3_data["Bank/Organisation Name"] = web3_data["Organisation Chain"].str.split('|').str[:3].str.join('|')
            web3_data['City/District/Location'] = web3_data["Bank/Organisation Name"].str.extract(r'Govt of ([^|]*)')[0].str.strip()
            # Rename columns as per combine.ipynb
            web3_data.rename(columns={
                "Auction ID": "Auction ID",
                "Submission End Date": "last_date_of_submission",
                "Starting Price": "Reserve Price",
                "EMD Amount": "EMD",
                'Product Category': "Category"
            }, inplace=True)
            web3_data.fillna("-", inplace=True)
            # Select required columns
            web3_data = web3_data[["Auction ID", 'Bank/Organisation Name', "City/District/Location", 'last_date_of_submission', 'Reserve Price', "EMD", "Category"]]
            # Add source column
            web3_data["Source"] = "link_of_website_web3"
            # Standardize last_date_of_submission (format: DD-Mon-YYYY HH:MM AM/PM, e.g., 24-May-2025 09:30 AM)
            web3_data['last_date_of_submission'] = pd.to_datetime(
                web3_data['last_date_of_submission'], format='%d-%b-%Y %I:%M %p', errors='coerce'
            )
            if web3_data['last_date_of_submission'].isna().any():
                logger.warning("Some dates in web3_scrape last_date_of_submission could not be parsed.")
            combined_data.append(web3_data)
        except Exception as e:
            logger.error(f"Failed to process web3_scrape data: {e}")

    # Combine all data
    if combined_data:
        final_df = pd.concat(combined_data, ignore_index=True)

        # Calculate days_until_submission
        today = pd.to_datetime(datetime.now().date())
        final_df['days_until_submission'] = (final_df['last_date_of_submission'] - today).dt.days

        # Convert last_date_of_submission back to string in DD-MM-YYYY format
        final_df['last_date_of_submission'] = final_df['last_date_of_submission'].dt.strftime('%d-%m-%Y')
        # Replace NaT (failed parsing) with "-"
        final_df['last_date_of_submission'] = final_df['last_date_of_submission'].fillna('-')
        final_df['days_until_submission'] = final_df['days_until_submission'].fillna('-')

        # Save to CSV
        today_str = datetime.now().strftime('%Y%m%d')
        output_file = f"auction_exports/combined_auctions_{today_str}.csv"
        final_df.to_csv(output_file, index=False)
        logger.info("Combined data saved to: %s", output_file)
        return output_file
    else:
        logger.error("No data to combine.")
        return None

if __name__ == "__main__":
    process_and_combine()