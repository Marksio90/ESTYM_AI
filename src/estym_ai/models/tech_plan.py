"""TechPlan — the manufacturing process plan with PSI precedence graph."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .enums import OperationType, PrecedenceRelation


class Operation(BaseModel):
    """A single manufacturing operation in the process plan."""
    op_code: str  # unique within TechPlan, e.g. "OP010"
    op_name: str  # human-readable name
    op_type: OperationType
    workcenter: str  # machine / work station code
    workcenter_name: str = ""

    # Time norms
    cycle_time_sec: float = 0.0  # per-piece cycle time
    setup_time_sec: float = 0.0  # one-time setup per batch
    handling_time_sec: float = 0.0  # load/unload per piece

    # Multiplier: e.g. 20 identical wire segments = multiplier 20
    multiplier: float = 1.0

    # Fixtures / tooling
    requires_fixture: bool = False
    fixture_type: Optional[str] = None
    fixture_design_time_h: float = 0.0
    fixture_build_time_h: float = 0.0
    fixture_cost: float = 0.0

    # Labor
    operator_count: int = 1
    skill_level: str = "standard"  # standard / skilled / specialist

    # QA
    qa_check_required: bool = False
    qa_check_description: str = ""

    # Dependencies (filled via precedence_edges, but also listed here for convenience)
    inputs: list[str] = Field(default_factory=list)  # op_codes this depends on
    outputs: list[str] = Field(default_factory=list)  # op_codes that depend on this

    notes: list[str] = Field(default_factory=list)


class PrecedenceEdge(BaseModel):
    """Directed edge in the PSI precedence graph."""
    from_op_code: str
    to_op_code: str
    relation: PrecedenceRelation = PrecedenceRelation.MUST_FINISH_BEFORE


class TechPlan(BaseModel):
    """
    Complete manufacturing technology plan with PSI precedence graph.

    The operations list defines all steps; precedence_edges define
    the directed graph of dependencies (PSI: następniki/poprzedniki).
    """
    plan_id: str = ""
    part_id: str = ""
    plan_version: int = 1

    operations: list[Operation] = Field(default_factory=list)
    precedence_edges: list[PrecedenceEdge] = Field(default_factory=list)

    # Batch-level parameters
    batch_size: int = 1
    total_setup_time_sec: float = 0.0
    total_cycle_time_sec: float = 0.0  # sum of all ops × multipliers
    total_time_with_overhead_sec: float = 0.0
    social_overhead_percent: float = 10.0

    notes_for_operator: list[str] = Field(default_factory=list)
    qa_checks: list[str] = Field(default_factory=list)

    def compute_totals(self) -> None:
        """Recompute aggregate time fields from operations."""
        self.total_setup_time_sec = sum(op.setup_time_sec for op in self.operations)
        self.total_cycle_time_sec = sum(
            (op.cycle_time_sec + op.handling_time_sec) * op.multiplier
            for op in self.operations
        )
        per_piece = self.total_cycle_time_sec + (self.total_setup_time_sec / max(self.batch_size, 1))
        self.total_time_with_overhead_sec = per_piece * (1 + self.social_overhead_percent / 100)

    def topological_order(self) -> list[str]:
        """Return operation codes in valid topological (PSI) order."""
        from collections import defaultdict, deque

        graph: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = {op.op_code: 0 for op in self.operations}

        for edge in self.precedence_edges:
            if edge.relation == PrecedenceRelation.MUST_FINISH_BEFORE:
                graph[edge.from_op_code].append(edge.to_op_code)
                in_degree[edge.to_op_code] = in_degree.get(edge.to_op_code, 0) + 1

        queue = deque(code for code, deg in in_degree.items() if deg == 0)
        order: list[str] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in graph[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return order
