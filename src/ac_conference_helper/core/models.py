"""Data models for conference submission data."""

from typing import Optional, List
from pydantic import BaseModel, Field
import re

import numpy as np
import pandas as pd

# Import logging configuration
from ac_conference_helper.utils.logging_config import get_logger

# Configure structured logging
logger = get_logger(__name__)


def int_list_to_str(ints: list[int]) -> str:
    """Convert list of integers to string representation."""
    output = ", ".join([str(item) for item in ints])
    if not output:
        output = "-"
    return output


class Review(BaseModel):
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

    def _extract_numeric_rating(
        self, recommendation_text: Optional[str]
    ) -> Optional[int]:
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

        match = re.search(r"(\d+)", self.confidence_level)
        return int(match.group(1)) if match else None

    def model_dump(self) -> dict:
        """Return model as dict with computed properties."""
        return {
            "reviewer_id": self.reviewer_id,
            "submission_date": self.submission_date,
            "modified_date": self.modified_date,
            "paper_summary": self.paper_summary,
            "preliminary_recommendation": self.preliminary_recommendation,
            "justification_for_recommendation": self.justification_for_recommendation,
            "confidence_level": self.confidence_level,
            "paper_strengths": self.paper_strengths,
            "major_weaknesses": self.major_weaknesses,
            "minor_weaknesses": self.minor_weaknesses,
            "final_recommendation": self.final_recommendation,
            "final_justification": self.final_justification,
            "raw_content": self.raw_content,
            "numeric_rating_final_reccomendation": self.numeric_rating_final_reccomendation,
            "numeric_rating_preliminary_recommendation": self.numeric_rating_preliminary_recommendation,
            "numeric_confidence": self.numeric_confidence,
        }

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



class MetaReview(BaseModel):
    """Class containing meta-review information."""

    content: Optional[str] = None
    preliminary_decision: Optional[str] = None
    final_decision: Optional[str] = None
    raw_content: Optional[str] = None  # Store original HTML content for parsing

    def _extract_decision(self, content_text: str, search_key: str) -> Optional[str]:
        """Extract decision from meta-review content."""
        if not content_text:
            return None

        # Find the section after the search key
        pattern = rf"{re.escape(search_key)}\s*(.*?)(?=\n|$)"
        match = re.search(pattern, content_text, re.DOTALL | re.IGNORECASE)

        if not match:
            return None

        decision_text = match.group(1).strip()
        if not decision_text:
            return None

        decision_lower = decision_text.lower()

        # Common decision patterns
        if any(phrase in decision_lower for phrase in ["clear accept"]):
            return "Clear Accept"
        elif any(phrase in decision_lower for phrase in ["clear reject"]):
            return "Clear Reject"
        elif any(phrase in decision_lower for phrase in ["needs discussion", "borderline", "discuss"]):
            return "Needs Discussion"
        elif "accept" in decision_lower:
            return "Accept"
        elif "reject" in decision_lower:
            return "Reject"

        return decision_text

    def model_post_init(self, __context):
        """Extract decisions from content after initialization."""
        try:
            self.preliminary_decision = self._extract_decision(self.content, "Preliminary Recommendation:")
            self.final_decision = self._extract_decision(self.content, "Final Recommendation:")  # Often same for meta-reviews
        except Exception as e:
            # If decision extraction fails, set to None to prevent crashes
            self.preliminary_decision = None
            self.final_decision = None
            logger.warning(f"Error extracting decisions from meta-review: {e}")

    def __str__(self) -> str:
        """String representation of meta-review."""
        output = f"Meta Review:\n"
        if self.preliminary_decision:
            output += f"Preliminary Decision: {self.preliminary_decision}\n"
        if self.final_decision:
            output += f"Final Decision: {self.final_decision}\n"
        if self.content:
            content_preview = self.content[:200] + "..." if len(self.content) > 200 else self.content
            output += f"Content: {content_preview}\n"
        return output


class Submission(BaseModel):
    """Class containing submission details."""

    title: str
    sub_id: str
    url: str
    reviews: List[Review] = Field(default_factory=list)  # Detailed reviews
    meta_review: Optional[MetaReview] = None  # Meta-review information
    pdf_url: Optional[str] = None  # Store PDF URL
    rebuttal_url: Optional[str] = None  # Store rebuttal URL
    withdrawn: bool = False  # Withdrawal status

    model_config = {
        "arbitrary_types_allowed": True  # Allow numpy arrays in computed properties
    }

    @property
    def final_ratings(self) -> list[int]:
        """Extract all final ratings from reviews."""
        final_ratings = []
        for review in self.reviews:
            final_rating = review.numeric_rating_final_reccomendation
            if final_rating is not None:
                final_ratings.append(final_rating)
        return final_ratings

    @property
    def ratings(self) -> list[int]:
        """Extract all ratings from reviews."""
        ratings = []
        for review in self.reviews:
            rating = review.numeric_rating_preliminary_recommendation
            if rating is not None:
                ratings.append(rating)
        return ratings

    @property
    def confidences(self) -> list[int]:
        """Extract all confidences from reviews."""
        confidences = []
        for review in self.reviews:
            confidence = review.numeric_confidence
            if confidence is not None:
                confidences.append(confidence)
        return confidences

    @property
    def final_ratings(self) -> list[int]:
        """Extract all final ratings from reviews."""
        final_ratings = []
        for review in self.reviews:
            final_rating = review.numeric_rating_final_reccomendation
            if final_rating is not None:
                final_ratings.append(final_rating)
        return final_ratings

    def model_post_init(self, __context):
        """Validate data after initialization."""
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

    def model_dump(self) -> dict:
        """Return model as dict with computed properties."""
        return {
            "title": self.title,
            "sub_id": self.sub_id,
            "url": self.url,
            "ratings": self.ratings,
            "confidences": self.confidences,
            "final_ratings": self.final_ratings,
            "reviews": [review.model_dump() for review in self.reviews],
            "avg_rating": self.avg_rating,
            "std_rating": self.std_rating,
            "avg_final_rating": self.avg_final_rating,
            "std_final_rating": self.std_final_rating,
            "detailed_reviews_count": self.detailed_reviews_count,
            "has_pdf": self.pdf_url is not None,
            "has_rebuttal": self.rebuttal_url is not None,
            "pdf_url": self.pdf_url,
            "rebuttal_url": self.rebuttal_url,
        }

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
