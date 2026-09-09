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

"""
Generic JSON-RPC 2.0 client with OpenRPC-based client-side validation.

This module was originally written for the S32DS embedded plugin but the
behaviour is server-agnostic: any HTTP JSON-RPC endpoint that implements
the reserved ``rpc.discover`` method (returning an OpenRPC 1.x document)
can be driven by it.

At startup the client calls ``rpc.discover`` once, caches the assembled
OpenRPC document, and uses it for client-side parameter validation on
every subsequent call.

Server-specific behaviour (extended socket timeouts for long-polling
methods, the component logger, …) is opt-in via constructor arguments
and subclass hooks - see :meth:`RpcClient._effective_timeout`.
"""

from __future__ import annotations

import json
import logging
import threading
import urllib.error
import urllib.request
from itertools import count
from typing import Any, Optional

_JSONRPC_VERSION = "2.0"
_METHOD_DISCOVER = "rpc.discover"


class RpcError(Exception):
	"""Raised when the JSON-RPC server returns an ``error`` envelope."""

	def __init__(self, code: int, message: str, data: Any = None):
		super().__init__(f"[{code}] {message}")
		self.code = code
		self.message = message
		self.data = data

	def to_dict(self) -> dict:
		return {"ok": False, "error": self.message, "code": self.code, "data": self.data}


