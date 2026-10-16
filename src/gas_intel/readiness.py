"""Report Stage 2 evidence coverage without certifying unfinished source contracts."""

import hashlib
import json
from pathlib import Path

import yaml

from gas_intel.geography import DLSBox
from gas_intel.history_profiling import month_number


def source_readiness(root: Path) -> list[dict[str, str]]:
    """Return pass/fail/pending checks; missing evidence is pending, malformed evidence fails."""
    checks: list[dict[str, str]] = []

    def check(name: str, status: str, detail: str) -> None:
        checks.append({"check": name, "status": status, "detail": detail})

    for category in ["facilities", "operators", "operator_history"]:
        path = root / "docs/evidence" / f"reference_{category}.json"
        try:
            report = json.loads(path.read_text())
            clean = (
                report["row_count"] > 0
                and report["blank_key_rows"] == 0
                and report["duplicate_extra_rows"] == 0
            )
            check(f"reference_{category}", "pass" if clean else "fail", "Reference key diagnostics")
        except FileNotFoundError:
            check(f"reference_{category}", "pending", "Reference evidence not available")
        except (OSError, ValueError, TypeError, KeyError):
            check(f"reference_{category}", "fail", "Reference evidence is malformed")
    try:
        contract = root / "config/sources.yaml"
        digest = hashlib.sha256(contract.read_bytes()).hexdigest()
        baselines = json.loads((root / "docs/evidence/known_month_baselines.json").read_text())
        pinned = len(baselines) >= 2 and all(
            item["source_contract_sha256"] == digest for item in baselines
        )
        check(
            "baseline_contract",
            "pass" if pinned else "fail",
            "Reviewed baseline config hashes; run full offline verifier separately",
        )
    except FileNotFoundError:
        check("baseline_contract", "pending", "Known-month baseline or source config is missing")
    except (OSError, ValueError, TypeError, KeyError):
        check("baseline_contract", "fail", "Baseline evidence is malformed")
    try:
        config = yaml.safe_load((root / "config/study_area.yaml").read_text())
        proposal = config.get("candidate_proposal")
        if not proposal:
            check("study_scope", "pending", "No study scope proposal recorded")
        else:
            DLSBox(
                **{
                    key: proposal[key]
                    for key in [
                        "township_min",
                        "township_max",
                        "range_min",
                        "range_max",
                        "meridian",
                    ]
                }
            )
            length = month_number(proposal["end_month"]) - month_number(proposal["start_month"]) + 1
            if length != 24:
                raise ValueError("Window must contain exactly 24 months")
            # Approval is only one requirement; it does not certify cohort or source contracts.
            approved = proposal.get("approved") is True
            check(
                "study_scope",
                "pass" if approved else "pending",
                "Scope confirmation recorded"
                if approved
                else "Human confirmation of candidate box and dates pending",
            )
    except FileNotFoundError:
        check("study_scope", "pending", "Study configuration missing")
    except (OSError, ValueError, TypeError, KeyError, AttributeError, yaml.YAMLError):
        check("study_scope", "fail", "Invalid bounds or fixed 24-month window")
    check("cohort_contract", "pending", "Stable cohort and location policy not frozen")
    check("selected_window", "pending", "Availability and cohort-specific baseline not verified")
    check("source_exit_review", "pending", "Material contracts require Stage 2 exit review")
    return checks
