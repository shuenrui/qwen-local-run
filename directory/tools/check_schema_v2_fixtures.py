#!/usr/bin/env python3
"""Reproducible schema-v2 negative/positive fixture checks.

This tool never mutates live data. Each case copies the current dataset into a
temporary scratch directory, writes one synthetic setup, runs validate.py
against the scratch copy, and asserts the expected validator outcome.

Usage:
    python3 directory/tools/check_schema_v2_fixtures.py
"""
from __future__ import annotations

import contextlib
import copy
import io
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import validate as V  # noqa: E402

LIVE_DATA = os.path.join(PARENT, "data")
SOURCE_URL = "https://huggingface.co/unsloth/Qwen3.8-27B-GGUF"
RUN_URL = "https://github.com/ggml-org/llama.cpp"
KNOWN_WARNING = "hardware/gpu-multigpu-72gb: no device spec"
DATE = "2026-09-16"


def base_setup(sid: str) -> dict:
    return {
        "id": sid,
        "title": f"Schema fixture {sid}",
        "slug_note": "Synthetic validator fixture; never merged into the live dataset.",
        "model": "qwen3-8-27b",
        "status": "reported",
        "variation": {
            "checkpoint": "unsloth/Qwen3.8-27B-GGUF",
            "publisher": "unsloth",
            "quant": "gguf-q4",
            "quant_detail": "fixture quant",
            "format": "gguf",
            "size_gb": 16.7,
            "url": SOURCE_URL,
            "license": "Apache-2.0",
            "downloads": None,
        },
        "engine": {
            "id": "llama-cpp",
            "config": f"fixture engine config {sid}",
            "image": None,
            "requires_fork": False,
            "draft_model": None,
            "spec_decode": "none",
            "flags": [],
        },
        "hardware": ["gpu-24gb"],
        "requirements": {
            "memory_gb": 20,
            "disk_gb": 17,
            "min_vram_gb": 20,
            "notes": "fixture requirement",
        },
        "run": {
            "command": None,
            "repo": RUN_URL,
            "profile": None,
            "steps": [{"kind": "cmd", "text": "llama-server -m fixture.gguf"}],
            "auto_bootable": False,
        },
        "measurements": [base_measurement("m001", 50.0)],
        "caveats": [],
        "provenance_tier": "forum",
        "sources": [
            {"url": SOURCE_URL, "kind": "model", "note": "fixture source"}
        ],
        "updated": DATE,
    }


def base_measurement(mid: str, value: float) -> dict:
    return {
        "id": mid,
        "metric": "decode_per_stream",
        "value": value,
        "unit": "tok/s",
        "concurrency": 1,
        "provenance": "forum",
        "date": DATE,
        "source": SOURCE_URL,
        "method": "fixture server telemetry",
        "note": "fixture measurement note",
    }


def valid_v2_setup(sid: str) -> dict:
    s = base_setup(sid)
    s["schema_version"] = 2
    s["engine"]["version"] = "b10454"
    s["measurements"][0]["conditions"] = {
        "context_tokens": 8192,
        "workload": "chat",
        "concurrency": 1,
        "spec_decode": "none",
        "kv_dtype": "q4_0",
        "hardware_count": 1,
        "backend": "cuda",
        "greedy": True,
        "thinking": False,
        "temperature": 0.0,
        "warm": True,
        "client": "fixture-client",
    }
    s["measurements"][0]["evidence"] = {
        "level": "c2_observation",
        "contrast_kind": "none",
        "lineage_id": "fixture-lineage",
        "method_grade": "server_telemetry",
        "quality_status": "unchecked",
    }
    s["evidence"] = {
        "rubric_version": DATE,
        "lineages": [
            {
                "id": "fixture-lineage",
                "actor": "fixture",
                "kind": "forum",
                "sources": [
                    {"url": SOURCE_URL, "kind": "model", "locator": "model card"}
                ],
                "locator": "fixture lineage locator",
            }
        ],
    }
    return s


def two_measurement_v2_setup(sid: str) -> dict:
    s = valid_v2_setup(sid)
    second = copy.deepcopy(s["measurements"][0])
    second["id"] = "m002"
    second["value"] = 60.0
    s["measurements"].append(second)
    return s