class RpcClient:
	"""
	Synchronous JSON-RPC 2.0 client with OpenRPC discovery.

	Lifecycle:
	  1. ``__init__`` records the endpoint and timeout (no I/O yet).
	  2. ``discover()`` calls ``rpc.discover``, fills the method index/details
	     cache. Either call it explicitly or let the first ``call(...)`` do it
	     lazily.

	Public surface:
	  * ``discover()`` - force the contract reload.
	  * ``call(method, **params)`` - validate, send, return ``result`` or raise.
	  * ``list_methods(tag=None)`` - full catalogue: each entry is the complete
	    OpenRPC Method Object.
	  * ``set_port(port)`` - sticky, idempotent port switch; repoints the client
	    at a new port and forces the next call to re-run ``rpc.discover``. A
	    no-op when ``port`` is ``None`` or already the current port.
	  * ``has_method(name)`` - membership check used by ``execute``.
	"""

	def __init__(
		self,
		port: int,
		host: str = "localhost",
		timeout: int = 30,
		path: str = "/rpc",
		logger: Optional[logging.Logger] = None,
	):
		self._path = path
		self._host = host
		self._port = port
		self._url = f"http://{host}:{port}{path}"
		self._timeout = timeout

		# Log through the owning MCP server's logger so that RPC records are
		# grouped with the rest of that component's output and honour its
		# configured level/handlers. Callers should pass the component logger
		# obtained from ``setup_logging(...)``; if omitted we fall back to a
		# module-scoped child so records are never silently dropped.
		self._logger = logger or logging.getLogger(__name__)

		self._lock = threading.RLock()
		self._ids = count(1)

		self._spec: Optional[dict] = None
		self._method_index: dict[str, dict] = {}
		self._method_details: dict[str, dict] = {}

	# ------------------------------------------------------------------ public

	def discover(self) -> dict:
		"""
		Call ``rpc.discover`` and cache the result. Returns the full OpenRPC
		document (also cached on ``self``).

		The lock is held across the whole round-trip so that the cache swap in
		:meth:`_install_spec` is atomic with respect to other readers and so a
		lazy caller nested inside this method (via :meth:`_ensure_discovered`)
		reacquires the same reentrant lock safely.
		"""
		with self._lock:
			spec = self._raw_call(_METHOD_DISCOVER, None, timeout=self._timeout)
			self._install_spec(spec)
			self._logger.info(
				"rpc.discover OK from %s: %d methods cached",
				self._url, len(self._method_details),
			)
			return spec

	def is_ready(self) -> bool:
		return self._spec is not None

	@property
	def port(self) -> int:
		return self._port

	def set_port(self, port: Optional[int]) -> Optional[dict]:
		"""
		Sticky, idempotent port switch.

		Repoints the client at a new port on the same host and path. It is a
		no-op (returns ``None``) when ``port`` is ``None`` (caller did not
		request a switch) or when it already matches the current port.

		Otherwise the discovery cache is invalidated so the next ``call`` /
		``list_methods`` re-runs ``rpc.discover`` against the new endpoint, and
		the new port persists for all subsequent calls until changed again.

		Returns a small confirmation dict when a switch happened, otherwise
		``None``.
		"""
		if port is None:
			return None
		new_port = int(port)
		with self._lock:
			if new_port == self.port:
				return None
			self._port = int(port)
			self._url = f"http://{self._host}:{self._port}{self._path}"
			# Invalidate the cached contract - a different port is a different
			# endpoint, so the next call must re-discover.
			self._spec = None
			self._method_index = {}
			self._method_details = {}
		self._logger.info("RPC client repointed to %s", self._url)
		return {"ok": True, "port": self._port, "url": self._url}

	def list_methods(self, tag: Optional[str] = None) -> list[dict]:
		"""
		Full catalogue: each entry is the complete OpenRPC Method Object.

		If ``tag`` is provided, filter to methods carrying that tag.
		"""
		self._ensure_discovered()
		out: list[dict] = []
		for name, detail in self._method_details.items():
			if tag is not None and self._method_index.get(name, {}).get("tag") != tag:
				continue
			out.append(detail)
		out.sort(key=lambda m: m.get("name", ""))
		return out

	def has_method(self, name: str) -> bool:
		self._ensure_discovered()
		return name in self._method_details

	def call(self, method: str, **params) -> dict:
		"""
		Validate ``params`` against the cached schema, send the request,
		return the ``result`` field.

		Raises:
		  RpcError: the server returned an error envelope.
		  ValueError: client-side validation failed (missing required param,
		              wrong type).
		  ConnectionError: the server could not be reached.
		"""
		self._ensure_discovered()
		if method != _METHOD_DISCOVER:
			spec = self._method_details.get(method)
			if spec is None:
				raise ValueError(
					f"Unknown method '{method}'. Use list_methods() to see what's available."
				)
			self._validate_params(method, spec, params)

		return self._raw_call(method, params, timeout=self._effective_timeout(method, params))

	# ----------------------------------------------------------------- internal

	def _ensure_discovered(self) -> None:
		if self._spec is not None:
			return
		with self._lock:
			if self._spec is None:
				self.discover()

	def _install_spec(self, spec: dict) -> None:
		methods = spec.get("methods", []) if isinstance(spec, dict) else []
		index: dict[str, dict] = {}
		details: dict[str, dict] = {}
		for m in methods:
			if not isinstance(m, dict):
				continue
			name = m.get("name")
			if not isinstance(name, str):
				continue
			tags = m.get("tags") or []
			tag = tags[0].get("name") if tags and isinstance(tags[0], dict) else None
			index[name] = {"tag": tag, "summary": m.get("summary", "")}
			details[name] = m
		with self._lock:
			self._method_index = index
			self._method_details = details
			self._spec = spec

	def _effective_timeout(self, method: str, params: dict) -> int:
		"""
		Return the socket timeout (in seconds) to use for a given call.

		Default implementation returns the timeout passed to ``__init__``.
		Subclasses can override this to extend the timeout for long-polling
		methods (e.g. a ``waitForJob`` that blocks server-side until a job
		finishes or an internal timeout elapses).
		"""
		return self._timeout

	# --- param validation --------------------------------------------------

	def _validate_params(self, method: str, spec: dict, params: dict) -> None:
		"""
		Lightweight check using the cached OpenRPC Method Object.

		Thin wrapper that delegates to :meth:`_validate_params_from_list`.
		"""
		self._validate_params_from_list(method, spec.get("params", []) or [], params)

	def _validate_params_from_list(
		self,
		method: str,
		declared: Any,
		params: dict,
	) -> None:
		"""
		Validate ``params`` against a list of OpenRPC-shaped param declarations.

		For each declared param we enforce:
		  * required + missing -> raise
		  * present -> coarse JSON-type check against ``schema.type``
		  * unknown params -> raise (catches typos before dispatch)
		"""
		declared_list = list(declared) if declared else []
		declared_by_name = {p.get("name"): p for p in declared_list if isinstance(p, dict)}

		# Required-but-missing
		missing = [
			p["name"]
			for p in declared_list
			if isinstance(p, dict) and p.get("required") and p.get("name") not in params
		]
		if missing:
			raise ValueError(
				f"Method '{method}' is missing required parameter(s): {sorted(missing)}"
			)

		# Unknown
		unknown = sorted(set(params) - set(declared_by_name))
		if unknown:
			raise ValueError(
				f"Method '{method}' received unknown parameter(s): {unknown}. "
				f"Allowed: {sorted(declared_by_name)}"
			)

		# Type
		for name, value in params.items():
			schema = (declared_by_name.get(name) or {}).get("schema") or {}
			expected = schema.get("type")
			if expected and not _matches_json_type(value, expected):
				raise ValueError(
					f"Method '{method}' parameter '{name}' should be of type "
					f"'{expected}', got {type(value).__name__}"
				)

	# --- transport ---------------------------------------------------------

	def _raw_call(self, method: str, params: Optional[dict], timeout: int) -> Any:
		"""
		Send one JSON-RPC request and return its ``result``. Raises ``RpcError``
		on JSON-RPC errors, ``ConnectionError`` on transport failures.
		"""
		req: dict[str, Any] = {
			"jsonrpc": _JSONRPC_VERSION,
			"method": method,
			"id": next(self._ids),
		}
		if params is not None:
			# Drop None values so we don't surface them as explicit nulls -
			# the server schema validates by-name.
			req["params"] = {k: v for k, v in params.items() if v is not None}

		body = json.dumps(req).encode("utf-8")
		http_req = urllib.request.Request(
			self._url,
			data=body,
			headers={"Content-Type": "application/json"},
			method="POST",
		)

		try:
			with urllib.request.urlopen(http_req, timeout=timeout) as resp:
				raw = resp.read()
		except urllib.error.HTTPError as e:
			# The server still returns 200 for JSON-RPC errors; HTTPError here
			# means a transport-level issue (e.g. 405). Try to parse a body.
			try:
				err_body = json.loads(e.read().decode("utf-8"))
			except Exception:
				err_body = None
			raise ConnectionError(
				f"JSON-RPC server returned HTTP {e.code}: {e.reason}"
				+ (f" body={err_body}" if err_body is not None else "")
			) from e
		except urllib.error.URLError as e:
			raise ConnectionError(
				f"JSON-RPC server not reachable at {self._url}: {e.reason}"
			) from e

		try:
			envelope = json.loads(raw.decode("utf-8"))
		except (json.JSONDecodeError, UnicodeDecodeError) as e:
			raise ConnectionError(f"Malformed JSON-RPC response: {e}") from e

		if isinstance(envelope, list):
			raise ConnectionError(
				"Batch response received for a single request; this client does not batch."
			)

		if not isinstance(envelope, dict):
			raise ConnectionError(f"Unexpected JSON-RPC envelope: {envelope!r}")

		if "error" in envelope and envelope["error"] is not None:
			err = envelope["error"] or {}
			raise RpcError(
				code=err.get("code", -32603),
				message=err.get("message", "Unknown error"),
				data=err.get("data"),
			)

		return envelope.get("result")


# --- helpers ---------------------------------------------------------------

_PY_TO_JSON = {
	# allow ints to satisfy 'number'
	int: ("integer", "number"),
	float: ("number",),
	bool: ("boolean",),
	str: ("string",),
	list: ("array",),
	tuple: ("array",),
	dict: ("object",),
	type(None): ("null",),
}


def _matches_json_type(value: Any, expected: str) -> bool:
	# bool is a subclass of int - guard it first so a bool isn't typed 'integer'
	if isinstance(value, bool):
		return expected == "boolean"
	for py_type, json_types in _PY_TO_JSON.items():
		if isinstance(value, py_type):
			return expected in json_types
	return True  # unknown Python type -> don't block, server will validate
