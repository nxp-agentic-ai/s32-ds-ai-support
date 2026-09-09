# Copyright 2026 NXP
#
# NXP Proprietary. This software is owned or controlled by NXP and may
# only be used strictly in accordance with the applicable license terms.
# By expressly accepting such terms or by downloading, installing,
# activating and/or otherwise using the software, you are agreeing that
# you have read, and that you agree to comply with and are bound by,
# such license terms.  If you do not agree to be bound by the applicable
# license terms, then you may not retain, install, activate or otherwise
# use the software.

"""High-level search orchestration for shared action search."""
from __future__ import annotations

from collections.abc import Iterable
from enum import Enum

from .. import errors
from ..models import ActionContract, ActionOutcome
from .bm25 import bm25_search_action_contracts
from .regex import regex_search_action_contracts
from .text import normalize_search_text


class SearchStrategy(Enum):
    """Supported shared action-search strategies."""

    BM25 = "bm25"
    REGEX = "regex"

    @classmethod
    def from_string(cls, value: str | None) -> SearchStrategy:
        """Parse a caller-provided strategy string, defaulting to BM25."""

        normalized_value = normalize_search_text(value or "") or cls.BM25.value
        try:
            return cls(normalized_value)
        except ValueError:
            return SearchStrategy.BM25


SEARCH_HANDLERS = {
    SearchStrategy.BM25: bm25_search_action_contracts,
    SearchStrategy.REGEX: regex_search_action_contracts,
}


def _requested_strategy_value(strategy: SearchStrategy | str | None) -> str | None:
    """Return the caller-visible normalized strategy value for diagnostics."""

    if isinstance(strategy, SearchStrategy):
        return strategy.value
    return normalize_search_text(strategy or "") or None


def _success_outcome(actions: Iterable[ActionContract]) -> ActionOutcome:
    """Build the canonical search success outcome payload."""

    return ActionOutcome(
        result={
            "actions": [action.to_contract_payload() for action in actions],
        }
    )


def search_actions(
    actions: Iterable[ActionContract],
    *,
    query: str | None,
    limit: int,
    strategy: SearchStrategy | str | None = SearchStrategy.BM25,
) -> ActionOutcome:
    """Search action contracts using one of the supported search strategies."""

    action_list = sorted(actions, key=lambda item: item.name)
    requested_strategy = _requested_strategy_value(strategy)
    resolved_strategy = strategy if isinstance(strategy, SearchStrategy) else SearchStrategy.from_string(strategy)

    if not action_list or limit <= 0:
        return _success_outcome(())

    normalized_query = normalize_search_text(query or "")
    if not normalized_query:
        return _success_outcome(action_list[:limit])

    # Short-circuit exact action-name lookups for the default/BM25 flow. If the caller
    # already knows the fully qualified action name, return only that action instead of
    # spending tokens on additional ranked matches. We do not apply this shortcut to the
    # regex strategy because an explicit regex query is expected to preserve regex match
    # semantics, including the possibility of returning multiple actions.
    if resolved_strategy is SearchStrategy.BM25:
        exact_match = next(
            (
                action
                for action in action_list
                if normalize_search_text(action.name) == normalized_query
            ),
            None,
        )
        if exact_match is not None:
            return _success_outcome((exact_match,))

    try:
        search_handler = SEARCH_HANDLERS[resolved_strategy]
    except KeyError:  # pragma: no cover - defensive fallback
        return ActionOutcome(
            error_code=errors.INVALID_PARAMS,
            error_message=errors.ErrorLabel.INVALID_SEARCH_STRATEGY,
            error_details={
                "message": f"Unsupported action search strategy '{resolved_strategy.value}'",
                "query": query,
                "strategy": requested_strategy,
                "supported_strategies": [member.value for member in SearchStrategy],
            },
        )

    try:
        results = search_handler(action_list, normalized_query, limit=limit)
    except Exception as exc:  # pragma: no cover - defensive fallback
        return ActionOutcome(
            error_code=errors.FORWARD_ERROR,
            error_message=errors.ErrorLabel.SEARCH_FAILED,
            error_details={
                "message": str(exc),
                "query": query,
                "strategy": requested_strategy,
            },
        )

    return _success_outcome(results)
