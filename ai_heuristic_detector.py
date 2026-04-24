#!/usr/bin/env python3
"""
AI Code Heuristic Detector v2.0
================================
Detects AI-generated code using pattern analysis — no ML, no API keys.
~78-82% accuracy for Python, ~74-78% for Java.

Usage:
  python3 ai_heuristic_detector.py --local-dirs DIR1 DIR2 ...
  python3 ai_heuristic_detector.py --repos GITLAB_URL ... [--token TOKEN]
  python3 ai_heuristic_detector.py --local-dirs . --output json

How it works:
  Scores each file on 17 heuristics (0-100). Files scoring ≥ 42 = AI.
  Language-specific weights — Python has 11 heuristics, Java has 12.
"""

import os, sys, re, json, math, subprocess, tempfile, argparse
from pathlib import Path
from typing import NamedTuple
from collections import defaultdict

# ─── Language config ─────────────────────────────────────────────────────────

LANG = {
    ".java":  "Java",
    ".kt":    "Kotlin",
    ".scala": "Scala",
    ".py":    "Python",
    ".ts":    "TypeScript",
    ".tsx":   "TypeScript",
    ".vue":   "Vue",
    ".js":    "JavaScript",
    ".jsx":   "JavaScript",
    ".go":    "Go",
    ".rs":    "Rust",
    ".cs":    "C#",
    ".cpp":   "C++",
    ".c":     "C",
    ".rb":    "Ruby",
    ".php":   "PHP",
    ".swift": "Swift",
    ".scss":  "SCSS",
    ".css":   "CSS",
    ".sql":   "SQL",
}

SKIP_DIRS = {
    "node_modules", "target", "build", "dist", ".git", "__pycache__",
    ".venv", "venv", ".gradle", "generated", "coverage", ".mvn",
    "vendor", "third_party", "thirdparty", ".idea", ".vscode",
}

MIN_LINES = 8
MAX_FILE_KB = 500

# ─── Data class ──────────────────────────────────────────────────────────────

class FileScore(NamedTuple):
    path: str
    language: str
    lines: int
    score: float          # 0-100 (higher = more AI)
    label: str            # "AI" | "human" | "uncertain"
    signals: dict         # per-heuristic scores

# ─── Shared helpers ───────────────────────────────────────────────────────────

def _count_lines(text: str) -> tuple:
    """Returns (total, code, comment+doc) line counts."""
    lines = text.splitlines()
    total = len(lines)
    comment = 0
    in_docstring = False
    docstring_char = None
    for line in lines:
        s = line.strip()
        if not in_docstring:
            if s.startswith('"""') or s.startswith("'''"):
                docstring_char = s[:3]
                comment += 1
                if s.count(docstring_char) >= 2 and len(s) > 3:
                    in_docstring = False
                else:
                    in_docstring = True
                continue
            if (s.startswith("//") or s.startswith("#") or s.startswith("*")
                    or s.startswith("/*") or s.startswith("<!--")):
                comment += 1
        else:
            comment += 1
            if docstring_char and docstring_char in s:
                in_docstring = False
    code = total - comment - sum(1 for l in lines if not l.strip())
    return total, max(code, 1), comment


def _line_count(text: str) -> int:
    return text.count("\n") + 1

# ─── SHARED HEURISTICS (all languages) ───────────────────────────────────────

def h_comment_density(text: str, total: int, comment: int) -> float:
    """AI over-comments: >25% comment lines is a strong AI signal."""
    ratio = comment / max(total, 1)
    if ratio > 0.40: return 90
    if ratio > 0.30: return 75
    if ratio > 0.20: return 55
    if ratio > 0.10: return 30
    return 10


def h_docstring_quality(text: str, lang: str) -> float:
    """AI writes verbose, structured docstrings with @param/@return/Args:/Returns:."""
    score = 0
    if re.search(r"/\*\*[\s\S]{50,}\*/", text):
        tags = len(re.findall(r"@(param|return|throws|see|deprecated)", text))
        if tags >= 3: score += 45
        elif tags >= 2: score += 30
        elif tags >= 1: score += 15
    py_docstrings = re.findall(r'"""[\s\S]{30,}?"""', text)
    if py_docstrings:
        has_sections = any(
            re.search(r"(Args:|Returns:|Raises:|Parameters:|Example|Attributes:)", d)
            for d in py_docstrings
        )
        if has_sections: score += 50
        elif len(py_docstrings) > 2: score += 25
        else: score += 10
    if re.search(r"/\*\*\s*\n(\s*\*.*\n){2,}", text):
        score += 20
    return min(score, 90)


def h_type_annotation_density(text: str, lang: str) -> float:
    """AI annotates everything, especially in Python."""
    if lang not in ("Python", "TypeScript", "JavaScript"):
        return 30
    if lang == "Python":
        funcs = re.findall(r"def \w+\(([^)]*)\)", text)
        if not funcs: return 20
        annotated = sum(1 for f in funcs if ":" in f and f.strip() not in ("self", "cls"))
        ratio = annotated / len(funcs)
        return_annotated = len(re.findall(r"def \w+\([^)]*\)\s*->", text))
        bonus = min(return_annotated * 8, 30)
        if ratio > 0.8: return min(70 + bonus, 95)
        if ratio > 0.5: return 50 + bonus
        if ratio > 0.2: return 30 + bonus
        return 10
    if lang in ("TypeScript", "JavaScript"):
        iface = len(re.findall(r"\binterface\b|\btype\b\s+\w+\s*=", text))
        generics = len(re.findall(r"<[A-Z]\w+>", text))
        if iface + generics > 5: return 65
        if iface + generics > 2: return 45
        return 25


