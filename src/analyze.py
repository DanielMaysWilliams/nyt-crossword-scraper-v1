import argparse
import datetime
import json
import logging
import os
from typing import Any

from transformers import pipeline

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d:%H:%M:%S",
    level=os.environ.get("LOGLEVEL", "INFO").upper(),
)


def valid_date(s: str) -> datetime.datetime:
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a valid date: {s!r}")


def main(puzzle_date: datetime.date):
    filename = f"comments/comments-{puzzle_date:%Y-%m-%d}.json"
    logger.info(f"Analyzing comments from file {filename}")

    with open(filename, "r") as f:
        comments = json.load(f)

    sentiment_analyzer = pipeline(
        "text-classification",
        model="cardiffnlp/twitter-roberta-base-sentiment-latest",
        device=0,
    )

    for i, comment in enumerate(comments):
        logger.info(f"Analyzing comment {comment["commentID"]}")
        analyzer: Any = sentiment_analyzer(
            comment["commentBody"],
            truncation=True,
            max_length=512,
        )
        sentiment = analyzer[0]
        comments[i]["sentimentLabel"] = sentiment["label"]
        comments[i]["sentimentScore"] = sentiment["score"]

    with open(filename, "w") as f:
        json.dump(comments, f)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-d",
        "--date",
        help="The Puzzle Date - format YYYY-MM-DD",
        required=True,
        type=valid_date,
    )
    args = parser.parse_args()
    puzzle_day: datetime.date = args.date.date()
    main(puzzle_day)
