import os
import json
import re

from flask import Flask, render_template, request
from dotenv import load_dotenv
from groq import Groq

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)

# Read Groq API key
api_key = os.getenv("GROQ_API_KEY")

# Connect to Groq
client = Groq(api_key=api_key) if api_key else None

# Groq model
MODEL = "openai/gpt-oss-120b"


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/analyze", methods=["POST"])
def analyze():

    language = request.form.get("language", "").strip()
    code = request.form.get("code", "").strip()

    # Validate input
    if not code:
        return render_template(
            "index.html",
            error="Please enter your code or error message."
        )

    if not client:
        return render_template(
            "index.html",
            error="Groq API key is missing. Please configure your .env file."
        )

    if len(code) > 12000:
        return render_template(
            "index.html",
            error="Your input is too long. Please enter a shorter code sample."
        )

    prompt = f"""
    You are DebugEase, an expert programming assistant
    who explains errors to beginners in simple English.

    Programming language: {language}

    User's code or error message:
    {code}

    Analyse the input and return ONLY a valid JSON object
    with these exact keys:

    {{
        "explanation": "Explain the error in simple English",
        "reason": "Explain why the error occurred",
        "solution": "Give clear step-by-step instructions to fix it",
        "corrected_code": "Provide the corrected code",
        "tips": "Give useful tips to prevent this error"
    }}

    If the input has no error, explain that and provide
    helpful feedback. Do not invent errors.
    """

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful programming error explainer. Always return valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.3,
            max_completion_tokens=2000,
            response_format={"type": "json_object"}
        )

        ai_response = response.choices[0].message.content

        # Remove accidental Markdown code fences
        ai_response = re.sub(
            r"^```(?:json)?\s*|\s*```$",
            "",
            ai_response.strip(),
            flags=re.IGNORECASE
        )

        result = json.loads(ai_response)

        # Check that all required fields exist
        required_fields = [
            "explanation",
            "reason",
            "solution",
            "corrected_code",
            "tips"
        ]

        for field in required_fields:
            if field not in result:
                result[field] = "No information provided."

        return render_template(
            "index.html",
            result=result
        )

    except json.JSONDecodeError:
        return render_template(
            "index.html",
            error="The AI returned an unexpected response. Please try again."
        )

    except Exception as e:
        print("Groq API Error:", str(e))

        return render_template(
            "index.html",
            error="Unable to analyse your code right now. Please check your API key and internet connection."
        )


if __name__ == "__main__":
    app.run(debug=True)