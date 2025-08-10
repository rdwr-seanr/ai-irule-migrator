"""LangGraph wiring skeleton.
Builds MainGraph with Router -> (qa | migrate | status) branches (stubs).
"""

from typing import Literal, Dict, Any
try:
    from langgraph.graph import StateGraph, END
except ImportError:  # allow import before dependency installed
    StateGraph = object  # type: ignore
    END = None  # type: ignore
from pydantic import BaseModel
from packages.rag.retriever import retrieve
from packages.tools.irule_parser import parse_irule
from packages.tools.appshape_generator import generate_appshape

class GraphState(BaseModel):
    intent: Literal['qa','migrate','status','unknown'] = 'unknown'
    question: str | None = None
    answer: str | None = None
    citations: list | None = None
    irule_code: str | None = None
    report: Dict[str, Any] | None = None
    ast: Dict[str, Any] | None = None
    diagnostics: list | None = None
    plan: Dict[str, Any] | None = None
    script: str | None = None
    mapping: list | None = None

# Router node

def router_node(state: GraphState) -> GraphState:
    if state.question:
        state.intent = 'qa'
    elif state.irule_code:
        state.intent = 'migrate'
    else:
        state.intent = 'status'
    return state

# RAG_QA node

def rag_qa_node(state: GraphState) -> GraphState:
    rr = retrieve(state.question, top_k=6)
    state.answer = 'Placeholder answer'  # TODO: synthesis with LLM
    state.citations = rr.citations
    return state

# Migration pipeline stubs

def parse_node(state: GraphState) -> GraphState:
    parsed = parse_irule(state.irule_code or '')
    state.ast = parsed['ast']
    state.diagnostics = parsed['diagnostics']
    return state


def capability_map_node(state: GraphState) -> GraphState:
    ast = state.ast or {}
    supported = 0
    total = 0
    for ev in ast.get('events', []):
        for node in ev.get('body', []):
            total += 1
            if 'unmapped' not in node.get('cmd',''):
                supported += 1
    state.plan = {"status": "full" if supported == total else ("partial" if supported else "blocked"), "supported": supported, "total": total}
    return state


def plan_node(state: GraphState) -> GraphState:
    # Already computed; could enrich with reasons
    return state


def translate_node(state: GraphState) -> GraphState:
    if not state.ast or not state.plan:
        return state
    gen = generate_appshape(state.ast, state.plan)
    state.script = gen['code']
    state.mapping = gen['mapping']
    return state


def verify_node(state: GraphState) -> GraphState:
    # Simple linter: check unmapped occurrences
    unmapped = [m for m in (state.mapping or []) if m.get('target') is None]
    state.report = state.report or {}
    state.report['unmapped'] = unmapped
    return state


def report_builder_node(state: GraphState) -> GraphState:
    if state.plan and state.script:
        state.report = state.report or {}
        coverage = 0
        total = state.plan.get('total', 0) or 1
        coverage = state.plan.get('supported',0)/total
        state.report.update({
            'migration_status': state.plan['status'],
            'coverage': coverage,
            'script': state.script,
            'mapping': state.mapping,
            'diagnostics': state.diagnostics
        })
    return state


def build_graph():
    try:
        sg = StateGraph(GraphState)
    except TypeError:
        return None
    sg.add_node('Router', router_node)
    sg.add_node('RAG_QA', rag_qa_node)
    sg.add_node('IRule_Parse', parse_node)
    sg.add_node('IRule_Capability_Map', capability_map_node)
    sg.add_node('Migration_Plan', plan_node)
    sg.add_node('Translate_To_AppShapePP', translate_node)
    sg.add_node('Verifier', verify_node)
    sg.add_node('Report_Builder', report_builder_node)

    # Edges
    sg.set_entry_point('Router')
    sg.add_conditional_edges('Router', lambda s: s.intent, {
        'qa': 'RAG_QA',
        'migrate': 'IRule_Parse',
        'status': 'Report_Builder',
        'unknown': 'Report_Builder'
    })
    sg.add_edge('RAG_QA', 'Report_Builder')
    sg.add_edge('IRule_Parse', 'IRule_Capability_Map')
    sg.add_edge('IRule_Capability_Map', 'Migration_Plan')
    sg.add_edge('Migration_Plan', 'Translate_To_AppShapePP')
    sg.add_edge('Translate_To_AppShapePP', 'Verifier')
    sg.add_edge('Verifier', 'Report_Builder')
    sg.add_edge('Report_Builder', END)
    return sg.compile()
