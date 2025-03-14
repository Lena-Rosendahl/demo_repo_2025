"""
File: download_URLs
Author: Lena Rosendahl
Publication date: 03.2025
"""

import requests
import json
import os
import argparse
from pathlib import Path
import pandas as pd
from tqdm import tqdm
import xlsxwriter
from fake_useragent import UserAgent
import random
"""
Step 1: Read in metadata about URLs
Step 2: Use URLs to access PDFs
Step 3: Check that PDF can be opened and is in english
Step 4: Convert to text
Step 5: Clean text
Step 6: Idenfity matches
Step 7: Collect a section of surrounding text
Step 8: Clean mentions
Step 9: Store cleaned mentions
Step 10: Remove PDF
"""

def get_all_uas():
    """
    Gets the full list of potential user-agents from fake_useragent. Can be used to sample all UAs sequentially.

    Args:
        None

    Returns:
        all_uas (list): List of all user agents we cycle through for queries
    """
    ua = UserAgent()
    data_browsers = (ua.__dict__).get("data_browsers")
    all_uas = list(pd.DataFrame(data_browsers)["useragent"].unique())
    return all_uas

def make_scrape_request(url, headers):
    """
    Makes a request for info using requests.get
    Args:
        url (str): Where the info comes from
        headers: Metadata to include with request.

    Returns:
        response: server response
    """
    # Request information. Time out request if server does not respond after 10 seconds.
    # Time out request even if server does respond after 1 minute.
    if headers:
        response = requests.get(url, headers=headers, timeout=(10, 60))
    else:
        response = requests.get(url, timeout=(10, 60))
    response.raise_for_status()
    return response        

def read_paper(
    url, headers
):
    """
    Downloads a PDF from a URL provided by OpenAlex

    Args:
        url (str): URL for attempted download,
        headers (str): Header selected for request to URL,
        pdf_path (path): Location to save PDF,
        
    Returns:
        status (str): Information about how the scrape went

    """

    try:
        
        response = make_scrape_request(url, headers)
        bytes = response.content
        text = bytes.decode('utf-8')
        print(f"> Read {id}.pdf from URL")
    except Exception as e:
        print(f"> Error - Scrape failed at this URL: {e}")
        text = None
    return text
    


###
def main(metadata_path):
    urls_df = pd.read_excel(metadata_path, sheet_name = "urls_info")
    urls_dict = urls_df.to_dict(orient = 'records')
    attempt_meta_info = list()
    # Get a set of user agent info to use in requests. Can help improve success rate.
    all_headers = get_all_uas()
    for work, locations in urls_dict.items():
        status = 'Fail'
        if locations:
            for url in locations:
                # Attempt download from each location until one is successful.
                headers = {"User-Agent": random.choice(all_headers)}
                print(f"> Attempting location: {url}")
                text = read_paper(url, headers)
                if text: 
                    # clean_text
                    print("cleaning")
                else: 
                    attempt_meta_info.extend([{'OA_id': work, 'URL_attempted': url, 'status': status, 'Fail type': 'Could not read PDF'}])
                
                if status == 'Success':
                    break
            else: continue
        else: 
            attempt_meta_info.extend([{'OA_id': work, 'URL_attempted': 'None', 'status': status, 'Fail type': 'No URLs'}])
