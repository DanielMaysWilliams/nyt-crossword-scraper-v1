Scrape comments from today's New York Times crossword and do some sentiment analysis to see what people think.
The process has been simplified by querying the NYT API directly to get comments.
Comments are then analyzed by a sentiment analysis pipeline from Hugging Face, then uploaded to S3 with DuckDB. 
