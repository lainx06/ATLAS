"""Table reading shared by the host and the runner container.

Imports pandas only (no policy, contracts or evaluator code), so it can be mounted into the
runner container next to the adapter and recorder. Supported formats: csv, parquet.
"""

from pathlib import Path

import pandas as pd


def read_table(path: Path, fmt: str, row_id: str) -> pd.DataFrame:
    """The table indexed by string row IDs."""
    if fmt == "csv":
        table = pd.read_csv(path, dtype={row_id: str})
    elif fmt == "parquet":
        table = pd.read_parquet(path)
        table[row_id] = table[row_id].astype(str)
    else:
        raise ValueError(f"unsupported table format {fmt!r}")
    table = table.set_index(row_id)
    if not table.index.is_unique:
        raise ValueError("row_id values are not unique")
    return table