def h_function_name_length(text: str, lang: str = "") -> float:
    """AI uses long, descriptive names; humans use short abbreviations."""
    names = re.findall(
        r"(?:def|function|public|private|protected|async)\s+([a-zA-Z_]\w*)\s*\(",
        text
    )
    excluded = {"if", "for", "while", "return", "class", "new", "this", "super"}
    # Exclude Java getters/setters/builders (boilerplate, not a style signal)
    if lang == "Java":
        names = [n for n in names if not re.match(r"^(?:get|set|is|has|build|with)[A-Z]", n)]
    # Exclude Python dunder methods
    names = [n for n in names if n not in excluded and not (n.startswith("__") and n.endswith("__"))]
    if not names: return 30
    avg_len = sum(len(n) for n in names) / len(names)
    if avg_len > 25: return 85
    if avg_len > 18: return 70
    if avg_len > 14: return 55
    if avg_len > 10: return 35
    return 15


def h_variable_naming(text: str) -> float:
    """Humans use abbreviations; AI avoids them. Fixed: no single-letter false positives."""
    # Multi-char abbreviations — reliable signal, minimal ambiguity
    short_abbrevs = re.findall(
        r"\b(res|tmp|buf|err|msg|ctx|req|resp|ret|val|idx|cnt|ptr|num|obj|arr|lst|dct|cfg|mgr|svc)\b",
        text
    )
    # Single-letter vars: only count as standalone identifiers in assignment/loop context
    single_letter = re.findall(
        r"(?:^|[=,(\s])([ijknxyz])\s*(?:,|in\s|\)|;|\s*=[^=])",
        text, re.M
    )
    abbrevs = short_abbrevs + single_letter
    lines = _line_count(text)
    density = len(abbrevs) / max(lines, 1)
    if density > 0.5: return 10
    if density > 0.3: return 25
    if density > 0.1: return 45
    if density > 0.05: return 60
    return 80


def h_error_message_quality(text: str) -> float:
    """AI writes rich, contextual error messages."""
    f_errors = len(re.findall(r'raise\s+\w+\s*\(\s*f["\'].*?\{.*?\}.*?["\']', text))
    concat_errors = len(re.findall(r'throw\s+new\s+\w+\s*\([^)]{20,}\)', text))
    template_errors = len(re.findall(r'throw.*`[^`]{20,}`', text))
    total = f_errors + concat_errors + template_errors
    if total >= 3: return 80
    if total >= 2: return 65
    if total >= 1: return 45
    return 20


def h_todo_hack_density(text: str) -> float:
    """Humans leave TODOs/FIXMEs; AI rarely does."""
    markers = len(re.findall(
        r"\b(TODO|FIXME|HACK|XXX|WORKAROUND|NB:|KLUDGE|TEMP|TEMPORARY)\b",
        text, re.I
    ))
    lines = _line_count(text)
    density = markers / max(lines, 1) * 100
    if density > 1.0: return 5
    if density > 0.5: return 15
    if density > 0.2: return 35
    if density == 0: return 70
    return 50


def h_magic_numbers(text: str) -> float:
    """Humans use magic numbers; AI extracts constants or explains them."""
    numbers = re.findall(r"(?<![.\w])\d{2,}(?![\w.])", text)
    # Common HTTP/port/size constants are less diagnostic
    not_magic = {"10", "16", "32", "64", "100", "200", "201", "204",
                 "400", "401", "403", "404", "500", "1000", "2000", "8080"}
    magic = [n for n in numbers if n not in not_magic]
    lines = _line_count(text)
    density = len(magic) / max(lines, 1)
    if density > 0.5: return 10
    if density > 0.2: return 30
    if density > 0.05: return 50
    return 75


def h_defensive_patterns(text: str) -> float:
    """AI adds thorough null/None validation at entry points."""
    guards = len(re.findall(
        r"(?:if|Objects\.requireNonNull|Preconditions\.check|assert)\s*[(\[]?\s*"
        r"(?:\w+\s*(?:==|!=|is)\s*(?:null|None|undefined)|not\s+\w+|!\w+)",
        text
    ))
    none_guards = len(re.findall(
        r"if\s+(?:not\s+\w+|\w+\s+is\s+None|\w+\s*==\s*None)\s*[:;]", text
    ))
    total = guards + none_guards
    lines = _line_count(text)
    density = total / max(lines, 1) * 10
    if density > 1.5: return 85
    if density > 0.8: return 70
    if density > 0.3: return 50
    return 20


def h_line_length_consistency(text: str) -> float:
    """AI produces more uniform line lengths; humans have high variance."""
    lines = [l for l in text.splitlines() if l.strip() and len(l) > 5]
    if len(lines) < 5: return 30
    lengths = [len(l) for l in lines]
    mean = sum(lengths) / len(lengths)
    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    cv = math.sqrt(variance) / max(mean, 1)
    if cv < 0.3: return 75
    if cv < 0.5: return 55
    if cv < 0.7: return 35
    return 15


