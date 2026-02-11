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

## 📁 Project Structure

```
conference_helper/
├── src/ac_conference_helper/     # Main package
│   ├── client/                  # External API clients
│   │   └── openreview_client.py
│   ├── config/                  # Configuration modules
│   │   ├── conference_config.py
│   │   └── constants.py
│   ├── core/                    # Core functionality
│   │   ├── models.py            # Data models with enum-based status system
│   │   ├── display.py           # Display utilities with Plotly visualizations
│   │   ├── chat_system.py       # AI-powered chat interface
│   │   ├── submission_analyzer.py
│   │   └── llm_integration.py
│   ├── ui/                      # User interfaces
│   │   └── streamlit_chat.py    # Enhanced web interface
│   └── utils/                   # Utilities
│       ├── utils.py
│       └── logging_config.py
├── scripts/                     # Executable scripts
│   ├── run.py                  # Main CLI script
│   └── run_tests.py            # Test runner
├── tests/                       # Test files
├── docs/                        # Documentation
├── cache/                       # Cached data
├── pyproject.toml              # Project configuration
└── README.md                   # This file
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
uv run python scripts/run.py --conf cvpr_2026

# Skip reviews for faster loading
uv run python scripts/run.py --conf cvpr_2026 --skip-reviews

# Save results to CSV
uv run python scripts/run.py --conf cvpr_2026 --output results.csv

# Simulate with dummy data (for testing)
uv run python scripts/run.py --simulate
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
uv run streamlit run src/ac_conference_helper/ui/streamlit_chat.py
```

**Method 2: Using run.py chat mode**
```bash
uv run python scripts/run.py --chat
```

Both methods will launch the same Streamlit web interface at `http://localhost:8501`. The `--chat` flag automatically launches the Streamlit interface from the correct package location.

## ✨ Key Features

- **🎯 Smart Status Management**: Enum-based system with visual indicators (🚫/📋/✅)
- **📊 Professional Charts**: Interactive Plotly visualizations with proper axis labels
- **📈 Advanced Analytics**: Rating distribution, meta-review analysis, improvement tracking
- **🤖 AI Integration**: LLM-powered summaries, meta-reviews, and chat interface
- **🌐 Modern Web UI**: Interactive dashboard with filtering and mobile-responsive design
- **📝 Complete Review Display**: Expandable sections with full reviewer details
- **🔗 OpenReview Integration**: Direct links and real-time data fetching

### 🌐 Modern Web Interface
Access at `http://localhost:8501` after launching.

**Features:**
- Interactive submission browser with advanced filtering
- AI-powered chat for paper analysis
- Professional analytics dashboard with visualizations
- Detailed review content display with expandable sections
- One-click analysis actions
- Mobile-responsive design
- Real-time status updates

## 🙏 Acknowledgments

This project was inspired by and builds upon the excellent work done in:
- **[openreview_helper](https://github.com/arunmallya/openreview_helper)** by Arun Mallya

### Enhanced Features in This Version
- **Modern uv-based dependency management**
- **Enum-based status system with type safety**
- **Plotly Express visualizations with proper axis labels**
- **Enhanced Streamlit web interface**
- **Professional analytics dashboard**
- **Improved LLM integration**
- **Withdrawal and desk rejection detection**
- **Interactive rating analysis with improvement tracking**
- **Mobile-responsive design**
- **Better error handling and logging**

Thank you to Arun Mallya and contributors for the original implementation!
