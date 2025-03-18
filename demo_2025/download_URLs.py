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
import ast
import pymupdf
from PIL import Image
from langdetect import detect
import pytesseract
import re
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

def read_location_info(metadata_path):
    urls_df = pd.read_excel(metadata_path, sheet_name = "urls_info")[['work_id','urls']]
    urls_df['urls'] = urls_df['urls'].apply(ast.literal_eval)
    urls_dict = dict(zip(urls_df['work_id'],urls_df['urls']))
    return urls_dict

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

def download_paper(
    url, headers, pdf_path, work_id
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
        fn = work_id.split('/')[-1] + '.pdf'
        pdf_file_path = pdf_path / fn
        response = make_scrape_request(url, headers)
        with open(pdf_file_path, "wb") as pdf_file:
            pdf_file.write(response.content)
        downloaded = True
        print(f"> Read {fn} from URL")
    except Exception as e:
        print(f"> Error - Scrape failed at this URL: {e}")
        downloaded = False
    return downloaded, pdf_file_path
    
def verify_file(pdf_file):
    """
    Reads text from PDFs

    Args:
        pdf_path: Path to pdf

    Returns:
        text (str): The cleaned text.
    """
    # pdf_path = pdf_path / chosen_pdf
    # Extract text from the PDF
    # Check that there are pages in the doc?
    text = ""
    doc = False
    try:
        doc = pymupdf.open(pdf_file)
    except:
        print(f"Failed to read in {pdf_file.stem}")
    if doc:
        try:
            for page in doc:
                text += page.get_text("text", flags=pymupdf.TEXT_PRESERVE_LIGATURES)
            # If no text was extracted, try OCR
            if not text.strip():
                for page in doc:
                    pix = page.get_pixmap()
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    text += pytesseract.image_to_string(img) # Something is corrupting PDFs and I think this might be the culprit. 
        except:
            print(f"> Failed to parse text for {pdf_file}")
        doc.close()
    if text and detect(text)=="en":
        print(f"> {pdf_file.stem} is probably in English")
    else:
        print(f"> {pdf_file.stem} is probably NOT in English. Attempting another location")
        text = ""
    os.remove(pdf_file)
    return text

def clean_text(text):
    """
    Clean the extracted text by removing unnecessary whitespace, non-printable characters,
    and applying language-specific rules.

    Parameters:
        text (str): Raw extracted text.

    Returns:
        str: Cleaned text.
    """
    # Remove unicode characters
    text = re.sub(r"[^\x00-\x7F]+", "", text)

    # Remove non-printable characters
    text = "".join(
        char for char in text if char.isprintable() or char in ["\n", "\t"]
    )

    # Remove repeated spaces
    text = re.sub(r"\s{2,}", " ", text)

    # Remove newlines
    text = re.sub(r"\n{1,}", " ", text)

    # Remove hyphenation at line breaks
    text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)

    # Remove patterns like "[1]", often used for citations
    text = re.sub(r"\[\d+\]", "", text)

    # Remove isolated numbers
    text = re.sub(r"\b\d+\b", "", text)

    # Where multiple spaces have been introduced, replace with single space
    text = re.sub(r"\s{2,}", " ", text)

    # Remove floating punctuation
    # Step 1: floating punctuation
    text = re.sub(r"\s+[><=+#*!?.,;:%$-]{1,}\s+", ".", text)
    # Step 2: punctuation clumps
    text = re.sub(r"(\s*[><=+#*!?.,;:%$-]{2,}\s*)", ".", text)
    # Step 3: Remove carats
    text = re.sub(r"\^", "", text)

    # Replace backslashes with nothing
    text = text.replace("\\","")

    # Do special replacements for bracket type artifacts
    text = re.sub(r"\s*[,.;:]\s*\)", ")", text)
    text = re.sub(r"\s*[,.;:]\s*\]", "]", text)
    text = re.sub(r"\s*[,.;:]\s*\}", "}", text)
    text = re.sub(r"[\(\{\[][^A-Za-z]+[\)\}\]]|[\(\{\[][\)\}\]]", "",text)

    # Remove patterns like "% % % % % %"
    # Step 1: Remove punctuation surrounded by spaces.
    # Replace with a single period (so a floating period that should be a regular period won't get removed completely.)
    text = re.sub(r"(\s[><=+#*!?.,;:%$-]\s)", ".", text)
    # Step 2: Where this results in clumps of repeat punctuation, remove and replace with a single "."
    text = re.sub(r"([&><=+#*!?.,;:%$-]{2,})", ".", text)
    # Step 3: Anywhere we've introduced white space clumps, remove and replace with ". "
    text = re.sub(r"\s{2,}", ". ", text)

    # Remove known remaining artifacts
    # Step 1: Remove words concateneated with a '.'
    dotpattern = re.compile(r"[^\s{1,}]\.[^\s{1,}]")
    cases_in_text = re.findall(dotpattern, text)  # word.word or letter.letter.
    replacements = [re.sub(r"\.", " ", case) for case in cases_in_text]
    for idx, case in enumerate(cases_in_text):
        # text = re.sub(case, replacements[idx], text)
        text = text.replace(case,replacements[idx])
    # Step 2: Remove any "wordpart- wordpart" patterns.
    hyphenations = re.compile(r"[A-Za-z]+\-\s{1,}[A-Za-z]+")  # prev- alence type pattern.
    cases = re.findall(hyphenations, text)  # word.word or letter.letter.
    replacements = [re.sub(r"\-\s{1,}", "", case) for case in cases]
    for idx, case in enumerate(cases):
        # text = re.sub(case, replacements[idx], text)
        text = text.replace(case,replacements[idx])
    # Step 3: Remove any url and email type patterns
    text = re.sub(r"http\S+|www\.\S+|\S+\.com\S*|\S+.org\S*|\S+.gov\S*|\S+\@\S+",'',text)

    return text.strip()

