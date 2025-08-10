from pydantic import BaseModel, Field
from typing import List, Optional

class UnmappedNode(BaseModel):
    node: str
    line: int
    why: str

class FailureDetail(BaseModel):
    name: str
    detail: str

class VerificationResult(BaseModel):
    tests_run: int
    passed: int
    failures: List[FailureDetail] = []

class Coverage(BaseModel):
    mapped_nodes: int
    total_nodes: int

class Reason(BaseModel):
    code: str
    detail: str

class AuditInfo(BaseModel):
    source_hash: str
    created_at: str
    prompt_version: str
    model: str

class MigrationReport(BaseModel):
    migration_status: str  # full|partial|blocked
    confidence: float = 0.0
    reasons: List[Reason] = []
    coverage: Coverage
    unmapped: List[UnmappedNode] = []
    script_appshape_pp: str = ""
    verification: Optional[VerificationResult] = None
    audit: Optional[AuditInfo] = None
