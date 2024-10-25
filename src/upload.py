import argparse
import datetime
import os

from dotenv import load_dotenv
import duckdb

load_dotenv()


def valid_date(s: str) -> datetime.datetime:
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a valid date: {s!r}")


def main(puzzle_date: datetime.date):
    con = duckdb.connect()
    con.sql(f"""
    CREATE OR REPLACE SECRET (
        TYPE S3, 
        KEY_ID '{os.getenv("AWS_ACCESS_KEY_ID")}', 
        SECRET '{os.getenv("AWS_SECRET_ACCESS_KEY")}', 
        ENDPOINT '{os.getenv("ENDPOINT_URL")}',
        REGION 'auto'
    )
    """)

    con.sql(f"""
    COPY (from 'comments/comments-{puzzle_date:%Y-%m-%d}.json') 
    TO 's3://nyt-comments/comments-{puzzle_date:%Y-%m-%d}.parquet'
    """)


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
