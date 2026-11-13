"""Lightweight grading helpers for the ≥15 question quality set."""

from __future__ import annotations

from relay.loadtest.questions import EvalQuestion
from relay.pipeline.types import AnswerGrade, PipelineResult


def _is_capacity_refuse(text: str) -> bool:
    return (
        "try later" in text
        or "try again later" in text
        or "budget/capacity" in text
        or "budget is tight" in text and "extractive answer" in text
    )


def grade_result(q: EvalQuestion, result: PipelineResult) -> AnswerGrade:
    text = (result.answer_text or "").lower()
    capacity = _is_capacity_refuse(text)
    refused = result.refused or "the papers do not say" in text or capacity

    if q.expect == "unanswerable":
        if capacity:
            return AnswerGrade.UNGRADED
        if refused:
            return AnswerGrade.REFUSED_CORRECTLY
        return AnswerGrade.REFUSED_WRONGLY

    # answerable
    if capacity and result.refused and "extractive answer" not in text:
        return AnswerGrade.UNGRADED
    if refused and "extractive answer" not in text:
        return AnswerGrade.REFUSED_WRONGLY
    # crude: must have a citation-looking token or extractive quote marker
    if "::c" in text or "extractive answer" in text or "[" in text:
        return AnswerGrade.CORRECT
    return AnswerGrade.WRONG


def apply_grades(questions: list[EvalQuestion], results: list[PipelineResult]) -> None:
    for q, r in zip(questions, results):
        r.answer_grade = grade_result(q, r)
