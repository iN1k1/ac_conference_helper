"""Printing and display utilities for conference submission data."""

import argparse
from typing import Optional

import pandas as pd
from tabulate import tabulate

from ac_conference_helper.core.models import Submission
from ac_conference_helper.core.models import int_list_to_str


# ANSI color codes for terminal output
class Colors:
    GREEN = "\033[92m"  # Bright green
    RED = "\033[91m"  # Bright red
    YELLOW = "\033[93m"  # Bright yellow
    BLUE = "\033[94m"  # Bright blue
    MAGENTA = "\033[95m"  # Bright magenta
    CYAN = "\033[96m"  # Bright cyan
    WHITE = "\033[97m"  # Bright white
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    END = "\033[0m"


def submissions_to_dataframe(
    subs: list[Submission], include_urls: bool = False
) -> pd.DataFrame:
    """Convert submissions list to pandas DataFrame with color coding."""
    data = []
    for idx, sub in enumerate(subs):
        # Count valid ratings (excluding -1 values)
        valid_prelim_ratings = [r for r in sub.ratings if r != -1]
        valid_final_ratings = [r for r in sub.final_ratings if r != -1]
        
        # Determine color based on valid ratings - color is green if both have >= 3 valid ratings
        line_color = Colors.GREEN if (len(valid_prelim_ratings) >= 3 and len(valid_final_ratings) >= 3) else Colors.RED

        # Create URL link if available
        url_link = ""
        if include_urls and hasattr(sub, "url"):
            url_link = f"{Colors.BLUE}{sub.url}{Colors.END}"

        # Apply color to all text fields in the row
        data.append(
            {
                "#": f"{line_color}{idx + 1}{Colors.END}",
                "ID": f"{line_color}{sub.sub_id}{Colors.END}",
                "Title": f"{line_color}{sub.title}{Colors.END}",
                "URL": url_link if url_link else f"{line_color}{Colors.END}",
                "Ratings": f"{line_color}{int_list_to_str(sub.ratings)}{Colors.END}",
                "Avg_Rating": f"{line_color}{sub.avg_rating:.2f}{Colors.END}",
                "Std_Rating": f"{line_color}{sub.std_rating:.2f}{Colors.END}",
                "Confidences": f"{line_color}{int_list_to_str(sub.confidences)}{Colors.END}",
                "Final_Ratings": f"{line_color}{int_list_to_str(sub.final_ratings)}{Colors.END}",
                "Avg_Final": f"{line_color}{sub.avg_final_rating:.2f}{Colors.END}",
                "Std_Final": f"{line_color}{sub.std_final_rating:.2f}{Colors.END}",
            }
        )
    return pd.DataFrame(data)


def submissions_to_dataframe_streamlit(
    subs: list[Submission], include_urls: bool = False
) -> pd.DataFrame:
    """Convert submissions list to pandas DataFrame for Streamlit display without ANSI colors."""
    data = []
    for idx, sub in enumerate(subs):
        # Count valid ratings (excluding -1 values)
        valid_prelim_ratings = [r for r in sub.ratings if r != -1]
        valid_final_ratings = [r for r in sub.final_ratings if r != -1]
        
        # Determine status based on valid ratings
        status = "✅ Complete" if (len(valid_prelim_ratings) >= 3 and len(valid_final_ratings) >= 3) else "⚠️ Incomplete"

        # Create URL link if available
        url_link = ""
        if include_urls and hasattr(sub, "url"):
            url_link = sub.url

        # Add data without ANSI colors
        data.append(
            {
                "#": idx + 1,
                "ID": sub.sub_id,
                "Title": sub.title,
                "URL": url_link if url_link else "",
                "Status": status,
                "Ratings": int_list_to_str(sub.ratings),
                "Avg_Rating": f"{sub.avg_rating:.2f}",
                "Std_Rating": f"{sub.std_rating:.2f}",
                "Confidences": int_list_to_str(sub.confidences),
                "Final_Ratings": int_list_to_str(sub.final_ratings),
                "Avg_Final": f"{sub.avg_final_rating:.2f}",
                "Std_Final": f"{sub.std_final_rating:.2f}",
            }
        )
    return pd.DataFrame(data)


def print_table(
    subs: list[Submission], table_format: str = "grid", include_urls: bool = False
) -> None:
    """Pretty print submissions table using tabulate."""
    df = submissions_to_dataframe(subs, include_urls=include_urls)
    print_table_with_format(df, table_format)


def print_table_with_format(df: pd.DataFrame, table_format: str) -> None:
    """Print DataFrame with specified format."""
    colalign = [
        "right",
        "right",
        "left",
        "right",
        "right",
        "right",
        "right",
        "right",
        "right",
        "right",
        "right",
    ]

    table_str = tabulate(
        df, headers="keys", tablefmt=table_format, showindex=False, colalign=colalign
    )

    print(table_str)
    print()


