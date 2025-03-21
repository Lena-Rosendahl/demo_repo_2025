# ###
# File: Author analysis
# Author: Lena Rosendahl
# Publication date: 03.2025
# ###

# ###
# Step 1: Read in author metadata
# Step 2: Do author analysis
#   - Count unique authors by ID
#   - Count unique first authors by ID
#   - Count unique countries
#   - Count unique authors by country
#   - Can we viz coauthor groups?
# Step 3: Output relevant tables to xlsx.
# ###
library('readxl')
library('tidyverse')
# library('xlsx')
authors_data <- read_excel("C:/Users/LRosendahl/OneDrive - Mathematica/Documents/demo_2025/metadata_storage/OA_works_metadata.xlsx", 
                           sheet = "authors_info"
)
authors_data = authors_data %>% rename('position' = '...1')

# Clean prefixes off of author IDs
authors_data$id = sapply(strsplit(authors_data$id, '/'),'[',4)

#count unqiue authors by ID
unique_authors = authors_data$id %>% n_distinct()

# Count unique first authors by ID
unique_first_authors = (authors_data %>% filter(position == 1))$id %>% n_distinct()

#Count authors per work 
authors_per_work = authors_data %>% group_by(work_id) %>% summarize(authors = n_distinct(id)) %>% arrange(desc(authors))

# Count works per author
contributions_per_authors = authors_data %>% 
  group_by(id) %>% 
  summarize('contributions' = n_distinct(work_id)) %>% 
  arrange(desc(contributions))

# Count first authorships per author
first_authorships = authors_data %>% 
  filter(position==1) %>% 
  group_by(id) %>% 
  summarize('contributions' = n_distinct(work_id)) %>% 
  arrange(desc(contributions))

# Count unique countries
authors_data$countries = gsub("\\[|\\]|\\'","",authors_data$countries)
authors_data$countries = gsub('"',"",authors_data$countries)
all_countries = strsplit(authors_data$countries,",") %>% # split lists within list
  unlist() %>% #flatten
  gsub(" ","",.)

unique_countries = all_countries %>% #clean white space
  unique()
unique_countries = length(unique_countries)

countries_df = as.data.frame(all_countries)
colnames(countries_df) = 'country'

# Count number of times a country appears. 
country_appearances = countries_df %>% group_by(country) %>% summarize(count = n()) %>% arrange(desc(count))

library('ggplot2')
authors_per_work %>% ggplot(aes(x = authors)) + 
  geom_histogram(binwidth = 1, color = 'black', fill = 'white')

authors_wide = authors_data %>% 
  pivot_wider(id_cols = work_id,
              names_from = position, 
              values_from = id, 
              names_prefix = "pos_" )

coauthorship_df = data.frame()
for (author in contributions_per_authors$id) {
  print(author)
  appears_in = authors_data %>% filter(id == author)
  coauthors = (authors_data %>% filter(work_id %in% appears_in$work_id))$id
  work = (authors_data %>% filter(work_id %in% appears_in$work_id))$work_id
  df = data.frame(ref_author = author, coauthors = coauthors, on_what = work)
  coauthorship_df = coauthorship_df %>% rbind(df)
}

# Remove pairings of author with themself
coauthorship_df = coauthorship_df %>% filter(ref_author != coauthors)

# How many coauthors does each author have?
coauthorship_df %>% 
  group_by(ref_author) %>% 
  summarize(num_coauthors = n_distinct(coauthors)) %>% 
  arrange(desc(num_coauthors)) 

# On how many works does each author appear with each of their coauthors?
coauthorship_df %>% 
  group_by(ref_author, coauthors) %>% 
  summarize(num_works = n_distinct(on_what)) %>% 
  arrange(desc(num_works)) 