def comparison_fixture(sid: str, contrast_kind: str, level: str = "c2_observation",
                       variable_field: str = "variable", include_gate: bool = False) -> dict:
    s = two_measurement_v2_setup(sid)
    cmp = {
        "id": "fixture-comparison",
        "question": "What does the fixture comparison report?",
        "a": {"label": "A", "measurement_id": "m001"},
        "b": {"label": "B", "measurement_id": "m002"},
        "result": "b_better",
        "effect_metric": "decode_per_stream",
        "effect_direction": "increase",
        "contrast_kind": contrast_kind,
        "conditions_constant": ["same fixture hardware"],
        "conditions_unstated": ["exact binary build"],
        "evidence_level": level,
        "lineage_id": "fixture-lineage",
        "source": SOURCE_URL,
        "locator": "fixture comparison locator",
    }
    if variable_field:
        cmp[variable_field] = "fixture_stack"
    if level == "c3_matched_ab":
        cmp["binary_provenance_status"] = "unresolved"
        cmp["re_review_triggers"] = ["fixture binary pin is resolved"]
    if include_gate:
        cmp["promotion_gate"] = {
            "target_level": "c3_matched_ab",
            "target_contrast_kind": "single_variable",
            "required_facts": ["both arms recorded", "same workload"],
            "status": "open",
        }
    s["evidence"]["comparisons"] = [cmp]
    return s


def case_live_baseline() -> dict:
    return {"setup": None}


def case_measurement_id_exemption() -> dict:
    s = base_setup("fixture-measurement-id-exemption")
    return {"setup": s}


def case_valid_v2() -> dict:
    return {"setup": valid_v2_setup("fixture-valid-v2")}


def case_false_c3() -> dict:
    s = valid_v2_setup("fixture-false-c3")
    s["measurements"][0]["evidence"]["level"] = "c3_matched_ab"
    s["measurements"][0]["evidence"]["contrast_kind"] = "single_variable"
    return {"setup": s}


def case_c3_uncontrolled_comparison() -> dict:
    s = comparison_fixture("fixture-c3-uncontrolled", "uncontrolled", "c3_matched_ab")
    for m in s["measurements"]:
        m["evidence"]["level"] = "c3_matched_ab"
        m["evidence"]["contrast_kind"] = "uncontrolled"
        m["evidence"]["contrast_id"] = "fixture-comparison"
    return {"setup": s}


def case_false_c4() -> dict:
    s = valid_v2_setup("fixture-false-c4")
    s["measurements"][0]["evidence"]["level"] = "c4_independent_reproduction"
    return {"setup": s}


def case_c4_one_lineage_comparison() -> dict:
    s = comparison_fixture("fixture-c4-one-lineage", "single_variable", "c4_independent_reproduction")
    s["evidence"]["comparisons"][0]["binary_provenance_status"] = "resolved"
    return {"setup": s}


def case_uncontrolled_with_settled_variable() -> dict:
    s = comparison_fixture("fixture-uncontrolled-variable", "uncontrolled", "c2_observation",
                           variable_field="variable", include_gate=True)
    return {"setup": s}


def case_valid_bundle_vs_uncontrolled() -> dict:
    s = comparison_fixture("fixture-valid-bundle", "bundle", "c2_observation",
                           variable_field="variable")
    return {"setup": s}


def case_valid_uncontrolled_candidate_variable() -> dict:
    s = comparison_fixture("fixture-valid-uncontrolled", "uncontrolled", "c2_observation",
                           variable_field="candidate_variable", include_gate=True)
    return {"setup": s}


def case_unsourced_offload_none() -> dict:
    s = valid_v2_setup("fixture-unsourced-offload-none")
    s["requirements"]["offload"] = {
        "strategy": "none",
        "locator": "fixture offload locator",
    }
    return {"setup": s}


def case_expected_cold_start_as_observed() -> dict:
    s = valid_v2_setup("fixture-expected-cold-start")
    s["requirements"]["offload"] = {
        "strategy": "pageable_ple",
        "source": SOURCE_URL,
        "locator": "fixture offload locator",
        "cold_start_effect": "expected disk-bound first-token latency",
    }
    return {"setup": s}


def case_untested_with_measurement() -> dict:
    s = base_setup("fixture-untested-measurement")
    s["status"] = "untested"
    return {"setup": s}


def case_broken_lineage_ref() -> dict:
    s = valid_v2_setup("fixture-broken-lineage")
    s["measurements"][0]["evidence"]["lineage_id"] = "missing-lineage"
    return {"setup": s}


def case_stored_condition_completeness() -> dict:
    s = valid_v2_setup("fixture-stored-completeness")
    s["measurements"][0]["condition_completeness"] = "partial"
    return {"setup": s}


def case_quality_in_evidence_level() -> dict:
    s = valid_v2_setup("fixture-c5-quality-level")
    s["measurements"][0]["evidence"]["level"] = "c5_quality_verified"
    return {"setup": s}


