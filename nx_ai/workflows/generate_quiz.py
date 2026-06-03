import os
import json

from nx_ai.openai_service.openai_api import generate_quiz_with_gpt
from nx_ai.github_service.github_api import create_pull_request_on_github


def create_quiz_folder():
    if not os.path.exists("nx_ai/quizzes_data"):
        os.makedirs("nx_ai/quizzes_data")


def generate_quiz_beta(url: str, filename: str, simulate):
    generated_quiz = generate_quiz_with_gpt(url, simulate)

    create_quiz_folder()
    with open(f"nx_ai/quizzes_data/{filename}.json", "w", encoding="utf-8") as file:
        json.dump({"data": generated_quiz.data}, file, indent=4, ensure_ascii=False)

    # In simulate mode we generate the file locally but skip opening a PR.
    pr_url = None
    if not simulate:
        pr_url = create_pull_request_on_github(filename=filename, type="quiz")

    return {
        "filename": filename,
        "questions": generated_quiz.data,
        "pr_url": pr_url
    }
