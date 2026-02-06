import argparse
import os
import random
import string
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional
import re
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import NoSuchElementException
from tqdm import tqdm

from utils import (
    timeout,
    wait_for_page_load,
    wait_for_url_change,
    navigate_and_wait,
    logger,
)
from models import Submission, Review
from display import display_results

TIMEOUT_DURATION = 6


class ORAPI:
    """OpenReview API for fetching conference submission data."""

    CONF_TO_URL = {
        "cvpr_2026": "https://openreview.net/group?id=thecvf.com/CVPR/2026/Conference/Area_Chairs",
    }

    def __init__(self, conf: str, headless: bool = True):
        """Initialize the OpenReview API.

        Args:
            conf: Conference name
            headless: Run browser without GUI
        """
        self.conf = conf
        self.driver = self._create_driver(headless)
        self.paper_urls: list[str] = []

        self._login(self._get_url(conf))

    def __del__(self):
        if hasattr(self, "driver"):
            self.driver.quit()

    def _create_driver(self, headless: bool) -> webdriver.Firefox:
        """Create and configure Firefox WebDriver."""
        options = webdriver.FirefoxOptions()
        if headless:
            options.add_argument("--headless")
        return webdriver.Firefox(options=options)

    def _get_url(self, conf: str) -> str:
        """Get conference Area Chair URL."""
        if conf not in self.CONF_TO_URL:
            raise ValueError(
                f"Conference '{conf}' not supported. Available: {list(self.CONF_TO_URL.keys())}"
            )
        return self.CONF_TO_URL[conf]

    def _login(self, url: str) -> None:
        """Login to OpenReview and fetch paper URLs."""
        username, password = self._load_credentials()

        logger.info("Opening login page", url=url)
        navigate_and_wait(
            self.driver,
            url,
            timeout=TIMEOUT_DURATION,
            wait_for_elements=[
                (By.ID, "email-input"),
                (By.ID, "password-input"),
                (By.CLASS_NAME, "btn-login"),
            ],
        )

        # Fill login form (elements are guaranteed to be present by navigate_and_wait)
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

    @wait_for_page_load(
        element_id="content", content_selector=".note", timeout=TIMEOUT_DURATION
    )
    def _load_paper_urls(self) -> list[str]:
        """Load paper URLs from the landing page."""
        while True:
            urls = self.driver.find_elements(By.XPATH, "//div[@class='note']/h4/a")
            urls = [url.get_attribute("href") for url in urls]
            if urls:
                break
        logger.info("Successfully logged in and loaded paper URLs")
        return urls

    def _parse_reviews(self, review_elements) -> list[Review]:
        """Parse review elements into Review objects."""
        reviews = []

        for element in review_elements:
            try:
                # Extract content from specific subobjects
                subheading = None
                review_content = None

                try:
                    subheading = element.find_element(By.CSS_SELECTOR, ".subheading")
                except:
                    pass

                # Try to find the main content div (not the subheading)
                # Look for common content container patterns
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
                        # Make sure we're not getting the subheading again
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
                # Handles cases where field and content are on same line
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

        return reviews

    def _parse_iclr_rating(self, content: str) -> tuple[Optional[int], Optional[int]]:
        """Parse ICLR rating format."""
        rating_start = content.find("Rating: ")
        if rating_start <= 0:
            return None, None

        confidence_start = content.find("Confidence: ")
        code_start = content.find("Code Of Conduct: ")

        try:
            rating = int(content[rating_start:confidence_start].split(":")[1].strip())
            confidence = int(content[confidence_start:code_start].split(":")[1].strip())
            return rating, confidence
        except (ValueError, IndexError):
            return None, None

    def _parse_cvpr_rating(
        self, content: str
    ) -> tuple[Optional[int], Optional[int], Optional[int]]:
        """Parse CVPR rating format."""
        rating_start = content.find("Preliminary Recommendation: ")
        if rating_start <= 0:
            return None, None, None

        try:
            just_start = content.find(
                "Justification For Recommendation And Suggestions For Rebuttal: "
            )
            conf_start = content.find("Confidence Level: ")

            rating = int(content[rating_start:just_start].split(":")[1].strip())
            confidence = int(content[conf_start:].split(":")[1].strip())

            final_rating = None
            final_rating_start = content.find("Final Rating:")
            final_rating_end = content.find("Final Rating Justification:")
            if final_rating_start > 0:
                final_rating = int(
                    content[final_rating_start:final_rating_end].split(":")[1].strip()
                )

            return rating, confidence, final_rating
        except (ValueError, IndexError):
            return None, None, None

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
            timeout=TIMEOUT_DURATION,
            wait_for_elements=[
                (By.CLASS_NAME, "citation_title"),
                (By.XPATH, "//div[@class='forum-note']/div[@class='note-content']"),
            ],
        )

        # Get submission title and ID (elements are guaranteed to be present by navigate_and_wait)
        title = self.driver.find_element(By.CLASS_NAME, "citation_title").text
        content = self.driver.find_element(
            By.XPATH, "//div[@class='forum-note']/div[@class='note-content']"
        ).text
        sub_id = content.split("Number:")[1].strip()

        # Get reviews
        review_elements = [] if skip_reviews else self._load_reviews()

        # Parse reviews into Review objects
        detailed_reviews = (
            self._parse_reviews(review_elements) if review_elements else []
        )

        # Extract ratings for backward compatibility
        ratings = [
            r.numeric_rating_preliminary_recommendation
            for r in detailed_reviews
            if r.numeric_rating_preliminary_recommendation is not None
        ]
        confidences = [
            r.numeric_confidence
            for r in detailed_reviews
            if r.numeric_confidence is not None
        ]
        final_ratings = [
            r.numeric_rating_final_reccomendation
            for r in detailed_reviews
            if r.final_recommendation
            and r.numeric_rating_final_reccomendation is not None
        ]

        return Submission(
            title, sub_id, url, ratings, confidences, final_ratings, reviews=detailed_reviews
        )

    @wait_for_page_load(
        element_id="forum-replies", content_selector=".note", timeout=TIMEOUT_DURATION
    )
    def _load_reviews(self) -> list:
        """Load reviews from submission page."""
        # Get the forum-replies element (now guaranteed to be loaded by decorator)
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
                print(f"Error with selector '{selector}': {e}")
                continue

        # Filter out non-review elements - only keep those with "official review" in subheading
        valid_reviews = []
        for reply in replies:
            try:
                # Look for the subheading div to confirm it's an official review
                subheading = reply.find_element(By.CSS_SELECTOR, ".subheading")
                if "official review" in subheading.text.lower():
                    valid_reviews.append(reply)
            except Exception as e:
                logger.error("Error filtering review", error=str(e))
                continue

        return valid_reviews

    def load_all_submissions(
        self, skip_reviews: bool = False, parallel: bool = True, workers: int = 4
    ) -> list[Submission]:
        """Get all submission info with optional parallel processing."""
        if not parallel or len(self.paper_urls) <= 1:
            # Sequential processing for small datasets or when disabled
            subs = [
                self.load_submission(paper_url, skip_reviews)
                for paper_url in tqdm(self.paper_urls, desc="Loading submissions")
            ]
        else:
            # Parallel processing
            subs = self._load_submissions_parallel(
                self.paper_urls, skip_reviews, workers
            )
        return subs

    def _load_submissions_parallel(
        self, paper_urls: list[str], skip_reviews: bool, workers: int
    ) -> list[Submission]:
        """Load submissions in parallel using ThreadPoolExecutor."""
        subs = [None] * len(paper_urls)  # Pre-allocate list to maintain order

        with ThreadPoolExecutor(max_workers=workers) as executor:
            # Submit all tasks
            future_to_index = {
                executor.submit(self.load_submission, url, skip_reviews): idx
                for idx, url in enumerate(paper_urls)
            }

            # Collect results as they complete
            with tqdm(
                total=len(paper_urls), desc="Loading submissions (parallel)"
            ) as pbar:
                for future in as_completed(future_to_index):
                    idx = future_to_index[future]
                    try:
                        sub = future.result()
                        subs[idx] = sub
                    except Exception as exc:
                        print(f"Submission {idx} generated an exception: {exc}")
                        # Create a placeholder submission for failed loads
                        subs[idx] = Submission(
                            title=f"ERROR (Index {idx})",
                            sub_id=f"ERROR_{idx}",
                            ratings=[],
                            confidences=[],
                            final_ratings=[],
                            reviews=[],
                        )
                    finally:
                        pbar.update(1)

        return subs


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch and analyze conference submission data"
    )
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument(
        "--skip-reviews", action="store_true", help="Skip fetching reviews"
    )
    parser.add_argument(
        "--conf",
        type=str,
        default="cvpr_2026",
        choices=list(ORAPI.CONF_TO_URL.keys()),
        help="Conference to fetch data from",
    )
    parser.add_argument(
        "--simulate", action="store_true", help="Simulate the process with dummy data"
    )
    parser.add_argument("--output", type=str, help="Save results to CSV file")
    parser.add_argument(
        "--format",
        choices=["grid", "pipe", "simple", "github"],
        default="grid",
        help="Table format for display",
    )
    parser.add_argument(
        "--workers", type=int, default=4, help="Number of parallel workers (default: 4)"
    )
    parser.add_argument(
        "--no-parallel", action="store_true", help="Disable parallel processing"
    )
    return parser.parse_args()


def main() -> None:
    """Main function to fetch and display submission data."""
    args = parse_args()

    if args.simulate:
        subs = _generate_mock_submissions(5)
    else:
        api = ORAPI(conf=args.conf, headless=args.headless)
        use_parallel = not args.no_parallel
        subs = api.load_all_submissions(
            skip_reviews=args.skip_reviews, parallel=use_parallel, workers=args.workers
        )

    # Display results using display module
    display_results(subs, args)


def _generate_mock_submissions(count: int) -> list[Submission]:
    """Generate mock submission data for simulation."""
    subs = []
    for _ in range(count):
        ratings = [random.choice(range(1, 6)) for _ in range(random.randint(0, 3))]
        final_ratings = [
            random.choice(range(1, 6)) for _ in range(random.randint(0, 3))
        ]
        subs.append(
            Submission(
                title="Title " + random.choice(string.ascii_uppercase),
                sub_id=str(random.choice(range(1000, 20000))),
                ratings=ratings,
                confidences=[random.choice(range(1, 5)) for _ in range(len(ratings))],
                final_ratings=final_ratings,
                reviews=[],  # Empty reviews for mock data
            )
        )
    return subs


if __name__ == "__main__":
    main()
