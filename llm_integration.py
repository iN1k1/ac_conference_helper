"""LLM integration module using official Ollama Python library."""

import json
import os
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import time
from dotenv import load_dotenv

from constants import AVAILABLE_ANALYSES

# Load environment variables
load_dotenv()

try:
    from ollama import Client, ResponseError
except ImportError:
    print(
        "Error: ollama-python library not installed. Install with: pip install ollama"
    )
    exit(1)


@dataclass
class LLMConfig:
    """Configuration for LLM endpoint."""

    host: str = "http://localhost:11434"
    model: str = "qwen3:8b"
    timeout: int = 60
    max_retries: int = 3


class OllamaClient:
    """Client for interacting with Ollama LLM endpoint using official library."""

    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize Ollama client."""
        self.config = config or LLMConfig()
        self.client = Client(host=self.config.host)

        # Ensure model is available
        self._ensure_model_exists()

    def _ensure_model_exists(self):
        """Check if model exists and pull if it doesn't."""
        try:
            models = self.client.list()
            available_models = [
                model["model"].split(":")[0] for model in models.get("models", [])
            ]
            model_name = self.config.model.split(":")[0]  # Remove tag if present

            if model_name not in available_models:
                print(
                    f"📥 Model '{self.config.model}' not found. Pulling from Ollama..."
                )
                try:
                    self.client.pull(self.config.model)
                    print(f"✅ Successfully pulled model '{self.config.model}'")
                except Exception as e:
                    print(f"❌ Failed to pull model '{self.config.model}': {e}")
                    print("💡 Please run: ollama pull", self.config.model)
                    print("⚠️  Continuing with potentially unavailable model...")
        except Exception as e:
            print(f"⚠️  Could not check available models: {e}")
            print("⚠️  Continuing without model verification...")

    def test_connection(self) -> bool:
        """Test if Ollama endpoint is accessible."""
        try:
            self.client.list()
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False

    def generate_response(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> str:
        """Generate response from LLM."""
        for attempt in range(self.config.max_retries):
            try:
                options = {}
                if system_prompt:
                    response = self.client.chat(
                        model=self.config.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": prompt},
                        ],
                        options=options,
                    )
                else:
                    response = self.client.chat(
                        model=self.config.model,
                        messages=[{"role": "user", "content": prompt}],
                        options=options,
                    )

                return response["message"]["content"]

            except ResponseError as e:
                print(f"Ollama API error: {e}")
                if "model" in str(e).lower():
                    print(f"Model '{self.config.model}' not found. Available models:")
                    try:
                        models = self.client.list()
                        for model in models.get("models", []):
                            print(f"  - {model['name']}")
                    except:
                        pass
                break
            except Exception as e:
                print(f"LLM request failed (attempt {attempt + 1}): {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2**attempt)  # Exponential backoff

        return f"Error: Failed to get response from LLM after {self.config.max_retries} attempts"

    def analyze_submission_reviews(
        self, submission_title: str, reviews: List[str], analysis_type: str = "summary"
    ) -> str:
        """Analyze submission reviews using LLM."""

        assert analysis_type in AVAILABLE_ANALYSES

        # Prepare reviews text
        reviews_text = "\n\n".join(
            [f"Review {i+1}:\n{review}" for i, review in enumerate(reviews)]
        )

        system_prompts = {
            "summary": (
                "You are assisting a meta-reviewer by analyzing the provided peer reviews of a research paper. "
                "Produce a clear, structured summary that: "
                "- Lists the main strengths mentioned across reviews "
                "- Lists the main weaknesses and concerns "
                "- Highlights recurring themes or repeated points "
                "- Notes major differences in emphasis between reviewers "
                "- Reflects the overall tone of the reviews without adding new opinions "
                "Use neutral, precise academic language and do not introduce your own evaluation."
            ),
            "meta_review": (
                "You are assisting a human meta-reviewer by analyzing the provided reviews. "
                "Your task is to extract and organize the reviewers’ viewpoints to support decision-making. "
                "Produce a structured analysis that: "
                "- Identifies points of agreement among reviewers "
                "- Identifies points of disagreement or conflicting assessments "
                "- Summarizes how each reviewer weighs strengths versus weaknesses "
                "- Highlights major uncertainties, ambiguities, or reviewer-specific concerns "
                "- Notes whether critiques focus on methodology, novelty, clarity, experiments, or presentation "
                "Do not provide an accept/reject recommendation and do not add new judgments. "
                "Focus only on faithfully representing and organizing the reviewers’ perspectives."
            ),
            "improvement_suggestions": (
                "You are assisting the authors by distilling reviewer feedback into actionable revision guidance. "
                "Based only on the provided reviews, generate a list of concrete improvement suggestions. "
                "For each suggestion: "
                "- State which reviewer concern it addresses "
                "- Summarize the underlying issue "
                "- Propose a specific action the authors could take "
                "- Indicate whether the change appears minor, moderate, or major based on reviewer emphasis "
                "Do not invent new criticisms or suggestions not supported by the reviews."
            ),
        }

        system_prompt = system_prompts.get(analysis_type, system_prompts["summary"])

        user_prompt = f"""
Paper Title: {submission_title}

Reviews:
{reviews_text}

Please provide your analysis based on the reviews above.
"""

        return self.generate_response(user_prompt, system_prompt)

    def chat_about_submission(
        self,
        submission_title: str,
        reviews: List[str],
        user_question: str,
        chat_history: Optional[List[Dict]] = None,
    ) -> str:
        """Chat with LLM about a specific submission."""

        reviews_text = "\n\n".join(
            [f"Review {i+1}:\n{review}" for i, review in enumerate(reviews)]
        )

        system_prompt = f"""You are an expert research assistant helping analyze a paper submission titled "{submission_title}". 

The paper has received the following reviews:
{reviews_text}

Answer the user's questions about this paper based on the provided reviews. Be helpful, accurate, and provide specific insights from the review content."""

        # Build conversation messages
        messages = [{"role": "system", "content": system_prompt}]

        # Add chat history
        if chat_history:
            for msg in chat_history[-10:]:  # Keep last 10 messages for context
                if msg["role"] in ["user", "assistant"]:
                    messages.append({"role": msg["role"], "content": msg["content"]})

        # Add current question
        messages.append({"role": "user", "content": user_question})

        try:
            response = self.client.chat(model=self.config.model, messages=messages)
            return response["message"]["content"]
        except Exception as e:
            return f"Error generating response: {e}"


def create_llm_client_from_env() -> OllamaClient:
    """Create LLM client from environment variables."""
    config = LLMConfig(
        host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        model=os.getenv("OLLAMA_MODEL", "qwen3:8b"),
        timeout=int(os.getenv("OLLAMA_TIMEOUT", "60")),
        max_retries=int(os.getenv("OLLAMA_MAX_RETRIES", "3")),
    )
    return OllamaClient(config)
