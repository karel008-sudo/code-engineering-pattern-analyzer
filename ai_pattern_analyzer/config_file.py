"""
config_file.py — YAML/JSON config file loader for ai-analyzer.yaml.

Loads scan configuration from ai-analyzer.yaml or ai-analyzer.json.
Falls back to defaults if no config file is found.

Supported config fields:
  scoring_model_version, ruleset, ignored_paths, generated_paths,
  critical_paths, domain_terms, team_profiles, suppressions,
  report_mode, privacy_mode, enabled_integrations, thresholds,
  output_formats

Extension points:
  - Add new integrations by registering them in INTEGRATION_REGISTRY
  - Add team profiles by adding entries under team_profiles:
  - Override domain_terms for vocabulary-aware scoring

Usage:
  cfg = load_config(Path("./ai-analyzer.yaml"))
  cfg = load_config(None)  # returns defaults
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .domain import ScanConfig


_CONFIG_FILENAMES = [
    "ai-analyzer.yaml", "ai-analyzer.yml",
    "ai-analyzer.json",
    ".ai-analyzer.yaml", ".ai-analyzer.yml",
]


def _find_config(directory: Path) -> Optional[Path]:
    """Look for a config file in the given directory."""
    for name in _CONFIG_FILENAMES:
        candidate = directory / name
        if candidate.exists():
            return candidate
    return None


def _parse_yaml_simple(text: str) -> Dict[str, Any]:
    """
    Very simple YAML parser for flat/list structures without external deps.
    Supports: string values, lists, nested dicts (2 levels).
    Falls back to json for complex structures.
    """
    result: Dict[str, Any] = {}
    current_key = None
    current_list: Optional[List] = None
    current_dict: Optional[Dict] = None
    current_dict_key = None

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        indent = len(line) - len(line.lstrip())

        if stripped.startswith("- ") and indent >= 2:
            # List item
            val = stripped[2:].strip().strip("'\"")
            if current_list is not None:
                current_list.append(val)
            elif current_dict is not None and current_dict_key:
                current_dict.setdefault(current_dict_key, [])
                if isinstance(current_dict[current_dict_key], list):
                    current_dict[current_dict_key].append(val)
            continue

        if ":" in stripped:
            key, _, raw_val = stripped.partition(":")
            key = key.strip()
            raw_val = raw_val.strip()

            if indent == 0:
                # Top-level key
                current_list = None
                current_dict = None
                current_dict_key = None
                current_key = key

                if raw_val:
                    # Inline value
                    result[key] = _parse_scalar(raw_val)
                else:
                    # Will be list or dict
                    result[key] = None
                    current_list = []
                    result[key] = current_list

            elif indent == 2 and current_key:
                # Nested key
                if not isinstance(result.get(current_key), dict):
                    result[current_key] = {}
                    current_dict = result[current_key]
                current_dict_key = key
                if raw_val:
                    current_dict[key] = _parse_scalar(raw_val)
                else:
                    current_dict[key] = []

    return result


def _parse_scalar(val: str) -> Any:
    val = val.strip().strip("'\"")
    if val.lower() in ("true", "yes"):
        return True
    if val.lower() in ("false", "no"):
        return False
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val


def _load_raw(path: Path) -> Dict[str, Any]:
    """Load raw config dict from file."""
    text = path.read_text(encoding="utf-8", errors="ignore")
    suffix = path.suffix.lower()

    if suffix == ".json":
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    # Try stdlib json first in case it's actually JSON
    if text.strip().startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Try yaml if available
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text) or {}
    except ImportError:
        pass

    # Fallback: simple YAML parser
    return _parse_yaml_simple(text)


def load_config(
    config_path: Optional[Path],
    scan_dir: Optional[Path] = None,
) -> ScanConfig:
    """
    Load ScanConfig from a config file.

    Lookup order:
    1. Explicitly provided config_path
    2. Auto-discovery in scan_dir
    3. Auto-discovery in current directory
    4. Defaults (no config file)
    """
    raw: Dict[str, Any] = {}

    # Resolve config file
    resolved_path = None
    if config_path and config_path.exists():
        resolved_path = config_path
    elif scan_dir:
        resolved_path = _find_config(scan_dir)
    if resolved_path is None:
        resolved_path = _find_config(Path.cwd())

    if resolved_path:
        try:
            raw = _load_raw(resolved_path)
        except Exception:
            raw = {}

    # Build ScanConfig from raw dict
    cfg = ScanConfig()

    # Thresholds
    thresh = raw.get("thresholds", {})
    if isinstance(thresh, dict):
        cfg.ai_thresh_high = float(thresh.get("ai_high", cfg.ai_thresh_high))
        cfg.ai_thresh_low  = float(thresh.get("ai_low",  cfg.ai_thresh_low))
        cfg.min_confidence = float(thresh.get("min_confidence", cfg.min_confidence))

    # Paths
    cfg.ignored_paths  = _as_list(raw.get("ignored_paths", []))
    cfg.critical_paths = _as_list(raw.get("critical_paths", []))
    cfg.generated_paths = _as_list(raw.get("generated_paths", []))

    # Domain terms
    cfg.domain_terms = _as_list(raw.get("domain_terms", []))

    # Privacy
    cfg.privacy_mode = str(raw.get("privacy_mode", cfg.privacy_mode))

    # Output
    output_formats = raw.get("output_formats", [])
    if isinstance(output_formats, list) and output_formats:
        cfg.output_format = output_formats[0]
    elif isinstance(output_formats, str):
        cfg.output_format = output_formats

    # Scoring versions
    cfg.scoring_model_version = str(raw.get("scoring_model_version", cfg.scoring_model_version))
    cfg.ruleset_version       = str(raw.get("ruleset_version", cfg.ruleset_version))

    # Suppressions
    suppressions = raw.get("suppressions", {})
    if isinstance(suppressions, dict):
        cfg.suppressions = {str(k): str(v) for k, v in suppressions.items()}

    # Ruleset groups
    cfg.ruleset_groups = _as_list(raw.get("ruleset", cfg.ruleset_groups))

    # Fail on policy
    cfg.fail_on_policy = bool(raw.get("fail_on_policy", cfg.fail_on_policy))

    return cfg


def _as_list(val: Any) -> List[str]:
    if isinstance(val, list):
        return [str(v) for v in val]
    if isinstance(val, str):
        return [val]
    return []


def generate_example_config() -> str:
    """Generate an example ai-analyzer.yaml file content."""
    return """\
