# Catalog Importer

A Streamlit application to import catalog structures from CSV files to Deliverect.

## Local Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. For local development, create a `.env` file with:
```
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
```

## Running Locally

Start the Streamlit app:
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Deploying to Streamlit Cloud

1. Push your code to GitHub

2. Go to [Streamlit Cloud](https://share.streamlit.io/) and connect your repository

3. In the app settings, go to "Secrets" and add:
   ```
   DELIVERECT_CLIENT_ID = "your_client_id"
   DELIVERECT_CLIENT_SECRET = "your_client_secret"
   ```

4. The app will automatically deploy and use the secrets from Streamlit's vault

**Note:** The app will automatically use Streamlit secrets when deployed, and fall back to `.env` file for local development.

## Usage

1. Enter your **Account ID** in the sidebar
2. Enter a **Menu Name** for the new catalog
3. Upload your **CSV file** with the catalog structure
4. Click "Start Import" to begin the import process

## CSV Format

Your CSV file should have the following columns:
- `Category 1`: Main category name
- `Category 2`: Subcategory name  
- `Plu`: Product PLU code

## Account Linking

If you get an error about account access, you need to link your account to the developer account:
- Developer Account ID: `690ca201b9c6f85ca05b6eb1`

## Features

- ✅ Account access validation
- ✅ Catalog listing
- ✅ Progress tracking
- ✅ Error handling
- ✅ Import statistics

# RetailCatalogImporter
