# AC Conference Helper

A modern Python tool for Area Chairs to analyze conference submissions and reviews from OpenReview. Built with uv for fast, reliable dependency management.

## 🚀 Quick Start with uv

### Prerequisites
- [uv](https://docs.astral.sh/uv/) - Modern Python package installer
- Python 3.10+ (uv will manage this for you)

### Installation
```bash
# Clone and install dependencies
git clone <repository-url>
cd conference_helper
uv sync

# That's it! uv creates a virtual environment and installs everything.
```

## 📋 Setup Guide

### Step 1: Configure Credentials
Create a `.env` file with your configuration:

```bash
# OpenReview Credentials
USERNAME=your-email@example.com
PASSWORD=your-password

# Ollama Configuration (for LLM features)
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen3:8b
OLLAMA_TIMEOUT=60
OLLAMA_MAX_RETRIES=3

# Cache Configuration
CACHE_DIR=cache
CACHE_FILE_PREFIX=submissions_
```

**⚠️ Security Note:** 
- Never commit the `.env` file to version control
- The `.env` file is already included in `.gitignore`
- Keep your credentials secure and private

**Configuration Details:**
- **USERNAME/PASSWORD**: Your OpenReview login credentials
- **OLLAMA_HOST**: Ollama server URL for local LLM (default: http://localhost:11434)
- **OLLAMA_MODEL**: LLM model to use for analysis (default: qwen3:8b)
- **OLLAMA_TIMEOUT**: Request timeout in seconds (default: 60)
- **OLLAMA_MAX_RETRIES**: Maximum retry attempts (default: 3)
- **CACHE_DIR**: Directory for cached submission data (default: cache)
- **CACHE_FILE_PREFIX**: Prefix for cache files (default: submissions_)

### Step 2: Fetch Conference Data
```bash
# Basic usage
uv run python run.py --conf cvpr_2026

# Skip reviews for faster loading
uv run python run.py --conf cvpr_2026 --skip-reviews

# Save results to CSV
uv run python run.py --conf cvpr_2026 --output results.csv

# Simulate with dummy data (for testing)
uv run python run.py --simulate
```

#### Available Arguments
- `--conf {cvpr_2026}` - Conference to fetch data from
- `--skip-reviews` - Skip fetching reviews for faster loading
- `--output FILE` - Save results to CSV file
- `--format {grid,pipe,simple,github}` - Table display format (default: grid)
- `--no-save-cache` - Don't save submissions to cache
- `--clear-cache` - Clear all cached submission files
- `--analyze {summary,meta_review,improvement_suggestions}` - Run LLM analysis
- `--analysis-output FILE` - Save LLM analyses to file
- `--chat` - Launch Streamlit web interface
- `--log-level {DEBUG,INFO,WARNING,ERROR}` - Set logging level
- `--simulate` - Use dummy data for testing

**Note:** The application runs in headless mode by default (no browser window visible).

### Step 3: Launch Web Interface (Optional)

**Method 1: Direct Streamlit launch**
```bash
uv run streamlit run streamlit_chat.py
```

**Method 2: Using run.py chat mode**
```bash
uv run python run.py --chat
```

Both methods will launch the same Streamlit web interface at `http://localhost:8501`.

## 🌐 Web Interface

The modern web interface provides:
- **📋 Interactive Submission Browser** - Filter, sort, and explore submissions
- **💬 AI-Powered Chat** - Ask questions about submissions with LLM assistance  
- **📈 Analytics Dashboard** - Visualizations and statistics
- **🚀 Quick Actions** - One-click analysis (summary, recommendations, improvements)
- **📱 Responsive Design** - Works on desktop and mobile devices

Access at `http://localhost:8501` after launching.

## 🙏 Acknowledgments

This project was inspired by and builds upon the excellent work done in:
- **[openreview_helper](https://github.com/arunmallya/openreview_helper)** by Arun Mallya

The original project provided the foundation and inspiration for this enhanced version with additional features like:
- Modern uv-based dependency management
- Streamlit web interface
- Enhanced LLM integration
- Improved caching and configuration options

Thank you to Arun Mallya and contributors for the original implementation!