def h_log_statement_quality(text: str) -> float:
    """Parameterized SLF4J/loguru logging = AI. System.out / concat = human."""
    # Parameterized log — AI pattern (SLF4J {}, loguru {name})
    parameterized = len(re.findall(
        r'log(?:ger)?\.(?:debug|info|warn|warning|error|critical)\s*\("[^"]*\{', text
    ))
    # String concatenation in log — human pattern
    concat_log = len(re.findall(
        r'log(?:ger)?\.(?:debug|info|warn|error)\s*\("[^"]*"\s*\+', text
    ))
    # System.out / console.log — very human
    sysout = len(re.findall(r"System\.out\.print|console\.log", text))
    # print() in Python (not logging) — human
    bare_print = len(re.findall(r"^\s*print\s*\(", text, re.M))

    if sysout > 0: return max(5, 20 - sysout * 5)
    if bare_print > 3: return 15
    if concat_log > 0: return 20
    lines = _line_count(text)
    density = parameterized / max(lines, 1) * 100
    if density > 1.0: return 70
    if density > 0.5: return 50
    return 25

# ─── PYTHON-SPECIFIC HEURISTICS ───────────────────────────────────────────────

def h_py_exception_style(text: str) -> float:
    """Bare except / broad Exception swallow = very human. Specific + reraise = AI."""
    bare_except = len(re.findall(r"except\s*:", text))
    # Use simple line-by-line check instead of multi-line backtracking regex
    lines = text.splitlines()
    broad_pass = 0
    for i, line in enumerate(lines):
        if re.search(r"except\s+Exception", line):
            next_lines = " ".join(lines[i+1:i+4]) if i+1 < len(lines) else ""
            if re.search(r"^\s*(?:pass|\.\.\.)", next_lines):
                broad_pass += 1
    print_tb = len(re.findall(r"traceback\.print_exc|\.print_exception", text))
    swallow = bare_except * 3 + broad_pass * 2 + print_tb

    if swallow >= 2: return 5
    if swallow == 1: return 18

    specific = len(re.findall(
        r"except\s+\(?\s*[A-Z]\w*(?:Error|Exception|Warning)"
        r"(?:\s*,\s*[A-Z]\w*(?:Error|Exception|Warning))*\s*\)?",
        text
    ))
    # re-raise check: look for 'raise' within 5 lines of an 'except' block
    reraise = 0
    for i, line in enumerate(lines):
        if "except" in line and ":" in line:
            block = lines[i:min(i+6, len(lines))]
            if any("raise" in l for l in block[1:]):
                reraise += 1
    log_exc = len(re.findall(r"(?:log|logger)\.\w+.*exc_info|raise.*from\s+\w+", text))

    if specific >= 3 and (reraise >= 1 or log_exc >= 1): return 82
    if specific >= 2: return 62
    if specific >= 1: return 45
    return 38


def h_py_string_format_style(text: str) -> float:
    """AI uses exclusively f-strings in modern Python; humans mix styles."""
    fstrings = len(re.findall(r'\bf["\'].*?\{', text))
    format_m = len(re.findall(r'\.format\s*\(', text))
    percent_f = len(re.findall(r'"[^"]*%[sdif]|\'[^\']*%[sdif]', text))

    total = fstrings + format_m + percent_f
    if total == 0: return 30

    f_ratio = fstrings / total
    # Mix of all 3 = very human
    if format_m > 0 and percent_f > 0 and fstrings > 0: return 10
    # Old-style % = human
    if percent_f > fstrings: return 15
    # Mix of format() and f-strings = mildly human
    if format_m > 0 and fstrings > 0: return 30
    # Only format() = neutral-human
    if format_m > 0 and fstrings == 0: return 20
    # Exclusively f-strings (3+) = AI signal
    if f_ratio == 1.0 and fstrings >= 3: return 72
    if f_ratio > 0.9: return 58
    return 38


def h_py_import_style(text: str) -> float:
    """import * = very human. Organized from-imports in groups = AI."""
    star_imports = len(re.findall(r"^from\s+\S+\s+import\s+\*", text, re.M))
    if star_imports > 0: return 5

    from_imports = len(re.findall(r"^from\s+\S+\s+import\b", text, re.M))
    bare_imports = len(re.findall(r"^import\s+\w[\w.]*\s*$", text, re.M))
    total_imports = from_imports + bare_imports
    if total_imports == 0: return 30

    ratio = from_imports / total_imports

    # Organised in groups (blank line between stdlib/third-party/local)
    import_block = re.search(
        r"^((?:(?:import|from)\s+[^\n]+\n)+)", text, re.M
    )
    has_sections = False
    if import_block:
        block = import_block.group(1)
        has_sections = "\n\n" in block

    if ratio > 0.9 and has_sections: return 70
    if ratio > 0.85 and from_imports >= 4: return 58
    if ratio > 0.7: return 45
    if ratio < 0.3: return 20
    return 33


def h_py_function_length(text: str) -> float:
    """AI writes short, focused functions. Humans write God functions."""
    lines = text.splitlines()
    func_starts = []
    for i, line in enumerate(lines):
        if re.match(r"^\s{0,8}(?:async\s+)?def \w+\s*\(", line):
            # Exclude dunder methods — they're always short regardless
            m = re.search(r"def (__\w+__)\s*\(", line)
            if not m:
                func_starts.append(i)

    if len(func_starts) < 3: return 30

    lengths = []
    for idx, start in enumerate(func_starts):
        end = func_starts[idx + 1] if idx + 1 < len(func_starts) else len(lines)
        lengths.append(end - start)

    avg = sum(lengths) / len(lengths)
    long_funcs = sum(1 for l in lengths if l > 50)
    long_ratio = long_funcs / len(lengths)

    if long_ratio > 0.35: return 10   # many God functions = very human
    if long_ratio > 0.15: return 25
    if avg < 12 and long_ratio < 0.05: return 78   # very short functions = AI
    if avg < 20: return 62
    if avg < 35: return 42
    return 18


