#!/bin/bash

export $(grep -v '^#' .env | xargs)
source .venv/bin/activate

DATE=`date -I -d '-1 day'`

echo "Beginning run_all for puzzleDate $DATE"

python src/scrape.py -d $DATE
python src/analyze.py -d $DATE
python src/upload.py -d $DATE

echo "Finished run_all for puzzleDate $DATE"
