
def getToken():
    import requests
    import json
    import os
    
    # Try to get credentials from Streamlit secrets first (for Streamlit Cloud)
    try:
        import streamlit as st
        client_id = st.secrets.get("CLIENT_ID")
        client_secret = st.secrets.get("CLIENT_SECRET")
    except:
        # Fall back to .env file for local development
        from dotenv import load_dotenv
        load_dotenv()
        client_id = os.getenv("CLIENT_ID")
        client_secret = os.getenv("CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError("CLIENT_ID and CLIENT_SECRET must be set in Streamlit secrets or .env file")

    url = "https://api.deliverect.io/oauth/token"

    payload = json.dumps({
    "client_id": client_id,
    "client_secret": client_secret,
    "audience": "https://api.deliverect.com",
    "grant_type": "token"
    })
    headers = {
    'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload).json()
    return response["access_token"]

