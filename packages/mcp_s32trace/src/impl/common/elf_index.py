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

"""ELF DWARF index built with pyelftools.

Provides two main lookup directions:
  - address -> (symbol_name, offset, section, file, line)
  - (file, line) -> [address, ...]

All address comparisons use integer arithmetic.  The index is built once at
construction time and is read-only after that.
"""

from __future__ import annotations

import bisect
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from elftools.elf.elffile import ELFFile
from elftools.elf.sections import SymbolTableSection
from elftools.dwarf.dwarfinfo import DWARFInfo


@dataclass(frozen=True)
class SymbolEntry:
    name: str
    addr: int
    size: int
    section: str
    decl_file: str | None = None   # DW_AT_decl_file if available


@dataclass(frozen=True)
class LineEntry:
    file: str          # path as stored in DWARF (may be build-machine absolute)
    line: int
    col: int


@dataclass
class ElfIndex:
    """Read-only ELF/DWARF index for a single binary.

    Attributes
    ----------
    path:
        Path to the ELF file.
    symbols:
        Sorted list of (addr, SymbolEntry) by address.
    addr_to_line:
        Mapping from address (int) to LineEntry.
    file_line_to_addrs:
        Mapping from (basename_lower, line) to list of addresses.
        Used for source-location lookups that don't know the full path.
    full_file_line_to_addrs:
        Mapping from (full_dwarf_path_lower, line) to list of addresses.
        Preferred when the full DWARF path is available.
    sections:
        List of (name, vaddr, size) for all loadable sections.
    arch:
        ELF machine/architecture string.
    """

    path: str
    symbols: list[tuple[int, SymbolEntry]] = field(default_factory=list)
    addr_to_line: dict[int, LineEntry] = field(default_factory=dict)
    file_line_to_addrs: dict[tuple[str, int], list[int]] = field(default_factory=dict)
    full_file_line_to_addrs: dict[tuple[str, int], list[int]] = field(default_factory=dict)
    sections: list[tuple[str, int, int]] = field(default_factory=list)
    arch: str = "unknown"

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def from_file(cls, elf_path: str | Path) -> "ElfIndex":
        elf_path = Path(elf_path)
        if not elf_path.exists():
            raise FileNotFoundError(f"ELF not found: {elf_path}")

        obj = cls(path=str(elf_path))
        with elf_path.open("rb") as fh:
            elf = ELFFile(fh)
            obj.arch = elf.get_machine_arch()
            _collect_symbols(elf, obj)
            _collect_sections(elf, obj)
            if elf.has_dwarf_info():
                _collect_dwarf_lines(elf, obj)
        # Sort symbols by address for bisect lookup.
        obj.symbols.sort(key=lambda t: t[0])
        return obj

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def lookup_address(self, addr: int) -> dict[str, Any]:
        """Return enriched info for a given address.

        Returns dict with keys:
          symbol, symbol_addr, offset, section, file, line, col
        Values may be None when not available.
        """
        sym_name, sym_addr, offset, section = self._nearest_symbol(addr)
        line_entry = self.addr_to_line.get(addr)
        return {
            "symbol": sym_name,
            "symbol_addr": sym_addr,
            "offset": offset,
            "section": section,
            "file": line_entry.file if line_entry else None,
            "line": line_entry.line if line_entry else None,
            "col": line_entry.col if line_entry else None,
        }

    def lookup_symbol(self, name: str) -> list[dict[str, Any]]:
        """Find all symbols whose name equals (case-sensitive) ``name``."""
        return [
            {
                "symbol": sym.name,
                "addr": sym.addr,
                "size": sym.size,
                "section": sym.section,
                "decl_file": sym.decl_file,
            }
            for _, sym in self.symbols
            if sym.name == name
        ]

    def lookup_file_line(self, file_hint: str, line: int) -> list[int]:
        """Return addresses for a given file + line number.

        ``file_hint`` may be a full DWARF path or just a basename.
        """
        # Try full path first (case-insensitive).
        key_full = (file_hint.lower(), line)
        addrs = self.full_file_line_to_addrs.get(key_full)
        if addrs:
            return addrs
        # Fall back to basename lookup.
        base = os.path.basename(file_hint).lower()
        return self.file_line_to_addrs.get((base, line), [])

    def functions(self) -> list[SymbolEntry]:
        """Return all function symbols."""
        return [sym for _, sym in self.symbols if sym.size > 0]

    def _nearest_symbol(self, addr: int) -> tuple[str | None, int | None, int | None, str | None]:
        """Binary-search for the symbol that contains ``addr``."""
        if not self.symbols:
            return None, None, None, None
        addrs = [a for a, _ in self.symbols]
        idx = bisect.bisect_right(addrs, addr) - 1
        if idx < 0:
            return None, None, None, None
        sym_addr, sym = self.symbols[idx]
        offset = addr - sym_addr
        # If the symbol has a known size, validate we are inside it.
        if sym.size > 0 and offset >= sym.size:
            # Check if a closer symbol covers this address.
            pass  # still return best candidate
        return sym.name, sym_addr, offset, sym.section


