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

def read_tag_info(metadata_path):
    tags_df = pd.read_excel(metadata_path, sheet_name = "tagging_metadata")
    
    return tags_df

def sentiment_analysis_per_sentence(tags_df):
    sentences = list(tags_df['snippet'])
    # Initialize VADER sentiment analyzer
    sid = SentimentIntensityAnalyzer()
    
    # Perform sentiment analysis
    sentiment_scores = [sid.polarity_scores(sentence).get('compound') for sentence in sentences]
    tags_df['sentiment'] = sentiment_scores
    return tags_df

def sentiment_analysis_whole_document(tags_df):
    whole_doc_df = tags_df[['work_id','snippet']]
    whole_doc_tags_df = whole_doc_df.groupby('work_id')['snippet'].apply(lambda x: '. '.join(x))
    whole_doc_tags_df = whole_doc_tags_df.reset_index()
    all_texts = list(whole_doc_tags_df['snippet'])
    sid = SentimentIntensityAnalyzer()
    sentiment_scores = [sid.polarity_scores(text).get('compound') for text in all_texts]
    whole_doc_tags_df['sentiment'] = sentiment_scores
    return whole_doc_tags_df

def write_sentiment_analysis_results(tags_df, whole_doc_tags_df, metadata_path):

    # Write to an xlsx
    writer = pd.ExcelWriter(metadata_path, engine='xlsxwriter')
    tags_df.to_excel(writer,'sentence_level')
    whole_doc_tags_df.to_excel(writer,'work_level')
    
    # Close
    writer.close()
    
def main(metadata_path):
    # Download VADER lexicon
    nltk.download('vader_lexicon')
    tags_df = read_tag_info(metadata_path)
    tags_df = sentiment_analysis_per_sentence(tags_df)
    whole_doc_tags_df = sentiment_analysis_whole_document(tags_df)
    write_sentiment_analysis_results(tags_df, whole_doc_tags_df, metadata_path)
    print('complete')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sentiment analysis on text"
    )
    parser.add_argument("--metadata_path", type=str, help="Path to store metadata")

    args = parser.parse_args()
    metadata_path = Path(args.metadata_path)

    main(metadata_path)