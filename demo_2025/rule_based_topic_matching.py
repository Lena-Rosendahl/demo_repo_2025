"""
File: rule_based_topic_matching
Author: Lena Rosendahl
Publication date: 03.2025
"""

"""
Step 1: Read in text
Step 2: Identify all exact matches in text
- Store the line on which it was found.
- Store metadata about the match.
Step 3: Identify all strong fuzzy matches in text.
- Store the line on which it was found.
- Store metadata about the match.
Step 4: Idenfify all weak fuzzy matches in text.
- Store the line on which it was found.
- Store metadata about the match.
Step 5: Identify and remove redundant matches.
- Define a redundant match as any for which the same topic is identified in the same line for different match types.
- Keep only the strongest of a match type.

"""
from rapidfuzz import fuzz, process
import pandas as pd
import nltk
import re
import numpy as np
import argparse
from pathlib import Path
import os
from tqdm import tqdm


def read_text(text_loc):
    # Step two, extract work id
    work_id = text_loc.stem
    # Step three, read in

    with open(text_loc, "r") as file:
        body_text = file.readlines()

    body_text = [line.strip() for line in body_text]
    return body_text, work_id


def tag_exact(topic, work_id, body_text):
    """
    Tag exact matches for datasets in one document.

    Parameters:
        work_id (str): ID of document
        body_text (list): Body text of the document as sentences.
        tags (list): Dataset names.

    Returns:
        tag_dict (dict): Dictionary of tags and metadata about tags.
    """

    if isinstance(topic, list):
        all_topics = re.compile(r"\b(" + "|".join(topic) + r")\b")
    else:
        all_topics = re.compile(topic)

    tag_list = []
    snippet_list = []
    section_id_list = []
    # Find exact matches to topic
    for sentence in body_text:
        exact_match_in_sentence = []
        exact_match_in_sentence = [
            m.group() for m in all_topics.finditer(sentence, re.IGNORECASE)
        ]
        if exact_match_in_sentence:
            snippet_list.extend([sentence] * len(exact_match_in_sentence))
            tag_list += exact_match_in_sentence
            section_id_list.extend(
                [body_text.index(sentence) + 1] * len(exact_match_in_sentence)
            )

    tag_dict = {
        "work_id": work_id,
        "section_id": section_id_list,
        "tag": tag_list,
        "score": None,
        "snippet": snippet_list,
        "tagger": "exact",
        "strength": "exact",
        # "flag_for_zs": [False]*len(tag_list)
    }

    return tag_dict


def tag_fuzzy(
    work_id,
    body_text,
    exact_tags,
    strong_fuzzy_tags,
    strength,
    topic,
    fuzzy_thresholds,
):
    """
    Tag exact matches for datasets in one document.

    Parameters
        work_id (str): ID of document
        body_text (list): Body text of the document as sentences.
        topic (list): Dataset names.

    Returns:
        tag_dict (dict): Dictionary of tags and metadata about tags.
    """

    found_exact_match = True if exact_tags.get("tag") != [] else False
    tag_list, snippet_list, section_id_list = get_fuzzy_matches_at_threshold(
        body_text, topic, fuzzy_thresholds[strength][0], fuzzy_thresholds[strength][1]
    )

    # Create comparison match list for cleaning redundant matches.
    found_control_match, control_tags = create_control_tags(
        found_exact_match, exact_tags, strong_fuzzy_tags, work_id, strength
    )

    # Flag matches for zero shot depending on redundancy with stronger matches.
    flag_for_zeroshot = tag_redundant_matches(
        control_tags, tag_list, found_control_match
    )
    # For strong matches: If no matches except unigrams, flag matches for zeroshot

    if all(
        [
            (not tag_list),
            (not found_exact_match),
            strength == "strong",
        ]
    ):
        flag_for_zeroshot = [True]
    # For weak matches: Flag for zero shot
    elif strength == "weak" and tag_list:
        flag_for_zeroshot = [True] * len(tag_list)

    tag_dict = {
        "work_id": work_id,
        "section_id": section_id_list,
        "tag": tag_list,
        "score": None,
        "snippet": snippet_list,
        "tagger": "fuzzy",
        "strength": strength,
        # "flag_for_zs": flag_for_zeroshot,
    }

    return tag_dict