# ---------------------------------------------------------------------------
# Internal builders
# ---------------------------------------------------------------------------

def _collect_symbols(elf: ELFFile, idx: ElfIndex) -> None:
    for section in elf.iter_sections():
        if not isinstance(section, SymbolTableSection):
            continue
        for sym in section.iter_symbols():
            if sym.name and sym["st_value"] != 0:
                entry = SymbolEntry(
                    name=sym.name,
                    addr=sym["st_value"],
                    size=sym["st_size"],
                    section=sym["st_shndx"] if isinstance(sym["st_shndx"], str) else "",
                )
                idx.symbols.append((entry.addr, entry))


def _collect_sections(elf: ELFFile, idx: ElfIndex) -> None:
    for section in elf.iter_sections():
        if section["sh_flags"] & 0x2:  # SHF_ALLOC
            idx.sections.append((section.name, section["sh_addr"], section["sh_size"]))


def _collect_dwarf_lines(elf: ELFFile, idx: ElfIndex) -> None:
    dwarf: DWARFInfo = elf.get_dwarf_info()
    for cu in dwarf.iter_CUs():
        try:
            line_prog = dwarf.line_program_for_CU(cu)
        except Exception:
            continue
        if line_prog is None:
            continue

        file_entries = line_prog.header["file_entry"]
        include_dirs: list[bytes] = list(line_prog.header.get("include_directory", []))

        def _resolve_file(file_idx: int) -> str:
            if file_idx < 1 or file_idx > len(file_entries):
                return ""
            fe = file_entries[file_idx - 1]
            fname = fe.name.decode("utf-8", errors="replace") if isinstance(fe.name, bytes) else str(fe.name)
            dir_idx = fe.dir_index
            if dir_idx == 0:
                return fname
            if dir_idx <= len(include_dirs):
                d = include_dirs[dir_idx - 1]
                d_str = d.decode("utf-8", errors="replace") if isinstance(d, bytes) else str(d)
                return d_str.rstrip("/\\") + "/" + fname
            return fname

        for entry in line_prog.get_entries():
            if entry.state is None:
                continue
            state = entry.state
            addr = state.address
            line = state.line
            col = state.column
            file_str = _resolve_file(state.file)

            le = LineEntry(file=file_str, line=line, col=col)
            # Prefer first entry for a given address.
            if addr not in idx.addr_to_line:
                idx.addr_to_line[addr] = le

            # Build reverse indices.
            base = os.path.basename(file_str).lower()
            key_base = (base, line)
            idx.file_line_to_addrs.setdefault(key_base, [])
            if addr not in idx.file_line_to_addrs[key_base]:
                idx.file_line_to_addrs[key_base].append(addr)

            key_full = (file_str.lower(), line)
            idx.full_file_line_to_addrs.setdefault(key_full, [])
            if addr not in idx.full_file_line_to_addrs[key_full]:
                idx.full_file_line_to_addrs[key_full].append(addr)
