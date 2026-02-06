"""Data models for conference submission data."""

from dataclasses import dataclass
from typing import Optional, List

import numpy as np
import pandas as pd

from utils import int_list_to_str


@dataclass
class Review:
    """Class containing detailed review information."""

    reviewer_id: Optional[str] = None
    submission_date: Optional[str] = None
    modified_date: Optional[str] = None
    paper_summary: Optional[str] = None
    preliminary_recommendation: Optional[str] = None
    justification_for_recommendation: Optional[str] = None
    confidence_level: Optional[str] = None
    paper_strengths: Optional[str] = None
    major_weaknesses: Optional[str] = None
    minor_weaknesses: Optional[str] = None
    final_recommendation: Optional[str] = None
    final_justification: Optional[str] = None
    raw_content: Optional[str] = None  # Store original HTML content for parsing

    def _extract_numeric_rating(self, recommendation_text: Optional[str]) -> Optional[int]:
        """Helper method to extract numeric rating from recommendation text."""
        if not recommendation_text:
            return -1

        # Map common rating strings to numbers
        rating_map = {
            "1: Reject": 1,
            "2: Weak Reject": 2,
            "3: Borderline Reject": 3,
            "4: Borderline Accept": 4,
            "5: Weak Accept": 5,
            "6: Accept": 6,
            "Reject": 1,
            "Weak Reject": 2,
            "Borderline Reject": 3,
            "Borderline Accept": 4,
            "Weak Accept": 5,
            "Accept": 6,
        }

        for rating_str, numeric in rating_map.items():
            if rating_str in recommendation_text:
                return numeric

        return None

    @property
    def numeric_rating_final_reccomendation(self) -> Optional[int]:
        """Extract numeric rating from final recommendation."""
        return self._extract_numeric_rating(self.final_recommendation)

    @property
    def numeric_rating_preliminary_recommendation(self) -> Optional[int]:
        """Extract numeric rating from preliminary recommendation."""
        return self._extract_numeric_rating(self.preliminary_recommendation)

    @property
    def numeric_confidence(self) -> Optional[int]:
        """Extract numeric confidence from confidence level."""
        if not self.confidence_level:
            return None

        # Extract number from confidence string
        import re

        match = re.search(r"(\d+)", self.confidence_level)
        return int(match.group(1)) if match else None

    def __str__(self) -> str:
        """String representation uses pretty print by default."""
        # Capture pretty print output
        import io
        import sys
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            self.pretty_print()

        return f.getvalue()

    def pretty_print(self) -> None:
        """Print review details as a formatted table."""
        print(f"\n{'='*60}")
        print(f"REVIEW BY: {self.reviewer_id or 'Unknown'}")
        print(f"{'='*60}")

        # Create table data
        data = []
        if self.paper_summary:
            data.append(
                [
                    "Paper Summary",
                    (
                        self.paper_summary[:80] + "..."
                        if len(self.paper_summary) > 80
                        else self.paper_summary
                    ),
                ]
            )
        if self.preliminary_recommendation:
            data.append(["Preliminary Recommendation", self.preliminary_recommendation])
        if self.justification_for_recommendation:
            data.append(
                [
                    "Justification for Recommendation",
                    (
                        self.justification_for_recommendation[:80] + "..."
                        if len(self.justification_for_recommendation) > 80
                        else self.justification_for_recommendation
                    ),
                ]
            )
        if self.confidence_level:
            data.append(["Confidence Level", self.confidence_level])
        if self.paper_strengths:
            data.append(
                [
                    "Paper Strengths",
                    (
                        self.paper_strengths[:80] + "..."
                        if len(self.paper_strengths) > 80
                        else self.paper_strengths
                    ),
                ]
            )
        if self.major_weaknesses:
            data.append(
                [
                    "Major Weaknesses",
                    (
                        self.major_weaknesses[:80] + "..."
                        if len(self.major_weaknesses) > 80
                        else self.major_weaknesses
                    ),
                ]
            )
        if self.minor_weaknesses:
            data.append(
                [
                    "Minor Weaknesses",
                    (
                        self.minor_weaknesses[:80] + "..."
                        if len(self.minor_weaknesses) > 80
                        else self.minor_weaknesses
                    ),
                ]
            )
        if self.final_recommendation:
            data.append(["Final Recommendation", self.final_recommendation])
        if self.final_justification:
            data.append(
                [
                    "Final Justification",
                    (
                        self.final_justification[:80] + "..."
                        if len(self.final_justification) > 80
                        else self.final_justification
                    ),
                ]
            )

        if data:
            df = pd.DataFrame(data, columns=["Field", "Content"])
            pd.set_option("display.max_colwidth", None)
            pd.set_option("display.colheader_justify", "left")
            print(df.to_string(index=False))
        else:
            print("No review data available")

        print(f"{'='*60}\n")


