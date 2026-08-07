#!/usr/bin/env python3
"""Validate cv_master.json structure and candidate-claim provenance."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
DATE_RE = re.compile(r"^(?:\d{4}-(?:0[1-9]|1[0-2])|present)$")
INCLUDE_POLICIES = {"always", "targeted", "conditional", "never"}
FIT_PRIORITIES = {"must", "preferred", "context"}
FIT_STATUSES = {"proven", "adjacent", "gap", "unclear"}


class Validator:
    def __init__(self, strict_provenance: bool = False) -> None:
        self.strict_provenance = strict_provenance
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.ids: dict[str, str] = {}
        self.achievement_ids: set[str] = set()
        self.skill_ids: set[str] = set()

    def error(self, path: str, message: str) -> None:
        self.errors.append(f"{path}: {message}")

    def warn(self, path: str, message: str, provenance: bool = False) -> None:
        if provenance and self.strict_provenance:
            self.error(path, message)
        else:
            self.warnings.append(f"{path}: {message}")

    def require_dict(self, value: Any, path: str) -> dict[str, Any]:
        if not isinstance(value, dict):
            self.error(path, "must be an object")
            return {}
        return value

    def require_list(self, value: Any, path: str) -> list[Any]:
        if not isinstance(value, list):
            self.error(path, "must be an array")
            return []
        return value

    def require_text(self, obj: dict[str, Any], key: str, path: str) -> str:
        value = obj.get(key)
        if not isinstance(value, str) or not value.strip():
            self.error(f"{path}.{key}", "must be a non-empty string")
            return ""
        return value.strip()

    def register_id(self, obj: dict[str, Any], path: str, kind: str) -> str:
        item_id = self.require_text(obj, "id", path)
        if not item_id:
            return ""
        if not ID_RE.fullmatch(item_id):
            self.error(f"{path}.id", "use lowercase letters, digits, and hyphens")
        previous = self.ids.get(item_id)
        if previous:
            self.error(f"{path}.id", f"duplicate ID; already used at {previous}")
        else:
            self.ids[item_id] = path
        if kind == "achievement":
            self.achievement_ids.add(item_id)
        elif kind == "skill":
            self.skill_ids.add(item_id)
        return item_id

    def validate_dates(self, obj: dict[str, Any], path: str) -> None:
        start = self.require_text(obj, "start", path)
        end = self.require_text(obj, "end", path)
        for key, value in (("start", start), ("end", end)):
            if value and not DATE_RE.fullmatch(value):
                self.error(f"{path}.{key}", "use YYYY-MM or present")
        if start == "present":
            self.error(f"{path}.start", "start cannot be present")
        if start and end and end != "present" and DATE_RE.fullmatch(start) and DATE_RE.fullmatch(end):
            if end < start:
                self.error(path, "end date precedes start date")

    def validate_achievement(self, value: Any, path: str) -> None:
        obj = self.require_dict(value, path)
        self.register_id(obj, path, "achievement")
        self.require_text(obj, "statement", path)
        refs = self.require_list(obj.get("skill_refs", []), f"{path}.skill_refs")
        for i, ref in enumerate(refs):
            if not isinstance(ref, str) or not ref:
                self.error(f"{path}.skill_refs[{i}]", "must be a non-empty skill ID")

    def validate_timeline_items(self, data: dict[str, Any], key: str) -> None:
        items = self.require_list(data.get(key, []), key)
        for i, value in enumerate(items):
            path = f"{key}[{i}]"
            obj = self.require_dict(value, path)
            self.register_id(obj, path, key.rstrip("s"))
            required_fields = ("company", "role", "dates_label") if key == "experiences" else (
                "name",
                "dates_label",
            )
            for field in required_fields:
                self.require_text(obj, field, path)
            self.validate_dates(obj, path)
            policy = obj.get("include_policy", "targeted")
            if policy not in INCLUDE_POLICIES:
                self.error(f"{path}.include_policy", f"must be one of {sorted(INCLUDE_POLICIES)}")
            achievements = obj.get("achievements")
            if achievements is None:
                legacy = obj.get("bullets") or obj.get("metrics")
                if legacy:
                    self.warn(path, "legacy bullets/metrics must be migrated to achievements with IDs", True)
                else:
                    self.warn(path, "has no evidence-bearing achievements", True)
                continue
            for j, achievement in enumerate(self.require_list(achievements, f"{path}.achievements")):
                self.validate_achievement(achievement, f"{path}.achievements[{j}]")

    def validate_skills(self, data: dict[str, Any]) -> None:
        skills = self.require_dict(data.get("skills", {}), "skills")
        pending_refs: list[tuple[str, str]] = []
        for category, values in skills.items():
            path = f"skills.{category}"
            for i, value in enumerate(self.require_list(values, path)):
                item_path = f"{path}[{i}]"
                if isinstance(value, str):
                    self.warn(item_path, "legacy skill string lacks an ID and evidence references", True)
                    continue
                obj = self.require_dict(value, item_path)
                self.register_id(obj, item_path, "skill")
                self.require_text(obj, "name", item_path)
                refs = self.require_list(obj.get("evidence", []), f"{item_path}.evidence")
                if not refs:
                    self.warn(item_path, "skill has no achievement evidence", True)
                for j, ref in enumerate(refs):
                    if isinstance(ref, str) and ref:
                        pending_refs.append((f"{item_path}.evidence[{j}]", ref))
                    else:
                        self.error(f"{item_path}.evidence[{j}]", "must be a non-empty achievement ID")
        for path, ref in pending_refs:
            if ref not in self.achievement_ids:
                self.error(path, f"unknown achievement ID: {ref}")

    def validate_achievement_skill_refs(self, data: dict[str, Any]) -> None:
        for key in ("experiences", "projects"):
            for i, item in enumerate(data.get(key, [])):
                if not isinstance(item, dict):
                    continue
                for j, achievement in enumerate(item.get("achievements", [])):
                    if not isinstance(achievement, dict):
                        continue
                    for k, ref in enumerate(achievement.get("skill_refs", [])):
                        if isinstance(ref, str) and ref not in self.skill_ids:
                            self.error(
                                f"{key}[{i}].achievements[{j}].skill_refs[{k}]",
                                f"unknown skill ID: {ref}",
                            )

    def validate_simple_id_lists(self, data: dict[str, Any]) -> None:
        required_fields = {
            "education": ("degree", "school"),
            "languages": ("language", "level"),
            "certifications": ("name", "issuer", "date"),
            "strengths": ("name",),
        }
        pending_refs: list[tuple[str, str]] = []
        for key in ("education", "languages", "certifications", "strengths"):
            for i, value in enumerate(self.require_list(data.get(key, []), key)):
                path = f"{key}[{i}]"
                obj = self.require_dict(value, path)
                self.register_id(obj, path, key.rstrip("s"))
                for field in required_fields[key]:
                    self.require_text(obj, field, path)
                if key == "strengths":
                    refs = self.require_list(obj.get("evidence", []), f"{path}.evidence")
                    if not refs:
                        self.warn(path, "strength has no achievement evidence", True)
                    for j, ref in enumerate(refs):
                        if isinstance(ref, str) and ref:
                            pending_refs.append((f"{path}.evidence[{j}]", ref))
                        else:
                            self.error(f"{path}.evidence[{j}]", "must be a non-empty achievement ID")
        for path, ref in pending_refs:
            if ref not in self.achievement_ids:
                self.error(path, f"unknown achievement ID: {ref}")

    def validate_rules(self, data: dict[str, Any]) -> None:
        for key in ("exclusions", "conditional_include"):
            for i, value in enumerate(self.require_list(data.get(key, []), key)):
                path = f"{key}[{i}]"
                obj = self.require_dict(value, path)
                ref = self.require_text(obj, "ref_id", path)
                if ref and ref not in self.ids:
                    self.error(f"{path}.ref_id", f"unknown master ID: {ref}")

    def validate(self, value: Any) -> None:
        data = self.require_dict(value, "root")
        version = data.get("schema_version")
        if version != 2:
            self.warn("schema_version", "expected version 2; migrate the master file", True)
        identity = self.require_dict(data.get("identity"), "identity")
        self.register_id(identity, "identity", "identity")
        self.require_text(identity, "full_name", "identity")
        self.require_text(identity, "professional_identity", "identity")
        if not any(isinstance(identity.get(key), str) and identity[key].strip() for key in ("email", "phone")):
            self.error("identity", "provide at least one contact method: email or phone")
        self.validate_timeline_items(data, "experiences")
        self.validate_timeline_items(data, "projects")
        self.validate_simple_id_lists(data)
        self.validate_skills(data)
        self.validate_achievement_skill_refs(data)
        self.validate_rules(data)

    def validate_fit_matrix(self, value: Any) -> None:
        data = self.require_dict(value, "fit_matrix")
        self.require_dict(data.get("target"), "fit_matrix.target")
        requirements = self.require_list(data.get("requirements"), "fit_matrix.requirements")
        for i, value in enumerate(requirements):
            path = f"fit_matrix.requirements[{i}]"
            obj = self.require_dict(value, path)
            self.require_text(obj, "requirement", path)
            priority = self.require_text(obj, "priority", path)
            status = self.require_text(obj, "status", path)
            self.require_text(obj, "cv_action", path)
            if priority and priority not in FIT_PRIORITIES:
                self.error(f"{path}.priority", f"must be one of {sorted(FIT_PRIORITIES)}")
            if status and status not in FIT_STATUSES:
                self.error(f"{path}.status", f"must be one of {sorted(FIT_STATUSES)}")
            refs = self.require_list(obj.get("master_refs", []), f"{path}.master_refs")
            if status in {"proven", "adjacent"} and not refs:
                self.error(f"{path}.master_refs", f"{status} requirements need supporting master IDs")
            if status == "gap" and refs:
                self.error(f"{path}.master_refs", "gap requirements cannot cite candidate evidence")
            for j, ref in enumerate(refs):
                if not isinstance(ref, str) or not ref:
                    self.error(f"{path}.master_refs[{j}]", "must be a non-empty master ID")
                elif ref not in self.ids:
                    self.error(f"{path}.master_refs[{j}]", f"unknown master ID: {ref}")

    def validate_claim_ledger(self, value: Any) -> None:
        data = self.require_dict(value, "claim_ledger")
        self.require_text(data, "target", "claim_ledger")
        claims = self.require_list(data.get("claims"), "claim_ledger.claims")
        claim_ids: set[str] = set()
        for i, value in enumerate(claims):
            path = f"claim_ledger.claims[{i}]"
            obj = self.require_dict(value, path)
            claim_id = self.require_text(obj, "id", path)
            if claim_id:
                if not ID_RE.fullmatch(claim_id):
                    self.error(f"{path}.id", "use lowercase letters, digits, and hyphens")
                if claim_id in claim_ids:
                    self.error(f"{path}.id", "duplicate claim ID")
                claim_ids.add(claim_id)
            self.require_text(obj, "section", path)
            self.require_text(obj, "text", path)
            refs = self.require_list(obj.get("source_refs"), f"{path}.source_refs")
            if not refs:
                self.error(f"{path}.source_refs", "every candidate claim needs at least one master ID")
            for j, ref in enumerate(refs):
                if not isinstance(ref, str) or not ref:
                    self.error(f"{path}.source_refs[{j}]", "must be a non-empty master ID")
                elif ref not in self.ids:
                    self.error(f"{path}.source_refs[{j}]", f"unknown master ID: {ref}")


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}") from exc


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("master", type=Path, help="path to cv_master.json")
    parser.add_argument(
        "--strict-provenance",
        action="store_true",
        help="treat legacy or unproven claims as errors",
    )
    parser.add_argument("--fit-matrix", type=Path, help="optional application fit matrix to validate")
    parser.add_argument("--claim-ledger", type=Path, help="optional generated-claim ledger to validate")
    args = parser.parse_args()

    try:
        data = load_json(args.master)
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 2

    validator = Validator(strict_provenance=args.strict_provenance)
    validator.validate(data)
    for path, callback in (
        (args.fit_matrix, validator.validate_fit_matrix),
        (args.claim_ledger, validator.validate_claim_ledger),
    ):
        if path:
            try:
                callback(load_json(path))
            except (OSError, ValueError) as exc:
                validator.error(str(path), str(exc))
    for warning in validator.warnings:
        print(f"WARNING: {warning}")
    for error in validator.errors:
        print(f"ERROR: {error}")
    if validator.errors:
        print(f"Validation failed: {len(validator.errors)} error(s), {len(validator.warnings)} warning(s)")
        return 3
    print(f"Master valid: {len(validator.ids)} traceable ID(s), {len(validator.warnings)} warning(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
