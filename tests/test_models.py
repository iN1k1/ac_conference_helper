"""Unit tests for models.py."""

import pytest
import io
import sys
import os
from contextlib import redirect_stdout

# Add parent directory to path to import modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from ac_conference_helper.core.models import Review, Submission, int_list_to_str

class TestReview:
    """Test the Review class."""

    def test_review_creation_empty(self):
        """Test creating empty review."""
        review = Review()
        assert review.reviewer_id is None
        assert review.submission_date is None
        assert review.final_recommendation is None

    def test_review_creation_with_data(self):
        """Test creating review with data."""
        data = {
            "reviewer_id": "reviewer1",
            "final_recommendation": "6: Accept",
            "confidence_level": "4: High",
            "paper_summary": "Good paper about ML"
        }
        review = Review(**data)
        assert review.reviewer_id == "reviewer1"
        assert review.final_recommendation == "6: Accept"
        assert review.confidence_level == "4: High"
        assert review.paper_summary == "Good paper about ML"

    def test_extract_numeric_rating_valid(self):
        """Test extracting numeric rating from valid recommendation."""
        review = Review()
        
        # Test various rating formats
        test_cases = [
            ("1: Reject", 1),
            ("2: Weak Reject", 2),
            ("3: Borderline Reject", 3),
            ("4: Borderline Accept", 4),
            ("5: Weak Accept", 5),
            ("6: Accept", 6),
            ("Reject", 1),
            ("Accept", 6),
        ]
        
        for text, expected in test_cases:
            assert review._extract_numeric_rating(text) == expected

    def test_extract_numeric_rating_invalid(self):
        """Test extracting numeric rating from invalid recommendation."""
        review = Review()
        
        # Test invalid cases
        assert review._extract_numeric_rating(None) == -1
        assert review._extract_numeric_rating("") == -1
        assert review._extract_numeric_rating("Invalid rating") is None

    def test_numeric_rating_properties(self):
        """Test numeric rating properties."""
        review = Review(
            preliminary_recommendation="5: Weak Accept",
            final_recommendation="6: Accept"
        )
        
        assert review.numeric_rating_preliminary_recommendation == 5
        assert review.numeric_rating_final_reccomendation == 6

    def test_numeric_confidence_valid(self):
        """Test extracting numeric confidence."""
        review = Review(confidence_level="4: High")
        assert review.numeric_confidence == 4

    def test_numeric_confidence_invalid(self):
        """Test extracting numeric confidence from invalid input."""
        review = Review()
        assert review.numeric_confidence is None
        
        review.confidence_level = "Invalid"
        assert review.numeric_confidence is None

    def test_model_dump(self):
        """Test model_dump method includes computed properties."""
        review = Review(
            reviewer_id="reviewer1",
            final_recommendation="6: Accept",
            confidence_level="4: High"
        )
        
        dump = review.model_dump()
        
        assert dump["reviewer_id"] == "reviewer1"
        assert dump["final_recommendation"] == "6: Accept"
        assert dump["numeric_rating_final_reccomendation"] == 6
        assert dump["numeric_confidence"] == 4

    def test_str_representation(self):
        """Test string representation calls pretty_print."""
        review = Review(reviewer_id="reviewer1")
        
        # Capture output
        f = io.StringIO()
        with redirect_stdout(f):
            output = str(review)
        
        # Should contain pretty print output
        assert "REVIEW BY: reviewer1" in output

    def test_pretty_print_with_data(self):
        """Test pretty_print with review data."""
        review = Review(
            reviewer_id="reviewer1",
            paper_summary="A good paper",
            preliminary_recommendation="5: Weak Accept",
            confidence_level="4: High"
        )
        
        # Capture output
        f = io.StringIO()
        with redirect_stdout(f):
            review.pretty_print()
        
        output = f.getvalue()
        assert "REVIEW BY: reviewer1" in output
        assert "Paper Summary" in output
        assert "A good paper" in output

    def test_pretty_print_empty(self):
        """Test pretty_print with empty review."""
        review = Review()
        
        # Capture output
        f = io.StringIO()
        with redirect_stdout(f):
            review.pretty_print()
        
        output = f.getvalue()
        assert "No review data available" in output


