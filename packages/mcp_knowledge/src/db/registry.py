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

"""Per-corpus :class:`KnowledgeStore` registry.

Holds a single shared LanceDB connection and a single shared embedder, and
opens/creates one :class:`KnowledgeStore` per named corpus on demand. All
tables for the registered corpora live in the same ``db_path`` directory.

Every corpus may also declare a ``group``. Corpora sharing the same group
value are combined together at search time; see :meth:`get_by_group`.
"""
from __future__ import annotations

import logging
from pathlib import Path
from collections.abc import Iterable

from .store import KnowledgeStore
from nxp.mcp.knowledge.embeddings.base import EmbedderProvider
from nxp.mcp.knowledge.metadata import MCP_SERVER_NAME

logger = logging.getLogger(MCP_SERVER_NAME)


class UnknownCorpusError(KeyError):
    """Raised when a corpus name is requested that was not registered."""


class UnknownGroupError(KeyError):
    """Raised when a group name is requested that was not registered."""


class KnowledgeStoreRegistry:
    """Multi-corpus front-end over a single LanceDB directory.

    Args:
        db_path:  Directory where LanceDB stores its data files (one folder,
                  one table per registered corpus).
        embedder: :class:`EmbedderProvider` instance shared by every store.
        corpora:  Iterable of ``(name, group)`` pairs to pre-register. When a
                  group is falsy (None or empty), it defaults to the corpus
                  name so that an ungrouped corpus forms a group of one.
                  Stores are still created lazily on first :meth:`get` call.
    """

    def __init__(
        self,
        db_path: str,
        embedder: EmbedderProvider,
        corpora: Iterable[Tuple[str, str | None]] = (),
    ) -> None:
        import lancedb  # lazy import - only needed at runtime

        self._db_path = db_path
        self._embedder = embedder
        Path(db_path).mkdir(parents=True, exist_ok=True)
        self._db = lancedb.connect(db_path)

        self._stores: dict[str, KnowledgeStore] = {}
        # Track configured corpus names (in registration order) and the group
        # each one belongs to, even before their store is materialized so
        # tools can discover valid targets without forcing table creation.
        self._configured: list[str] = []
        self._group_of: dict[str, str] = {}
        seen: set[str] = set()
        for entry in corpora:
            # Accept both a plain corpus name and a (name, group) pair.
            # A bare string keeps backward compatibility with callers that
            # only know corpus names; its group then defaults to the name.
            if isinstance(entry, str):
                name, group = entry, None
            else:
                name, group = entry
            if name in seen:
                raise ValueError(f"Duplicate corpus name in registry: {name!r}")
            seen.add(name)
            self._configured.append(name)
            # Fall back to the corpus name when no group is supplied.
            self._group_of[name] = group if group else name

    # ------------------------------------------------------------------
    # Inspection
    # ------------------------------------------------------------------

    @property
    def db_path(self) -> str:
        return self._db_path

    @property
    def embedder(self) -> EmbedderProvider:
        return self._embedder

    def names(self) -> list[str]:
        """Return the configured corpus names in registration order."""
        return list(self._configured)

    def groups(self) -> list[str]:
        """Return the configured group names in first-seen order."""
        out: list[str] = []
        for name in self._configured:
            grp = self._group_of[name]
            if grp not in out:
                out.append(grp)
        return out

    def tables_by_group(self) -> dict[str, list[str]]:
        """Map each group to its member corpus names, in registration order.

        Groups appear in first-seen order (matching :meth:`groups`) and the
        corpora within each group keep their configuration order. A corpus
        without an explicit group forms a single-member group named after
        itself. This is the discovery counterpart to :meth:`groups`: it also
        exposes the individual table (corpus) names that ``kb_ingest`` and
        ``kb_remove`` operate on, whereas ``kb_search`` targets a whole group.
        """
        out: dict[str, list[str]] = {}
        for name in self._configured:
            out.setdefault(self._group_of[name], []).append(name)
        return out

    def default(self) -> str | None:
        """Return the sole configured corpus name, or ``None`` if not exactly one."""
        return self._configured[0] if len(self._configured) == 1 else None


    # ------------------------------------------------------------------
    # Resolution
    # ------------------------------------------------------------------

    def get(self, name: str) -> KnowledgeStore:
        """Return the :class:`KnowledgeStore` for *name*, creating it on first use.

        Raises:
            UnknownCorpusError: if *name* is not a registered corpus.
        """
        if name not in self._configured:
            raise UnknownCorpusError(
                f"Unknown corpus {name!r}. Configured: {self._configured}"
            )
        store = self._stores.get(name)
        if store is None:
            group = self._group_of[name]
            store = KnowledgeStore(
                collection=name,
                embedder=self._embedder,
                connection=self._db,
                group=group,
            )
            self._stores[name] = store
            logger.debug(
                "Materialized KnowledgeStore for corpus %r with group %r", name, group
            )
        return store

    def get_by_group(self, group: str) -> list[KnowledgeStore]:
        """Return the list of :class:`KnowledgeStore` belonging to *group*.

        Every corpus configured with the given group value is materialized
        (created on first use) and returned in registration order. Because a
        corpus without an explicit group defaults to its own name, passing a
        plain corpus name here returns a single-element list for that corpus.

        Raises:
            UnknownGroupError: if no configured corpus belongs to *group*.
        """
        members = [name for name in self._configured if self._group_of[name] == group]
        if not members:
            raise UnknownGroupError(
                f"Unknown group {group!r}. Configured groups: {self.groups()}"
            )
        logger.debug("get_by_group %r, found: %r", group, members)
        return [self.get(name) for name in members]

    def resolve(self, name: str | None) -> KnowledgeStore:
        """Resolve *name* to a store, falling back to the default corpus.

        - If *name* is given, behaves like :meth:`get`.
        - If *name* is ``None`` and exactly one corpus is configured, returns
          that one.
        - Otherwise raises :class:`UnknownCorpusError`.
        """
        if name is not None:
            return self.get(name)
        default = self.default()
        if default is None:
            raise UnknownCorpusError(
                "No corpus specified and no unique default available; "
                f"configured corpora: {self._configured}"
            )
        return self.get(default)

    def items(self) -> list[tuple[str, KnowledgeStore]]:
        """Return ``(name, store)`` pairs for every configured corpus.

        This forces materialization of every store; use sparingly.
        """
        return [(name, self.get(name)) for name in self._configured]
