"""Shared types for The Relay pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import IntEnum, Enum
from typing import Any, Optional


class LadderLevel(IntEnum):
    FULL = 0
    SKIP_REWRITE = 1
    SKIP_LLM_VERIFY = 2
    SHRINK_RETRIEVAL = 3
    EXTRACTIVE = 4
    TRY_LATER = 5


class RequestStatus(str, Enum):
    OK = "ok"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    ERROR = "error"


class AnswerGrade(str, Enum):
    CORRECT = "correct"
    WRONG = "wrong"
    REFUSED_CORRECTLY = "refused_correctly"
    REFUSED_WRONGLY = "refused_wrongly"
    UNGRADED = "ungraded"


@dataclass
class Passage:
    passage_id: str
    paper_id: str
    paper_title: str
    section: str
    text: str
    score: float = 0.0

    def cite(self) -> str:
        return f"[{self.passage_id} | {self.paper_id} | {self.section}]"


@dataclass
class ModelUsage:
    tokens_in: int = 0
    tokens_out: int = 0
    first_token_ms: Optional[float] = None
    total_ms: float = 0.0
    model: str = ""
    raw_error: str = ""


@dataclass
class PipelineResult:
    request_id: str
    question: str
    scenario: str
    source: str  # "real" | "stand-in"
    start_time: str
    first_token_ms: Optional[float]
    total_ms: float
    status: RequestStatus
    retries: int
    tokens_in: int
    tokens_out: int
    retrieval_setting: str
    answer_grade: AnswerGrade
    answer_text: str = ""
    ladder_level: int = 0
    passages: list[Passage] = field(default_factory=list)
    refused: bool = False
    refuse_reason: str = ""
    waiting_ms: float = 0.0
    working_ms: float = 0.0
    retrying_ms: float = 0.0
    peak_queue_length: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_csv_row(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "scenario": self.scenario,
            "source": self.source,
            "start_time": self.start_time,
            "first_token_ms": "" if self.first_token_ms is None else round(self.first_token_ms, 3),
            "total_ms": round(self.total_ms, 3),
            "status": self.status.value,
            "retries": self.retries,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "retrieval_setting": self.retrieval_setting,
            "answer_grade": self.answer_grade.value,
        }

    def as_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["answer_grade"] = self.answer_grade.value
        return d
