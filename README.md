# auction_alert_system_v2
Description: “Updated auction scraper for multiple sources with unified schema and enhanced features.” Visibility: Private (or Public, based on your preference). Initialize with a READM
# Auction Scraper V2

This project scrapes auction data from multiple sources, combines them into a unified schema, and provides a Streamlit app for viewing the data and sending email alerts for upcoming auctions.

## Features
- Scrapes auction data from IBBI, Albion Bank, Bank e-Auctions, and Web3.
- Combines data into a unified schema with columns: `Auction ID`, `Bank/Organisation Name`, `City/District/Location`, `last_date_of_submission`, `Reserve Price`, `EMD`, `Category`, `Source`, `days_until_submission`.
- Streamlit app for viewing and filtering auctions by `Source` and `days_until_submission`.
- Email alerts for auctions with submission deadlines within 7 days, including a CSV attachment.
- Automated daily scraping via GitHub Actions.
