"""Interactive chat system for submission analysis."""

import sys
import readline
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import numpy as np
import pandas as pd
from tabulate import tabulate

from models import Submission
from submission_analyzer import EnhancedSubmission, SubmissionAnalyzer
from llm_integration import create_llm_client_from_env

# Import logging configuration
from logging_config import get_logger

# Configure structured logging
logger = get_logger(__name__)

# Local functions for statistics
mean_std = lambda values: (
    f"{np.mean([v for v in values if v != -1]):.2f}±{np.std([v for v in values if v != -1]):.2f}"
    if values and any(v != -1 for v in values)
    else "-"
)


@dataclass
class ChatSession:
    """Chat session state."""

    current_submission_id: Optional[str] = None
    chat_history: List[Dict[str, str]] = None
    session_history: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.chat_history is None:
            self.chat_history = []
        if self.session_history is None:
            self.session_history = []


class SubmissionChatSystem:
    """Interactive chat system for analyzing submissions."""

    def __init__(self, submissions: List[Submission] = None):
        """Initialize chat system."""
        self.submissions = submissions or []
        self.submissions_dict = {sub.sub_id: sub for sub in self.submissions}
        self.llm_client = create_llm_client_from_env()
        self.session = ChatSession()

        # Available commands
        self.commands = {
            "help": self.show_help,
            "list": self.list_submissions,
            "search": self.search_submissions,
            "select": self.select_submission,
            "current": self.show_current_submission,
            "clear": self.clear_chat,
            "history": self.show_history,
            "exit": self.exit_chat,
            "quit": self.exit_chat,
            "analyze": self.analyze_current,
            "summary": self.get_summary,
            "recommendation": self.get_recommendation,
            "improvements": self.get_improvements,
            "stats": self.show_stats,
        }

    def start(self):
        """Start the interactive chat system."""
        print("=" * 60)
        print("🤖 Conference Submission Chat System")
        print("=" * 60)
        print()

        # Check LLM connection
        if not self.llm_client.test_connection():
            print("⚠️  Warning: Cannot connect to Ollama endpoint.")
            print("   Please ensure Ollama is running with: ollama serve")
            print("   Some features may not work properly.")
            print()

        # Check submissions
        if not self.submissions:
            print("📝 No submissions available.")
            print("   Please run the data fetching first.")
            print()
        else:
            print(f"📚 Loaded {len(self.submissions)} submissions")
            print()

        self.show_help()

        # Main chat loop
        while True:
            try:
                user_input = input("💬 ").strip()

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    command = None
                    try:
                        command_parts = user_input[1:].split()
                        command = command_parts[0].lower()
                        args = command_parts[1:] if len(command_parts) > 1 else []
                    except Exception as e:
                        print(f"❌ Error parsing command: {e}")
                        continue

                    if command in self.commands:
                        try:
                            self.commands[command](args)
                        except Exception as e:
                            print(f"❌ Error executing command: {e}")
                    else:
                        print(f"❌ Unknown command: /{command}")
                        print("   Type /help for available commands")
                else:
                    # Regular chat message
                    self.handle_chat_message(user_input)

            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except EOFError:
                print("\n👋 Goodbye!")
                break

    def handle_chat_message(self, message: str):
        """Handle regular chat message."""
        if not self.session.current_submission_id:
            print("❌ No submission selected. Use /select <id> or /list to choose one.")
            return

        # Get submission from our dictionary
        submission = self.submissions_dict.get(self.session.current_submission_id)
        if not submission:
            print(f"❌ Submission {self.session.current_submission_id} not found.")
            return

        # Create context for LLM
        context = self._create_submission_context(submission)

        # Get LLM response
        print("🤔 Thinking...")
        try:
            response = self.llm_client.chat_about_submission(
                "", [context], message, self.session.chat_history
            )

            # Add to chat history
            self.session.chat_history.append({"role": "user", "content": message})
            self.session.chat_history.append({"role": "assistant", "content": response})

            print(f"🤖 {response}")
            print()

        except Exception as e:
            print(f"❌ Error getting LLM response: {e}")

    def _create_submission_context(self, submission: Submission) -> Dict[str, Any]:
        """Create context dictionary from submission object."""
        context = {
            "submission_id": submission.sub_id,
            "title": submission.title,
            "avg_rating": submission.avg_rating,
            "avg_final_rating": submission.avg_final_rating,
            "pdf_url": submission.pdf_url,
            "rebuttal_url": submission.rebuttal_url,
            "reviews": [],
            "llm_analyses": [],
        }

        # Add reviews
        for i, review in enumerate(submission.reviews):
            context["reviews"].append(
                {
                    "content": f"Review {i+1}: {review.paper_summary or ''}\n"
                    f"Preliminary Recommendation: {review.preliminary_recommendation or ''}\n"
                    f"Justification: {review.justification_for_recommendation or ''}\n"
                    f"Final Recommendation: {review.final_recommendation or ''}\n"
                    f"Final Justification: {review.final_justification or ''}\n"
                    f"Strengths: {review.paper_strengths or ''}\n"
                    f"Weaknesses: {review.major_weaknesses or ''}\n"
                    f"Minor Weaknesses: {review.minor_weaknesses or ''}",
                    "reviewer_id": review.reviewer_id or f"reviewer_{i}",
                    "submission_date": review.submission_date or "",
                    "modified_date": review.modified_date or "",
                    "review_index": i,
                    "numeric_rating_preliminary_recommendation": review.numeric_rating_preliminary_recommendation,
                    "numeric_rating_final_reccomendation": review.numeric_rating_final_reccomendation,
                    "confidence_level": review.confidence_level,
                    "paper_summary": review.paper_summary,
                    "preliminary_recommendation": review.preliminary_recommendation,
                    "final_recommendation": review.final_recommendation,
                    "justification_for_recommendation": review.justification_for_recommendation,
                    "final_justification": review.final_justification,
                    "paper_strengths": review.paper_strengths,
                    "major_weaknesses": review.major_weaknesses,
                    "minor_weaknesses": review.minor_weaknesses,
                }
            )

        return context

    def show_help(self, args=None):
        """Show help information."""
        print("📖 Available Commands:")
        print("  /help                 - Show this help message")
        print("  /list [limit]         - List available submissions")
        print("  /search <query>       - Search submissions by title/content")
        print("  /select <id>          - Select a submission to chat about")
        print("  /current              - Show current submission info")
        print("  /clear                - Clear current chat history")
        print("  /history              - Show chat session history")
        print(
            "  /analyze <type>       - Analyze current submission (summary/recommendation/improvements)"
        )
        print("  /summary              - Get quick summary of current submission")
        print("  /recommendation       - Get recommendation for current submission")
        print(
            "  /improvements         - Get improvement suggestions for current submission"
        )
        print("  /stats                - Show submission statistics")
        print("  /exit, /quit          - Exit the chat system")
        print()
        print("💡 You can also just type questions about the selected submission!")
        print(
            "🔍 Search supports semantic queries like 'machine learning' or 'computer vision'"
        )
        print()

    def list_submissions(self, args):
        """List available submissions."""
        limit = int(args[0]) if args and args[0].isdigit() else 10

        if not self.submissions:
            print("📝 No submissions available.")
            return

        # Get submission summaries
        print(
            f"📚 Available Submissions (showing {min(limit, len(self.submissions))}):"
        )
        print("-" * 60)

        for i, submission in enumerate(self.submissions[:limit]):
            current_marker = (
                "👉 "
                if submission.sub_id == self.session.current_submission_id
                else "   "
            )
            print(f"{current_marker}{submission.sub_id}: {submission.title}")
            print(
                f"      Rating: {submission.avg_rating:.2f} | Final: {submission.avg_final_rating:.2f}"
            )
            print(f"      Reviews: {len(submission.reviews)}")

        if len(self.submissions) > limit:
            print(f"      ... and {len(self.submissions) - limit} more submissions")
        print("-" * 60)
        print()

    def search_submissions(self, args):
        """Search submissions."""
        if not args:
            print("❌ Please provide a search query.")
            print("   Usage: /search <query>")
            return

        query = " ".join(args).lower()
        results = []

        # Simple text search in titles and review content
        for submission in self.submissions:
            score = 0
            # Check title match
            if query in submission.title.lower():
                score += 10

            # Check review content matches
            for review in submission.reviews:
                if review.paper_summary and query in review.paper_summary.lower():
                    score += 3
                if (
                    review.final_recommendation
                    and query in review.final_recommendation.lower()
                ):
                    score += 2
                if review.paper_strengths and query in review.paper_strengths.lower():
                    score += 1

            if score > 0:
                results.append((submission, score))

        # Sort by score (descending)
        results.sort(key=lambda x: x[1], reverse=True)

        if not results:
            print(f"🔍 No submissions found for: {query}")
            return

        print(f"🔍 Search Results for '{query}':")
        print("-" * 60)

        for submission, score in results[:10]:  # Limit to top 10 results
            current_marker = (
                "👉 "
                if submission.sub_id == self.session.current_submission_id
                else "   "
            )
            print(
                f"{current_marker}{submission.sub_id}: {submission.title} (score: {score})"
            )
            print(
                f"      Rating: {submission.avg_rating:.2f} | Reviews: {len(submission.reviews)}"
            )

        print("-" * 60)
        print()

    def _display_submission_with_ratings(self, submission: Submission):
        """Display submission information with comprehensive ratings table."""
        print(
            f"📄 {'Selected' if submission.sub_id != self.session.current_submission_id else 'Current'} Submission: {submission.sub_id}"
        )
        print(f"📝 Title: {submission.title}")
        print()
        
        # Display PDF and rebuttal URLs if available
        if submission.pdf_url:
            print(f"📕 PDF: {submission.pdf_url}")
        if submission.rebuttal_url:
            print(f"📄 Rebuttal: {submission.rebuttal_url}")
        print()

        # Display ratings table
        if submission.reviews:
            # Extract data from reviews
            review_data = []
            for i, review in enumerate(submission.reviews):
                review_data.append(
                    {
                        "Reviewer": review.reviewer_id or f"reviewer_{i}",
                        "Initial": review.numeric_rating_preliminary_recommendation,
                        "Final": review.numeric_rating_final_reccomendation,
                        "Confidence": review.numeric_confidence,
                    }
                )

            if review_data:
                # Create table data
                table_data = []
                for row in review_data:
                    table_data.append(
                        [
                            row["Reviewer"],
                            row["Initial"] or "-",
                            row["Final"] or "-",
                            row["Confidence"] or "-",
                        ]
                    )

                # Calculate statistics
                initial_values = [
                    r["Initial"] for r in review_data if r["Initial"] is not None
                ]
                final_values = [
                    r["Final"] for r in review_data if r["Final"] is not None
                ]
                confidence_values = [
                    r["Confidence"] for r in review_data if r["Confidence"] is not None
                ]

                # Add statistics row
                headers = ["Reviewer", "Initial", "Final", "Confidence"]
                table_data.append(
                    [
                        "STATISTICS",
                        mean_std(initial_values),
                        mean_std(final_values),
                        mean_std(confidence_values),
                    ]
                )

                print("📊 Review Ratings Summary:")
                print("=" * 80)
                print(tabulate(table_data, headers=headers, tablefmt="grid"))
                print("=" * 80)
                print()

        print(f"📊 Reviews: {len(submission.reviews)}")
        print()
        print("💬 You can now ask questions about this submission!")
        print()

    def select_submission(self, args):
        """Select a submission to chat about."""
        if not args:
            print("❌ Please provide a submission ID.")
            print("   Usage: /select <submission_id>")
            return

        submission_id = args[0]
        submission = self.submissions_dict.get(submission_id)

        if not submission:
            print(f"❌ Submission {submission_id} not found.")
            return

        # Save current session to history
        if self.session.current_submission_id:
            self.session.session_history.append(
                {
                    "submission_id": self.session.current_submission_id,
                    "chat_history": self.session.chat_history.copy(),
                }
            )

        # Switch to new submission
        self.session.current_submission_id = submission_id
        self.session.chat_history = []

        # Use shared function to display submission with ratings
        self._display_submission_with_ratings(submission)

    def show_current_submission(self, args=None):
        """Show current submission info."""
        if not self.session.current_submission_id:
            print("❌ No submission currently selected.")
            return

        submission = self.submissions_dict.get(self.session.current_submission_id)
        if not submission:
            print(f"❌ Submission {self.session.current_submission_id} not found.")
            return

        # Use shared function to display submission with ratings
        self._display_submission_with_ratings(submission)

    def clear_chat(self, args=None):
        """Clear current chat history."""
        self.session.chat_history = []
        print("🧹 Chat history cleared.")
        print()

    def show_history(self, args=None):
        """Show chat session history."""
        if not self.session.session_history:
            print("📝 No previous chat sessions.")
            return

        print("📜 Chat Session History:")
        print("-" * 40)
        for i, session_data in enumerate(self.session.session_history, 1):
            sub_id = session_data["submission_id"]
            msg_count = len(session_data["chat_history"])
            print(f"  {i}. Submission {sub_id} ({msg_count} messages)")
        print("-" * 40)
        print()

    def analyze_current(self, args):
        """Analyze current submission."""
        if not self.session.current_submission_id:
            print("❌ No submission selected.")
            return

        analysis_type = args[0].lower() if args else "summary"
        valid_types = ["summary", "recommendation", "improvements", "meta_review"]

        if analysis_type not in valid_types:
            print(f"❌ Invalid analysis type. Choose from: {', '.join(valid_types)}")
            return

        submission = self.submissions_dict.get(self.session.current_submission_id)
        if not submission:
            print(f"❌ Submission {self.session.current_submission_id} not found.")
            return

        print(f"🔍 Analyzing submission with {analysis_type}...")
        try:
            context = self._create_submission_context(submission)
            result = self.llm_client.analyze_submission_reviews(context, analysis_type)
            print(f"🤖 {analysis_type.title()} Analysis:")
            print("-" * 40)
            print(result)
            print("-" * 40)
            print()

        except Exception as e:
            print(f"❌ Error during analysis: {e}")

    def get_summary(self, args=None):
        """Get quick summary."""
        self.analyze_current(["summary"])

    def get_recommendation(self, args=None):
        """Get recommendation."""
        self.analyze_current(["recommendation"])

    def get_improvements(self, args=None):
        """Get improvement suggestions."""
        self.analyze_current(["improvements"])

    def show_stats(self, args=None):
        """Show submission statistics."""
        print("📊 Submission Statistics:")
        print("-" * 40)
        print(f"Total Submissions: {len(self.submissions)}")

        if self.submissions:
            # Calculate some basic statistics
            total_reviews = sum(len(sub.reviews) for sub in self.submissions)
            avg_reviews = total_reviews / len(self.submissions)

            ratings = []
            final_ratings = []
            for sub in self.submissions:
                if sub.ratings:
                    ratings.extend(sub.ratings)
                if sub.final_ratings:
                    final_ratings.extend(sub.final_ratings)

            print(f"Total Reviews: {total_reviews}")
            print(f"Average Reviews per Submission: {avg_reviews:.2f}")

            if ratings:
                import statistics

                print(f"Average Rating: {statistics.mean(ratings):.2f}")
                print(f"Rating Std Dev: {statistics.stdev(ratings):.2f}")

            if final_ratings:
                import statistics

                print(f"Average Final Rating: {statistics.mean(final_ratings):.2f}")
                print(f"Final Rating Std Dev: {statistics.stdev(final_ratings):.2f}")

        print("-" * 40)
        print()

    def exit_chat(self, args=None):
        """Exit the chat system."""
        print("👋 Goodbye!")
        sys.exit(0)


def main():
    """Main function to start chat system."""
    chat_system = SubmissionChatSystem()
    chat_system.start()


if __name__ == "__main__":
    main()