def get_fuzzy_matches_at_threshold(body_text, topic, lower_threshold, upper_threshold):
    """
    Identify fuzzy matches with match strength within a certain range.

    Parameters:
        body_text (list): List of sentences in body text
        topic (list): List of topic to identify
        lower_threshold (numeric): Lower threshold for fuzzy matches
        upper_thrshold (numeric): Upper threshold for fuzzy matches

    Returns:
        tag_list (list): List of identified tags
        snippet_list (list): List containing sentences where tags were identified
        section_id_list (list): List containing the index of the sentences where tags were identified
    """
    topic_list = topic if isinstance(topic, list) else [topic]
    body_text_lc = [sentence.lower() for sentence in body_text]
    match_results = process.cdist(
        body_text_lc, topic_list, scorer=fuzz.partial_ratio
    )  # Returns a sentence_num by options_num array of match scores.
    section_id_list = np.array(
        (
            np.where(
                (match_results <= upper_threshold) & (match_results > lower_threshold)
            )
        )
    )  # Converts scores to boolean "matches"
    tag_list = [
        topic_list[x] for x in section_id_list[1, :]
    ]  # Returns the items identified
    snippet_list = [body_text[x] for x in section_id_list[0, :]]  # Returns a snippet.
    section_id_list = section_id_list[
        0, :
    ].tolist()  # Convert match_loc array to sentence idxs where match was
    section_id_list = [
        x + 1 for x in section_id_list
    ]  # Add 1 to every index to match DH

    return tag_list, snippet_list, section_id_list


def analysis_of_all_tag_metadata(dirty_tags_df):
    total_mentions_found = len(dirty_tags_df)
    total_mentions_by_strength = dirty_tags_df.groupby("strength").size()
    total_mentions_by_strength = total_mentions_by_strength.reset_index(name = 'count')
    return total_mentions_found, total_mentions_by_strength


def create_control_tags(
    found_exact_match, exact_tags, strong_fuzzy_tags, work_id, strength
):
    """
    To remove redundant fuzzy matches, create a list to compare fuzzy matches to (control_tags).
    If the fuzzy matches we're cleaning are strong matches, the control_tags will contain only exact matches.
    If the fuzzy matches we're cleaning are weak fuzzy matches, the control_tags will contain both exact and fuzzy matches.

    Parameters:
        found_exact_match (bool): Whether any exact matches were found
        exact_tags (dict): Dictionary of metadata about exact matches found, including lists of tags.
        strong_fuzzy_tags (dict): Dictionary of metadata about strong matches found, including lists of tags.
        work_id (str): Work ID (form open alex)
        strength (str): Strength of the current set of fuzzy matches (strong or weak)

    Returns:
        found_control_match (bool): Whether a control match (stronger match than strength) was found
        control_tags (dict): Dictionary of metadata about control matches.

    """

    if strength == "strong":
        found_control_match = found_exact_match
        control_tags = exact_tags

    else:
        found_strong_fuzzy_match = (
            strong_fuzzy_tags.get("matches") if strong_fuzzy_tags else False
        ) != []
        found_control_match = found_exact_match or found_strong_fuzzy_match

        if found_exact_match and not found_strong_fuzzy_match:
            control_tags = exact_tags
        elif found_strong_fuzzy_match and not found_exact_match:
            control_tags = strong_fuzzy_tags
        elif found_strong_fuzzy_match and exact_tags:
            control_tags = {
                "work_id": work_id,
                "tag": exact_tags.get("tag") + strong_fuzzy_tags.get("tag"),
                "tagger": "mixed",
                "section_id": exact_tags.get("section_id")
                + strong_fuzzy_tags.get("section_id"),
                "snippet": exact_tags.get("snippet") + strong_fuzzy_tags.get("snippet"),
                "strength": "mixed",
                # "flag_for_zs": [False]
                # * (len(exact_tags.get("tag")) + len(strong_fuzzy_tags.get("tag"))),
            }

    return found_control_match, control_tags


def tag_redundant_matches(
    control_tags,
    comparison_tags,
    found_control_match,
):
    """
    To identify cases where a weaker match that is more specific than a stronger match may be redundant,
    compare control and comparison tags.
        If a control match is a substring of a comparison match,
        flag the work to be passed through zero-shot classification.
    Example: Exact match = "Census Data", Strong fuzzy match = "1-year Census Data". In a case like this,
    it's possible the fuzzy match is a better one than the weak match (text contains "One-year Census Data".)
    or that the exact match is a better one (text only contains Census Data, but 1-year census data has a
    high enough match score to fall within the thresholds for matching.)


    Parameters:
        control_tags (dict): Dictionary of metadata about control matches.
        comparison_tags (dict):  Dictionary of metadata about comparison matches.
        found_control_match (bool): Whether a control match (stronger match than strength) was found

    Returns:
        flag_for_zeroshot (list): List of boolean flags of whether comparison_tags should be
            examined by the ZS algorithm
    """

    flag_for_zeroshot = [False] * len(comparison_tags)
    if (
        comparison_tags and found_control_match
    ):  # If we have both comparison and control matches
        control_matches = control_tags.get(
            "tag"
        )  # Get the names of assets in the control match list.

        # If a control match is a substring of a comparison match, tag the match for zeroshot.
        for control in control_matches:
            for compare in comparison_tags:
                if (control in compare) and (compare in comparison_tags):
                    flag_for_zeroshot[comparison_tags.index(compare)] = True

    return flag_for_zeroshot


