# Source-verification acquisition

Acquisition is available for explicitly requested verification months. It does not
approve a study scope, load a warehouse or publish analytical exports.

```bash
gas-intel download --verification-month 2025-01
```

URLs and expected ordered headers come from config/sources.yaml. Each request uses
connect/read timeouts, at most three attempts, a bounded streamed response and a
temporary file. Accepted data must match the nested ZIP packaging, schema and
reporting month. Every accepted revision stays at data/raw/<sha256>/source.zip.

Publication uses an exclusive hard link from a fully written and synced temporary
file. This is atomic and cannot replace an existing raw file; data/processed and
data/raw must be on the same filesystem. A failure stops safely. Existing accepted
bytes are checked before an identical revision is reused. Failed or invalid new
responses never replace a prior revision.

The local data/raw/manifest.csv records attempt ID, source, period, original URL,
acquisition UTC time, bytes, content hash, source path, row count, configuration
hash and status/error type. Updates use an exclusive writer lock and atomic CSV
replacement. A lock left by an interrupted process requires inspection before
manual removal; simultaneous acquisitions fail clearly rather than interleave.

Tests use mocked requests and invented values with verified headers. They cover
successful/unchanged acquisition, retained changed revisions, bounded retries,
invalid responses, failure history and atomic-publication failure.

## Candidate-window inventory

For reproducible window verification, the acquisition function returns both an
event and its measured profile. Save each selected result as local metadata:

```python
import json
from pathlib import Path
from gas_intel.ingestion.download import acquire_month

root = Path.cwd()
months = ["2023-12"] + [f"{year}-{number:02d}" for year in (2024, 2025) for number in range(1, 13)]
for month in months:
    inventory = root / "data/verification" / f"{month}.json"
    if inventory.exists():
        continue  # Retain the explicitly selected snapshot, not a new vintage.
    result = acquire_month(root, month)
    inventory.parent.mkdir(parents=True, exist_ok=True)
    inventory.write_text(json.dumps(result, indent=2) + "\n")
```

January/February 2025 inventory reuses the original pinned October 16 snapshots
and their original acquisition metadata. Other months were acquired October 18.
Those legacy downloads predate the acquisition manifest and remain traceable via
the earlier evidence files. The window inventory selects one exact revision per
month; it never combines two revisions in a monthly total. Raw bytes and local
inventory remain excluded from Git.

Current files may change at the provider. Reacquiring a different hash requires a
reviewed new inventory selection; do not silently overwrite reviewed expectations.