def case_unknown_technique_id() -> dict:
    s = valid_v2_setup("fixture-unknown-technique")
    s["evidence"]["claims"] = [
        {
            "id": "fixture-claim",
            "technique_id": "not-a-registered-technique",
            "kind": "mechanism",
            "statement": "Fixture claim uses an unregistered technique id.",
            "evidence_level": "c1_configuration",
            "lineage_id": "fixture-lineage",
            "source": SOURCE_URL,
            "locator": "fixture claim locator",
            "status": "recorded",
        }
    ]
    return {"setup": s}


def case_unknown_condition_key() -> dict:
    s = valid_v2_setup("fixture-unknown-condition-key")
    s["measurements"][0]["conditions"]["bogus_field"] = True
    return {"setup": s}


def case_wall_clock_missing_note() -> dict:
    s = valid_v2_setup("fixture-wall-clock-missing-note")
    s["measurements"][0]["evidence"]["method_grade"] = "wall_clock_division"
    s["measurements"][0].pop("method", None)
    return {"setup": s}


def case_wall_clock_valid() -> dict:
    s = valid_v2_setup("fixture-wall-clock-valid")
    s["measurements"][0]["evidence"]["method_grade"] = "wall_clock_division"
    s["measurements"][0]["evidence"]["method_note"] = "Task time divided by output tokens."
    s["measurements"][0]["method"] = "wall-clock division"
    s["measurements"][0]["note"] = "Weak wall-clock-derived speed; not comparable."
    return {"setup": s}


def case_migrated_fork_missing_revision() -> dict:
    s = valid_v2_setup("fixture-migrated-fork")
    s["engine"]["requires_fork"] = True
    return {"setup": s}


def case_legacy_fork_warning() -> dict:
    s = base_setup("fixture-legacy-fork")
    s["engine"]["requires_fork"] = True
    return {"setup": s, "legacy_pin_warnings": True}


CASES = [
    ("live dataset baseline", case_live_baseline, "pass", []),
    ("lone measurement id exemption", case_measurement_id_exemption, "pass", []),
    ("valid schema-v2 C2 record", case_valid_v2, "pass", []),
    ("false C3 without comparison", case_false_c3, "error", [
        "c3_matched_ab requires contrast_id linking a comparison",
    ]),
    ("C3 cannot ride uncontrolled contrast", case_c3_uncontrolled_comparison, "error", [
        "c3_matched_ab requires contrast_kind single_variable or bundle",
    ]),
    ("false C4 without linked comparison", case_false_c4, "error", [
        "c4_independent_reproduction requires a linked comparison with distinct lineages",
    ]),
    ("false C4 with one lineage", case_c4_one_lineage_comparison, "error", [
        "c4_independent_reproduction requires at least two distinct lineages",
    ]),
    ("uncontrolled contrast rejects settled variable", case_uncontrolled_with_settled_variable, "error", [
        "uncontrolled contrasts may use candidate_variable, not a settled variable",
    ]),
    ("bundle contrast accepts recorded variable", case_valid_bundle_vs_uncontrolled, "pass", []),
    ("uncontrolled contrast accepts candidate variable", case_valid_uncontrolled_candidate_variable, "pass", []),
    ("unsourced offload none", case_unsourced_offload_none, "error", [
        "offload.strategy 'none' requires an explicit source",
    ]),
    ("expected cold-start encoded as observed", case_expected_cold_start_as_observed, "error", [
        "cold_start_effect may record only an observed/measured outcome",
    ]),
    ("untested setup with measurement", case_untested_with_measurement, "error", [
        "status 'untested' must not contain measurements",
    ]),
    ("broken lineage reference", case_broken_lineage_ref, "error", [
        "unknown evidence.lineages[] id reference 'missing-lineage'",
    ]),
    ("stored condition_completeness", case_stored_condition_completeness, "error", [
        "condition_completeness is derived only and must not be stored",
    ]),
    ("quality inside evidence_level / C5", case_quality_in_evidence_level, "error", [
        "c5_quality_verified",
        "must be one of",
    ]),
    ("unknown technique_id", case_unknown_technique_id, "error", [
        "unknown technique registry id reference 'not-a-registered-technique'",
    ]),
    ("unknown condition key", case_unknown_condition_key, "error", [
        "unknown conditions keys ['bogus_field']",
    ]),
    ("wall-clock without method note", case_wall_clock_missing_note, "error", [
        "method_grade wall_clock_division requires evidence.method_note",
    ]),
    ("wall-clock with method note", case_wall_clock_valid, "pass", []),
    ("migrated fork-required without revision", case_migrated_fork_missing_revision, "error", [
        "migrated fork-required lane requires engine.fork_revision",
    ]),
    ("legacy fork-required warning", case_legacy_fork_warning, "warn", [
        "unmigrated legacy fork-required lane has no engine.fork_revision",
    ]),
]