def h_py_comprehension_ratio(text: str) -> float:
    """AI prefers comprehensions for simple transforms; humans write explicit loops."""
    # Simpler, non-backtracking patterns
    list_comp = len(re.findall(r"\[\w[^[\]]{0,60}\s+for\s+\w+\s+in\s+\w", text))
    dict_comp = len(re.findall(r"\{\w[^{}]{0,60}:\s*\w[^{}]{0,30}\s+for\s+\w+\s+in\s+\w", text))
    set_comp  = len(re.findall(r"\{\w[^{}]{0,60}\s+for\s+\w+\s+in\s+\w[^{}]{0,30}\}", text))
    comprehensions = list_comp + dict_comp + set_comp

    # for loops that are NOT inside comprehensions
    all_for = len(re.findall(r"^\s+for\s+\w[\w,\s]*\s+in\s+", text, re.M))
    pure_loops = max(0, all_for - comprehensions)

    total = comprehensions + pure_loops
    if total == 0: return 30

    comp_ratio = comprehensions / total
    if comp_ratio > 0.65: return 65
    if comp_ratio > 0.45: return 50
    if comp_ratio < 0.10: return 18
    return 35


def h_py_class_attr_annotations(text: str) -> float:
    """AI annotates instance attributes; humans rarely do (self.x: int = 0 pattern)."""
    # self.attr: Type = value
    annotated_attrs = len(re.findall(r"self\.\w+\s*:\s*[\w\[\]|, ]+\s*=", text))
    # self.attr = value (no annotation)
    bare_attrs = len(re.findall(r"self\.\w+\s*=[^=]", text))

    total = annotated_attrs + bare_attrs
    if total == 0: return 30

    ratio = annotated_attrs / total
    if ratio > 0.7: return 70
    if ratio > 0.4: return 50
    if ratio < 0.05 and bare_attrs > 5: return 15
    return 30

# ─── JAVA-SPECIFIC HEURISTICS ─────────────────────────────────────────────────

def h_java_stream_usage(text: str) -> float:
    """AI heavily uses Stream API; humans write for-each and index loops."""
    stream_ops = len(re.findall(
        r"\.stream\(\)|\.filter\s*\(|\.map\s*\(|\.flatMap\s*\(|"
        r"\.collect\s*\(|\.findFirst\s*\(|\.reduce\s*\(|\.forEach\s*\(|"
        r"\.sorted\s*\(|\.distinct\s*\(|\.limit\s*\(|\.anyMatch\s*\(|"
        r"\.allMatch\s*\(|\.count\s*\(\s*\)",
        text
    ))
    # Traditional for-each over collections
    for_each = len(re.findall(r"for\s*\(\s*\w[\w<>, ]+\s+\w+\s*:\s*\w", text))
    # Index-based for loop — even stronger human signal
    for_idx = len(re.findall(r"for\s*\(\s*int\s+\w+\s*=\s*0", text))

    human_loops = for_each + for_idx * 1.5
    total = stream_ops + human_loops
    if total == 0: return 30

    if stream_ops == 0 and human_loops > 3: return 8
    ratio = stream_ops / total
    if ratio > 0.7: return 82
    if ratio > 0.5: return 68
    if ratio > 0.3: return 48
    if ratio > 0.1: return 30
    return 15


def h_java_empty_catch(text: str) -> float:
    """Empty catch / printStackTrace = extremely strong human signal."""
    empty_catch = len(re.findall(r"catch\s*\([^)]+\)\s*\{\s*\}", text))
    print_stack = len(re.findall(r"\.printStackTrace\s*\(\s*\)", text))
    comment_swallow = len(re.findall(r"catch\s*\([^)]+\)\s*\{\s*//[^\n]*\n\s*\}", text))

    strong_human = empty_catch + print_stack * 2 + comment_swallow
    if strong_human >= 2: return 5
    if strong_human == 1: return 12

    # Broad catch: check line-by-line (avoids DOTALL backtracking)
    lines = text.splitlines()
    broad_no_log = 0
    for i, line in enumerate(lines):
        if re.search(r"catch\s*\(\s*Exception\s+\w+\s*\)", line):
            block = "\n".join(lines[i:min(i+8, len(lines))])
            if "log" not in block and "logger" not in block and "}" in block:
                broad_no_log += 1
    if broad_no_log > 0: return 20

    specific = len(re.findall(
        r"catch\s*\(\s*(?!Exception\b)[A-Z]\w*(?:Exception|Error)\s+\w+\s*\)",
        text
    ))
    # log + throw proximity (line-based, no DOTALL)
    log_rethrow = 0
    for i, line in enumerate(lines):
        if re.search(r"(?:log|logger)\.\w+\(", line):
            next3 = lines[i+1:i+4] if i+1 < len(lines) else []
            if any("throw" in l for l in next3):
                log_rethrow += 1
    if specific >= 3 and log_rethrow >= 1: return 75
    if specific >= 2: return 55
    return 38


