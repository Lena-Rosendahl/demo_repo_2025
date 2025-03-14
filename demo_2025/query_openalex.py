"""
File: OA_query
Author: Lena Rosendahl
Publication date: 03.2025
"""

""" 
Step 1: Query OA API
Step 2: Collect and write metadata information
"""

"""
Helper functions for OpenAlex queries.
Authors: Lena Rosendahl
Date: August 2024
"""

import requests
import json
import os
import argparse
from pathlib import Path
import pandas as pd
from tqdm import tqdm
import xlsxwriter

def setup_params(param_path, email, topics, per_page=200):
    """
    Reads in parameter lists from json and creates appropriate variables for OA search

    Args:
        param_path (path): Where parameters json lives
        email (str): Email for polite pool
        per_page (int): Number of results per page

    Returns:
        oa_base_params (dict): Base parameters for OA search
        oa_addtl_filters (dict): Additional filters for OA search
    """
    with open(param_path, "r") as f:
        all_params = json.load(f)

    oa_base_params = all_params.get("OA_base_params")
    # Build out base parameters.
    oa_base_params.update({"per_page": per_page, "mailto": email})
    oa_addtl_filters = all_params.get("OA_addtl_filters")
    oa_addtl_filters["default.search"] = topics
    return oa_base_params, oa_addtl_filters


def sample_publications_ids(params, base_url, addtl_filters=None):
    """
    Samples publications from the OpenAlex API based on the given parameters.

    Args:
        params (dict): The parameters to pass to the API.
        addtl_filters (dict): Additional filters to apply to the sample.
        base_url (str): URL on which parameters are appended for OA search.

    Returns:
        data (dict): The response data from the API.
    """
    sample_params = params.copy()

    if addtl_filters:
        filter_str = sample_params.get("filter", "")
        addtl_filter_str = ",".join(
            [f"{key}:{value}" for key, value in addtl_filters.items()]
        )
        sample_params["filter"] = (
            filter_str + ("," if filter_str else "") + addtl_filter_str
        )

    try:
        response = requests.get(base_url, params=sample_params)
        response.raise_for_status()
        print(response.url)
        data = response.json()

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Request exception: {req_err}")
    except Exception as e:
        print(f"Error: {e}")

    return data

def get_metadata(resp):
    works = resp.get('results')
    meta_df = pd.DataFrame(resp.get('meta'), index = [0])
    works_df = pd.DataFrame(works)[['id','doi','title','relevance_score','publication_year']]
    # Get author info
    auths_df = pd.DataFrame()
    pdf_urls = list()
    for work in tqdm(works, desc = "Processing metadata...", unit = "work"):
        work_id = work.get('id')

        # Get author information in a dataframe
        auth_info = pd.DataFrame.from_records(pd.DataFrame(work.get('authorships'))['author'])
        auth_info['work_id'] = work_id
        auth_info['countries'] = pd.DataFrame(work.get('authorships'))['countries']
        auths_df = pd.concat([auths_df ,auth_info])

        # Get URL info in a list
        loc_info = pd.DataFrame(work.get("locations"))
        pdf_urls.extend([{'work_id': work_id, 'urls': [x for x in list(loc_info["pdf_url"]) if x is not None]}])
    urls_df = pd.DataFrame(pdf_urls)
    return meta_df, works_df, auths_df, urls_df

def write_metadata(data_path, meta_df, works_df, authors_df, urls_df):

    # Make sure directory exists
    os.makedirs(data_path, exist_ok=True)

    # Write to an xlsx
    writer = pd.ExcelWriter(data_path / 'OA_works_metadata.xlsx', engine='xlsxwriter')
    meta_df.to_excel(writer,'works_count')
    works_df.to_excel(writer,'works_info')
    authors_df.to_excel(writer,'authors_info')
    urls_df.to_excel(writer,'urls_info')
    
    # Close
    writer.close()


def main(param_path, email, topics, per_page, base_url, data_path):
    # Set up query
    params, addtl_filters = setup_params(
        param_path,
        email,
        topics,
        per_page,
    )

    try: 
        # Query
        resp = sample_publications_ids(
            params,
            base_url,
            addtl_filters
        )
    except:
        print("> Error: Could not complete OA query")
    
    
    # Get metadata
    
    meta_df, works_df, authors_df, urls_df = get_metadata(resp)
    
    # Write metadata
    # Although they're not efficient, xlsx workbooks are easy to read when opened in excel, so we'll use that. 
    write_metadata(data_path, meta_df, works_df, authors_df, urls_df)
    




if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pull list of works using OpenAlex as index."
    )
    parser.add_argument("--email", type=str, help="Email address")
    parser.add_argument("--data_path", type=str, help="Path to output data to")
    parser.add_argument(
        "--base_url",
        type=str,
        default="https://api.openalex.org/works",
        help="OpenAlex index URL, defaults to /works",
    )
    parser.add_argument(
        "--per_page", type=int, default=200, help="Number of results to return per page"
    )
    parser.add_argument(
        "--topics", type = str, help= "Topic to search using OA"
    )
    args = parser.parse_args()
    data_path = Path(args.data_path)

    main(
        "demo_2025/sampling_params.json",
        args.email,
        args.topics,
        args.per_page,
        args.base_url,
        data_path
    )