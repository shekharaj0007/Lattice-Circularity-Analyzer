"""End-to-end Relay pipeline with fixed degrade ladder after 80% budget use."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from relay.config import settings
from relay.index.retrieve import hits_are_weak, retrieve
from relay.models.groq_client import GroqClient
from relay.models.standin_client import StandinClient
from relay.pipeline.admission import AdmissionController
from relay.pipeline.budget import BudgetTracker
from relay.pipeline.classify import classify
from relay.pipeline.draft import draft
from relay.pipeline.extractive import extractive_answer, try_later_message
from relay.pipeline.rewrite import rewrite
from relay.pipeline.types import (
    AnswerGrade,
    LadderLevel,
    PipelineResult,
    RequestStatus,
)
from relay.pipeline.verify import local_citation_check, llm_verify


def make_client(source: str) -> Any:
    if source == "real":
        return GroqClient()
    if source == "stand-in":
        return StandinClient()
    raise ValueError(f"unknown source: {source}")


class Orchestrator:
    def __init__(
        self,
        budget: Optional[BudgetTracker] = None,
        source: str = "stand-in",
        retrieval_setting: Optional[str] = None,
    ) -> None:
        self.budget = budget or BudgetTracker()
        self.admission = AdmissionController(self.budget)
        self.source = source
        self.retrieval_setting = retrieval_setting or settings.DEFAULT_RETRIEVAL_SETTING
        self.client = make_client(source)

    def handle(
        self,
        question: str,
        *,
        scenario: str = "ad_hoc",
        request_id: Optional[str] = None,
        force_ladder: Optional[int] = None,
    ) -> PipelineResult:
        rid = request_id or str(uuid.uuid4())
        start_wall = datetime.now(timezone.utc).isoformat()
        t0 = time.perf_counter()
        tokens_in = 0
        tokens_out = 0
        retries = 0
        waiting_ms = 0.0
        retrying_ms = 0.0
        first_token_ms: Optional[float] = None
        ladder = force_ladder if force_ladder is not None else self.budget.current_ladder()

        def finish(
            *,
            status: RequestStatus,
            answer: str,
            refused: bool = False,
            reason: str = "",
            passages=None,
            grade: AnswerGrade = AnswerGrade.UNGRADED,
        ) -> PipelineResult:
            total_ms = (time.perf_counter() - t0) * 1000.0
            working_ms = max(0.0, total_ms - waiting_ms - retrying_ms)
            return PipelineResult(
                request_id=rid,
                question=question,
                scenario=scenario,
                source=self.source,
                start_time=start_wall,
                first_token_ms=first_token_ms,
                total_ms=total_ms,
                status=status,
                retries=retries,
                tokens_in=tokens_in,
                tokens_out=tokens_out,
                retrieval_setting=self.retrieval_setting,
                answer_grade=grade,
                answer_text=answer,
                ladder_level=ladder,
                passages=passages or [],
                refused=refused,
                refuse_reason=reason,
                waiting_ms=waiting_ms,
                working_ms=working_ms,
                retrying_ms=retrying_ms,
                peak_queue_length=self.budget.peak_queue_length,
            )

        # Ladder 5 before admission: honest try-later
        if ladder >= LadderLevel.TRY_LATER:
            msg = try_later_message("budget_low_consumption_ladder")
            return finish(status=RequestStatus.OK, answer=msg, refused=True, reason="try_later")

        decision = self.admission.acquire()
        waiting_ms = decision.waited_ms
        if not decision.admitted:
            msg = try_later_message(decision.reason)
            status = (
                RequestStatus.RATE_LIMITED
                if "budget" in decision.reason or "rate" in decision.reason
                else RequestStatus.TIMEOUT
            )
            return finish(status=status, answer=msg, refused=True, reason=decision.reason)

        try:
            # Re-read ladder after waiting (usage may have climbed)
            if force_ladder is None:
                ladder = self.budget.current_ladder()
            if ladder >= LadderLevel.TRY_LATER:
                msg = try_later_message("budget_exhausted_after_queue")
                return finish(status=RequestStatus.OK, answer=msg, refused=True, reason="try_later")

            # --- classify (small model) ---
            answerable, cls_reason, cls_res = classify(self.client, question)
            tokens_in += cls_res.tokens_in
            tokens_out += cls_res.tokens_out
            if cls_res.status == "rate_limited":
                self.budget.record_rate_limit_hit()
                return finish(
                    status=RequestStatus.RATE_LIMITED,
                    answer=try_later_message("rate_limited_on_classify"),
                    refused=True,
                    reason="rate_limited",
                )
            if not answerable:
                self.budget.record_success(cls_res.tokens_in + cls_res.tokens_out)
                ans = (
                    "The papers do not say. This question does not appear answerable "
                    f"from the three-paper library ({cls_reason})."
                )
                return finish(
                    status=RequestStatus.OK,
                    answer=ans,
                    refused=True,
                    reason="classify_refuse",
                )

            # --- retrieve (tool) + optional one loop ---
            shrink = ladder >= LadderLevel.SHRINK_RETRIEVAL
            passages = retrieve(
                question, setting_name=self.retrieval_setting, shrink=shrink
            )
            if hits_are_weak(passages) and settings.MAX_RETRIEVAL_LOOPS >= 1 and not shrink:
                # one more fetch with expanded query hint
                more = retrieve(
                    question + " method architecture results",
                    setting_name=self.retrieval_setting,
                    shrink=False,
                )
                # merge unique
                seen = {p.passage_id for p in passages}
                for p in more:
                    if p.passage_id not in seen:
                        passages.append(p)
                        seen.add(p.passage_id)

            if not passages:
                self.budget.record_success(tokens_in + tokens_out)
                return finish(
                    status=RequestStatus.OK,
                    answer="The papers do not say.",
                    refused=True,
                    reason="no_passages",
                )

            # --- ladder 4: extractive only ---
            if ladder >= LadderLevel.EXTRACTIVE:
                ans = extractive_answer(question, passages)
                self.budget.record_success(tokens_in + tokens_out)
                # first token ≈ when extractive text is ready (no model stream)
                first_token_ms = (time.perf_counter() - t0) * 1000.0 - waiting_ms
                return finish(
                    status=RequestStatus.OK,
                    answer=ans,
                    passages=passages,
                    reason="extractive",
                )

            # --- draft (large) with limited retries ---
            draft_res = None
            for attempt in range(settings.MAX_RETRIES + 1):
                if attempt:
                    retries += 1
                    backoff = settings.RETRY_BACKOFF_S * (2 ** (attempt - 1))
                    rt0 = time.perf_counter()
                    time.sleep(backoff)
                    retrying_ms += (time.perf_counter() - rt0) * 1000.0
                draft_res = draft(self.client, question, passages)
                tokens_in += draft_res.tokens_in
                tokens_out += draft_res.tokens_out
                if draft_res.first_token_ms is not None and first_token_ms is None:
                    first_token_ms = waiting_ms + draft_res.first_token_ms
                if draft_res.status == "ok":
                    break
                if draft_res.status == "rate_limited":
                    self.budget.record_rate_limit_hit()
                    # Retrying 429 under overload often makes things worse — cap and bail.
                    if attempt >= settings.MAX_RETRIES:
                        return finish(
                            status=RequestStatus.RATE_LIMITED,
                            answer=try_later_message("rate_limited_on_draft"),
                            refused=True,
                            reason="rate_limited",
                            passages=passages,
                        )
                    continue
                if draft_res.status in ("timeout", "error"):
                    if attempt >= settings.MAX_RETRIES:
                        return finish(
                            status=RequestStatus.TIMEOUT
                            if draft_res.status == "timeout"
                            else RequestStatus.ERROR,
                            answer=try_later_message(draft_res.status),
                            refused=True,
                            reason=draft_res.status,
                            passages=passages,
                        )
            assert draft_res is not None
            answer_text = draft_res.text.strip()

            # --- rewrite (small) unless ladder >= 1 ---
            if ladder < LadderLevel.SKIP_REWRITE and answer_text:
                rw = rewrite(self.client, answer_text)
                tokens_in += rw.tokens_in
                tokens_out += rw.tokens_out
                if rw.status == "ok" and rw.text.strip():
                    answer_text = rw.text.strip()
                elif rw.status == "rate_limited":
                    self.budget.record_rate_limit_hit()
                    # Keep draft; do not fail the request for rewrite.

            # --- verify: local always; LLM only if ladder == 0 ---
            local = local_citation_check(answer_text, passages)
            if not local.ok:
                # Never guess — fall back to extractive rather than inventing fixes.
                ans = extractive_answer(question, passages)
                self.budget.record_success(tokens_in + tokens_out)
                return finish(
                    status=RequestStatus.OK,
                    answer=ans,
                    passages=passages,
                    reason=f"verify_failed:{local.reason}",
                )

            if ladder < LadderLevel.SKIP_LLM_VERIFY:
                lv = llm_verify(self.client, question, answer_text, passages)
                if lv.llm_result:
                    tokens_in += lv.llm_result.tokens_in
                    tokens_out += lv.llm_result.tokens_out
                if not lv.ok:
                    ans = extractive_answer(question, passages)
                    self.budget.record_success(tokens_in + tokens_out)
                    return finish(
                        status=RequestStatus.OK,
                        answer=ans,
                        passages=passages,
                        reason=f"llm_verify_failed:{lv.reason}",
                    )

            self.budget.record_success(tokens_in + tokens_out)
            refused = "the papers do not say" in answer_text.lower()
            return finish(
                status=RequestStatus.OK,
                answer=answer_text,
                refused=refused,
                reason="ok" if not refused else "model_refuse",
                passages=passages,
            )
        finally:
            self.admission.release()