def write_text(text, text_path, work):
    # Split text into sentences and assign unique IDs
    fn = work.split('/')[-1] + '.txt'
    text_file_path = text_path / fn
    sentences = re.split(r"[.]+", text)
    with open(text_file_path, "w", encoding="utf-8") as text_file:
        for i, sent in enumerate(sentences):
            unique_id = f"{id}_{i+1}"
            text_file.write(f"{unique_id}: {sent}\n")
    print(f"> Text written.")

def write_metadata(data_path, meta_df):

    # Make sure directory exists
    os.makedirs(data_path, exist_ok=True)

    # Write to an xlsx
    writer = pd.ExcelWriter(data_path / 'OA_works_metadata.xlsx', mode = 'a', engine='openpyxl')
    meta_df.to_excel(writer,'download_attempt_info')
    
    # Close
    writer.close()

def main(metadata_path):
    data_dir = metadata_path.parent
    urls_dict = read_location_info(metadata_path)
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
                downloaded, pdf_file_path = download_paper(url, headers, data_dir, work)
                if downloaded: 
                    # open and clean text.
                    print("> Verifying")
                    text = verify_file(pdf_file_path)
                    if text:
                        print("> Cleaning and saving.")
                        text = clean_text(text)
                        write_text(text, data_dir, work)
                        status = "Success"
                        attempt_meta_info.extend([{'OA_id': work, 'URL_attempted': url, 'status': status, 'Fail type': ''}])
                    else: 
                        attempt_meta_info.extend([{'OA_id': work, 'URL_attempted': url, 'status': status, 'Fail type': 'Could not read PDF'}])
                else: 
                    attempt_meta_info.extend([{'OA_id': work, 'URL_attempted': url, 'status': status, 'Fail type': 'Could not download PDF'}])
                
                if status == 'Success':
                    break
            else: continue
        else: 
            attempt_meta_info.extend([{'OA_id': work, 'URL_attempted': 'None', 'status': status, 'Fail type': 'No URLs'}])
    meta_df = pd.DataFrame(attempt_meta_info)
    write_metadata(data_dir, meta_df)
    print('> Complete')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download and clean OA papers"
    )
    parser.add_argument("--metadata_path", type=str, help="Path to URL information")
    args = parser.parse_args()
    data_path = Path(args.metadata_path)

    main(
        metadata_path = data_path
    )