def print_csv(subs: list[Submission], include_urls: bool = False) -> None:
    """Print submissions as CSV using pandas with color indicators."""
    df = submissions_to_dataframe(subs, include_urls=include_urls)

    # Create CSV header
    print("-" * 80)
    print("CSV OUTPUT")
    print("-" * 80)

    # Print CSV format with color indicators
    for _, row in df.iterrows():
        # Extract raw ratings without color codes for CSV
        import re

        prelim_ratings_raw = re.sub(r"\033\[[0-9;]*m", "", row["Ratings"])
        final_ratings_raw = re.sub(r"\033\[[0-9;]*m", "", row["Final_Ratings"])
        url_raw = re.sub(r"\033\[[0-9;]*m", "", row["URL"]) if include_urls else ""

        if include_urls:
            csv_line = f"{row['#']}, {row['ID']}, {row['Title']}, {url_raw}, {prelim_ratings_raw}, {final_ratings_raw}"
        else:
            csv_line = f"{row['#']}, {row['ID']}, {row['Title']}, {prelim_ratings_raw}, {final_ratings_raw}"
        print(csv_line)

    print("-" * 80)


def save_to_csv(subs: list[Submission], filename: str) -> None:
    """Save submissions to CSV file without color codes."""
    # Create clean DataFrame without color codes
    clean_data = []
    for idx, sub in enumerate(subs):
        clean_data.append(
            {
                "#": idx + 1,
                "ID": sub.sub_id,
                "Title": sub.title,
                "URL": getattr(sub, "url", ""),
                "Ratings": int_list_to_str(sub.ratings),
                "Avg_Rating": f"{sub.avg_rating:.2f}",
                "Std_Rating": f"{sub.std_rating:.2f}",
                "Confidences": int_list_to_str(sub.confidences),
                "Final_Ratings": int_list_to_str(sub.final_ratings),
                "Avg_Final": f"{sub.avg_final_rating:.2f}",
                "Std_Final": f"{sub.std_final_rating:.2f}",
            }
        )

    df = pd.DataFrame(clean_data)
    df.to_csv(filename, index=False)
    print(f"Results saved to {filename}")


def parse_display_args() -> argparse.Namespace:
    """Parse command line arguments for display operations."""
    parser = argparse.ArgumentParser(
        description="Display and format conference submission data"
    )
    parser.add_argument(
        "--format",
        choices=["grid", "pipe", "simple", "github"],
        default="grid",
        help="Table format for display",
    )
    parser.add_argument("--output", type=str, help="Save results to CSV file")
    parser.add_argument("--csv-only", action="store_true", help="Only show CSV output")
    parser.add_argument(
        "--urls", action="store_true", help="Include clickable URLs in output"
    )
    return parser.parse_args()


def print_incomplete_ratings_table(
    subs: list[Submission], table_format: str = "grid", include_urls: bool = False
) -> None:
    """Print table showing only submissions with incomplete ratings (< 3 valid ratings or final ratings)."""
    # Filter submissions with incomplete ratings (excluding -1 values)
    incomplete_subs = []
    for sub in subs:
        valid_prelim_ratings = [r for r in sub.ratings if r != -1]
        valid_final_ratings = [r for r in sub.final_ratings if r != -1]
        if len(valid_prelim_ratings) < 3 or len(valid_final_ratings) < 3:
            incomplete_subs.append(sub)
    
    if not incomplete_subs:
        print(f"\n{Colors.GREEN}All submissions have complete ratings (≥ 3 ratings and final ratings){Colors.END}")
        return
    
    print(f"\n{Colors.YELLOW}Submissions with Incomplete Ratings ({len(incomplete_subs)} submissions){Colors.END}")
    print(f"{Colors.YELLOW}Showing submissions with < 3 ratings or < 3 final ratings{Colors.END}\n")
    
    df = submissions_to_dataframe(incomplete_subs, include_urls=include_urls)
    print_table_with_format(df, table_format)


def display_results(
    subs: list[Submission], args: Optional[argparse.Namespace] = None
) -> None:
    """Display submission results with various formatting options."""
    if args is None:
        args = parse_display_args()

    print(f"\nFound {len(subs)} submissions\n")

    # Handle both display module args and run.py args
    csv_only = getattr(args, "csv_only", False)
    table_format = getattr(args, "format", "grid")
    output_file = getattr(args, "output", None)
    include_urls = True  # getattr(args, 'urls', False)

    if not csv_only:
        print_table(subs, table_format, include_urls=include_urls)
        
        # Show incomplete ratings table
        print_incomplete_ratings_table(subs, table_format, include_urls=include_urls)

    print_csv(subs, include_urls=include_urls)

    if output_file:
        save_to_csv(subs, output_file)


if __name__ == "__main__":
    # Demo with sample data
    from ac_conference_helper.core.models import Submission
    import random
    import string

    # Generate sample submissions
    sample_subs = []
    for i in range(3):
        ratings = [random.choice(range(1, 6)) for _ in range(random.randint(0, 3))]
        final_ratings = [
            random.choice(range(1, 6)) for _ in range(random.randint(0, 3))
        ]
        sample_subs.append(
            Submission(
                title=f"Sample Paper {string.ascii_uppercase[i]}",
                sub_id=f"{1000 + i}",
                ratings=ratings,
                confidences=[random.choice(range(1, 5)) for _ in range(len(ratings))],
                final_ratings=final_ratings,
            )
        )

    # Parse command line args and display
    args = parse_display_args()
    display_results(sample_subs, args)