class TestSubmission:
    """Test the Submission class."""

    def test_submission_creation_minimal(self):
        """Test creating submission with minimal data."""
        sub = Submission(title="Test Paper", sub_id="123", url="http://example.com")
        assert sub.title == "Test Paper"
        assert sub.sub_id == "123"
        assert sub.url == "http://example.com"
        assert sub.reviews == []

    def test_submission_with_reviews(self):
        """Test creating submission with reviews."""
        review1 = Review(final_recommendation="6: Accept", confidence_level="4: High")
        review2 = Review(final_recommendation="3: Borderline Reject", confidence_level="2: Low")
        
        sub = Submission(
            title="Test Paper",
            sub_id="123", 
            url="http://example.com",
            reviews=[review1, review2]
        )
        
        assert len(sub.reviews) == 2
        assert sub.final_ratings == [6, 3]

    def test_ratings_property(self):
        """Test ratings property extraction."""
        review1 = Review(preliminary_recommendation="5: Weak Accept", confidence_level="4: High")
        review2 = Review(preliminary_recommendation="6: Accept", confidence_level="3: Medium")
        review3 = Review(preliminary_recommendation="4: Borderline Accept", confidence_level="2: Low")  # Add recommendation
        
        sub = Submission(
            title="Test",
            sub_id="123",
            url="http://example.com",
            reviews=[review1, review2, review3]
        )
        
        assert sub.ratings == [5, 6, 4]

    def test_confidences_property(self):
        """Test confidences property extraction."""
        review1 = Review(preliminary_recommendation="5: Weak Accept", confidence_level="4: High")
        review2 = Review(preliminary_recommendation="6: Accept", confidence_level="2: Low")
        review3 = Review(preliminary_recommendation="4: Borderline Accept", confidence_level="3: Medium")  # Add confidence
        
        sub = Submission(
            title="Test",
            sub_id="123",
            url="http://example.com",
            reviews=[review1, review2, review3]
        )
        
        assert sub.confidences == [4, 2, 3]

    def test_duplicate_final_ratings_property(self):
        """Test that duplicate final_ratings property works (line 263-270)."""
        review1 = Review(final_recommendation="6: Accept", confidence_level="4: High")
        review2 = Review(final_recommendation="3: Borderline Reject", confidence_level="3: Medium")
        
        sub = Submission(
            title="Test",
            sub_id="123",
            url="http://example.com",
            reviews=[review1, review2]
        )
        
        # Both properties should return the same result
        assert sub.final_ratings == [6, 3]
        # Access the second definition
        assert sub.final_ratings == [6, 3]

    def test_validation_mismatched_lengths(self):
        """Test validation fails when ratings and confidences lengths don't match."""
        review1 = Review(
            preliminary_recommendation="5: Weak Accept",
            confidence_level="4: High"
        )
        review2 = Review(preliminary_recommendation="6: Accept")  # No confidence
        
        with pytest.raises(ValueError, match="Ratings and confidences must have same length"):
            Submission(
                title="Test",
                sub_id="123",
                url="http://example.com",
                reviews=[review1, review2]
            )

    def test_validation_matched_lengths(self):
        """Test validation passes when ratings and confidences lengths match."""
        review1 = Review(
            preliminary_recommendation="5: Weak Accept",
            confidence_level="4: High"
        )
        review2 = Review(
            preliminary_recommendation="6: Accept",
            confidence_level="3: Medium"
        )
        
        # Should not raise exception
        sub = Submission(
            title="Test",
            sub_id="123",
            url="http://example.com",
            reviews=[review1, review2]
        )
        assert sub.ratings == [5, 6]
        assert sub.confidences == [4, 3]

    def test_avg_rating(self):
        """Test average rating calculation."""
        review1 = Review(preliminary_recommendation="4: Borderline Accept", confidence_level="3: Medium")
        review2 = Review(preliminary_recommendation="6: Accept", confidence_level="4: High")
        
        sub = Submission(
            title="Test",
            sub_id="123",
            url="http://example.com",
            reviews=[review1, review2]
        )
        
        assert sub.avg_rating == 5.0

    def test_avg_rating_empty(self):
        """Test average rating with no ratings."""
        sub = Submission(title="Test", sub_id="123", url="http://example.com")
        assert sub.avg_rating == 0.0

    def test_std_rating(self):
        """Test standard deviation calculation."""
        review1 = Review(preliminary_recommendation="4: Borderline Accept", confidence_level="3: Medium")
        review2 = Review(preliminary_recommendation="6: Accept", confidence_level="4: High")
        
        sub = Submission(
            title="Test",
            sub_id="123",
            url="http://example.com",
            reviews=[review1, review2]
        )
        
        assert abs(sub.std_rating - 1.0) < 0.001

    def test_std_rating_empty(self):
        """Test standard deviation with no ratings."""
        sub = Submission(title="Test", sub_id="123", url="http://example.com")
        assert sub.std_rating == 0.0

    def test_avg_final_rating(self):
        """Test average final rating calculation."""
        review1 = Review(final_recommendation="4: Borderline Accept", confidence_level="3: Medium")
        review2 = Review(final_recommendation="6: Accept", confidence_level="4: High")
        
        sub = Submission(
            title="Test",
            sub_id="123",
            url="http://example.com",
            reviews=[review1, review2]
        )
        
        assert sub.avg_final_rating == 5.0

    def test_detailed_reviews_count(self):
        """Test detailed reviews count."""
        review1 = Review(final_recommendation="6: Accept", confidence_level="4: High")
        review2 = Review(confidence_level="3: Medium")  # No final recommendation
        review3 = Review(final_recommendation="3: Borderline Reject", confidence_level="2: Low")
        
        sub = Submission(
            title="Test",
            sub_id="123",
            url="http://example.com",
            reviews=[review1, review2, review3]
        )
        
        assert sub.detailed_reviews_count == 2

    def test_review_without_final_recommendation(self):
        """Test review without final recommendation."""
        review = Review(
            preliminary_recommendation="5: Weak Accept",
            confidence_level="4: High"
            # No final_recommendation
        )
        
        # Should not raise any exceptions
        assert review.final_recommendation is None
        assert review.numeric_rating_final_reccomendation == -1  # Returns -1 for None
        
        # Test in submission context
        sub = Submission(
            title="Test Paper",
            sub_id="123",
            url="http://example.com",
            reviews=[review]
        )
        
        # Should handle missing final recommendation gracefully
        assert sub.final_ratings == [-1]  # -1 values are included (not filtered out)
        assert sub.avg_final_rating == -1.0  # Mean of [-1] is -1
        assert sub.std_final_rating == 0.0
        assert sub.detailed_reviews_count == 0  # Only counts reviews with actual final recommendations

    def test_model_dump(self):
        """Test model_dump includes computed properties."""
        review = Review(
            preliminary_recommendation="5: Weak Accept", 
            final_recommendation="6: Accept", 
            confidence_level="4: High"
        )
        sub = Submission(
            title="Test Paper",
            sub_id="123",
            url="http://example.com",
            reviews=[review],
            pdf_url="http://example.com/pdf",
            rebuttal_url="http://example.com/rebuttal"
        )
        
        dump = sub.model_dump()
        
        assert dump["title"] == "Test Paper"
        assert dump["avg_rating"] == 5.0  # Has preliminary recommendation
        assert dump["has_pdf"] is True
        assert dump["has_rebuttal"] is True
        assert dump["pdf_url"] == "http://example.com/pdf"

    def test_str_representation(self):
        """Test string representation calls pretty_print."""
        sub = Submission(title="Test", sub_id="123", url="http://example.com")
        
        # Capture output
        f = io.StringIO()
        with redirect_stdout(f):
            output = str(sub)
        
        # Should contain pretty print output
        assert "SUBMISSION: Test" in output

    def test_info_method(self):
        """Test info method."""
        review = Review(preliminary_recommendation="5: Weak Accept", confidence_level="4: High")
        sub = Submission(
            title="Test Paper",
            sub_id="123",
            url="http://example.com",
            reviews=[review]
        )
        
        info = sub.info()
        assert "ID: 123" in info
        assert "Test Paper" in info
        assert "Ratings: [5]" in info
        assert "Avg: 5.00" in info

    def test_pretty_print(self):
        """Test pretty_print method."""
        review = Review(
            preliminary_recommendation="5: Weak Accept",
            final_recommendation="6: Accept", 
            confidence_level="4: High"
        )
        sub = Submission(
            title="Test Paper",
            sub_id="123",
            url="http://example.com",
            reviews=[review]
        )
        
        # Capture output
        f = io.StringIO()
        with redirect_stdout(f):
            sub.pretty_print()
        
        output = f.getvalue()
        assert "SUBMISSION: Test Paper" in output
        assert "ID: 123" in output
        assert "Average Rating 5.00" in output  # Note: no colon, space after "Rating"
        assert "Average Final Rating 6.00" in output

    def test_urls_optional(self):
        """Test optional URL fields."""
        sub = Submission(
            title="Test",
            sub_id="123",
            url="http://example.com"
        )
        
        assert sub.pdf_url is None
        assert sub.rebuttal_url is None
        
        dump = sub.model_dump()
        assert dump["has_pdf"] is False
        assert dump["has_rebuttal"] is False


if __name__ == "__main__":
    pytest.main([__file__])
