"""OpenReview API client for fetching conference submission data."""

import re
import os
from typing import List, Optional
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options as ChromeOptions

from ac_conference_helper.utils.utils import (
    wait_for_page_load,
    navigate_and_wait,
)

# Import logging configuration
from ac_conference_helper.utils.logging_config import get_logger
from tqdm import tqdm

# Configure structured logging
logger = get_logger(__name__)

# Load environment variables from .env file
load_dotenv()
from ac_conference_helper.core.models import Submission, Review, MetaReview, SubmissionStatus
from ac_conference_helper.config.conference_config import get_conference_config, ConferenceConfig


class OpenReviewClient:
    """Client for interacting with OpenReview API."""

    def __init__(self, conference_name: str, headless: bool = True):
        """Initialize OpenReview client.

        Args:
            conference_name: Conference identifier
            headless: Run browser without GUI
        """
        self.conference_config = get_conference_config(conference_name)
        self.driver = self._create_driver(headless)
        self.paper_urls: List[str] = []

        logger.info(
            "Initializing OpenReview client",
            conference=self.conference_config.name,
            display_name=self.conference_config.display_name,
        )

        self._login()

    def __del__(self):
        if hasattr(self, "driver"):
            try:
                self.driver.quit()
            except Exception as e:
                logger.warning("Error quitting driver during cleanup", error=str(e))

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with proper cleanup."""
        try:
            if hasattr(self, "driver"):
                self.driver.quit()
                logger.info("WebDriver properly closed")
        except Exception as e:
            logger.error("Error during cleanup", error=str(e))
        finally:
            # Force cleanup of any remaining multiprocessing resources
            import multiprocessing
            try:
                # Clean up any remaining resources
                multiprocessing.active_children()
            except:
                pass
        return False  # Don't suppress exceptions

    def _create_driver(self, headless: bool) -> webdriver.Chrome:
        """Create and configure Chrome WebDriver."""
        options = ChromeOptions()
        if headless:
            options.add_argument("--headless")
        
        # Set download preferences for PDF handling
        prefs = {
            "download.default_directory": os.path.abspath(
                os.getenv("CACHE_DIR", "cache")
            ),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "plugins.always_open_pdf_externally": True,  # Ensure PDFs download instead of opening in browser
        }
        options.add_experimental_option("prefs", prefs)

        return webdriver.Chrome(options=options)

    def _login(self) -> None:
        """Login to OpenReview and fetch paper URLs."""
        username, password = self._load_credentials()
        area_chair_url = self.conference_config.area_chair_url

        logger.info("Opening login page", url=area_chair_url)
        navigate_and_wait(
            self.driver,
            area_chair_url,
            timeout=6,
            wait_for_elements=[
                (By.ID, "email-input"),
                (By.ID, "password-input"),
                (By.CLASS_NAME, "btn-login"),
            ],
        )

        # Fill login form
        self.driver.find_element(By.ID, "email-input").send_keys(username)
        self.driver.find_element(By.ID, "password-input").send_keys(password)
        self.driver.find_element(By.CLASS_NAME, "btn-login").click()
        logger.info("Login form submitted")

        # Wait for page to load and get paper URLs
        self.paper_urls = self._load_paper_urls()
        logger.info("Found submissions", count=len(self.paper_urls))

    def _load_credentials(self) -> tuple[str, str]:
        """Load login credentials from environment variables."""
        load_dotenv()

        try:
            username = os.environ["USERNAME"]
            password = os.environ["PASSWORD"]
            return username, password
        except KeyError as e:
            raise ValueError(f"Missing environment variable: {e}")

    @wait_for_page_load(element_id="content", content_selector=".note", timeout=6)
    def _load_paper_urls(self) -> List[str]:
        """Load paper URLs from the landing page."""
        urls = self.driver.find_elements(By.XPATH, "//div[@class='note']/h4/a")
        urls = [url.get_attribute("href") for url in urls]
        logger.info("Successfully logged in and loaded paper URLs")
        return urls

    def _parse_reviews(self, review_elements) -> tuple[List[Review], Optional[MetaReview]]:
        """Parse review elements into Review objects and separate meta-review."""
        reviews = []
        meta_review = None

        for element in review_elements:
            try:
                # Extract content from specific subobjects
                subheading = None
                review_content = None

                try:
                    subheading = element.find_element(By.CSS_SELECTOR, ".subheading")
                except:
                    pass

                # Check if this is a meta-review
                is_meta_review = False
                if subheading and "meta review" in subheading.text.lower():
                    is_meta_review = True

                # Try to find the main content div
                content_selectors = [
                    ".note-content",
                    ".content",
                    ".review-content",
                    "div:not(.subheading)",
                ]

                for selector in content_selectors:
                    try:
                        potential_content = element.find_element(
                            By.CSS_SELECTOR, selector
                        )
                        if potential_content != subheading:
                            review_content = potential_content
                            break
                    except:
                        continue

                # Fallback to full element text if specific content div not found
                if not review_content:
                    content = element.text
                else:
                    content = review_content.text

                if is_meta_review:
                    meta_review = MetaReview(content=content, raw_content=content)

                    try:
                        if subheading and subheading.text:
                            subheading_text = subheading.text

                            # Extract submission date (first date)
                            date_match = re.search(
                                r"(\d{1,2}\s+\w+\s+\d{4},\s+\d{1,2}:\d{2})", subheading_text
                            )
                            if date_match:
                                meta_review.raw_content = f"Date: {date_match.group(1)}\n\n{content}"
                    except Exception as e:
                        logger.error(
                            "Error parsing meta-review info from subheading", error=str(e)
                        )
                else:
                    # Create regular Review object
                    review = Review(raw_content=content)

                    # Parse reviewer ID and dates from subheading if available
                    try:
                        if subheading:
                            subheading_text = subheading.text

                            # Extract reviewer ID using regex
                            reviewer_match = re.search(
                                r"by Reviewer\s+(.+?\))", subheading_text
                            )
                            if reviewer_match:
                                review.reviewer_id = reviewer_match.group(1).strip()

                            # Extract submission date (first date)
                            date_match = re.search(
                                r"(\d{1,2}\s+\w+\s+\d{4},\s+\d{1,2}:\d{2})", subheading_text
                            )
                            if date_match:
                                review.submission_date = date_match.group(1)

                            # Extract modified date (after "modified:")
                            modified_match = re.search(
                                r"modified:\s*(\d{1,2}\s+\w+\s+\d{4},\s+\d{1,2}:\d{2})",
                                subheading_text,
                            )
                            if modified_match:
                                review.modified_date = modified_match.group(1)

                    except Exception as e:
                        logger.error(
                            "Error parsing reviewer info from subheading", error=str(e)
                        )
                        pass

                    # Fallback to original signature extraction if subheading doesn't have reviewer info
                    if not review.reviewer_id:
                        try:
                            signature_element = element.find_element(
                                By.CSS_SELECTOR, ".signatures"
                            )
                            if signature_element:
                                review.reviewer_id = signature_element.text
                        except:
                            pass

                    # Pattern to find field headers and content
                    field_patterns = {
                        "paper_summary": r"Paper Summary:\s*(.*?)(?=\n[A-Z]|$)",
                        "preliminary_recommendation": r"Preliminary Recommendation:\s*(.*?)(?=\n[A-Z]|$)",
                        "justification_for_recommendation": r"Justification For Recommendation.*?:\s*(.*?)(?=\n[A-Z]|$)",
                        "confidence_level": r"Confidence Level:\s*(.*?)(?=\n[A-Z]|$)",
                        "paper_strengths": r"Paper Strengths:\s*(.*?)(?=\n[A-Z]|$)",
                        "major_weaknesses": r"Major Weaknesses:\s*(.*?)(?=\n[A-Z]|$)",
                        "minor_weaknesses": r"Minor Weaknesses:\s*(.*?)(?=\n[A-Z]|$)",
                        "final_recommendation": r"Final Recommendation:\s*(.*?)(?=\n[A-Z]|$)",
                        "final_justification": r"Final Justification:\s*(.*?)(?=\n[A-Z]|$)",
                    }

                    # Extract fields using regex
                    for field_name, pattern in field_patterns.items():
                        match = re.search(pattern, content, re.DOTALL)
                        if match:
                            content_text = match.group(1).strip()
                            if content_text:
                                setattr(review, field_name, content_text)

                    reviews.append(review)

            except Exception as e:
                logger.error("Error parsing review", error=str(e))
                continue

        return reviews, meta_review

    def _parse_cvpr_rating(
        self, content: str
    ) -> tuple[Optional[int], Optional[int], Optional[int]]:
        """Parse CVPR rating format."""
        rating_start = content.find("Preliminary Recommendation:")
        if rating_start <= 0:
            return None, None, None

        try:
            just_start = content.find(
                "Justification For Recommendation And Suggestions For Rebuttal:"
            )
            conf_start = content.find("Confidence Level:")
            final_rating_start = content.find("Final Rating:")

            # Parse rating more carefully
            if just_start > 0:
                rating = int(content[rating_start:just_start].split(":")[1].strip())
            else:
                # No justification text, find next line or confidence
                rating_part = content[rating_start:]
                if conf_start > rating_start:
                    rating = int(content[rating_start:conf_start].split(":")[1].strip())
                elif final_rating_start > rating_start:
                    rating = int(content[rating_start:final_rating_start].split(":")[1].strip())
                else:
                    rating = int(content[rating_start:].split(":")[1].strip())
            
            # Parse confidence more carefully
            conf_end = final_rating_start if final_rating_start > 0 else len(content)
            confidence = int(content[conf_start:conf_end].split(":")[1].strip())

            final_rating = None
            final_rating_end = content.find("Final Rating Justification:")
            if final_rating_start > 0:
                if final_rating_end > 0:
                    # Parse with justification
                    final_rating = int(
                        content[final_rating_start:final_rating_end].split(":")[1].strip()
                    )
                else:
                    # Parse without justification
                    final_rating = int(
                        content[final_rating_start:].split(":")[1].strip()
                    )

            return rating, confidence, final_rating
        except (ValueError, IndexError):
            return None, None, None

    def _parse_ratings_from_review(
        self, review: Review
    ) -> tuple[List[int], List[int], List[int]]:
        """Extract ratings from a review based on conference type."""
        content = getattr(review, "raw_content", "")

        if "cvpr" in self.conference_config.name.lower():
            rating, confidence, final_rating = self._parse_cvpr_rating(content)
            ratings = [rating] if rating is not None else []
            confidences = [confidence] if confidence is not None else []
            final_ratings = [final_rating] if final_rating is not None else []
        else:
            # Default parsing for other conferences
            ratings = []
            confidences = []
            final_ratings = []

        return ratings, confidences, final_ratings

    def load_submission(self, url: str, skip_reviews: bool = False) -> Submission:
        """Navigate to submission link and parse info.

        Args:
            url: URL to submission
            skip_reviews: Skip looking for reviews and ratings

        Returns:
            Submission object with parsed data
        """
        logger.info("Loading submission", url=url)
        navigate_and_wait(
            self.driver,
            url,
            timeout=6,
            wait_for_elements=[
                (By.CLASS_NAME, "citation_title"),
                (By.XPATH, "//div[@class='forum-note']/div[@class='note-content']"),
            ],
        )

        # Get submission title and ID
        title = self.driver.find_element(By.CLASS_NAME, "citation_title").text
        content = self.driver.find_element(
            By.XPATH, "//div[@class='forum-note']/div[@class='note-content']"
        ).text
        sub_id = content.split("Number:")[1].strip().split("\n")[0].strip()

        # Get reviews
        review_elements = [] if skip_reviews else self._load_reviews()

        # Parse reviews into Review objects and separate meta-review
        detailed_reviews = []
        meta_review = None
        if review_elements:
            detailed_reviews, meta_review = self._parse_reviews(review_elements)

        # Get PDF URL
        pdf_url = None
        try:
            pdf_element = self.driver.find_element(By.CSS_SELECTOR, ".citation_pdf_url")
            pdf_url = pdf_element.get_attribute("href")
            if pdf_url:
                logger.info("PDF URL found", submission_id=sub_id, pdf_url=pdf_url)
            else:
                logger.warning("No PDF URL found", submission_id=sub_id)
        except Exception as e:
            logger.warning("Error finding PDF URL", submission_id=sub_id, error=str(e))

        # Get rebuttal URL
        rebuttal_url = None
        try:
            rebuttal_elements = self.driver.find_elements(
                By.CSS_SELECTOR, ".attachment-download-link[title='Download PDF']"
            )
            if rebuttal_elements:
                rebuttal_url = rebuttal_elements[0].get_attribute("href")
                if rebuttal_url:
                    logger.info(
                        "Rebuttal URL found",
                        submission_id=sub_id,
                        rebuttal_url=rebuttal_url,
                    )
                else:
                    logger.warning(
                        "Rebuttal element found but no URL", submission_id=sub_id
                    )
            else:
                logger.info("No rebuttal found", submission_id=sub_id)
        except Exception as e:
            logger.warning(
                "Error finding rebuttal URL", submission_id=sub_id, error=str(e)
            )

        # Create submission with URLs
        # Determine submission status
        status = SubmissionStatus.ACTIVE
        if self._check_withdrawal_status():
            status = SubmissionStatus.WITHDRAWN
        elif self._check_desk_rejection_status():
            status = SubmissionStatus.DESK_REJECTED

        submission = Submission(
            title=title,
            sub_id=sub_id,
            url=url,
            reviews=detailed_reviews,
            meta_review=meta_review,
            pdf_url=pdf_url,
            rebuttal_url=rebuttal_url,
            status=status,
        )

        return submission

    def _check_withdrawal_status(self) -> bool:
        """Check if the paper has been withdrawn by looking for 'Withdrawal' in subheadings."""
        try:
            # Look for elements containing "Withdrawal" in their text
            withdrawal_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Withdrawal')]")
            if withdrawal_elements:
                logger.info(f"Found withdrawal indicators: {len(withdrawal_elements)}")
                return True
            
            # Also check for common withdrawal patterns in page source
            page_source = self.driver.page_source.lower()
            withdrawal_patterns = [
                "withdrawal:",
                "paper withdrawn",
                "submission withdrawn",
                "withdrawn by"
            ]
            
            for pattern in withdrawal_patterns:
                if pattern in page_source:
                    logger.info(f"Found withdrawal pattern: {pattern}")
                    return True
                    
            return False
        except Exception as e:
            logger.warning(f"Error checking withdrawal status: {e}")
            return False

    def _check_desk_rejection_status(self) -> bool:
        """Check if the paper has been desk rejected by looking for 'Desk Rejection' in subheadings."""
        try:
            # Look for elements containing "Desk Rejection" in their text
            desk_rejection_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Desk Rejection')]")
            if desk_rejection_elements:
                logger.info(f"Found desk rejection indicators: {len(desk_rejection_elements)}")
                return True
            
            # Also check for desk rejection patterns in page source
            page_source = self.driver.page_source.lower()
            desk_rejection_patterns = [
                "desk rejection",
                "desk reject",
                "desk rejected"
            ]
            
            for pattern in desk_rejection_patterns:
                if pattern in page_source:
                    logger.info(f"Found desk rejection pattern: {pattern}")
                    return True
                    
            return False
        except Exception as e:
            logger.warning(f"Error checking desk rejection status: {e}")
            return False

    @wait_for_page_load(element_id="forum-replies", content_selector=".note.depth-odd")
    def _load_reviews(self) -> List:
        """Load reviews from submission page."""
        # Get the forum-replies element
        forum_replies = self.driver.find_element(By.ID, "forum-replies")

        # Try different selectors for review elements
        selectors = [
            ".note.depth-odd",
            ".note[data-id]",
            "[class*='depth-']",
        ]

        replies = []
        for selector in selectors:
            try:
                elements = forum_replies.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    replies = elements
                    break
            except Exception as e:
                logger.debug(f"Error with selector '{selector}': {e}")
                continue

        # Filter out non-review elements
        valid_reviews = []
        for reply in replies:
            try:
                # Look for the subheading div to confirm it's an official review
                subheading = reply.find_element(By.CSS_SELECTOR, ".subheading")
                if "official review" in subheading.text.lower() or "meta review" in subheading.text.lower():
                    valid_reviews.append(reply)
            except Exception as e:
                logger.debug("Error filtering review", error=str(e))
                continue

        return valid_reviews

    def load_all_submissions(
        self, skip_reviews: bool = False, parallel: bool = False, workers: int = 1
    ) -> List[Submission]:
        """Get all submission info using sequential processing."""
        logger.info("Loading all submissions", skip_reviews=skip_reviews)

        subs = []
        
        # Use tqdm with enhanced stability measures
        for paper_url in tqdm(self.paper_urls, desc="Loading submissions..."):
            try:
                sub = self.load_submission(paper_url, skip_reviews=skip_reviews)
                subs.append(sub)
               
            except Exception as e:
                logger.error(f"Error loading submission {paper_url}", error=str(e))
                continue

        logger.info("Completed loading submissions", count=len(subs))
        return subs
