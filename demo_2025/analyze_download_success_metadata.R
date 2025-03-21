# ###
# File: Download success analysis
# Author: Lena Rosendahl
# Publication date: 03.2025
# ###

# ###
# Step 1: Read in download metadata
# Step 2: Do success analysis
#   - Count all works 
#   - Count works with any urls 
#   - Count all attempts at download
#   - Count number of successful attempts and get pct.
#   - Count number of successfully downloaded works and get pts.
#     - All
#     - With URLs
#   - At the attempt level, ID Domains for every URL and
#     - Filter for success and failure
#     - Count each by domain
#     - Return top 10 of each (or top something. 10 may not be worthwhile.)
# Step 3: Output relevant tables to xlsx.
# 
# ###
library('readxl')
library('tidyverse')
library('xlsx')
attempt_data <- read_excel("C:/Users/LRosendahl/OneDrive - Mathematica/Documents/demo_2025/metadata_storage/OA_works_metadata.xlsx", 
                           sheet = "download_attempt_info"
)
# Count all works
all_works = attempt_data['OA_id'] %>% unique() %>% count()
# Count works with any urls 
works_with_urls = attempt_data %>% 
  filter(URL_attempted != "None") %>% 
  select('OA_id') %>% 
  unique() %>% 
  count()
# Count all attempts at download
total_attempts_made = attempt_data %>% 
  filter(URL_attempted != "None") %>% 
  nrow()

names = c('Total works','Works with URLs','Total attempts made')
totals = c(all_works[[1]], works_with_urls[[1]], total_attempts_made[[1]])
counts_df = data.frame(names, total)

# Count number of successful attempts and get pct.
# Here, defining an attempt as a case where we had a URL and made a request.
percent_success_and_fail_per_attempt_df = attempt_data %>%
  filter(URL_attempted != "None") %>% 
  group_by(status) %>% 
  summarize(count = n()) %>%
  mutate(percent = 100*count/sum(count))

# Count number of successfully downloaded works and get pcts.
#  - All
#  - With URLs 
successfully_donwloaded_works = attempt_data %>% 
  filter(status == 'Success') %>% 
  select('OA_id') %>% 
  unique() %>% 
  count()
success_pct_of_total = 100*successfully_donwloaded_works/all_works
success_pct_of_works_with_urls = 100*successfully_donwloaded_works/works_with_urls
names = c('Percent of successful downloads: all works', 'Percent of successful downloads: works with urls')
percents = c(success_pct_of_total[[1]],success_pct_of_works_with_urls[[1]])
percent_success_per_work_df = data.frame(names, percents)

# - At the attempt level, ID Domains for every URL and
#   - Filter for success and failure
#   - Count each by domain
#   - Return top 10 of each (or top something. 10 may not be worthwhile.)

attempt_data$host = sapply(strsplit(attempt_data$URL_attempted,'/'),'[',3)
host_data = attempt_data %>% group_by(status, host) %>% summarize(count = n()) %>% arrange(desc(count))
top_10_most_successful_domains = host_data %>% filter(status == "Success") %>% head(10)
top_10_least_successful_domains = host_data %>% filter(status == "Fail", !is.na(host)) %>% head(10)

# All dfs: 
counts_df
percent_success_and_fail_per_attempt_df
percent_success_per_work_df
top_10_most_successful_domains
top_10_least_successful_domains

# Do writeout 
metadata_path = "C:/Users/LRosendahl/OneDrive - Mathematica/Documents/demo_2025/metadata_storage/OA_works_metadata.xlsx"
counts_df %>%  write.xlsx(metadata_path, sheet = "works_counts")
percent_success_and_fail_per_attempt_df %>%  write.xlsx(metadata_path, sheet = "percent_SF_per_attempt")
percent_success_per_work_df %>%  write.xlsx(metadata_path, sheet = "percent_success_per_work")
top_10_most_successful_domains %>% write.xlsx(metadata_path, sheet = "most_successful_domains")
top_10_least_successful_domains %>% write.xlsx(metadata_path, sheet = "least_successful_domains")