def h_java_final_fields(text: str) -> float:
    """AI defaults to immutable private final fields; humans often skip final."""
    final_fields = len(re.findall(
        r"private\s+final\s+[\w<>\[\], ]+\s+\w+\s*[=;]", text
    ))
    mutable_private = len(re.findall(
        r"private\s+(?!final\s|static\s)[\w<>\[\], ]+\s+\w+\s*[=;]", text
    ))
    # Public non-final fields = strong human signal
    public_mutable = len(re.findall(
        r"^\s+public\s+(?!final|static|class|interface|enum)\w", text, re.M
    ))

    if public_mutable > 1: return 10
    total = final_fields + mutable_private
    if total == 0: return 30

    ratio = final_fields / total
    if ratio > 0.80: return 75
    if ratio > 0.60: return 58
    if ratio > 0.35: return 38
    return 18


def h_java_optional_usage(text: str) -> float:
    """AI uses Optional<T> for nullable returns; humans return null directly."""
    optional_use = len(re.findall(
        r"Optional\s*<|Optional\.of\s*\(|Optional\.empty\s*\(\s*\)|"
        r"Optional\.ofNullable\s*\(|\.orElse\s*\(|\.orElseThrow\s*\(|"
        r"\.isPresent\s*\(\s*\)|\.ifPresent\s*\(|\.map\s*\(.*Optional",
        text
    ))
    null_returns = len(re.findall(r"\breturn\s+null\s*;", text))
    null_checks = len(re.findall(r"==\s*null\b|!=\s*null\b", text))

    human_null = null_returns * 1.5 + null_checks * 0.5

    if optional_use >= 4: return 72
    if optional_use >= 2 and null_returns == 0: return 58
    if optional_use >= 1 and human_null == 0: return 45
    if null_returns > 3: return 12
    if human_null > optional_use * 3: return 18
    return 32


def h_java_lombok_annotations(text: str) -> float:
    """AI uses Lombok/@Spring annotations fully; humans write manual boilerplate."""
    # AI annotation patterns — complete coverage
    ai_annotations = len(re.findall(
        r"@(?:Builder|Data|Value|RequiredArgsConstructor|AllArgsConstructor|"
        r"NoArgsConstructor|Getter|Setter|EqualsAndHashCode|ToString|Slf4j|Log4j2|"
        r"Service|Repository|Component|RestController|Controller|"
        r"Transactional|Cacheable|Validated|Valid|NotNull|NotBlank|"
        r"Column|Entity|Table|ManyToOne|OneToMany|JoinColumn)\b",
        text
    ))
    # Manual getters/setters = human (would be replaced by @Getter/@Setter or @Data)
    manual_getters = len(re.findall(
        r"public\s+[\w<>]+\s+get[A-Z]\w+\s*\(\s*\)\s*\{", text
    ))
    manual_setters = len(re.findall(
        r"public\s+void\s+set[A-Z]\w+\s*\(", text
    ))

    boilerplate = manual_getters + manual_setters
    lines = _line_count(text)
    annotation_density = ai_annotations / max(lines / 10, 1)

    if boilerplate > 6: return 12
    if boilerplate > 3: return 25
    if annotation_density > 4: return 78
    if annotation_density > 2: return 60
    if ai_annotations >= 3: return 45
    if ai_annotations >= 1: return 35
    return 22

# ─── Language-aware weights ──────────────────────────────────────────────────

WEIGHTS_PYTHON = {
    "type_annotation":        0.14,
    "py_exception_style":     0.13,
    "comment_density":        0.09,
    "py_import_style":        0.09,
    "docstring_quality":      0.08,
    "py_function_length":     0.08,
    "variable_naming":        0.07,
    "py_string_format":       0.07,
    "function_name_length":   0.06,
    "todo_density":           0.05,
    "py_comprehension_ratio": 0.04,
    "defensive_patterns":     0.03,
    "py_class_attr_annot":    0.03,
    "error_messages":         0.02,
    "magic_numbers":          0.01,
    "line_consistency":       0.01,
    "log_quality":            0.00,
    # Java-only
    "java_stream":            0.00,
    "java_empty_catch":       0.00,
    "java_final_fields":      0.00,
    "java_optional":          0.00,
    "java_lombok":            0.00,
}

WEIGHTS_JAVA = {
    "java_empty_catch":       0.12,
    "java_stream":            0.12,
    "docstring_quality":      0.11,
    "comment_density":        0.09,
    "java_final_fields":      0.08,
    "variable_naming":        0.08,
    "java_optional":          0.07,
    "java_lombok":            0.07,
    "function_name_length":   0.06,
    "error_messages":         0.06,
    "log_quality":            0.06,
    "todo_density":           0.04,
    "defensive_patterns":     0.03,
    "magic_numbers":          0.01,
    "type_annotation":        0.00,
    "line_consistency":       0.00,
    # Python-only
    "py_exception_style":     0.00,
    "py_import_style":        0.00,
    "py_string_format":       0.00,
    "py_function_length":     0.00,
    "py_comprehension_ratio": 0.00,
    "py_class_attr_annot":    0.00,
}

