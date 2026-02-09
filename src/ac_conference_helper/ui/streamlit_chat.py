"""Streamlit web interface for conference submission chat system."""

import streamlit as st
import pandas as pd
from typing import List, Dict, Optional, Any
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from ac_conference_helper.core.models import Submission
from ac_conference_helper.core.submission_analyzer import SubmissionAnalyzer
from ac_conference_helper.config.constants import AVAILABLE_ANALYSES
from ac_conference_helper.core.llm_integration import create_llm_client_from_env
from ac_conference_helper.core.chat_system import SubmissionChatSystem, ChatSession
from ac_conference_helper.core.display import submissions_to_dataframe_streamlit, print_table_with_format
from ac_conference_helper.core.models import int_list_to_str

# Import logging configuration
from ac_conference_helper.utils.logging_config import get_logger

# Configure structured logging
logger = get_logger(__name__)

# Page configuration
st.set_page_config(
    page_title="Conference Submission Analyzer",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown(
    """
<style>
.metric-card {
    background-color: #f0f2f6;
    border: 1px solid #e1e5e9;
    border-radius: 0.5rem;
    padding: 1rem;
    margin-bottom: 1rem;
}
.rating-positive {
    color: #28a745;
    font-weight: bold;
}
.rating-negative {
    color: #dc3545;
    font-weight: bold;
}
.stDataFrame {
    width: 100%;
}
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data
def load_submissions():
    """Load submissions from cache file."""
    import pickle
    import os
    from glob import glob

    # Get cache directory from environment or use default
    cache_dir = os.getenv("CACHE_DIR", "cache")

    # Find the most recent cache file
    cache_files = glob(f"{cache_dir}/submissions_*.pkl")
    if not cache_files:
        return []

    cache_file = max(cache_files, key=os.path.getctime)

    try:
        with open(cache_file, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        st.error(f"Error loading submissions: {e}")
        return []


@st.cache_resource
def get_analyzer():
    """Get cached analyzer instance."""
    return SubmissionAnalyzer()


def main():
    """Main Streamlit application."""
    st.title("📚 Conference Submission Analyzer")
    st.markdown(
        "Interactive analysis system for conference submissions with LLM-powered insights"
    )

    # Initialize session state
    if "submissions" not in st.session_state:
        st.session_state.submissions = load_submissions()

    if "chat_system" not in st.session_state:
        st.session_state.chat_system = SubmissionChatSystem(
            st.session_state.submissions
        )

    if "current_submission_id" not in st.session_state:
        st.session_state.current_submission_id = None

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Sidebar for navigation
    with st.sidebar:
        st.header("🔧 Controls")

        # Refresh data button
        if st.button("🔄 Refresh Data", type="primary"):
            st.session_state.submissions = load_submissions()
            st.session_state.chat_system = SubmissionChatSystem(
                st.session_state.submissions
            )
            st.rerun()

        # Statistics
        st.subheader("📊 Statistics")
        total_submissions = len(st.session_state.submissions)
        total_reviews = sum(len(sub.reviews) for sub in st.session_state.submissions)

        st.metric("Total Submissions", total_submissions)
        st.metric("Total Reviews", total_reviews)

        # Filter options
        st.subheader("🔍 Filters")

        # Rating filter
        min_rating = st.slider("Minimum Average Rating", 1.0, 6.0, 1.0, 0.1)
        min_reviews = st.slider("Minimum Number of Reviews", 1, 10, 3)

        # Apply filters
        filtered_submissions = [
            sub
            for sub in st.session_state.submissions
            if sub.avg_rating >= min_rating and len(sub.reviews) >= min_reviews
        ]

        st.write(
            f"Showing {len(filtered_submissions)} of {total_submissions} submissions"
        )

    # Main content area
    tab1, tab2 = st.tabs(["📋 Submissions", "📈 Analytics"])

    with tab1:
        st.header("📋 Submission List")

        if not filtered_submissions:
            st.warning(
                "No submissions found. Make sure to run the data fetching first."
            )
            return

        # Create dataframe for display
        df = submissions_to_dataframe_streamlit(filtered_submissions, include_urls=True)

        # Display as interactive table with row selection
        event = st.dataframe(
            df.drop(columns=["#"]),  # Remove index column for cleaner display
            width="stretch",
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
        )

        # Handle row selection
        if event.selection.rows:
            selected_row_index = event.selection.rows[0]
            selected_sub_id = df.iloc[selected_row_index]["ID"]

            if st.session_state.current_submission_id != selected_sub_id:
                st.session_state.current_submission_id = selected_sub_id
                st.session_state.chat_history = []
                st.rerun()

        # Chat interface below the table
        if st.session_state.current_submission_id:
            st.divider()
            st.header("💬 Chat Analysis")

            # Get current submission
            current_submission = next(
                (
                    sub
                    for sub in st.session_state.submissions
                    if sub.sub_id == st.session_state.current_submission_id
                ),
                None,
            )

            if not current_submission:
                st.error("Submission not found!")
                return

            # Display submission info
            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader(f"📄 {current_submission.title}")
                st.write(f"**ID:** {current_submission.sub_id}")

                # Compact status and ratings info
                valid_prelim_ratings = [
                    r for r in current_submission.ratings if r != -1
                ]
                valid_final_ratings = [
                    r for r in current_submission.final_ratings if r != -1
                ]
                status = (
                    "✅ Complete"
                    if (
                        len(valid_prelim_ratings) >= 3 and len(valid_final_ratings) >= 3
                    )
                    else "⚠️ Incomplete"
                )

                # Create compact info row
                info_cols = st.columns(6)
                with info_cols[0]:
                    st.metric("Avg Rating", f"{current_submission.avg_rating:.2f}")
                with info_cols[1]:
                    st.metric(
                        "Final Rating", f"{current_submission.avg_final_rating:.2f}"
                    )
                with info_cols[2]:
                    st.metric("Reviews", len(current_submission.reviews))
                with info_cols[3]:
                    st.write("**Status:**")
                    st.write(status)
                with info_cols[4]:
                    st.write("**Valid Prelim:**")
                    st.write(f"{len(valid_prelim_ratings)}")
                with info_cols[5]:
                    st.write("**Valid Final:**")
                    st.write(f"{len(valid_final_ratings)}")

                # Compact URLs row
                url_cols = st.columns(2)
                with url_cols[0]:
                    if (
                        hasattr(current_submission, "pdf_url")
                        and current_submission.pdf_url
                    ):
                        st.markdown(f"📕 [PDF]({current_submission.pdf_url})")
                with url_cols[1]:
                    if (
                        hasattr(current_submission, "rebuttal_url")
                        and current_submission.rebuttal_url
                    ):
                        st.markdown(f"📄 [Rebuttal]({current_submission.rebuttal_url})")

                # Add reviewers table
                if current_submission.reviews:
                    st.subheader("👥 Reviewers")
                    reviewer_data = []
                    for i, review in enumerate(current_submission.reviews):
                        reviewer_data.append(
                            {
                                "Reviewer": review.reviewer_id or f"Reviewer_{i+1}",
                                "Preliminary Rating": (
                                    review.numeric_rating_preliminary_recommendation
                                    if review.numeric_rating_preliminary_recommendation
                                    != -1
                                    else None
                                ),
                                "Final Rating": (
                                    review.numeric_rating_final_reccomendation
                                    if review.numeric_rating_final_reccomendation != -1
                                    else None
                                ),
                                "Confidence": (
                                    review.confidence_level
                                    if review.confidence_level
                                    else None
                                ),
                                "Preliminary Recommendation": review.preliminary_recommendation
                                or "N/A",
                                "Final Recommendation": review.final_recommendation
                                or "N/A",
                            }
                        )

                    reviewers_df = pd.DataFrame(reviewer_data)
                    st.dataframe(reviewers_df, width="stretch", hide_index=True)

            with col2:
                # Quick analysis buttons
                st.subheader("🚀 Quick Actions")

                if st.button("📝 Get Summary", key="summary"):
                    with st.spinner("Analyzing..."):
                        analyzer = get_analyzer()
                        enhanced = analyzer.analyze_submission(
                            current_submission, [AVAILABLE_ANALYSES[0]]  # summary
                        )
                        if enhanced.llm_analyses:
                            st.success("Summary generated!")
                            st.session_state.last_summary = enhanced.llm_analyses[
                                0
                            ].result

                if st.button("📋 Get Meta Review", key="meta_review"):
                    with st.spinner("Analyzing..."):
                        analyzer = get_analyzer()
                        enhanced = analyzer.analyze_submission(
                            current_submission, [AVAILABLE_ANALYSES[1]]  # meta_review
                        )
                        if enhanced.llm_analyses:
                            st.success("Meta review generated!")
                            st.session_state.last_meta_review = enhanced.llm_analyses[
                                0
                            ].result

                if st.button("💡 Get Improvements", key="improvements"):
                    with st.spinner("Analyzing..."):
                        analyzer = get_analyzer()
                        enhanced = analyzer.analyze_submission(
                            current_submission,
                            [AVAILABLE_ANALYSES[2]],  # improvement_suggestions
                        )
                        if enhanced.llm_analyses:
                            st.success("Improvement suggestions generated!")
                            st.session_state.last_improvements = enhanced.llm_analyses[
                                0
                            ].result

            # Display analysis results
            if hasattr(st.session_state, "last_summary"):
                with st.expander("📝 Summary", expanded=True):
                    st.write(st.session_state.last_summary)

            if hasattr(st.session_state, "last_meta_review"):
                with st.expander("📋 Meta Review"):
                    st.write(st.session_state.last_meta_review)

            if hasattr(st.session_state, "last_improvements"):
                with st.expander("💡 Improvement Suggestions"):
                    st.write(st.session_state.last_improvements)

            # Chat interface
            st.subheader("💬 Ask Questions")

            # Display chat history
            if st.session_state.chat_history:
                st.write("**Chat History:**")
                for message in st.session_state.chat_history:
                    if message["role"] == "user":
                        st.write(f"**You:** {message['content']}")
                    else:
                        st.write(f"**🤖 Assistant:** {message['content']}")
                    st.write("---")

            # Chat input
            user_question = st.text_input(
                "Ask about this submission:", key="chat_input"
            )

            if st.button("Send", key="send_button") and user_question:
                with st.spinner("Thinking..."):
                    try:
                        # Create context for LLM
                        context = {
                            "submission_id": current_submission.sub_id,
                            "title": current_submission.title,
                            "avg_rating": current_submission.avg_rating,
                            "avg_final_rating": current_submission.avg_final_rating,
                            "pdf_url": getattr(current_submission, "pdf_url", None),
                            "rebuttal_url": getattr(
                                current_submission, "rebuttal_url", None
                            ),
                            "reviews": [],
                        }

                        # Add reviews to context
                        for i, review in enumerate(current_submission.reviews):
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
                                    "reviewer_id": review.reviewer_id
                                    or f"reviewer_{i}",
                                    "submission_date": review.submission_date or "",
                                    "modified_date": review.modified_date or "",
                                    "review_index": i,
                                    "numeric_rating_preliminary_recommendation": review.numeric_rating_preliminary_recommendation,
                                    "numeric_rating_final_reccomendation": review.numeric_rating_final_reccomendation,
                                    "confidence_level": review.confidence_level,
                                }
                            )

                        # Get LLM response
                        llm_client = create_llm_client_from_env()
                        response = llm_client.chat_about_submission(
                            "", [context], user_question, st.session_state.chat_history
                        )

                        # Add to chat history
                        st.session_state.chat_history.append(
                            {"role": "user", "content": user_question}
                        )
                        st.session_state.chat_history.append(
                            {"role": "assistant", "content": response}
                        )

                        st.success("Response received!")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Error getting response: {e}")
        else:
            st.info(
                "👆 Click on a row in the table above to start chatting about that submission."
            )

    with tab2:
        st.header("📈 Analytics Dashboard")

        if not st.session_state.submissions:
            st.warning("No data available for analytics.")
            return

        # Rating distribution
        st.subheader("📊 Rating Distribution")

        all_ratings = []
        all_final_ratings = []

        for sub in st.session_state.submissions:
            all_ratings.extend([r for r in sub.ratings if r != -1])
            all_final_ratings.extend([r for r in sub.final_ratings if r != -1])

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Preliminary Ratings**")
            if all_ratings:
                rating_counts = pd.Series(all_ratings).value_counts().sort_index()
                st.bar_chart(rating_counts)
            else:
                st.write("No ratings data")

        with col2:
            st.write("**Final Ratings**")
            if all_final_ratings:
                final_rating_counts = (
                    pd.Series(all_final_ratings).value_counts().sort_index()
                )
                st.bar_chart(final_rating_counts)
            else:
                st.write("No final ratings data")

        # Statistics
        st.subheader("📈 Overall Statistics")

        if all_ratings:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric(
                    "Avg Preliminary Rating", f"{pd.Series(all_ratings).mean():.2f}"
                )

            with col2:
                st.metric("Std Dev Preliminary", f"{pd.Series(all_ratings).std():.2f}")

            with col3:
                st.metric(
                    "Avg Final Rating", f"{pd.Series(all_final_ratings).mean():.2f}"
                )

            with col4:
                st.metric("Std Dev Final", f"{pd.Series(all_final_ratings).std():.2f}")

        # Top and bottom submissions
        st.subheader("🏆 Top & Bottom Performers")

        # Sort by average rating
        sorted_submissions = sorted(
            [sub for sub in st.session_state.submissions if sub.avg_rating > 0],
            key=lambda x: x.avg_rating,
            reverse=True,
        )

        if sorted_submissions:
            col1, col2 = st.columns(2)

            with col1:
                st.write("**🥇 Top 5 Submissions**")
                top_5 = sorted_submissions[:5]
                for i, sub in enumerate(top_5, 1):
                    st.write(
                        f"{i}. {sub.sub_id} - {sub.title[:50]}... ({sub.avg_rating:.2f})"
                    )

            with col2:
                st.write("**📉 Bottom 5 Submissions**")
                bottom_5 = (
                    sorted_submissions[-5:]
                    if len(sorted_submissions) >= 5
                    else sorted_submissions
                )
                for i, sub in enumerate(bottom_5, 1):
                    st.write(
                        f"{i}. {sub.sub_id} - {sub.title[:50]}... ({sub.avg_rating:.2f})"
                    )


if __name__ == "__main__":
    main()
