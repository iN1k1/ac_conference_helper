"""Unit tests for ac_conference_helper.client.py."""

import pytest
from unittest.mock import patch, MagicMock, Mock
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
import sys
import os

# Add parent directory to path to import modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from ac_conference_helper.client.openreview_client import OpenReviewClient
from ac_conference_helper.core.models import Review, Submission


class TestOpenReviewClient:
    """Test the OpenReviewClient class."""

    @patch('ac_conference_helper.client.openreview_client.webdriver.Chrome')
    @patch('ac_conference_helper.client.openreview_client.get_conference_config')
    @patch('ac_conference_helper.client.openreview_client.load_dotenv')
    def test_client_initialization(self, mock_load_dotenv, mock_config, mock_chrome):
        """Test client initialization."""
        # Mock conference config
        mock_conf = MagicMock()
        mock_conf.name = "test_conference"
        mock_conf.display_name = "Test Conference"
        mock_conf.area_chair_url = "http://example.com/login"
        mock_config.return_value = mock_conf
        
        # Mock driver
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Mock login method
        with patch.object(OpenReviewClient, '_login'):
            client = OpenReviewClient("test_conference", headless=True)
        
        assert client.conference_config == mock_conf
        assert client.driver == mock_driver
        mock_chrome.assert_called_once()

    @patch('ac_conference_helper.client.openreview_client.webdriver.Chrome')
    @patch('ac_conference_helper.client.openreview_client.get_conference_config')
    @patch('ac_conference_helper.client.openreview_client.load_dotenv')
    def test_client_destructor(self, mock_load_dotenv, mock_config, mock_chrome):
        """Test client destructor calls driver.quit()."""
        # Mock conference config
        mock_conf = MagicMock()
        mock_conf.name = "test_conference"
        mock_conf.area_chair_url = "http://example.com/login"
        mock_config.return_value = mock_conf
        
        # Mock driver
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        with patch.object(OpenReviewClient, '_login'):
            client = OpenReviewClient("test_conference")
        
        # Manually call destructor
        client.__del__()
        mock_driver.quit.assert_called_once()

    @patch('ac_conference_helper.client.openreview_client.webdriver.Chrome')
    @patch('ac_conference_helper.client.openreview_client.get_conference_config')
    @patch('ac_conference_helper.client.openreview_client.load_dotenv')
    def test_create_driver_headless(self, mock_load_dotenv, mock_config, mock_chrome):
        """Test _create_driver with headless=True."""
        mock_conf = MagicMock()
        mock_conf.name = "test_conference"
        mock_conf.area_chair_url = "http://example.com/login"
        mock_config.return_value = mock_conf
        
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        with patch.object(OpenReviewClient, '_login'):
            client = OpenReviewClient("test_conference", headless=True)
        
        # Check that headless option was added
        mock_chrome.assert_called_once()
        # The call should be webdriver.Chrome(options=options)
        call_kwargs = mock_chrome.call_args[1] if mock_chrome.call_args else {}
        assert 'options' in call_kwargs

        # Verify options were configured (we can't easily check the exact options without more mocking)


    @patch('os.environ')
    def test_load_credentials_success(self, mock_environ):
        """Test successful credential loading."""
        mock_environ.__getitem__.side_effect = lambda key: {
            'USERNAME': 'test@example.com',
            'PASSWORD': 'testpass'
        }[key]
        
        with patch('ac_conference_helper.client.load_dotenv'):
            client = OpenReviewClient.__new__(OpenReviewClient)  # Create without calling __init__
            username, password = client._load_credentials()
        
        assert username == 'test@example.com'
        assert password == 'testpass'

    @patch('os.environ')
    def test_load_credentials_missing(self, mock_environ):
        """Test credential loading with missing environment variables."""
        mock_environ.__getitem__.side_effect = KeyError("USERNAME")
        
        with patch('ac_conference_helper.client.load_dotenv'):
            client = OpenReviewClient.__new__(OpenReviewClient)
            
            with pytest.raises(ValueError, match="Missing environment variable: 'USERNAME'"):
                client._load_credentials()

    def test_parse_reviews_empty_list(self):
        """Test parsing empty review elements list."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        reviews, meta_review = client._parse_reviews([])
        assert reviews == []
        assert meta_review is None

    def test_parse_reviews_with_elements(self):
        """Test parsing review elements."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        
        # Mock review element
        mock_element = MagicMock()
        mock_element.find_element.side_effect = [
            MagicMock(text="by Reviewer (Anonymous Reviewer #1)"),  # subheading
            MagicMock(text="Paper Summary: Good paper\nFinal Recommendation: 6: Accept"),  # content
        ]
        
        reviews, meta_review = client._parse_reviews([mock_element])
        
        assert len(reviews) == 1
        assert reviews[0].reviewer_id == "(Anonymous Reviewer #1)"
        assert reviews[0].paper_summary == "Good paper"
        assert reviews[0].final_recommendation == "6: Accept"
        assert meta_review is None

    def test_parse_reviews_with_subheading_dates(self):
        """Test parsing review with date information in subheading."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        
        # Mock review element with date info
        mock_element = MagicMock()
        mock_subheading = MagicMock()
        mock_subheading.text = "by Reviewer (Anonymous Reviewer #1) on 15 Dec 2023, 10:30, modified: 16 Dec 2023, 11:45"
        
        mock_element.find_element.side_effect = [
            mock_subheading,  # subheading
            MagicMock(text="Final Recommendation: 5: Weak Accept"),  # content
        ]
        
        reviews, meta_review = client._parse_reviews([mock_element])
        
        assert len(reviews) == 1
        review = reviews[0]
        assert review.reviewer_id == "(Anonymous Reviewer #1)"
        assert review.submission_date == "15 Dec 2023, 10:30"
        assert review.modified_date == "16 Dec 2023, 11:45"

    def test_parse_reviews_fallback_to_signature(self):
        """Test parsing review falls back to signature when subheading doesn't have reviewer info."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        
        # Mock review element
        mock_element = MagicMock()
        mock_subheading = MagicMock()
        mock_subheading.text = "No reviewer info here"
        mock_signature = MagicMock()
        mock_signature.text = "Review Signature"
        
        mock_element.find_element.side_effect = [
            mock_subheading,  # subheading (no reviewer info)
            MagicMock(text="Final Recommendation: 4: Borderline Accept"),  # content
            mock_signature,  # signatures
        ]
        
        reviews, meta_review = client._parse_reviews([mock_element])
        
        assert len(reviews) == 1
        assert reviews[0].reviewer_id == "Review Signature"

    def test_parse_reviews_with_all_fields(self):
        """Test parsing review with all possible fields."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        
        content_text = """
        Paper Summary: This is a great paper about machine learning.
        Preliminary Recommendation: 5: Weak Accept
        Justification For Recommendation: The paper has novel contributions.
        Confidence Level: 4: High
        Paper Strengths: Novel approach, good experiments.
        Major Weaknesses: Limited scalability.
        Minor Weaknesses: Some typos.
        Final Recommendation: 6: Accept
        Final Justification: After rebuttal, concerns were addressed.
        """
        
        mock_element = MagicMock()
        mock_element.find_element.side_effect = [
            MagicMock(text="by Reviewer (Anonymous Reviewer #1)"),
            MagicMock(text=content_text),
        ]
        
        reviews, meta_review = client._parse_reviews([mock_element])
        
        assert len(reviews) == 1
        review = reviews[0]
        assert review.raw_content == content_text
        assert review.reviewer_id == "(Anonymous Reviewer #1)"

    def test_parse_reviews_exception_handling(self):
        """Test that parsing exceptions are handled gracefully."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        
        # Mock element that raises exception
        mock_element = MagicMock()
        mock_element.find_element.side_effect = Exception("Parse error")
        
        # Should not raise exception, but return empty list
        reviews, meta_review = client._parse_reviews([mock_element])
        assert reviews == []
        assert meta_review is None

    def test_parse_cvpr_rating_valid(self):
        """Test parsing CVPR rating format with valid data."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        
        content = """
        Some content here
        Preliminary Recommendation: 5
        Justification For Recommendation And Suggestions For Rebuttal: Good paper
        Confidence Level: 4
        Final Rating: 6
        Final Rating Justification: Strong paper
        """
        
        rating, confidence, final_rating = client._parse_cvpr_rating(content)
        
        assert rating == 5
        assert confidence == 4
        assert final_rating == 6

    def test_parse_cvpr_rating_no_preliminary(self):
        """Test parsing CVPR rating with no preliminary recommendation."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        
        content = "No rating information here"
        
        rating, confidence, final_rating = client._parse_cvpr_rating(content)
        
        assert rating is None
        assert confidence is None
        assert final_rating is None

    def test_parse_cvpr_rating_invalid_format(self):
        """Test parsing CVPR rating with invalid format."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        
        content = """
        Preliminary Recommendation: invalid
        Justification For Recommendation And Suggestions For Rebuttal: Good paper
        Confidence Level: not_a_number
        """
        
        rating, confidence, final_rating = client._parse_cvpr_rating(content)
        
        assert rating is None
        assert confidence is None
        assert final_rating is None

    def test_parse_cvpr_rating_no_final_rating(self):
        """Test parsing CVPR rating without final rating."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        
        content = """
        Preliminary Recommendation: 5
        Justification For Recommendation And Suggestions For Rebuttal: Good paper
        Confidence Level: 4
        """
        
        rating, confidence, final_rating = client._parse_cvpr_rating(content)
        
        assert rating == 5
        assert confidence == 4
        assert final_rating is None

    def test_parse_ratings_from_review_cvpr(self):
        """Test parsing ratings from review for CVPR conference."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        client.conference_config = MagicMock()
        client.conference_config.name = "cvpr2024"
        
        review = Review(raw_content="""
        Preliminary Recommendation: 5
        Justification For Recommendation And Suggestions For Rebuttal: Good paper
        Confidence Level: 4
        Final Rating: 6
        """)
        
        ratings, confidences, final_ratings = client._parse_ratings_from_review(review)
        
        assert ratings == [5]
        assert confidences == [4]
        assert final_ratings == [6]

    def test_parse_ratings_from_review_non_cvpr(self):
        """Test parsing ratings from review for non-CVPR conference."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        client.conference_config = MagicMock()
        client.conference_config.name = "icml2024"
        
        review = Review(raw_content="Some content")
        
        ratings, confidences, final_ratings = client._parse_ratings_from_review(review)
        
        assert ratings == []
        assert confidences == []
        assert final_ratings == []

    def test_parse_ratings_from_review_cvpr_partial(self):
        """Test parsing CVPR ratings with partial data."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        client.conference_config = MagicMock()
        client.conference_config.name = "cvpr2024"
        
        review = Review(raw_content="""
        Preliminary Recommendation: 5
        Confidence Level: 4
        """)
        
        ratings, confidences, final_ratings = client._parse_ratings_from_review(review)
        
        assert ratings == [5]
        assert confidences == [4]
        assert final_ratings == []

    @patch('ac_conference_helper.client.openreview_client.navigate_and_wait')
    def test_load_submission_basic(self, mock_navigate):
        """Test basic submission loading."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        client.driver = MagicMock()
        
        # Mock driver elements
        mock_title = MagicMock()
        mock_title.text = "Test Paper Title"
        mock_content = MagicMock()
        mock_content.text = "Number: 123\nOther info"
        
        client.driver.find_element.side_effect = [
            mock_title,  # citation_title
            mock_content,  # note-content
        ]
        
        # Mock find_elements for PDF and rebuttal URLs
        client.driver.find_elements.side_effect = [
            [],  # pdf_url (not found)
            [],  # rebuttal_url (not found)
        ]
        
        # Mock _load_reviews to return empty list
        with patch.object(client, '_load_reviews', return_value=[]):
            with patch.object(client, '_parse_reviews', return_value=[]):
                submission = client.load_submission("http://example.com/paper123")
        
        assert submission.title == "Test Paper Title"
        assert submission.sub_id == "123"
        assert submission.url == "http://example.com/paper123"
        assert submission.reviews == []

    @patch('ac_conference_helper.client.openreview_client.navigate_and_wait')
    def test_load_submission_with_pdf_url(self, mock_navigate):
        """Test submission loading with PDF URL."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        client.driver = MagicMock()
        
        # Mock driver elements
        mock_title = MagicMock()
        mock_title.text = "Test Paper"
        mock_content = MagicMock()
        mock_content.text = "Number: 456"
        mock_pdf = MagicMock()
        mock_pdf.get_attribute.return_value = "http://example.com/paper.pdf"
        
        client.driver.find_element.side_effect = [
            mock_title,  # citation_title
            mock_content,  # note-content
            mock_pdf,  # pdf_url
        ]
        
        # Mock find_elements for rebuttal URL
        client.driver.find_elements.side_effect = [
            [],  # rebuttal_url (not found)
        ]
        
        with patch.object(client, '_load_reviews', return_value=[]):
            with patch.object(client, '_parse_reviews', return_value=[]):
                submission = client.load_submission("http://example.com/paper456")
        
        assert submission.pdf_url == "http://example.com/paper.pdf"

    @patch('ac_conference_helper.client.openreview_client.navigate_and_wait')
    def test_load_submission_pdf_url_exception(self, mock_navigate):
        """Test submission loading with PDF URL exception."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        client.driver = MagicMock()
        
        # Mock driver elements
        mock_title = MagicMock()
        mock_title.text = "Test Paper"
        mock_content = MagicMock()
        mock_content.text = "Number: 789"
        
        # PDF element raises exception
        client.driver.find_element.side_effect = [
            mock_title,  # citation_title
            mock_content,  # note-content
            Exception("PDF not found"),  # pdf_url
        ]
        
        # Mock find_elements for rebuttal URL
        client.driver.find_elements.side_effect = [
            [],  # rebuttal_url (not found)
        ]
        
        with patch.object(client, '_load_reviews', return_value=[]):
            with patch.object(client, '_parse_reviews', return_value=[]):
                submission = client.load_submission("http://example.com/paper789")
        
        assert submission.pdf_url is None

    @patch('ac_conference_helper.client.openreview_client.navigate_and_wait')
    def test_load_submission_with_rebuttal(self, mock_navigate):
        """Test submission loading with rebuttal URL."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        client.driver = MagicMock()
        
        # Mock driver elements
        mock_title = MagicMock()
        mock_title.text = "Test Paper"
        mock_content = MagicMock()
        mock_content.text = "Number: 999"
        mock_rebuttal = MagicMock()
        mock_rebuttal.get_attribute.return_value = "http://example.com/rebuttal.pdf"
        
        client.driver.find_element.side_effect = [
            mock_title,  # citation_title
            mock_content,  # note-content
        ]
        
        # Mock find_elements for PDF and rebuttal URLs
        client.driver.find_elements.side_effect = [
            [],  # pdf_url (not found)
            [mock_rebuttal],  # rebuttal_elements
        ]
        
        with patch.object(client, '_load_reviews', return_value=[]):
            with patch.object(client, '_parse_reviews', return_value=[]):
                # Mock find_elements specifically for this test
                with patch.object(client.driver, 'find_elements') as mock_find_elements:
                    mock_find_elements.return_value = [mock_rebuttal]
                    submission = client.load_submission("http://example.com/paper999")
        
        assert submission.rebuttal_url == "http://example.com/rebuttal.pdf"

    @patch('ac_conference_helper.client.openreview_client.navigate_and_wait')
    def test_load_submission_skip_reviews(self, mock_navigate):
        """Test submission loading with skip_reviews=True."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        client.driver = MagicMock()
        
        # Mock driver elements
        mock_title = MagicMock()
        mock_title.text = "Test Paper"
        mock_content = MagicMock()
        mock_content.text = "Number: 111"
        
        client.driver.find_element.side_effect = [
            mock_title,  # citation_title
            mock_content,  # note-content
        ]
        
        # Mock find_elements for PDF and rebuttal URLs
        client.driver.find_elements.side_effect = [
            [],  # pdf_url (not found)
            [],  # rebuttal_url (not found)
        ]
        
        with patch.object(client, '_load_reviews') as mock_load_reviews:
            with patch.object(client, '_parse_reviews') as mock_parse_reviews:
                submission = client.load_submission("http://example.com/paper111", skip_reviews=True)
        
        mock_load_reviews.assert_not_called()
        mock_parse_reviews.assert_not_called()
        assert submission.reviews == []

    @patch('ac_conference_helper.client.openreview_client.navigate_and_wait')
    def test_load_submission_with_reviews(self, mock_navigate):
        """Test submission loading with reviews."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        client.driver = MagicMock()
        
        # Mock driver elements
        mock_title = MagicMock()
        mock_title.text = "Test Paper"
        mock_content = MagicMock()
        mock_content.text = "Number: 222"
        
        client.driver.find_element.side_effect = [
            mock_title,  # citation_title
            mock_content,  # note-content
        ]
        
        # Mock find_elements for PDF and rebuttal URLs
        client.driver.find_elements.side_effect = [
            [],  # pdf_url (not found)
            [],  # rebuttal_url (not found)
        ]
        
        # Mock review elements and parsing
        mock_review_element = MagicMock()
        mock_review = Review(
            reviewer_id="reviewer1",
            preliminary_recommendation="5: Weak Accept",
            confidence_level="4: High"
        )
        
        with patch.object(client, '_load_reviews', return_value=[mock_review_element]):
            with patch.object(client, '_parse_reviews', return_value=([mock_review], None)):
                submission = client.load_submission("http://example.com/paper222")
        
        assert len(submission.reviews) == 1
        assert submission.reviews[0].reviewer_id == "reviewer1"

    def test_load_reviews_success(self):
        """Test successful review loading."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        client.driver = MagicMock()
        
        # Mock forum-replies element
        mock_forum = MagicMock()
        client.driver.find_element.return_value = mock_forum
        
        # Mock review elements
        mock_review1 = MagicMock()
        mock_subheading1 = MagicMock()
        mock_subheading1.text = "Official Review by Reviewer 1"
        mock_review1.find_element.return_value = mock_subheading1
        
        mock_review2 = MagicMock()
        mock_subheading2 = MagicMock()
        mock_subheading2.text = "Some other content"  # Not an official review
        mock_review2.find_element.side_effect = Exception("No subheading")
        
        mock_forum.find_elements.return_value = [mock_review1, mock_review2]
        
        reviews = client._load_reviews()
        
        # Should only return the official review
        assert len(reviews) == 1
        assert reviews[0] == mock_review1

    def test_load_reviews_exception_handling(self):
        """Test review loading with exceptions."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        client.driver = MagicMock()
        
        mock_forum = MagicMock()
        mock_review = MagicMock()
        mock_review.find_element.side_effect = Exception("Error finding subheading")
        
        client.driver.find_element.return_value = mock_forum
        mock_forum.find_elements.return_value = [mock_review]
        
        reviews = client._load_reviews()
        
        # Should handle exception gracefully and return empty list
        assert len(reviews) == 0

    @patch('ac_conference_helper.client.tqdm')
    def test_load_all_submissions(self, mock_tqdm):
        """Test loading all submissions."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        client.paper_urls = ["http://example.com/paper1", "http://example.com/paper2"]
        
        # Mock tqdm to return the list as-is
        mock_tqdm.return_value = client.paper_urls
        
        submission1 = Submission(title="Paper 1", sub_id="1", url="http://example.com/paper1")
        submission2 = Submission(title="Paper 2", sub_id="2", url="http://example.com/paper2")
        
        with patch.object(client, 'load_submission') as mock_load:
            mock_load.side_effect = [submission1, submission2]
            
            submissions = client.load_all_submissions()
        
        assert len(submissions) == 2
        assert submissions[0].title == "Paper 1"
        assert submissions[1].title == "Paper 2"
        assert mock_load.call_count == 2

    @patch('ac_conference_helper.client.tqdm')
    def test_load_all_submissions_skip_reviews(self, mock_tqdm):
        """Test loading all submissions with skip_reviews=True."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        client.paper_urls = ["http://example.com/paper1"]
        
        mock_tqdm.return_value = client.paper_urls
        
        submission = Submission(title="Paper 1", sub_id="1", url="http://example.com/paper1")
        
        with patch.object(client, 'load_submission', return_value=submission) as mock_load:
            client.load_all_submissions(skip_reviews=True)
        
        mock_load.assert_called_once_with("http://example.com/paper1", skip_reviews=True)

    @patch('ac_conference_helper.client.tqdm')
    def test_load_all_submissions_empty_list(self, mock_tqdm):
        """Test loading all submissions with empty URL list."""
        client = OpenReviewClient.__new__(OpenReviewClient)
        client.paper_urls = []
        
        mock_tqdm.return_value = []
        
        with patch.object(client, 'load_submission') as mock_load:
            submissions = client.load_all_submissions()
        
        assert len(submissions) == 0
        mock_load.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__])
