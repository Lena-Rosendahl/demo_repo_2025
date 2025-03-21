"""
File: Sentiment analysis
Author: Lena Rosendahl
Publication date: 03.2025
"""

"""
Step 1: Read in snippets with mentions
Step 2: Pass snippets through nltk sentiment analysis using vader.
Step 3: Pass whole text through sentiment analysis.
Step 4: 

"""

import pandas as pd
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer
import re
import numpy as np
import argparse
from pathlib import Path
import os
from tqdm import tqdm

def read_tag_info(tag_data_path):
    tags_df = pd.read_excel(tag_data_path, sheet_name = "tagging_metadata")
    
    return tags_df

def read_title_info(works_data_path):
    titles_df = pd.read_excel(works_data_path, sheet_name = "works_info")
    
    return titles_df

def sentiment_analysis_per_sentence(tags_df):
    sentences = list(tags_df['snippet'])
    # Initialize VADER sentiment analyzer
    sid = SentimentIntensityAnalyzer()
    
    # Perform sentiment analysis
    sentiment_scores = [sid.polarity_scores(sentence).get('compound') for sentence in sentences]
    tags_df['sentiment'] = sentiment_scores
    return tags_df

def sentiment_analysis_all_mentions(tags_df):
    whole_doc_df = tags_df[['work_id','snippet']]
    whole_doc_tags_df = whole_doc_df.groupby('work_id')['snippet'].apply(lambda x: '. '.join(x))
    whole_doc_tags_df = whole_doc_tags_df.reset_index()
    all_texts = list(whole_doc_tags_df['snippet'])
    sid = SentimentIntensityAnalyzer()
    sentiment_scores = [sid.polarity_scores(text).get('compound') for text in all_texts]
    whole_doc_tags_df['sentiment_all_mentions'] = sentiment_scores
    whole_doc_tags_df = whole_doc_tags_df.drop('snippet', axis = 1)
    return whole_doc_tags_df

def sentiment_analysis_titles(titles_df):
    titles_df = titles_df[['work_id','title']]
    all_titles = list(titles_df['title'])
    sid = SentimentIntensityAnalyzer()
    sentiment_scores = [sid.polarity_scores(title).get('compound') for title in all_titles]
    titles_df['sentiment_title'] = sentiment_scores
    return titles_df

def read_text(text_loc):
    # Step two, extract work id
    work_id = text_loc.stem
    # Step three, read in

    with open(text_loc, 'r') as file:
        body_text = file.readlines()
    
    body_text = [line.strip() for line in body_text]
    return body_text, work_id

def sentiment_analysis_whole_doc(text_path, work_level_df):
    all_text_files = os.listdir(text_path)
    sentiment_scores = []
    for file in tqdm(all_text_files, desc = "Doing sentiment analysis on all sentences in document...", unit = "text file"):
        body_text, _ = read_text(text_path / file)
        body_text = '. '.join(body_text)
        sid = SentimentIntensityAnalyzer()
        sentiment_scores.append(sid.polarity_scores(body_text).get('compound'))
    work_level_df['sentiment_all_sentences'] = sentiment_scores
    return work_level_df
        

def write_sentiment_analysis_results(mention_level_df, work_level_df, metadata_path):

    # Write to an xlsx
    writer = pd.ExcelWriter(metadata_path, mode = 'a', engine='xlsxwriter')
    mention_level_df.to_excel(writer,'mention_level')
    work_level_df.to_excel(writer,'work_level')
    
    # Close
    writer.close()
    
def main(metadata_path, tag_fn, works_fn, text_path):
    # Download VADER lexicon
    nltk.download('vader_lexicon')
    tags_df = read_tag_info(metadata_path / tag_fn)
    mention_level_df = sentiment_analysis_per_sentence(tags_df)
    work_level_df = sentiment_analysis_all_mentions(tags_df)
    titles_df = read_title_info(metadata_path / works_fn)
    titles_df = sentiment_analysis_titles(titles_df)
    work_level_df = work_level_df.merge(titles_df)
    whole_doc_df = sentiment_analysis_whole_doc(text_path, work_level_df)
    work_level_df =work_level_df.merge(whole_doc_df)


    write_sentiment_analysis_results(mention_level_df, work_level_df, metadata_path / tag_fn)
    print('complete')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sentiment analysis on text"
    )
    parser.add_argument("--metadata_path", type=str, help="Path to stored metadata")
    parser.add_argument("--text_path", type=str, help="Path to stored text")
    parser.add_argument("--tag_fn", type=str, help="Filename for tags metadata")
    parser.add_argument("--works_fn", type=str, help="Filename for works metadata")
    args = parser.parse_args()

    metadata_path = Path(args.metadata_path)
    text_path = Path(args.text_path)
    
    main(metadata_path, args.tag_fn, args.works_fn, text_path)