def run_validator(setup: dict | None, legacy_pin_warnings: bool = False) -> tuple[int, str]:
    with tempfile.TemporaryDirectory(prefix="schema-v2-fixtures-") as tmp:
        data_dir = os.path.join(tmp, "data")
        shutil.copytree(LIVE_DATA, data_dir)
        if setup is not None:
            sid = setup["id"]
            path = os.path.join(data_dir, "setups", f"{sid}.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(setup, fh, indent=2)
                fh.write("\n")
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                rc = V.main(data_dir=data_dir, strict=False,
                            legacy_pin_warnings=legacy_pin_warnings)
        finally:
            V.DATA = LIVE_DATA
        return rc, buf.getvalue()


def check_derived_wall_clock_flags() -> None:
    measurement = {
        "metric": "decode_per_stream",
        "value": 10.0,
        "unit": "tok/s",
        "evidence": {
            "level": "c2_observation",
            "method_grade": "wall_clock_division",
            "method_note": "Task time divided by output tokens.",
        },
    }
    flags = V.derive_measurement_flags(measurement)
    assert flags["method_grade"] == "wall_clock_division"
    assert flags["method_note_required"] is True
    assert flags["headline_eligible"] is False
    assert flags["comparability_eligible"] is False

    speed = {
        "metric": "decode_per_stream",
        "value": 10.0,
        "unit": "tok/s",
        "evidence": {"level": "c2_observation", "method_grade": "server_telemetry"},
    }
    flags = V.derive_measurement_flags(speed)
    assert flags["headline_eligible"] is True
    assert flags["comparability_eligible"] is True


def check_derived_condition_completeness() -> None:
    partial = {
        "metric": "decode_per_stream",
        "value": 10.0,
        "conditions": {"context_tokens": 8192},
        "evidence": {"method_grade": "server_telemetry"},
    }
    assert V.derive_condition_completeness(partial) == "partial"

    full = {
        "metric": "decode_per_stream",
        "value": 10.0,
        "method": "server telemetry",
        "concurrency": 1,
        "conditions": {
            "context_tokens": 8192,
            "workload": "chat",
            "spec_decode": "none",
            "offload_strategy": "none",
            "kv_dtype": "q4_0",
            "hardware_count": 1,
            "backend": "cuda",
            "greedy": True,
            "thinking": False,
            "temperature": 0.0,
            "warm": True,
            "client": "fixture",
        },
        "evidence": {"method_grade": "server_telemetry"},
    }
    assert V.derive_condition_completeness(full) == "full"


def main() -> int:
    failures = []
    print("schema-v2 fixture suite")
    print(f"live data: {LIVE_DATA}")
    print("scratch copies: temporary directories; live data is never mutated\n")

    for name, builder, expect, substrings in CASES:
        case = builder()
        rc, out = run_validator(case.get("setup"), case.get("legacy_pin_warnings", False))
        errors = [line for line in out.splitlines() if line.startswith("ERROR")]
        warnings = [line for line in out.splitlines() if line.startswith("WARN")]
        ok = True
        detail = ""

        if expect == "pass":
            if rc != 0 or errors:
                ok = False
                detail = f"expected pass, got rc={rc} errors={len(errors)}"
            elif len(warnings) != 1 or KNOWN_WARNING not in warnings[0]:
                ok = False
                detail = f"expected only the known hardware warning, got {warnings}"
        elif expect == "error":
            if rc == 0 or not errors:
                ok = False
                detail = "expected validator errors, got none"
            else:
                joined = "\n".join(errors)
                missing = [s for s in substrings if s not in joined]
                if missing:
                    ok = False
                    detail = f"missing expected error substrings: {missing}"
        elif expect == "warn":
            if rc != 0 or errors:
                ok = False
                detail = "expected warnings only, got errors"
            else:
                joined = "\n".join(warnings)
                missing = [s for s in substrings if s not in joined]
                if missing:
                    ok = False
                    detail = f"missing expected warning substrings: {missing}"
        else:
            ok = False
            detail = f"unknown expectation {expect!r}"

        if not ok:
            failures.append((name, detail, out))
            print(f"FAIL  {name}: {detail}")
        else:
            print(f"PASS  {name}")

    try:
        check_derived_wall_clock_flags()
        check_derived_condition_completeness()
        print("PASS  derived wall-clock and condition-completeness helpers")
    except AssertionError as exc:
        failures.append(("derived helpers", str(exc), ""))
        print(f"FAIL  derived helpers: {exc}")

    if failures:
        print(f"\n{len(failures)} fixture failures")
        for name, detail, out in failures:
            print(f"\n--- {name} ---\n{detail}")
            if out:
                print(out[-4000:])
        return 1

    print(f"\n{len(CASES) + 1} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
