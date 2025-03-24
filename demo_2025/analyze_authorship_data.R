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
library('igraph')
library('data.table')
library('ggraph')
library('ggplot2')
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
contributions_per_authors$prolif_rank = paste("Rank",1:length(contributions_per_authors$id))

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
country_appearances = countries_df %>% 
  group_by(country) %>% 
  summarize(count = n()) %>% 
  arrange(desc(count))

authors_per_work %>% 
  ggplot(aes(x = authors)) + 
  geom_histogram(binwidth = 1,
                 color = 'black',
                 fill = 'white')

authors_wide = authors_data %>% 
  pivot_wider(id_cols = work_id,
              names_from = position, 
              values_from = id, 
              names_prefix = "pos_" )

coauthorship_df = data.frame()
for (author in contributions_per_authors$id) {
  appears_in = authors_data %>% filter(id == author)
  coauthors = (authors_data %>% filter(work_id %in% appears_in$work_id))$id
  rank = (contributions_per_authors %>% filter(id==author) %>% select(prolif_rank))[[1]]
  coauth_rank = contributions_per_authors %>% filter(id %in% coauthors) %>% select(prolif_rank)
  work = (authors_data %>% filter(work_id %in% appears_in$work_id))$work_id
  df = data.frame(ref_author = author,
                  ref_author_prolif_rank = rank,
                  coauthors = coauthors, 
                  # coauth_prolif_rank = coauth_rank,
                  on_what = work)
  coauthorship_df = coauthorship_df %>% rbind(df)
}

# Remove pairings of author with themselves
coauthorship_df = coauthorship_df %>% filter(ref_author != coauthors)
coauthorship_df$id = coauthorship_df$coauthors
coauthorship_df = coauthorship_df %>% merge(contributions_per_authors)
coauthorship_df$coauth_prolif_rank = coauthorship_df$prolif_rank
coauthorship_df = coauthorship_df %>% select(ref_author, 
                                             ref_author_prolif_rank,
                                             coauthors,
                                             coauth_prolif_rank,
                                             on_what)
# How many coauthors does each author have?
coauthorship_df %>% 
  group_by(ref_author_prolif_rank) %>% 
  summarize(num_coauthors = n_distinct(coauthors)) %>% 
  arrange(desc(num_coauthors)) 

# On how many works does each author appear with each of their coauthors?
how_many_collabs = coauthorship_df %>% 
  group_by(ref_author_prolif_rank, coauth_prolif_rank) %>% 
  summarize(num_works = n_distinct(on_what)) %>% 
  arrange(desc(num_works)) 

# Get top_N most prolific authors
top_n = 5
most_prolific = contributions_per_authors %>% head(top_n)

coauthorships_most_prolif = coauthorship_df %>% filter(ref_author %in% most_prolific$id)
# On how many works does each author appear with each of their coauthors?
how_many_collabs_mp = coauthorships_most_prolif %>% 
  group_by(ref_author_prolif_rank, coauth_prolif_rank) %>% 
  summarize(num_works = n_distinct(on_what)) %>% 
  arrange(desc(num_works)) 

# Set more standard column names
colnames(how_many_collabs_mp) = c("from","to","weight")
my_edgelist = graph_from_data_frame(how_many_collabs_mp, directed = F)

# If we prefer to work with an adjacency matrix, this will work
# my_adjacency = get.adjacency(my_edgelist)
number_of_collaborations = factor(E(my_edgelist)$weight)

ggraph(my_edgelist, layout = 'nicely') +
  geom_edge_link(aes(color = number_of_collaborations), width = 2)+
  scale_edge_color_brewer(palette = 'Dark2') + 
  geom_node_label(aes(label = name)) +
  ggtitle(paste('Collaborators with the most',
                top_n,
                'prolific authors'),
          subtitle = "Authors are 'ranked' from most to least publications") +
  labs(edge_color = "Number of collaborations") +
  theme_void(base_size = 15) +
  theme(plot.title = element_text(hjust = 0.5),
        plot.subtitle = element_text(hjust = 0.5)) +
  theme(legend.position = 'bottom')


  

