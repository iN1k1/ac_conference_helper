"""Submission analysis module using LLM."""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
import json
import os
from tqdm import tqdm

from ac_conference_helper.core.models import Submission, Review
from ac_conference_helper.core.llm_integration import OllamaClient, create_llm_client_from_env
from ac_conference_helper.config.constants import AVAILABLE_ANALYSES

# Import logging configuration
from ac_conference_helper.utils.logging_config import get_logger

# Configure structured logging
logger = get_logger(__name__)


@dataclass
class LLMAnalysis:
    """Container for LLM analysis results."""

    submission_id: str
    submission_title: str
    analysis_type: str
    result: str
    timestamp: str
    model_used: str
    processing_time: float = 0.0


@dataclass
class EnhancedSubmission:
    """Enhanced submission with LLM analysis."""

    original_submission: Submission
    llm_analyses: List[LLMAnalysis] = field(default_factory=list)

    @property
    def sub_id(self) -> str:
        return self.original_submission.sub_id

    @property
    def title(self) -> str:
        return self.original_submission.title

    @property
    def reviews(self) -> List[Review]:
        return self.original_submission.reviews

    def get_analysis(self, analysis_type: str) -> Optional[LLMAnalysis]:
        """Get analysis by type."""
        for analysis in self.llm_analyses:
            if analysis.analysis_type == analysis_type:
                return analysis
        return None

    def add_analysis(self, analysis: LLMAnalysis):
        """Add new analysis."""
        self.llm_analyses.append(analysis)


class SubmissionAnalyzer:
    """Analyzer for submissions using LLM."""

    def __init__(self, llm_client: Optional[OllamaClient] = None):
        """Initialize analyzer."""
        self.llm_client = llm_client or create_llm_client_from_env()

    def extract_review_texts(self, submission: Submission) -> List[str]:
        """Extract review texts from submission."""
        review_texts = []

        for review in submission.reviews:
            # Combine different parts of the review into a coherent text
            review_parts = []

            if hasattr(review, "paper_summary") and review.paper_summary:
                review_parts.append(f"Paper Summary: {review.paper_summary}")

            if (
                hasattr(review, "preliminary_recommendation")
                and review.preliminary_recommendation
            ):
                review_parts.append(
                    f"Preliminary Recommendation: {review.preliminary_recommendation}"
                )

            if (
                hasattr(review, "justification_for_recommendation")
                and review.justification_for_recommendation
            ):
                review_parts.append(
                    f"Justification: {review.justification_for_recommendation}"
                )

            if hasattr(review, "paper_strengths") and review.paper_strengths:
                review_parts.append(f"Strengths: {review.paper_strengths}")

            if hasattr(review, "major_weaknesses") and review.major_weaknesses:
                review_parts.append(f"Major Weaknesses: {review.major_weaknesses}")

            if hasattr(review, "minor_weaknesses") and review.minor_weaknesses:
                review_parts.append(f"Minor Weaknesses: {review.minor_weaknesses}")

            if hasattr(review, "final_recommendation") and review.final_recommendation:
                review_parts.append(
                    f"Final Recommendation: {review.final_recommendation}"
                )

            if hasattr(review, "final_justification") and review.final_justification:
                review_parts.append(
                    f"Final Justification: {review.final_justification}"
                )

            # If no structured content, use raw content
            if (
                not review_parts
                and hasattr(review, "raw_content")
                and review.raw_content
            ):
                review_parts.append(review.raw_content)

            if review_parts:
                review_texts.append("\n\n".join(review_parts))

        return review_texts

    def analyze_submission(
        self, submission: Submission, analysis_types: List[str]
    ) -> EnhancedSubmission:
        """Analyze a submission with specified analysis types."""
        import time

        # Validate analysis types
        invalid_types = [at for at in analysis_types if at not in AVAILABLE_ANALYSES]
        if invalid_types:
            raise ValueError(
                f"Invalid analysis types: {invalid_types}. "
                f"Available types: {AVAILABLE_ANALYSES}"
            )

        enhanced = EnhancedSubmission(original_submission=submission)
        review_texts = self.extract_review_texts(submission)

        if not review_texts:
            print(f"Warning: No review texts found for submission {submission.sub_id}")
            return enhanced

        start_time = time.time()

        for analysis_type in analysis_types:
            print(f"Analyzing submission {submission.sub_id} with {analysis_type}...")

            try:
                result = self.llm_client.analyze_submission_reviews(
                    submission.title, review_texts, analysis_type
                )

                analysis = LLMAnalysis(
                    submission_id=submission.sub_id,
                    submission_title=submission.title,
                    analysis_type=analysis_type,
                    result=result,
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                    model_used=self.llm_client.config.model,
                    processing_time=time.time() - start_time,
                )

                enhanced.add_analysis(analysis)

            except Exception as e:
                print(f"Error analyzing submission {submission.sub_id}: {e}")

        return enhanced

    def analyze_multiple_submissions(
        self, submissions: List[Submission], analysis_types: List[str]
    ) -> List[EnhancedSubmission]:
        """Analyze multiple submissions."""
        # Validate analysis types
        invalid_types = [at for at in analysis_types if at not in AVAILABLE_ANALYSES]
        if invalid_types:
            raise ValueError(
                f"Invalid analysis types: {invalid_types}. "
                f"Available types: {AVAILABLE_ANALYSES}"
            )

        enhanced_submissions = []

        if not self.llm_client.test_connection():
            print(
                "Error: Cannot connect to Ollama endpoint. Please ensure Ollama is running."
            )
            return enhanced_submissions

        for submission in tqdm(submissions, desc="Analyzing submissions"):
            enhanced = self.analyze_submission(submission, analysis_types)
            enhanced_submissions.append(enhanced)

        return enhanced_submissions

    def save_analyses(
        self, enhanced_submissions: List[EnhancedSubmission], filepath: str
    ):
        """Save analyses to file."""
        data = []
        for enhanced in enhanced_submissions:
            submission_data = {
                "submission_id": enhanced.sub_id,
                "title": enhanced.title,
                "analyses": [
                    {
                        "type": analysis.analysis_type,
                        "result": analysis.result,
                        "timestamp": analysis.timestamp,
                        "model": analysis.model_used,
                        "processing_time": analysis.processing_time,
                    }
                    for analysis in enhanced.llm_analyses
                ],
            }
            data.append(submission_data)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"Saved {len(enhanced_submissions)} analyzed submissions to {filepath}")

    def load_analyses(self, filepath: str) -> List[EnhancedSubmission]:
        """Load analyses from file."""
        if not os.path.exists(filepath):
            return []

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        enhanced_submissions = []

        for submission_data in data:
            # Create basic submission object
            submission = Submission(
                title=submission_data["title"],
                sub_id=submission_data["submission_id"],
                ratings=[],  # Not needed for analysis loading
                confidences=[],
                final_ratings=[],
                reviews=[],
            )

            enhanced = EnhancedSubmission(original_submission=submission)

            # Add analyses
            for analysis_data in submission_data["analyses"]:
                analysis = LLMAnalysis(
                    submission_id=submission_data["submission_id"],
                    submission_title=submission_data["title"],
                    analysis_type=analysis_data["type"],
                    result=analysis_data["result"],
                    timestamp=analysis_data["timestamp"],
                    model_used=analysis_data["model"],
                    processing_time=analysis_data.get("processing_time", 0.0),
                )
                enhanced.add_analysis(analysis)

            enhanced_submissions.append(enhanced)

        return enhanced_submissions
