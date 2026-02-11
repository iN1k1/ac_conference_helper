"""Streamlit web interface for conference submission chat system."""

import streamlit as st
import pandas as pd
from dotenv import load_dotenv
import plotly.express as px

# Load environment variables from .env file
load_dotenv()

from ac_conference_helper.core.submission_analyzer import SubmissionAnalyzer
from ac_conference_helper.config.constants import AVAILABLE_ANALYSES
from ac_conference_helper.core.llm_integration import create_llm_client_from_env
from ac_conference_helper.core.chat_system import SubmissionChatSystem
from ac_conference_helper.core.display import submissions_to_dataframe_streamlit
from ac_conference_helper.core.models import SubmissionStatus

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
.strikethrough-row {
    text-decoration: line-through !important;
    opacity: 0.6 !important;
}
.compact-metric {
    font-size: 1.1rem;
}
.compact-metric-label {
    font-size: 1rem;
    font-weight: normal;
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
    st.title("Conference Submission Analytics")
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
        
        # Meta-review decision statistics
        st.subheader("📋 Meta-Review Analysis")
        
        # Count meta-review decisions for active papers only (exclude withdrawn and desk rejected)
        active_submissions = [sub for sub in st.session_state.submissions if sub.status == SubmissionStatus.ACTIVE]
        
        prelim_accept = 0
        prelim_reject = 0
        prelim_discussion = 0
        prelim_missing = 0
        
        final_accept = 0
        final_reject = 0
        final_discussion = 0
        final_missing = 0
        
        for sub in active_submissions:
            if hasattr(sub, "meta_review") and sub.meta_review:
                # Preliminary decisions
                if sub.meta_review.preliminary_decision:
                    prelim_lower = sub.meta_review.preliminary_decision.lower()
                    if "accept" in prelim_lower:
                        prelim_accept += 1
                    elif "reject" in prelim_lower:
                        prelim_reject += 1
                    elif "discussion" in prelim_lower:
                        prelim_discussion += 1
                else:
                    prelim_missing += 1
                
                # Final decisions
                if sub.meta_review.final_decision:
                    final_lower = sub.meta_review.final_decision.lower()
                    if "accept" in final_lower:
                        final_accept += 1
                    elif "reject" in final_lower:
                        final_reject += 1
                    elif "discussion" in final_lower:
                        final_discussion += 1
                else:
                    final_missing += 1
            else:
                prelim_missing += 1
                final_missing += 1
        
        total_active = len(active_submissions)
        
        # Display preliminary stats
        st.write('<div class="compact-metric-label"><strong>Preliminary Decisions (Active Papers Only):</strong></div>', unsafe_allow_html=True)
        col_prelim1, col_prelim2, col_prelim3 = st.columns(3)
        with col_prelim1:
            st.markdown(f'<div class="compact-metric">Accept<br><strong>{prelim_accept/total_active*100:.1f}%</strong><small>({prelim_accept})</small></div>', unsafe_allow_html=True)
        with col_prelim2:
            st.markdown(f'<div class="compact-metric">Reject<br><strong>{prelim_reject/total_active*100:.1f}%</strong><small>({prelim_reject})</small></div>', unsafe_allow_html=True)
        with col_prelim3:
            st.markdown(f'<div class="compact-metric">Discussion<br><strong>{prelim_discussion/total_active*100:.1f}%</strong><small>({prelim_discussion})</small></div>', unsafe_allow_html=True)
        
        # Display final stats
        st.write('<div class="compact-metric-label"><strong>Final Decisions (Active Papers Only):</strong></div>', unsafe_allow_html=True)
        col_final1, col_final2, col_final3 = st.columns(3)
        with col_final1:
            st.markdown(f'<div class="compact-metric">Accept<br><strong>{final_accept/total_active*100:.1f}%</strong><small>({final_accept})</small></div>', unsafe_allow_html=True)
        with col_final2:
            st.markdown(f'<div class="compact-metric">Reject<br><strong>{final_reject/total_active*100:.1f}%</strong><small>({final_reject})</small></div>', unsafe_allow_html=True)
        with col_final3:
            st.markdown(f'<div class="compact-metric">Discussion<br><strong>{final_discussion/total_active*100:.1f}%</strong><small>({final_discussion})</small></div>', unsafe_allow_html=True)
        
        # Missing meta-reviews
        st.write('<div class="compact-metric-label"><strong>Papers Missing Meta-Reviews:</strong></div>', unsafe_allow_html=True)
        col_missing1, col_missing2 = st.columns(2)
        with col_missing1:
            st.markdown(f'<div class="compact-metric"><small>preliminary</small><br>{prelim_missing}</div>', unsafe_allow_html=True)
        with col_missing2:
            st.markdown(f'<div class="compact-metric"><small>final</small><br>{final_missing}</div>', unsafe_allow_html=True)

        # Status statistics
        withdrawn_count = sum(1 for sub in st.session_state.submissions if sub.status == SubmissionStatus.WITHDRAWN)
        desk_rejected_count = sum(1 for sub in st.session_state.submissions if sub.status == SubmissionStatus.DESK_REJECTED)
        active_count = sum(1 for sub in st.session_state.submissions if sub.status == SubmissionStatus.ACTIVE)
        
        # Calculate percentages
        total_submissions = len(st.session_state.submissions)
        withdrawn_pct = (withdrawn_count / total_submissions * 100) if total_submissions > 0 else 0
        desk_rejected_pct = (desk_rejected_count / total_submissions * 100) if total_submissions > 0 else 0
        active_pct = (active_count / total_submissions * 100) if total_submissions > 0 else 0
        
        st.write('<div class="compact-metric-label"><strong>Status Distribution:</strong></div>', unsafe_allow_html=True)
        col_status1, col_status2, col_status3 = st.columns(3)
        with col_status1:
            st.markdown(f'<div class="compact-metric">🚫<br><strong>{withdrawn_pct:.1f}%</strong><small>({withdrawn_count})</small></div>', unsafe_allow_html=True)
        with col_status2:
            st.markdown(f'<div class="compact-metric">📋<br><strong>{desk_rejected_pct:.1f}%</strong><small>({desk_rejected_count})</small></div>', unsafe_allow_html=True)
        with col_status3:
            st.markdown(f'<div class="compact-metric">✅<br><strong>{active_pct:.1f}%</strong><small>({active_count})</small></div>', unsafe_allow_html=True)

        # Filter options
        st.subheader("🔍 Filters")

        # Rating filter
        min_rating = st.slider("Minimum Average Rating", 0.0, 6.0, 0.0, 0.1)
        min_reviews = st.slider("Minimum Number of Reviews", 0, 6, 0)

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
        df = submissions_to_dataframe_streamlit(filtered_submissions, include_urls=False)
        
        # Apply strikethrough styling using pandas style
        def highlight_withdrawn(row):
            styles = [''] * len(row)
            status = row.get('status', '')
            if 'WITHDRAWN' in status or 'DESK REJECTED' in status:
                for i, col in enumerate(row.index):
                    styles[i] = 'text-decoration: line-through; opacity: 0.6; color: #666;'
            return styles
        
        # Apply styling and display
        styled_df = df.style.apply(highlight_withdrawn, axis=1)
        
        # Display as interactive table with row selection
        event = st.dataframe(
            styled_df,
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

            # Display submission info in two columns
            col1, col2 = st.columns([3, 1])  # Give more space to col1, ensure col2 is visible
            
            with col1:
                st.subheader(f"📄 {current_submission.title} ({current_submission.sub_id})")

                # Compact status info
                col1a, col1b, col1c, col1d = st.columns(4)
                with col1a:
                    st.metric("Initial Avg Rating", f"{current_submission.avg_rating:.2f}")
                with col1b:
                    st.metric("Final Avg Rating", f"{current_submission.avg_final_rating:.2f}")
                with col1c:
                    st.metric("Reviews", len(current_submission.reviews))
                with col1d:
                    if current_submission.status == SubmissionStatus.DESK_REJECTED:
                        st.error("📋 Desk Rejected")
                    elif current_submission.status == SubmissionStatus.WITHDRAWN:
                        st.error("🚫 Withdrawn")
                    else:
                        st.success("✅ Active")

                # Add meta-review information if available
                if hasattr(current_submission, "meta_review") and current_submission.meta_review:
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
                                    if review.numeric_rating_preliminary_recommendation != -1
                                    else None
                                ),
                                "Final Rating": (
                                    review.numeric_rating_final_reccomendation
                                    if review.numeric_rating_final_reccomendation != -1
                                    else None
                                ),
                                "Confidence": (
                                    review.confidence_level if review.confidence_level else None
                                ),
                                "Preliminary Recommendation": review.preliminary_recommendation or "N/A",
                                "Final Recommendation": review.final_recommendation or "N/A",
                            }
                        )

                    reviewers_df = pd.DataFrame(reviewer_data)
                    st.dataframe(reviewers_df, width="stretch", hide_index=True)
                    
                    # Add review content sections
                    st.subheader("📝 Review Content")
                    for i, review in enumerate(current_submission.reviews):
                        reviewer_name = review.reviewer_id or f"Reviewer_{i+1}"
                        with st.expander(f"📄 {reviewer_name} - Review Details", expanded=False):
                            col1a, col2a = st.columns(2)
                            
                            with col1a:
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
                            
                            with col2a:
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
                
                # PDF and Rebuttal links
                if hasattr(current_submission, "pdf_url") and current_submission.pdf_url:
                    st.markdown(f'<a href="{current_submission.pdf_url}" target="_blank"><button style="background-color:#28a745;color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;margin:2px 0;">📕 PDF</button></a>', unsafe_allow_html=True)
                if hasattr(current_submission, "rebuttal_url") and current_submission.rebuttal_url:
                    st.markdown(f'<a href="{current_submission.rebuttal_url}" target="_blank"><button style="background-color:#17a2b8;color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;margin:2px 0;">📄 Rebuttal</button></a>', unsafe_allow_html=True)

                if current_submission.url:
                    st.markdown(f'<a href="{current_submission.url}" target="_blank"><button style="background-color:#0066cc;color:white;border:none;padding:6px 12px;border-radius:4px;cursor:pointer;margin:2px 0;">🔗 OpenReview</button></a>', unsafe_allow_html=True)
                else:
                    st.warning("No OpenReview link available")

                if st.button("📝 Get Summary", key="summary"):
                    with st.spinner("Analyzing..."):
                        analyzer = get_analyzer()
                        enhanced = analyzer.analyze_submission(
                            current_submission, [AVAILABLE_ANALYSES[0]]  # summary
                        )
                        if enhanced.llm_analyses:
                            st.success("Summary generated!")
                            st.session_state.last_summary = enhanced.llm_analyses[0].result

                if st.button("📋 Get Meta Review", key="meta_review"):
                    with st.spinner("Analyzing..."):
                        analyzer = get_analyzer()
                        enhanced = analyzer.analyze_submission(
                            current_submission, [AVAILABLE_ANALYSES[1]]  # meta_review
                        )
                        if enhanced.llm_analyses:
                            st.success("Meta review generated!")
                            st.session_state.last_meta_review = enhanced.llm_analyses[0].result

                if st.button("💡 Get Improvements", key="improvements"):
                    with st.spinner("Analyzing..."):
                        analyzer = get_analyzer()
                        enhanced = analyzer.analyze_submission(
                            current_submission, [AVAILABLE_ANALYSES[2]]  # improvement_suggestions
                        )
                        if enhanced.llm_analyses:
                            st.success("Improvement suggestions generated!")
                            st.session_state.last_improvements = enhanced.llm_analyses[0].result


            # Chat interface below the submission info
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
            if all_ratings:
                rating_counts = pd.Series(all_ratings).value_counts().sort_index()
                
                # Create a more detailed chart with axis labels
                fig = px.bar(
                    x=rating_counts.index, 
                    y=rating_counts.values,
                    labels={"x": "Review Score", "y": "Review Count"},
                    title="Preliminary Ratings Distribution"
                )
                fig.update_layout(showlegend=False, height=300)
                st.plotly_chart(fig, width='stretch')
            else:
                st.write("No ratings data")

        with col2:
            if all_final_ratings:
                final_rating_counts = (
                    pd.Series(all_final_ratings).value_counts().sort_index()
                )
                
                # Create a more detailed chart with axis labels
                fig = px.bar(
                    x=final_rating_counts.index, 
                    y=final_rating_counts.values,
                    labels={"x": "Review Score", "y": "Review Count"},
                    title="Final Ratings Distribution"
                )
                fig.update_layout(showlegend=False, height=300)
                st.plotly_chart(fig, width='stretch')
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
            meta_prelim_data = {
                "Accept": prelim_accept,
                "Reject": prelim_reject,
                "Discussion": prelim_discussion
            }
            
            # Create Plotly chart with axis labels
            fig = px.bar(
                x=list(meta_prelim_data.keys()),
                y=list(meta_prelim_data.values()),
                labels={"x": "Decision Type", "y": "Count"},
                title="Preliminary Meta-Review Decisions"
            )
            fig.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig, width='stretch')
            
            # Calculate percentages
            total_prelim = prelim_accept + prelim_reject + prelim_discussion
            st.subheader(f"Active papers:")
            if total_prelim > 0:
                st.write(f"✅ Accept: {prelim_accept} ({prelim_accept/total_prelim*100:.1f}%)")
                st.write(f"❌ Reject: {prelim_reject} ({prelim_reject/total_prelim*100:.1f}%)")
                st.write(f"🔄 Discussion: {prelim_discussion} ({prelim_discussion/total_prelim*100:.1f}%)")
            else:
                st.write("No preliminary meta-review decisions found")
        
        with col2:
            meta_final_data = {
                "Accept": final_accept,
                "Reject": final_reject,
                "Discussion": final_discussion
            }
            
            # Create Plotly chart with axis labels
            fig = px.bar(
                x=list(meta_final_data.keys()),
                y=list(meta_final_data.values()),
                labels={"x": "Decision Type", "y": "Count"},
                title="Final Meta-Review Decisions"
            )
            fig.update_layout(showlegend=False, height=300)
            st.plotly_chart(fig, width='stretch')
            
            # Calculate percentages
            total_final = final_accept + final_reject + final_discussion
            if total_final > 0:
                st.write(f"✅ Accept: {final_accept} ({final_accept/total_final*100:.1f}%)")
                st.write(f"❌ Reject: {final_reject} ({final_reject/total_final*100:.1f}%)")
                st.write(f"🔄 Discussion: {final_discussion} ({final_discussion/total_final*100:.1f}%)")
            else:
                st.write("No final meta-review decisions found")

        # Status Statistics
        st.subheader("Status Analysis")
        
        withdrawn_count = sum(1 for sub in st.session_state.submissions if sub.withdrawn)
        desk_rejected_count = sum(1 for sub in st.session_state.submissions if sub.desk_rejected)
        active_count = total_submissions - withdrawn_count -  desk_rejected_count
        withdrawal_percentage = (withdrawn_count / total_submissions) * 100
        desk_rejected_percentage = (desk_rejected_count / total_submissions) * 100

        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Papers", total_submissions)
        with col2:
            st.metric("🚫 Withdrawn", f'{withdrawal_percentage:.2f}% ({withdrawn_count})')
        with col3:
            st.metric("📋 Desk Rejected", f'{desk_rejected_percentage:.2f}% ({desk_rejected_count})')
        with col4:
            st.metric("✅ Active", f'{(active_count/total_submissions)*100:.2f}% ({active_count})')
        
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
