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
    page_title="Conference Submission Analyzer Dashboard",
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
                info_cols = st.columns(7)
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
                    if current_submission.withdrawn:
                        st.error("🚫 Withdrawn")
                    else:
                        st.success("✅ Active")
                with info_cols[4]:
                    st.write("**Valid Prelim:**")
                    st.write(f"{len(valid_prelim_ratings)}")
                with info_cols[5]:
                    st.write("**Valid Final:**")
                    st.write(f"{len(valid_final_ratings)}")
                with info_cols[6]:
                    st.write("**Complete:**")
                    complete_status = (
                        "✅ Complete"
                        if (
                            len(valid_prelim_ratings) >= 3 and len(valid_final_ratings) >= 3
                        )
                        else "⚠️ Incomplete"
                    )
                    st.write(complete_status)

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

                # Add meta-review information if available
                if (
                    hasattr(current_submission, "meta_review")
                    and current_submission.meta_review
                ):
                    st.subheader("📋 Meta Review")
                    
                    # Create two columns for preliminary and final decisions
                    decision_cols = st.columns(2)
                    
                    with decision_cols[0]:
                        st.write("**Preliminary Decision:**")
                        if current_submission.meta_review.preliminary_decision:
                            decision = current_submission.meta_review.preliminary_decision.lower()
                            if "accept" in decision:
                                if "clear" in decision or "strong" in decision:
                                    st.success(f"✅ {current_submission.meta_review.preliminary_decision}")
                                else:
                                    st.info(f"📝 {current_submission.meta_review.preliminary_decision}")
                            elif "reject" in decision:
                                if "clear" in decision or "strong" in decision:
                                    st.error(f"❌ {current_submission.meta_review.preliminary_decision}")
                                else:
                                    st.warning(f"⚠️ {current_submission.meta_review.preliminary_decision}")
                            elif "discussion" in decision:
                                st.warning(f"🔄 {current_submission.meta_review.preliminary_decision}")
                            else:
                                st.write(current_submission.meta_review.preliminary_decision)
                        else:
                            st.write("N/A")
                    
                    with decision_cols[1]:
                        st.write("**Final Decision:**")
                        if current_submission.meta_review.final_decision:
                            decision = current_submission.meta_review.final_decision.lower()
                            if "accept" in decision:
                                if "clear" in decision or "strong" in decision:
                                    st.success(f"✅ {current_submission.meta_review.final_decision}")
                                else:
                                    st.info(f"📝 {current_submission.meta_review.final_decision}")
                            elif "reject" in decision:
                                if "clear" in decision or "strong" in decision:
                                    st.error(f"❌ {current_submission.meta_review.final_decision}")
                                else:
                                    st.warning(f"⚠️ {current_submission.meta_review.final_decision}")
                            elif "discussion" in decision:
                                st.warning(f"🔄 {current_submission.meta_review.final_decision}")
                            else:
                                st.write(current_submission.meta_review.final_decision)
                        else:
                            st.write("N/A")
                    
                    if current_submission.meta_review.content:
                        with st.expander("📄 Meta Review Content", expanded=False):
                            st.write(current_submission.meta_review.content)

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
                    
                    # Add review content sections
                    st.subheader("📝 Review Content")
                    for i, review in enumerate(current_submission.reviews):
                        reviewer_name = review.reviewer_id or f"Reviewer_{i+1}"
                        with st.expander(f"📄 {reviewer_name} - Review Details", expanded=False):
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.write("**Ratings & Recommendations**")
                                if review.numeric_rating_preliminary_recommendation != -1:
                                    st.write(f"📊 Preliminary Rating: {review.numeric_rating_preliminary_recommendation}")
                                if review.numeric_rating_final_reccomendation != -1:
                                    st.write(f"📊 Final Rating: {review.numeric_rating_final_reccomendation}")
                                if review.confidence_level:
                                    st.write(f"🎯 Confidence: {review.confidence_level}")
                                
                                st.write("**Recommendations**")
                                if review.preliminary_recommendation:
                                    st.write(f"📝 Preliminary: {review.preliminary_recommendation}")
                                if review.final_recommendation:
                                    st.write(f"📝 Final: {review.final_recommendation}")
                            
                            with col2:
                                st.write("**Review Content**")
                                if review.paper_summary:
                                    st.write("**📄 Summary:**")
                                    st.write(review.paper_summary)
                                
                                if review.justification_for_recommendation:
                                    st.write("**💭 Justification:**")
                                    st.write(review.justification_for_recommendation)
                                
                                if review.final_justification:
                                    st.write("**💭 Final Justification:**")
                                    st.write(review.final_justification)
                                
                                if review.paper_strengths:
                                    st.write("**💪 Strengths:**")
                                    st.write(review.paper_strengths)
                                
                                if review.major_weaknesses:
                                    st.write("**⚠️ Major Weaknesses:**")
                                    st.write(review.major_weaknesses)
                                
                                if review.minor_weaknesses:
                                    st.write("**⚠️ Minor Weaknesses:**")
                                    st.write(review.minor_weaknesses)
                            
                            # Add submission info if available
                            if review.submission_date or review.modified_date:
                                st.write("**📅 Timeline:**")
                                if review.submission_date:
                                    st.write(f"Submitted: {review.submission_date}")
                                if review.modified_date:
                                    st.write(f"Modified: {review.modified_date}")

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

                if current_submission.url:
                    st.markdown(f'🔗 <a href="{current_submission.url}" target="_blank" rel="noopener noreferrer">Open in OpenReview</a>', unsafe_allow_html=True)
                else:
                    st.warning("No OpenReview link available for this submission")

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

        # Meta-Review Decision Statistics
        st.subheader("📋 Meta-Review Decision Analysis")
        
        # Count meta-review decisions
        prelim_accept = 0
        prelim_reject = 0
        prelim_discussion = 0
        final_accept = 0
        final_reject = 0
        final_discussion = 0
        
        for sub in st.session_state.submissions:
            if sub.meta_review:
                # Preliminary decisions
                if sub.meta_review.preliminary_decision:
                    prelim_lower = sub.meta_review.preliminary_decision.lower()
                    if "accept" in prelim_lower:
                        prelim_accept += 1
                    elif "reject" in prelim_lower:
                        prelim_reject += 1
                    elif "discussion" in prelim_lower:
                        prelim_discussion += 1
                
                # Final decisions
                if sub.meta_review.final_decision:
                    final_lower = sub.meta_review.final_decision.lower()
                    if "accept" in final_lower:
                        final_accept += 1
                    elif "reject" in final_lower:
                        final_reject += 1
                    elif "discussion" in final_lower:
                        final_discussion += 1
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Preliminary Meta-Review Decisions**")
            meta_prelim_data = {
                "Accept": prelim_accept,
                "Reject": prelim_reject,
                "Discussion": prelim_discussion
            }
            st.bar_chart(meta_prelim_data)
            
            # Calculate percentages
            total_prelim = prelim_accept + prelim_reject + prelim_discussion
            if total_prelim > 0:
                st.write(f"✅ Accept: {prelim_accept} ({prelim_accept/total_prelim*100:.1f}%)")
                st.write(f"❌ Reject: {prelim_reject} ({prelim_reject/total_prelim*100:.1f}%)")
                st.write(f"🔄 Discussion: {prelim_discussion} ({prelim_discussion/total_prelim*100:.1f}%)")
            else:
                st.write("No preliminary meta-review decisions found")
        
        with col2:
            st.write("**Final Meta-Review Decisions**")
            meta_final_data = {
                "Accept": final_accept,
                "Reject": final_reject,
                "Discussion": final_discussion
            }
            st.bar_chart(meta_final_data)
            
            # Calculate percentages
            total_final = final_accept + final_reject + final_discussion
            if total_final > 0:
                st.write(f"✅ Accept: {final_accept} ({final_accept/total_final*100:.1f}%)")
                st.write(f"❌ Reject: {final_reject} ({final_reject/total_final*100:.1f}%)")
                st.write(f"🔄 Discussion: {final_discussion} ({final_discussion/total_final*100:.1f}%)")
            else:
                st.write("No final meta-review decisions found")

        # Withdrawal Statistics
        st.subheader("🚫 Withdrawal Analysis")
        
        withdrawn_count = sum(1 for sub in st.session_state.submissions if sub.withdrawn)
        active_count = len(st.session_state.submissions) - withdrawn_count
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Papers", len(st.session_state.submissions))
        with col2:
            st.metric("🚫 Withdrawn", withdrawn_count)
        with col3:
            st.metric("✅ Active", active_count)
        
        if withdrawn_count > 0:
            withdrawal_percentage = (withdrawn_count / len(st.session_state.submissions)) * 100
            st.warning(f"📊 Withdrawal Rate: {withdrawal_percentage:.1f}%")
        
        # Rating Improvement Analysis
        st.subheader("📈 Rating Improvement Analysis")
        
        # Add threshold slider
        threshold = st.slider("Rating Threshold", min_value=1.0, max_value=6.0, value=4.0, step=0.1)
        
        improved_papers = []
        declined_papers = []
        
        for sub in st.session_state.submissions:
            if sub.avg_rating > 0 and sub.avg_final_rating > 0:
                if sub.avg_rating <= threshold and sub.avg_final_rating > threshold:
                    improved_papers.append(sub)
                elif sub.avg_rating > threshold and sub.avg_final_rating <= threshold:
                    declined_papers.append(sub)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(f"📈 Below {threshold} → Above {threshold}", len(improved_papers))
        with col2:
            st.metric(f"📉 Above {threshold} → Below {threshold}", len(declined_papers))
        with col3:
            papers_with_ratings = len([s for s in st.session_state.submissions if s.avg_rating > 0 and s.avg_final_rating > 0])
            improvement_rate = (len(improved_papers) / papers_with_ratings) * 100 if papers_with_ratings > 0 else 0
            st.metric("📊 Improvement Rate", f"{improvement_rate:.1f}%")
        with col4:
            decline_rate = (len(declined_papers) / papers_with_ratings) * 100 if papers_with_ratings > 0 else 0
            st.metric("📉 Decline Rate", f"{decline_rate:.1f}%")
        
        # Show detailed lists if there are papers
        if improved_papers:
            with st.expander(f"📈 Papers that improved from ≤{threshold} to >{threshold}", expanded=False):
                for sub in improved_papers:
                    st.write(f"• {sub.sub_id}: {sub.avg_rating:.2f} → {sub.avg_final_rating:.2f} (+{sub.avg_final_rating - sub.avg_rating:.2f})")
        
        if declined_papers:
            with st.expander(f"📉 Papers that declined from >{threshold} to ≤{threshold}", expanded=False):
                for sub in declined_papers:
                    st.write(f"• {sub.sub_id}: {sub.avg_rating:.2f} → {sub.avg_final_rating:.2f} ({sub.avg_final_rating - sub.avg_rating:.2f})")

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
