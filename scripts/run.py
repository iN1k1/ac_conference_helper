import argparse
import os
import random
import string
import pickle
import sys
from pathlib import Path
from typing import Optional

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Import logging configuration
from ac_conference_helper.utils.logging_config import get_logger, configure_logger

# Configure structured logging
logger = get_logger(__name__)

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()

from ac_conference_helper.core.models import Submission
from ac_conference_helper.core.display import display_results
from ac_conference_helper.core.submission_analyzer import SubmissionAnalyzer
from ac_conference_helper.config.constants import AVAILABLE_ANALYSES
from ac_conference_helper.config.conference_config import (
    list_available_conferences,
    get_default_conference,
)
from ac_conference_helper.client.openreview_client import OpenReviewClient

TIMEOUT_DURATION = 6

# Load cache configuration from environment
CACHE_DIR = os.getenv("CACHE_DIR", "cache")
CACHE_FILE_PREFIX = os.getenv("CACHE_FILE_PREFIX", "submissions_")

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)


def get_cache_filename(conf: str, skip_reviews: bool) -> str:
    """Generate cache filename based on conference and settings."""
    reviews_suffix = "_no_reviews" if skip_reviews else ""
    return f"{CACHE_FILE_PREFIX}{conf}{reviews_suffix}.pkl"


def save_submissions_to_cache(
    subs: list[Submission], conf: str, skip_reviews: bool
) -> None:
    """Save submissions to cache file."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, get_cache_filename(conf, skip_reviews))

    with open(cache_file, "wb") as f:
        pickle.dump(subs, f)

    print(f"Cached {len(subs)} submissions to {cache_file}")


def load_submissions_from_cache(
    conf: str, skip_reviews: bool
) -> Optional[list[Submission]]:
    """Load submissions from cache file if exists."""
    cache_file = os.path.join(CACHE_DIR, get_cache_filename(conf, skip_reviews))

    if not os.path.exists(cache_file):
        return None

    try:
        with open(cache_file, "rb") as f:
            subs = pickle.load(f)
        print(f"Loaded {len(subs)} submissions from cache {cache_file}")
        return subs
    except Exception as e:
        print(f"Error loading cache file {cache_file}: {e}")
        return None


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Fetch and analyze conference submission data"
    )
    parser.add_argument(
        "--skip-reviews", action="store_true", help="Skip fetching reviews"
    )
    parser.add_argument(
        "--conf",
        type=str,
        default=get_default_conference(),
        choices=list_available_conferences(),
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
        "--no-save-cache",
        action="store_true",
        help="Don't save submissions to cache after loading",
    )
    parser.add_argument(
        "--clear-cache", action="store_true", help="Clear all cached submission files"
    )
    parser.add_argument(
        "--analyze",
        nargs="+",
        choices=AVAILABLE_ANALYSES,
        help=f"Analyze submissions with LLM. Available: {', '.join(AVAILABLE_ANALYSES)}",
    )
    parser.add_argument("--analysis-output", type=str, help="Save LLM analyses to file")
    parser.add_argument(
        "--chat", action="store_true", help="Launch Streamlit web interface for interactive analysis"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="WARNING",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Set logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    return parser.parse_args()


def main() -> None:
    """Main function to fetch and display submission data."""
    args = parse_args()

    # Configure logging first
    configure_logger(log_level=args.log_level)

    # Handle cache clearing
    if args.clear_cache:
        if os.path.exists(CACHE_DIR):
            import shutil

            shutil.rmtree(CACHE_DIR)
            logger.info("Cleared cache directory", cache_dir=CACHE_DIR)
        else:
            logger.info("No cache directory found to clear")

    # Try to load from cache if requested
    subs = load_submissions_from_cache(args.conf, args.skip_reviews)

    # If no cache loaded, fetch normally
    if subs is None:
        if args.simulate:
            subs = _generate_mock_submissions(5)
        else:
            client = OpenReviewClient(args.conf, headless=True)
            subs = client.load_all_submissions(skip_reviews=args.skip_reviews)

        # Save to cache by default (unless explicitly disabled)
        if not args.no_save_cache and not args.simulate:
            save_submissions_to_cache(subs, args.conf, args.skip_reviews)

    # Handle chat mode - launch Streamlit web interface
    if args.chat:
        # Check if streamlit is available
        try:
            import streamlit
        except ImportError:
            print("❌ Streamlit not installed. Install with:")
            print("   pip install streamlit")
            print("   Or use the console chat with: python run.py --chat (console mode)")
            return
        
        # Check if data exists
        if subs is None:
            print("❌ No submission data found. Please run data fetching first:")
            print(f"   python run.py --conf {args.conf}")
            return
        
        print("🚀 Launching Streamlit web interface...")
        print("📱 Open your browser and go to: http://localhost:8501")
        print("🛑 Press Ctrl+C to stop the server")
        
        # Launch streamlit
        import subprocess
        import sys
        subprocess.run([sys.executable, "-m", "streamlit", "run", "../src/ac_conference_helper/ui/streamlit_chat.py"])
        return

    # Handle LLM analysis
    enhanced_subs = None
    if args.analyze:
        # Set environment variables for LLM client
        os.environ["OLLAMA_MODEL"] = args.ollama_model
        os.environ["OLLAMA_HOST"] = args.ollama_host

        logger.info("Analyzing submissions", analysis_types=args.analyze)
        analyzer = SubmissionAnalyzer()
        enhanced_subs = analyzer.analyze_multiple_submissions(subs, args.analyze)

        # Save analyses if output file specified
        if args.analysis_output:
            analyzer.save_analyses(enhanced_subs, args.analysis_output)

    # Display results using display module
    if not args.analyze and not args.chat:
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