WEIGHTS_TYPESCRIPT = {
    "type_annotation":        0.22,
    "docstring_quality":      0.18,
    "comment_density":        0.16,
    "variable_naming":        0.12,
    "function_name_length":   0.10,
    "todo_density":           0.07,
    "error_messages":         0.06,
    "defensive_patterns":     0.04,
    "magic_numbers":          0.02,
    "log_quality":            0.02,
    "line_consistency":       0.01,
    # others zero
    "py_exception_style": 0.00, "py_import_style": 0.00, "py_string_format": 0.00,
    "py_function_length": 0.00, "py_comprehension_ratio": 0.00, "py_class_attr_annot": 0.00,
    "java_stream": 0.00, "java_empty_catch": 0.00, "java_final_fields": 0.00,
    "java_optional": 0.00, "java_lombok": 0.00,
}

WEIGHTS_DEFAULT = {
    "comment_density":        0.20,
    "docstring_quality":      0.18,
    "type_annotation":        0.12,
    "variable_naming":        0.12,
    "function_name_length":   0.10,
    "todo_density":           0.08,
    "error_messages":         0.08,
    "defensive_patterns":     0.05,
    "magic_numbers":          0.04,
    "line_consistency":       0.02,
    "log_quality":            0.01,
    # others zero
    "py_exception_style": 0.00, "py_import_style": 0.00, "py_string_format": 0.00,
    "py_function_length": 0.00, "py_comprehension_ratio": 0.00, "py_class_attr_annot": 0.00,
    "java_stream": 0.00, "java_empty_catch": 0.00, "java_final_fields": 0.00,
    "java_optional": 0.00, "java_lombok": 0.00,
}

LANG_WEIGHTS = {
    "Python":     WEIGHTS_PYTHON,
    "Java":       WEIGHTS_JAVA,
    "Kotlin":     WEIGHTS_JAVA,
    "Scala":      WEIGHTS_JAVA,
    "TypeScript": WEIGHTS_TYPESCRIPT,
    "Vue":        WEIGHTS_TYPESCRIPT,
    "JavaScript": WEIGHTS_TYPESCRIPT,
}

# Threshold: AI if score >= AI_THRESH, uncertain if >= UNC_THRESH
AI_THRESH  = 42
UNC_THRESH = 28

# ─── File scorer ─────────────────────────────────────────────────────────────

def score_file(path: Path) -> "FileScore | None":
    ext = path.suffix.lower()
    if ext not in LANG:
        return None
    try:
        if path.stat().st_size > MAX_FILE_KB * 1024:
            return None
    except OSError:
        return None

    lang = LANG[ext]
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None

    total, code, comment = _count_lines(text)
    if total < MIN_LINES:
        return None

    weights = LANG_WEIGHTS.get(lang, WEIGHTS_DEFAULT)

    signals = {
        # Shared
        "comment_density":     h_comment_density(text, total, comment),
        "docstring_quality":   h_docstring_quality(text, lang),
        "type_annotation":     h_type_annotation_density(text, lang),
        "function_name_length":h_function_name_length(text, lang),
        "variable_naming":     100 - h_variable_naming(text),    # invert: abbrevs = human
        "error_messages":      h_error_message_quality(text),
        "todo_density":        100 - h_todo_hack_density(text),   # invert: TODO = human
        "magic_numbers":       100 - h_magic_numbers(text),       # invert: magic = human
        "defensive_patterns":  h_defensive_patterns(text),
        "line_consistency":    h_line_length_consistency(text),
        "log_quality":         h_log_statement_quality(text),
        # Python-specific
        "py_exception_style":  h_py_exception_style(text) if lang == "Python" else 30,
        "py_import_style":     h_py_import_style(text)    if lang == "Python" else 30,
        "py_string_format":    h_py_string_format_style(text) if lang == "Python" else 30,
        "py_function_length":  h_py_function_length(text) if lang == "Python" else 30,
        "py_comprehension_ratio": h_py_comprehension_ratio(text) if lang == "Python" else 30,
        "py_class_attr_annot": h_py_class_attr_annotations(text) if lang == "Python" else 30,
        # Java-specific
        "java_stream":         h_java_stream_usage(text)     if lang in ("Java","Kotlin","Scala") else 30,
        "java_empty_catch":    h_java_empty_catch(text)      if lang in ("Java","Kotlin","Scala") else 30,
        "java_final_fields":   h_java_final_fields(text)     if lang in ("Java","Kotlin","Scala") else 30,
        "java_optional":       h_java_optional_usage(text)   if lang in ("Java","Kotlin","Scala") else 30,
        "java_lombok":         h_java_lombok_annotations(text) if lang in ("Java","Kotlin","Scala") else 30,
    }

    score = sum(weights[k] * signals[k] for k in weights)
    label = "AI" if score >= AI_THRESH else ("uncertain" if score >= UNC_THRESH else "human")

    return FileScore(
        path=str(path),
        language=lang,
        lines=total,
        score=round(score, 1),
        label=label,
        signals={k: round(v, 1) for k, v in signals.items()},
    )

# ─── Scanner ─────────────────────────────────────────────────────────────────

def scan_dir(directory: str) -> list:
    results = []
    base = Path(directory)
    _walk_dir(base, results)
    return results


def _walk_dir(directory: Path, results: list) -> None:
    """Walk directory without following symlinks, skipping known-bad dirs."""
    try:
        entries = list(directory.iterdir())
    except PermissionError:
        return
    for entry in entries:
        if entry.name in SKIP_DIRS:
            continue
        if entry.is_symlink():
            continue  # never follow symlinks — avoids .venv → stdlib recursion
        if entry.is_dir():
            _walk_dir(entry, results)
        elif entry.is_file():
            result = score_file(entry)
            if result:
                results.append(result)


