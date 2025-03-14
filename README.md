# demo_repo_2025
A repository containing demonstration code for resume items
Targeted resume items include:
- Web scraping:
  - Query the OpenAlex API to collect information about OA academic papers that may contain mentions of a topic or topics.
    - Use a set of query constraints to reduce the number of results to those likely to be relevant and reasonably easy to process.
    - Store query metadata
      - How many results are returned (Q1)
    - LIMITATION: To reduce needed resources and remain within the constraints of OpenAlex's "politeness" policies, I will be limiting work-level search results to only the first 200 results.
  - Store the work-level metadata for later analysis
    - OpenAlex ID used as a key
    - Publication year
    - Title
    - OpenAccess URLs
    - Topic
    - First author
    - First author's country
    - List of additional authors
  - Use the provided metadata to access those papers.
    - Using the list of all open access URLs, systematically query and download papers.
      - For each listed URL, attempt to download and, if successful, validate.
        - Validate downloads by opening and reading in and processing their contents.
        - NOTE: Although this process could be made more efficient via parallelization, reading in and processing a PDF's contents allows for validating the PDF's quality (file is in English and not corrupted) and accessing relevant data immediately so that files are not kept longer than the time required to read their contents.
      - Retain metdata about successful downloads and failed downloads (Q4)
        - Work-level success is defined as a paper that is downloaded and processed.
        - URL-level failure types include
          - Failed to download from URL
          - Download successful but item could not be opened
          - Download successful and item can be opened but text is not in english
        - Additional metadata to include
          - Number of URLs available for attempt
          - Number of URLs attempted before successful download
          - Domains of each URL
    - LIMITATION: To reduce needed resources, I will not be storing PDFs anywhere. For an equivalent project, I would recommend the use of AWS S3 buckets to do so. The boto3 package allows for easy upload.
  - Rule-based natural langauge processing:
    - Read in collected papers and identify any not in English
    - Convert the academic papers to machine readable text
    - Clean the resulting text
    - Identify those with exact mentions of the topic
    - Identify those with fuzzy matches to the topic using a set of strong and weak thresholds for match
    - For each mention identified, collect a section of surrounding text
  - Store the following information for later analysis:
    - OpenAlex ID (key)
    - The method used for identifying the mention (exact, rule-based strong match, rule-based fuzzy match)
    - The surrounding text
- Data wrangling and analysis:
    - Clean the set of all mentions:
      - Drop all of the following:
        - Mentions that are unlikely to contain a complete sentence (defined by length and token type). Such items may includ table and figure headers or notes.
        - Mentions that appear within the context of URLs or email addresses (these are likely coincidental mentions and ill-suited to sentiment analysis)
      - Retaining unique mentions priorizied by strength of identification strength (exact, then strong fuzzy, then weak fuzzy matches). (Q3)
- Machine learning natural language processing:
  - For each paper in which some mention was identified, conduct sentiment analysis on (Q5):
    - The title
    - All unique/cleaned mentions identified
    - Calculate an overall sentiment score by aggregating sentiments across mentions.

Items to be completed in Python:
- Web scraping
- Rule-based NLP
- ML-based NLP
Items to be completed in R:
- Any additional wrangling needed for analysis
- Any non-ML modeling conducted
- Visualizations

Questions of interest:
1. How does the number of results returned vary by year?
2. How many unique authors contribute to these results?

   2a. How many unique first authors?

   2b. How many unique authors per country? (NOTE: May remove this question as the English constraint necessarily introduces bias)

   2c. Can we visualize authorship by co-author? For example, a graph of authors taht appear together by frequency?
3. How much redundancy is there between matches identified using each matching method?
   
    3a. How many matches do we identify total?
   
    3b. How many matches do we identify by match strength?
   
    3c. What percentage of total matches do we drop when removing redundant matches?
   
    3d. What about by match strength (verify no exact matches are dropped)
   
4. What are the success rates of our download attempts?
   
    4a. At the work level?
   
    4b. Of the URL-level failures, what are the percentages by type?
   
    4c. Of the URL-level failures, what are the top 10 domains from which failed downloads originate?
   
5. What are the rates of positive and negative sentiments expressed?
   
    5a. By work?
   
    5b. By mention?
   
    5c. By year?
   

    
