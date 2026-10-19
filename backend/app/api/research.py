"""The free check as the research instrument (Research guide): one short question per result."""

import hashlib

from pydantic import BaseModel


class ResearchQuestion(BaseModel):
    id: str
    text: str
    options: list[str]


QUESTIONS = [
    ResearchQuestion(
        id="segment",
        text="Who are you posting this job for?",
        options=["My own company", "Clients (recruiting or staffing agency)", "Clients (HR consultant)", "Other"],
    ),
    ResearchQuestion(
        id="hr_system",
        text="Which HR or recruiting system do you post jobs from?",
        options=["BambooHR", "Workable", "Employment Hero", "ADP", "Workday", "Greenhouse", "Lever", "Other", "None"],
    ),
    ResearchQuestion(
        id="postings_per_month",
        text="How many job postings do you publish in a typical month?",
        options=["1–2", "3–10", "11–50", "More than 50"],
    ),
]
BY_ID = {question.id: question for question in QUESTIONS}


def question_for(check_id: str) -> ResearchQuestion:
    """The same check always gets the same question; checks spread evenly across the questions."""
    digest = hashlib.sha256(check_id.encode()).digest()
    return QUESTIONS[digest[0] % len(QUESTIONS)]
