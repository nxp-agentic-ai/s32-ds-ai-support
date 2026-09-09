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

"""LanceDB table schema for the knowledge store."""
import pyarrow as pa


def make_schema(dimension: int) -> pa.Schema:
    """Build the PyArrow schema for the knowledge table.

    Fields
    ------
    id          : str  — stable unique ID: ``sha256(<source>:<chunk_index>)``
    source      : str  — absolute or relative path of the original file
    chunk_index : int  — zero-based index of this chunk within the source file
    text        : str  — raw chunk text (used for retrieval display)
    vector      : fixed_size_list[float32, dimension]  — embedding vector
    source_hash : str  — SHA-256 hex digest of the source file's raw bytes;
                         used by the pipeline to skip re-ingestion of unchanged files

    Args:
        dimension: Embedding vector length (determined by the active embedder).
    """
    return pa.schema(
        [
            pa.field("id", pa.string()),
            pa.field("source", pa.string()),
            pa.field("chunk_index", pa.int32()),
            pa.field("text", pa.string()),
            pa.field("vector", pa.list_(pa.float32(), dimension)),
            pa.field("source_hash", pa.string()),
        ]
    )