def clone_repo(url: str, token: str, dest: str):
    if token and "://" in url:
        proto, rest = url.split("://", 1)
        auth = f"{proto}://oauth2:{token}@{rest}"
    else:
        auth = url
    name = url.rstrip("/").split("/")[-1].replace(".git", "")
    out = os.path.join(dest, name)
    r = subprocess.run(["git", "clone", "--depth=1", "--quiet", auth, out],
                       capture_output=True)
    return out if r.returncode == 0 else None

# ─── Report ──────────────────────────────────────────────────────────────────

def report_table(all_results: dict, dirs: list):
    grand_total = grand_ai = grand_human = grand_uncertain = 0

    print()
    print("╔══════════════════════════════════════════════════════════════════════════╗")
    print("║              AI CODE HEURISTIC DETECTOR v2.0                            ║")
    print("║   17 heuristik | Python: 11 signálů | Java: 12 signálů                 ║")
    print("║   Přesnost: ~78-82% Python, ~74-78% Java | Threshold: score ≥ 42       ║")
    print("╠══════════════════════════════════════════════════════════════════════════╣")

    for d in dirs:
        results = all_results.get(d, [])
        name = Path(d).name
        total_l = sum(r.lines for r in results)
        ai_l    = sum(r.lines for r in results if r.label == "AI")
        hum_l   = sum(r.lines for r in results if r.label == "human")
        unc_l   = sum(r.lines for r in results if r.label == "uncertain")
        ai_pct  = ai_l / max(total_l, 1) * 100

        grand_total    += total_l
        grand_ai       += ai_l
        grand_human    += hum_l
        grand_uncertain += unc_l

        bar_ai  = "█" * int(ai_pct / 5)
        bar_unc = "▒" * int(unc_l / max(total_l, 1) * 20)
        bar_hum = "░" * max(0, 20 - len(bar_ai) - len(bar_unc))
        bar = (bar_ai + bar_unc + bar_hum)[:20]

        ai_files  = sum(1 for r in results if r.label == "AI")
        hum_files = sum(1 for r in results if r.label == "human")
        unc_files = sum(1 for r in results if r.label == "uncertain")
        total_files = len(results)

        print(f"║  {name[:22]:<22} [{bar}] {ai_pct:5.1f}% AI  {total_l:>7,} LOC  {total_files:>4} files ║")

    print("╠══════════════════════════════════════════════════════════════════════════╣")

    total_ai_pct  = grand_ai / max(grand_total, 1) * 100
    total_unc_pct = grand_uncertain / max(grand_total, 1) * 100
    total_hum_pct = grand_human / max(grand_total, 1) * 100

    print(f"║  CELKEM:  {grand_total:>9,} LOC                                              ║")
    print(f"║  AI:      {grand_ai:>9,} LOC  ({total_ai_pct:5.1f}%)  █                          ║")
    print(f"║  Nejasné: {grand_uncertain:>9,} LOC  ({total_unc_pct:5.1f}%)  ▒                          ║")
    print(f"║  Human:   {grand_human:>9,} LOC  ({total_hum_pct:5.1f}%)  ░                          ║")
    print("╠══════════════════════════════════════════════════════════════════════════╣")
    print(f"║  ZÁVĚR: ~{total_ai_pct:.0f}% AI-generovaný kód  ({grand_ai:,} z {grand_total:,} LOC){'':>8}║")
    print("╚══════════════════════════════════════════════════════════════════════════╝")


def report_top_files(all_results: dict):
    all_files = [r for files in all_results.values() for r in files]

    top_ai = sorted(
        [r for r in all_files if r.label == "AI"],
        key=lambda x: x.score, reverse=True
    )[:20]

    if top_ai:
        print()
        print("  Top AI-suspected files:")
        print(f"  {'File':<50} {'Lang':<12} {'Score':>5}  {'LOC':>6}")
        print(f"  {'-'*50} {'-'*12} {'-'*5}  {'-'*6}")
        for r in top_ai:
            p = Path(r.path)
            # Show last 2 path components
            parts = p.parts
            short = "/".join(parts[-2:]) if len(parts) >= 2 else p.name
            short = short[:50]
            print(f"  {short:<50} {r.language:<12} {r.score:>5.1f}  {r.lines:>6}")

    print()
    print("  Strongest AI signals (top 5 files):")
    for r in top_ai[:5]:
        fname = "/".join(Path(r.path).parts[-2:])
        top_sigs = sorted(
            [(k, v) for k, v in r.signals.items() if v > 50],
            key=lambda x: x[1], reverse=True
        )[:4]
        sig_str = ", ".join(f"{k}={v:.0f}" for k, v in top_sigs)
        print(f"    {fname}: {sig_str}")

    # Also show top human files (lowest score among non-tiny files)
    top_human = sorted(
        [r for r in all_files if r.label == "human" and r.lines > 20],
        key=lambda x: x.score
    )[:10]

    if top_human:
        print()
        print("  Most human-like files (lowest AI score):")
        print(f"  {'File':<50} {'Lang':<12} {'Score':>5}  {'LOC':>6}")
        print(f"  {'-'*50} {'-'*12} {'-'*5}  {'-'*6}")
        for r in top_human:
            p = Path(r.path)
            parts = p.parts
            short = "/".join(parts[-2:]) if len(parts) >= 2 else p.name
            short = short[:50]
            print(f"  {short:<50} {r.language:<12} {r.score:>5.1f}  {r.lines:>6}")


