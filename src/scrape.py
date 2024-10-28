import argparse
import datetime
import json
import logging
import os
import random
import time
from pathlib import Path
from typing import Any

import requests

API_URL = "https://www.nytimes.com/svc/community/V3/requestHandler"

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s,%(msecs)03d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s",
    datefmt="%Y-%m-%d:%H:%M:%S",
    level=os.environ.get("LOGLEVEL", "INFO").upper(),
)


class PuzzleCommentScraper:
    def __init__(self, puzzle_date: datetime.date, max_requests: int = 10, api_url: str = API_URL) -> None:
        self.puzzle_date = puzzle_date
        self.max_requests = max_requests
        self.api_url = api_url

        self.output_file = Path(f"comments/comments-{puzzle_date:%Y-%m-%d}.json")

        self.params: dict[str, Any] = {
            "url": (
                f"https://www.nytimes.com/{puzzle_date - datetime.timedelta(days=1):%Y/%m/%d}/"
                f"crosswords/daily-puzzle-{puzzle_date:%Y-%m-%d}.html"
            ),
            "method": "get",
            "commentSequence": 0,
            "offset": 0,
            "includeReplies": "true",
            "sort": "oldest",
            "cmd": "GetCommentsAll",
        }

        self.headers: dict[str, Any] = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
            "content-type": "application/json",
            "Host": "www.nytimes.com",
            "Priority": "u=4",
            "Referer": self.params["url"],
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "TE": "trailers",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                "(KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246"
            ),
        }

        self.comments: list[dict[str, Any]] = []
        self.replies: list[dict[str, Any]] = []

    def get_all_parent_comments(self) -> list[dict[str, Any]]:
        logger.info(f"Beginning scraping parent comments {self.params["url"]}")
        request_count = 0

        # do first request
        response = requests.get(self.api_url, params=self.params, headers=self.headers)
        request_count += 1
        logger.info(f"Got status code {response.status_code}")
        response.raise_for_status()

        data: dict[str, Any] = response.json()
        self.comments.clear()
        self.comments.extend(data["results"]["comments"])

        totalParentCommentsFound: int = data["results"]["totalParentCommentsFound"]
        totalParentCommentsReturned: int = data["results"]["totalParentCommentsReturned"]

        while (totalParentCommentsReturned < totalParentCommentsFound) and (request_count < self.max_requests):
            # Start from the last comment of the previous response
            self.params["commentSequence"] = self.comments[-1]["commentID"]
            self.params["offset"] = 25 * request_count
            self.params["limit"] = 25  # new param

            time.sleep(0.5 + random.random())

            response = requests.get(self.api_url, params=self.params, headers=self.headers)
            logger.info(f"Got status code {response.status_code}")
            response.raise_for_status()

            data = response.json()
            self.comments.extend(data["results"]["comments"])

            totalParentCommentsReturned += data["results"]["totalParentCommentsReturned"]

            request_count += 1

        for comment in self.comments:
            comment["puzzleDate"] = self.puzzle_date

        return self.comments

    def pop_and_get_all_replies(self):
        logger.info(f"Beginning scraping replies {self.params["url"]}")
        for comment in self.comments:
            comment_replies = []
            if len(comment["replies"]) < comment["replyCount"]:
                logger.info(f"Getting more replies for commentID={comment["commentID"]}")
                time.sleep(0.5 + random.random())
                comment_params = {
                    "url": self.params["url"],
                    "method": "get",
                    "commentSequence": comment["commentID"],
                    "offset": "3",
                    "limit": "25",
                    "cmd": "GetRepliesBySequence",
                }
                response = requests.get(self.api_url, params=comment_params, headers=self.headers)
                logger.info(f"Got status code {response.status_code}")
                response.raise_for_status()

                data = response.json()
                comment["replies"].extend(data["results"]["comments"][0]["replies"])

            comment_replies.extend(comment.pop("replies"))
            for comment_reply in comment_replies:
                comment_reply.pop("replies")
                comment_reply["puzzleDate"] = puzzle_date
            self.replies.extend(comment_replies)

        return self.replies

    def write_to_json(self):
        with open(self.output_file, "w") as f:
            json.dump([*self.comments, *self.replies], f, default=str)


def main(puzzle_date: datetime.date, max_requests: int = 10):
    scraper = PuzzleCommentScraper(puzzle_date, max_requests)

    logger.info(f"Initialized scraper for URL {scraper.params["url"]}")

    try:
        scraper.get_all_parent_comments()
    except requests.HTTPError as e:
        logger.error(f"Got HTTPError {e.response} while reading parent comments, touching output file and exiting...")
        scraper.output_file.touch()
        raise e
    try:
        scraper.pop_and_get_all_replies()
    except requests.HTTPError as e:
        logger.error(f"Got HTTPError {e.response} while reading replies, touching output file and exiting...")
        scraper.output_file.touch()
        raise e
    scraper.write_to_json()


def valid_date(s: str) -> datetime.datetime:
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a valid date: {s!r}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        "-d",
        "--date",
        help="The Puzzle Date - format YYYY-MM-DD",
        required=True,
        type=valid_date,
    )
    parser.add_argument(
        "-m",
        "--max-requests",
        help="Maximum number of requests to allow for fetching parent comments",
        required=False,
        default=10,
        type=int,
    )
    args = parser.parse_args()
    puzzle_date: datetime.date = args.date.date()
    main(puzzle_date, args.max_requests)
