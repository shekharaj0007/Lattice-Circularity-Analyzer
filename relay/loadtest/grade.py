"""Lightweight grading helpers for the ≥15 question quality set."""

from __future__ import annotations

from relay.loadtest.questions import EvalQuestion
from relay.pipeline.types import AnswerGrade, PipelineResult


def grade_result(q: EvalQuestion, result: PipelineResult) -> AnswerGrade:
    text = (result.answer_text or "").lower()
    refused = result.refused or "the papers do not say" in text or "try later" in text or "try again later" in text

    if q.expect == "unanswerable":
        if refused and "try later" not in text:
            return AnswerGrade.REFUSED_CORRECTLY
        if refused and "try later" in text:
            # capacity refuse — not a quality judgment about the library
            return AnswerGrade.UNGRADED
        return AnswerGrade.REFUSED_WRONGLY if not refused else AnswerGrade.REFUSED_CORRECTLY

    # answerable
    if refused and "try later" in text:
        return AnswerGrade.UNGRADED
    if refused:
        return AnswerGrade.REFUSED_WRONGLY
    # crude: must have a citation-looking token or extractive quote marker
    if "::c" in text or "extractive answer" in text or "[" in text:
        return AnswerGrade.CORRECT
    return AnswerGrade.WRONG


def apply_grades(questions: list[EvalQuestion], results: list[PipelineResult]) -> None:
    for q, r in zip(questions, results):
        r.answer_grade = grade_result(q, r)