def clean_rb_tags(tags):
    """
    Clean rule-based tag dataframe by:
        - Reshaping data so that it has one row per match found
        - Removing rows where no matches were found.
        - Identify matches that are truly redundant
            and keeping only the strongest version of the match.
            Example: If the algorithm found the tag "Census Data"
            for exact, strong, and weak matches,
            in the same sentence, drop the strong and weak matches, but
            retain the exact match.

    Additionally:
        - Determine whether any non-unigram tags were ID'd

    Parameters:
        Tags (list): List of dictionaries containing tag info

    Returns:
        tags_df (dataframe): Cleaned tag info
        no_non_unigram_tags_present (bool): Flag indicating whether no non-unigram matches were found.
            (Used for passing to ZS)
    """

    # Convert to dataframe
    tags_df = pd.DataFrame(tags)
    # One row per match found
    tags_df = tags_df.explode(["section_id", "tag", "snippet"])  # "flag_for_zs"
    # Drop rows where matches are not found
    tags_df = tags_df.loc[tags_df["tag"].notna()]

    # Assign relative strength and, where a match is truly redundant, keep only the strongest.
    tags_df["rel_strength"] = np.where(
        (tags_df["strength"] == "exact"),
        1,
        np.where(
            tags_df["strength"] == "strong",
            2,
            np.where(tags_df["strength"] == "weak", 3, 4),
        ),
    )
    shrink = tags_df.groupby(["work_id", "section_id", "tag"]).min("rel_strength")
    shrink = shrink.reset_index()
    tags_df = shrink.merge(tags_df, how="left")
    tags_df["model"] = "rule_based"
    tags_df.drop("rel_strength", axis=1, inplace=True)
    tags_df = tags_df.drop_duplicates()
    return tags_df


def analysis_of_tag_redundancy(
    tags_df, total_mentions_found, total_mentions_by_strength
):
    total_tags = len(tags_df)
    dedupe_mentions_by_strength = tags_df.groupby("strength").size()
    dedupe_mentions_by_strength = dedupe_mentions_by_strength.reset_index(name = 'count')
    compare_counts = pd.DataFrame(
        {"level": ["all"] + list(total_mentions_by_strength["strength"]),
        
            "all": [total_mentions_found] +
                list(total_mentions_by_strength["count"])
            
        ,
        
            "deduplicated": [total_tags] + 
                list(dedupe_mentions_by_strength["count"])
            
        },
    )
    compare_counts["percentage_lost"] = (
        1 - compare_counts["deduplicated"] / compare_counts["all"]
    ) * 100

    return compare_counts


def write_metdata(metadata_path, tags, comparison_df):
    # Make sure directory exists
    os.makedirs(metadata_path, exist_ok=True)

    # Write to an xlsx
    writer = pd.ExcelWriter(metadata_path / "tagging_metadata.xlsx", engine="openpyxl")
    tags.to_excel(writer, "tagging_metadata")
    comparison_df.to_excel(writer, "count_info")

    # Close
    writer.close()


def main(metadata_path: Path, text_path: Path, topic: str, fuzzy_thresholds) -> dict:
    """
    Apply rule-based tagging to idenfity mentions for all documents.

    Parameters:

    """
    clean_tags_df = pd.DataFrame()
    dirty_tags_df = pd.DataFrame()
    all_text_files = os.listdir(text_path)
    for file in tqdm(all_text_files, desc="Idenfitying mentions...", unit="text file"):
        tags = []
        body_text, work_id = read_text(text_path / file)
        exact_tags = tag_exact(topic, work_id, body_text)
        strong_fuzzy_tags = tag_fuzzy(
            work_id,
            body_text,
            exact_tags,
            [],
            "strong",
            topic,
            fuzzy_thresholds,
        )
        weak_fuzzy_tags = tag_fuzzy(
            work_id,
            body_text,
            exact_tags,
            strong_fuzzy_tags,
            "weak",
            topic,
            fuzzy_thresholds,
        )
        
        tags.extend([exact_tags, strong_fuzzy_tags, weak_fuzzy_tags])
        
        dirty_tags_df = pd.concat([dirty_tags_df,pd.DataFrame(tags).explode(["section_id", "tag", "snippet"])])
        
        tags_df = clean_rb_tags(tags)
        clean_tags_df = pd.concat([clean_tags_df, tags_df])
    
    total_mentions_found, total_mentions_by_strength = analysis_of_all_tag_metadata(dirty_tags_df)
    comparison_df = analysis_of_tag_redundancy(
        clean_tags_df, total_mentions_found, total_mentions_by_strength
        )
    write_metdata(metadata_path, clean_tags_df, comparison_df)
    print('Complete')

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Identify mentions in text")
    parser.add_argument("--metadata_path", type=str, help="Path to store metadata")
    parser.add_argument("--text_path", type=str, help="Path to text")
    parser.add_argument(
        "--topics", type=str, help="topic for which to identify mentions"
    )

    args = parser.parse_args()
    metadata_path = Path(args.metadata_path)
    text_path = Path(args.text_path)

    main(
        metadata_path,
        text_path,
        args.topics,
        fuzzy_thresholds={"strong": [87.5, 100], "weak": [80, 87.5]},
    )
