"""Printing and display utilities for conference submission data."""

import argparse
import os
from typing import Optional

import pandas as pd
from tabulate import tabulate

from ac_conference_helper.core.models import Submission, MetaReview, SubmissionStatus
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


def format_meta_review_decision(decision: Optional[str]) -> str:
    """Format meta-review decision with appropriate colors."""
    if not decision:
        return f"{Colors.YELLOW}N/A{Colors.END}"
    
    decision_lower = decision.lower()
    if "accept" in decision_lower:
        if "clear" in decision_lower or "strong" in decision_lower:
            return f"{Colors.GREEN}{decision}{Colors.END}"
        else:
            return f"{Colors.CYAN}{decision}{Colors.END}"
    elif "reject" in decision_lower:
        if "clear" in decision_lower or "strong" in decision_lower:
            return f"{Colors.RED}{decision}{Colors.END}"
        else:
            return f"{Colors.MAGENTA}{decision}{Colors.END}"
    elif "discussion" in decision_lower:
        return f"{Colors.YELLOW}{decision}{Colors.END}"
    else:
        return decision


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

        # Get meta-review decisions
        meta_prelim_decision = ""
        meta_final_decision = ""
        if hasattr(sub, "meta_review") and sub.meta_review:
            meta_prelim_decision = format_meta_review_decision(sub.meta_review.preliminary_decision)
            meta_final_decision = format_meta_review_decision(sub.meta_review.final_decision)

        # Format withdrawal and desk rejection status
        if sub.status == SubmissionStatus.WITHDRAWN:
            withdrawal_status = f"{line_color}🚫 WITHDRAWN{Colors.END}"
        elif sub.status == SubmissionStatus.DESK_REJECTED:
            withdrawal_status = f"{line_color}📋 DESK REJECTED{Colors.END}"
        else:
            withdrawal_status = f"{line_color}✅ Active{Colors.END}"
        
        # Determine reviews status based on valid ratings
        reviews_status = f"{line_color}✅ Complete{Colors.END}" if (len(valid_prelim_ratings) >= 3 and len(valid_final_ratings) >= 3) else f"{line_color}⚠️ Incomplete{Colors.END}"

        # Apply color to all text fields in the row
        data.append(
            {
                "#": f"{line_color}{idx + 1}{Colors.END}",
                "ID": f"{line_color}{sub.sub_id}{Colors.END}",
                "Title": f"{line_color}{sub.title}{Colors.END}",
                "URL": url_link if url_link else f"{line_color}{Colors.END}",
                "Status": withdrawal_status,
                "reviews_status": reviews_status,
                "Meta_Prelim": meta_prelim_decision,
                "Meta_Final": meta_final_decision,
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
        reviews_status = "✅ Complete" if (len(valid_prelim_ratings) >= 3 and len(valid_final_ratings) >= 3) else "⚠️ Incomplete"

        # Create URL link if available
        url_link = ""
        if include_urls and hasattr(sub, "url"):
            url_link = sub.url

        # Get meta-review decisions
        meta_prelim_decision = ""
        meta_final_decision = ""
        if hasattr(sub, "meta_review") and sub.meta_review:
            meta_prelim_decision = sub.meta_review.preliminary_decision or "N/A"
            meta_final_decision = sub.meta_review.final_decision or "N/A"

        # Format withdrawal and desk rejection status
        if sub.status == SubmissionStatus.WITHDRAWN:
            status = "🚫 WITHDRAWN"
        elif sub.status == SubmissionStatus.DESK_REJECTED:
            status = "📋 DESK REJECTED"
        else:
            status = "✅ Active"

        # Add data without ANSI colors
        data.append(
            {
                "#": idx + 1,
                "ID": sub.sub_id,
                "Title": sub.title,
                # "URL": url_link if url_link else "",
                "status": status,
                "reviews_status": reviews_status,
                "Meta_Prelim": meta_prelim_decision,
                "Meta_Final": meta_final_decision,
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
        "left",
        "left",
        "left",
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
        # Get meta-review decisions
        meta_prelim_decision = ""
        meta_final_decision = ""
        if hasattr(sub, "meta_review") and sub.meta_review:
            meta_prelim_decision = sub.meta_review.preliminary_decision or "N/A"
            meta_final_decision = sub.meta_review.final_decision or "N/A"
            
        clean_data.append(
            {
                "#": idx + 1,
                "ID": sub.sub_id,
                "Title": sub.title,
                "URL": getattr(sub, "url", ""),
                "status": sub.status.value.upper(),
                "Meta_Prelim": meta_prelim_decision,
                "Meta_Final": meta_final_decision,
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
    parser.add_argument(
        "--save-reviews", type=str, metavar="DIR", default=None,
        help="Save anonymized reviews to separate txt files in specified directory"
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


def save_anonymized_reviews(subs: list[Submission], output_dir: str = "reviews") -> None:
    """Save anonymized reviews for each submission to separate txt files."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    for sub in subs:
        if not sub.reviews:
            continue
            
        # Create filename from submission ID and title (sanitized)
        safe_title = "".join(c for c in sub.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_title = safe_title[:50]  # Limit length
        filename = f"{sub.sub_id}_{safe_title}.txt"
        filepath = os.path.join(output_dir, filename)
        
        # Write anonymized reviews to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"Submission ID: {sub.sub_id}\n")
            f.write(f"Title: {sub.title}\n")
            f.write(f"URL: {getattr(sub, 'url', 'N/A')}\n")
            
            # Add meta-review if available
            if hasattr(sub, 'meta_review') and sub.meta_review:
                f.write(f"\n{'='*80}\n")
                f.write("META REVIEW\n")
                f.write(f"{'='*80}\n")
                if sub.meta_review.preliminary_decision:
                    f.write(f"Preliminary Decision: {sub.meta_review.preliminary_decision}\n")
                if sub.meta_review.final_decision:
                    f.write(f"Final Decision: {sub.meta_review.final_decision}\n")
                if sub.meta_review.content:
                    f.write(f"Content:\n{sub.meta_review.content}\n")
                f.write(f"\n{'='*80}\n")
            
            f.write(f"\n{'='*80}\n")
            f.write("REGULAR REVIEWS\n")
            f.write(f"{'='*80}\n\n")
            
            for i, review in enumerate(sub.reviews, 1):
                # Extract reviewer ID from format "id (reviewer_name)" and keep only the ID
                reviewer_id = review.reviewer_id or f"Reviewer_{i}"
                if ' (' in reviewer_id:
                    reviewer_id = reviewer_id.split(' (')[0]
                
                f.write(f"REVIEWER {reviewer_id}\n")
                f.write("-" * 40 + "\n")
                
                if review.paper_summary:
                    f.write(f"Paper Summary:\n{review.paper_summary}\n\n")
                
                if review.preliminary_recommendation:
                    f.write(f"Preliminary Recommendation: {review.preliminary_recommendation}\n")
                
                if review.justification_for_recommendation:
                    f.write(f"Justification: {review.justification_for_recommendation}\n")
                
                if review.confidence_level:
                    f.write(f"Confidence Level: {review.confidence_level}\n")
                
                if review.paper_strengths:
                    f.write(f"Strengths: {review.paper_strengths}\n")
                
                if review.major_weaknesses:
                    f.write(f"Major Weaknesses: {review.major_weaknesses}\n")
                
                if review.minor_weaknesses:
                    f.write(f"Minor Weaknesses: {review.minor_weaknesses}\n")
                
                if review.final_recommendation:
                    f.write(f"Final Recommendation: {review.final_recommendation}\n")
                
                if review.final_justification:
                    f.write(f"Final Justification: {review.final_justification}\n")
                
                f.write("\n" + "=" * 80 + "\n\n")
        
        print(f"Saved anonymized reviews for {sub.sub_id} to {filepath}")


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
    save_reviews_dir = getattr(args, "save_reviews", None)
    include_urls = True  # getattr(args, 'urls', False)

    if not csv_only:
        print_table(subs, table_format, include_urls=include_urls)
        
        # Show incomplete ratings table
        print_incomplete_ratings_table(subs, table_format, include_urls=include_urls)

    print_csv(subs, include_urls=include_urls)

    if output_file:
        save_to_csv(subs, output_file)
    
    # Save anonymized reviews if requested
    if save_reviews_dir:
        save_anonymized_reviews(subs, save_reviews_dir)


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