@dataclass
class Submission:
    """Class containing submission details."""

    title: str
    sub_id: str
    url: str
    ratings: list[int]
    confidences: list[int]
    final_ratings: list[int]
    reviews: List[Review] = None  # New field for detailed reviews

    def __post_init__(self):
        """Validate data after initialization."""
        if self.reviews is None:
            self.reviews = []

        if len(self.ratings) != len(self.confidences):
            raise ValueError("Ratings and confidences must have same length")

    @property
    def avg_rating(self) -> float:
        """Calculate average rating."""
        return np.mean(self.ratings) if self.ratings else 0.0

    @property
    def std_rating(self) -> float:
        """Calculate standard deviation of ratings."""
        return np.std(self.ratings) if self.ratings else 0.0

    @property
    def avg_final_rating(self) -> float:
        """Calculate average final rating."""
        return np.mean(self.final_ratings) if self.final_ratings else 0.0

    @property
    def std_final_rating(self) -> float:
        """Calculate standard deviation of final ratings."""
        return np.std(self.final_ratings) if self.final_ratings else 0.0

    @property
    def detailed_reviews_count(self) -> int:
        """Get count of detailed reviews."""
        return len([r for r in self.reviews if r.final_recommendation])

    def __str__(self) -> str:
        """String representation uses pretty print by default."""
        # Capture pretty print output
        import io
        import sys
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            self.pretty_print()

        return f.getvalue()

    def info(self) -> str:
        return (
            f"ID: {self.sub_id}, {self.title}, "
            + f"Ratings: {self.ratings}, "
            + f"Avg: {self.avg_rating:.2f}, "
            + f"Var: {np.var(self.ratings):.2f}"
        )

    def pretty_print(self) -> None:
        """Print submission details including reviews as formatted tables."""
        print(f"\n{'='*80}")
        print(f"SUBMISSION: {self.title}")
        print(f"ID: {self.sub_id}")
        print(f"{'='*80}")

        # Basic submission info
        basic_data = [
            ["Ratings", int_list_to_str(self.ratings)],
            ["Average Rating", f"{self.avg_rating:.2f}"],
            ["Rating Std Dev", f"{self.std_rating:.2f}"],
            ["Final Ratings", int_list_to_str(self.final_ratings)],
            ["Average Final Rating", f"{self.avg_final_rating:.2f}"],
            ["Final Rating Std Dev", f"{self.std_final_rating:.2f}"],
            ["Number of Reviews", str(len(self.reviews))],
            ["Detailed Reviews", str(self.detailed_reviews_count)],
        ]

        basic_df = pd.DataFrame(basic_data, columns=["Metric", "Value"])
        pd.set_option("display.colheader_justify", "left")
        print("\nSUBMISSION SUMMARY:")
        print(basic_df.to_string(index=False))

        # Detailed reviews
        if self.reviews:
            print(f"\n{'='*80}")
            print("DETAILED REVIEWS:")
            print(f"{'='*80}")

            for i, review in enumerate(self.reviews, 1):
                if review.final_recommendation:  # Only show reviews with actual content
                    print(f"\n--- REVIEW {i} ---")
                    review.pretty_print()

        print(f"\n{'='*80}\n")