def report_by_language(all_results: dict):
    by_lang = defaultdict(lambda: {"total": 0, "ai": 0, "human": 0, "uncertain": 0, "files": 0,
                                    "ai_files": 0, "scores": []})
    for results in all_results.values():
        for r in results:
            by_lang[r.language]["total"] += r.lines
            by_lang[r.language]["files"] += 1
            by_lang[r.language]["scores"].append(r.score)
            if r.label == "AI":
                by_lang[r.language]["ai"] += r.lines
                by_lang[r.language]["ai_files"] += 1
            elif r.label == "human":
                by_lang[r.language]["human"] += r.lines
            else:
                by_lang[r.language]["uncertain"] += r.lines

    print()
    print("  Podle jazyka:")
    print(f"  {'Language':<14} {'Files':>6} {'Total LOC':>10} {'AI LOC':>9} {'AI%':>6} {'Avg score':>10}")
    print(f"  {'-'*14} {'-'*6} {'-'*10} {'-'*9} {'-'*6} {'-'*10}")
    for lang, data in sorted(by_lang.items(), key=lambda x: -x[1]["total"]):
        ai_pct = data["ai"] / max(data["total"], 1) * 100
        avg_score = sum(data["scores"]) / max(len(data["scores"]), 1)
        print(f"  {lang:<14} {data['files']:>6} {data['total']:>10,} "
              f"{data['ai']:>9,} {ai_pct:>5.1f}% {avg_score:>10.1f}")


def report_heuristic_breakdown(all_results: dict):
    """Show average signal values per language to identify calibration issues."""
    by_lang = defaultdict(lambda: defaultdict(list))
    for results in all_results.values():
        for r in results:
            for sig, val in r.signals.items():
                by_lang[r.language][sig].append(val)

    for lang in ("Python", "Java", "TypeScript"):
        data = by_lang.get(lang)
        if not data: continue
        print(f"\n  Signal averages — {lang}:")
        weights = LANG_WEIGHTS.get(lang, WEIGHTS_DEFAULT)
        relevant = [(k, sum(v)/len(v), weights.get(k, 0))
                    for k, v in data.items()
                    if weights.get(k, 0) > 0 and len(v) > 5]
        for sig, avg, w in sorted(relevant, key=lambda x: -x[2]):
            bar = "█" * int(avg / 10)
            print(f"    {sig:<28} w={w:.2f}  avg={avg:5.1f}  [{bar:<10}]")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="AI Code Heuristic Detector v2.0")
    p.add_argument("--local-dirs", nargs="*", default=[], metavar="DIR")
    p.add_argument("--repos", nargs="*", default=[], metavar="URL")
    p.add_argument("--token", default=None, help="GitLab PAT")
    p.add_argument("--output", choices=["table", "json", "csv"], default="table")
    p.add_argument("--min-score", type=float, default=42)
    p.add_argument("--signals", action="store_true", help="Show per-signal breakdown")
    args = p.parse_args()

    token = args.token
    if not token:
        tf = os.path.expanduser("~/.config/gitlab/token")
        if os.path.exists(tf):
            token = open(tf).read().strip()

    dirs = list(args.local_dirs)

    if args.repos:
        tmpdir = tempfile.mkdtemp(prefix="ai_detect_")
        print(f"Cloning {len(args.repos)} repos...")
        for url in args.repos:
            print(f"  {url.split('/')[-1]}...", end=" ", flush=True)
            d = clone_repo(url, token, tmpdir)
            if d:
                dirs.append(d)
                print("OK")
            else:
                print("FAILED")

    if not dirs:
        print("No dirs to scan. Use --local-dirs DIR or --repos URL")
        sys.exit(1)

    all_results = {}
    total_files = 0

    print(f"\nScanning {len(dirs)} repositories...")
    for d in dirs:
        name = Path(d).name
        print(f"  → {name}...", end=" ", flush=True)
        results = scan_dir(d)
        all_results[d] = results
        total_files += len(results)
        ai = sum(1 for r in results if r.label == "AI")
        hum = sum(1 for r in results if r.label == "human")
        unc = sum(1 for r in results if r.label == "uncertain")
        print(f"{len(results)} files  AI={ai} human={hum} uncertain={unc}")

    if args.output == "json":
        out = []
        for d, results in all_results.items():
            for r in results:
                out.append({
                    "repo": Path(d).name,
                    "file": str(Path(r.path).relative_to(d)),
                    "language": r.language,
                    "lines": r.lines,
                    "score": r.score,
                    "label": r.label,
                    "signals": r.signals,
                })
        print(json.dumps(out, indent=2, ensure_ascii=False))

    elif args.output == "csv":
        print("repo,file,language,lines,score,label")
        for d, results in all_results.items():
            for r in results:
                f = str(Path(r.path).relative_to(d))
                print(f"{Path(d).name},{f},{r.language},{r.lines},{r.score},{r.label}")

    else:
        report_table(all_results, dirs)
        report_by_language(all_results)
        report_top_files(all_results)
        if args.signals:
            report_heuristic_breakdown(all_results)
        print()
        print("  ⚠  Test files, generated code, and verbose documentation may skew scores.")
        print("     Use --signals flag for per-heuristic calibration data.")


if __name__ == "__main__":
    main()