# ai-analyzer.yaml — Code Engineering Pattern Analyzer configuration
# v4.0 | https://github.com/your-org/ai-tools

# Scoring model and ruleset versions (for report reproducibility)
scoring_model_version: "4.0"
ruleset_version: "4.0"

# Paths to ignore during scanning (glob patterns supported)
ignored_paths:
  - "target/"
  - "build/"
  - ".gradle/"
  - "node_modules/"
  - "__pycache__/"
  - ".venv/"
  - "venv/"
  - "generated-sources/"

# Paths explicitly known to contain generated code (score excluded from KPI)
generated_paths:
  - "*/generated/**"
  - "*/openapi-client/**"
  - "*_pb2.py"

# Critical production paths (increases risk_score for files in these paths)
critical_paths:
  - "*/billing/**"
  - "*/payment/**"
  - "*/security/**"
  - "*/auth/**"

# Domain-specific vocabulary (used for domain specificity scoring)
domain_terms:
  - "subscription"
  - "tariff"
  - "customer"
  - "contract"
  - "invoice"

# Privacy mode: local (default), safe, hash
privacy_mode: local

# Output formats (first is default)
output_formats:
  - table
  - json
  - markdown

# Score thresholds (override defaults)
thresholds:
  ai_high: 0.68
  ai_low: 0.62
  min_confidence: 0.45

# Suppression rules (rule_id: reason)
suppressions: {}

# Ruleset groups to enable
ruleset:
  - default
  - java-enterprise
  - python-fastapi

# Fail CI if policy conditions are met (see --fail-on-policy flag)
fail_on_policy: false
"""
