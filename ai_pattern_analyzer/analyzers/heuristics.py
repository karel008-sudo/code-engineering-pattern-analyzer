"""
analyzers/heuristics.py — Refined code-style heuristics.

All functions accept (text: str, lang: str) and return float [0.0, 1.0].
1.0 = strong AI-like pattern. 0.5 = neutral.

Heuristics kept from v2.0 with fixes:
  - Downweighted based on empirical discrimination data
  - Single-letter variable regex fixed (no substring false positives)
  - Java getters/setters excluded from function_name_length
  - Java log_quality now non-zero weight
  - line_length_consistency removed (near-zero discrimination)
"""
from __future__ import annotations
import re
from typing import List, Tuple


# ── Comment density ───────────────────────────────────────────────────────────

def comment_density(text: str, lang: str) -> float:
    """Over-commenting relative to code = AI-like."""
    lines = text.splitlines()
    total = max(len(lines), 1)
    comment_count = 0
    in_block = False

    for line in lines:
        s = line.strip()
        if in_block:
            comment_count += 1
            if "*/" in s:
                in_block = False
            continue
        if s.startswith("/*") or s.startswith("/**"):
            comment_count += 1
            if "*/" not in s:
                in_block = True
        elif (s.startswith("//") or s.startswith("#") or
              s.startswith("*") or s.startswith("<!--")):
            comment_count += 1

    ratio = comment_count / total
    if ratio > 0.40: return 0.95
    if ratio > 0.30: return 0.80
    if ratio > 0.20: return 0.60
    if ratio > 0.12: return 0.35
    return 0.10


# ── Docstring quality ─────────────────────────────────────────────────────────

def docstring_quality(text: str, lang: str) -> float:
    """Structured docstrings with @param/@return/Args:/Returns: = AI-like."""
    score = 0.0

    # JavaDoc: /**...*/ with multiple @tags
    if re.search(r"/\*\*[\s\S]{50,}\*/", text):
        tags = len(re.findall(r"@(param|return|throws|see|deprecated)", text))
        if tags >= 3: score += 0.50
        elif tags >= 2: score += 0.35
        elif tags >= 1: score += 0.20

    # Python: """...""" with structured sections
    py_docs = re.findall(r'"""[\s\S]{30,}?"""', text)
    if py_docs:
        has_sections = any(
            re.search(r"(?:Args:|Returns:|Raises:|Parameters:|Attributes:|Example)", d)
            for d in py_docs
        )
        if has_sections: score += 0.55
        elif len(py_docs) > 2: score += 0.28
        else: score += 0.12

    # TSDoc: /** \n * ... \n */
    if re.search(r"/\*\*\s*\n(?:\s*\*.*\n){2,}", text):
        score += 0.22

    return min(round(score, 4), 0.95)


# ── Type annotations (Python) ─────────────────────────────────────────────────

def type_annotations(text: str, lang: str) -> float:
    """
    Full type annotation coverage in Python = AI-like.
    Java has mandatory types — not a useful signal there.
    """
    if lang not in ("Python", "TypeScript", "JavaScript"):
        return 0.40  # neutral for Java

    if lang == "Python":
        funcs = re.findall(r"def \w+\(([^)]*)\)", text)
        if not funcs:
            return 0.25
        annotated = sum(
            1 for f in funcs
            if ":" in f and f.strip() not in ("self", "cls", "self,", "cls,")
        )
        ratio = annotated / len(funcs)
        return_typed = len(re.findall(r"def \w+\([^)]*\)\s*->", text))
        bonus = min(return_typed * 0.06, 0.20)
        if ratio > 0.85: return min(0.80 + bonus, 0.95)
        if ratio > 0.60: return 0.58 + bonus
        if ratio > 0.30: return 0.38 + bonus
        return 0.12

    # TypeScript: interface/type alias density
    iface    = len(re.findall(r"\binterface\b|\btype\b\s+\w+\s*=", text))
    generics = len(re.findall(r"<[A-Z]\w+(?:,\s*[A-Z]\w+)*>", text))
    if iface + generics > 6: return 0.70
    if iface + generics > 3: return 0.52
    return 0.28


# ── Exception handling style ──────────────────────────────────────────────────

def exception_style(text: str, lang: str) -> float:
    """
    Bare except / Exception-swallow = human-like.
    Specific exceptions + reraise / from-chaining = AI-like.
    Uses line-by-line analysis to avoid catastrophic regex backtracking.
    """
    lines = text.splitlines()

    # Human signals
    bare_except   = len(re.findall(r"^\s*except\s*:", text, re.M))
    print_tb      = len(re.findall(r"traceback\.print_exc|\.print_exception", text))
    # Broad Exception + pass (line-based)
    broad_pass = sum(
        1 for i, line in enumerate(lines)
        if re.search(r"except\s+Exception", line)
        and any(re.match(r"\s*(?:pass|\.\.\.)\s*$", lines[j])
                for j in range(i+1, min(i+4, len(lines))))
    )

    human_score = bare_except * 3 + broad_pass * 2 + print_tb
    if human_score >= 2: return 0.05
    if human_score == 1: return 0.18

    # AI signals
    specific = len(re.findall(
        r"except\s+\(?\s*[A-Z]\w*(?:Error|Exception|Warning)"
        r"(?:\s*,\s*[A-Z]\w*(?:Error|Exception|Warning))*\s*\)?",
        text,
    ))
    reraise = sum(
        1 for i, line in enumerate(lines)
        if "except" in line and ":" in line
        and any("raise" in lines[j] for j in range(i+1, min(i+7, len(lines))))
    )
    from_chaining = len(re.findall(r"raise\s+\w+\s+from\s+\w+", text))

    if specific >= 3 and (reraise >= 1 or from_chaining >= 1): return 0.85
    if specific >= 2: return 0.65
    if specific >= 1: return 0.48
    return 0.38


# ── Error message quality ─────────────────────────────────────────────────────

def error_message_quality(text: str, lang: str) -> float:
    """Rich, contextual error messages with variable interpolation = AI-like."""
    py_f_errors    = len(re.findall(r'raise\s+\w+\s*\(\s*f["\'].*?\{.*?["\']', text))
    java_errors    = len(re.findall(r'throw\s+new\s+\w+\s*\([^)]{25,}\)', text))
    template_errs  = len(re.findall(r'throw.*`[^`]{20,}`', text))
    total = py_f_errors + java_errors + template_errs
    if total >= 4: return 0.85
    if total >= 2: return 0.68
    if total >= 1: return 0.48
    return 0.22


# ── Log statement quality ─────────────────────────────────────────────────────

def log_quality(text: str, lang: str) -> float:
    """Parameterized/structured logging = AI. System.out / bare print = human."""
    sysout      = len(re.findall(r"System\.out\.print|console\.log", text))
    bare_print  = len(re.findall(r"^\s*print\s*\(", text, re.M))
    concat_log  = len(re.findall(r'log(?:ger)?\.(?:debug|info|warn|error)\s*\("[^"]*"\s*\+', text))

    if sysout > 0:     return max(0.05, 0.20 - sysout * 0.05)
    if bare_print > 3: return 0.15
    if concat_log > 0: return 0.22

    # Parameterized: log.info("msg: {}", var) or log.info("msg: %s", var)
    parameterized = len(re.findall(
        r'log(?:ger)?\.(?:debug|info|warn|warning|error|critical)\s*\("[^"]*(?:\{\}|%[sdif])', text
    ))
    lines = max(text.count("\n") + 1, 1)
    density = parameterized / lines * 100
    if density > 1.0: return 0.75
    if density > 0.5: return 0.55
    return 0.28


# ── Function name length ──────────────────────────────────────────────────────

def function_name_length(text: str, lang: str) -> float:
    """Long, descriptive method names = AI-like. Short abbreviations = human."""
    names = re.findall(
        r"(?:def|function|public|private|protected|async)\s+([a-zA-Z_]\w*)\s*\(",
        text,
    )
    excluded = {"if", "for", "while", "return", "class", "new", "this", "super"}
    # Strip Java getters/setters — they're always long regardless of author
    if lang in ("Java", "Kotlin", "Scala"):
        names = [n for n in names if not re.match(r"^(?:get|set|is|has|build|with)[A-Z]", n)]
    # Strip Python dunders
    names = [n for n in names if n not in excluded
             and not (n.startswith("__") and n.endswith("__"))]

    if not names: return 0.35
    avg = sum(len(n) for n in names) / len(names)
    if avg > 25: return 0.88
    if avg > 18: return 0.72
    if avg > 14: return 0.55
    if avg > 10: return 0.38
    return 0.18


# ── Java: Stream API vs loops ─────────────────────────────────────────────────

def stream_usage(text: str, lang: str) -> float:
    """Stream API > traditional loops = AI-like (Java/Kotlin)."""
    if lang not in ("Java", "Kotlin", "Scala"):
        return 0.35

    stream_ops = len(re.findall(
        r"\.stream\(\)|\.filter\s*\(|\.map\s*\(|\.flatMap\s*\(|"
        r"\.collect\s*\(|\.findFirst\s*\(|\.reduce\s*\(|\.sorted\s*\(|"
        r"\.distinct\s*\(|\.anyMatch\s*\(|\.allMatch\s*\(|\.count\s*\(\s*\)",
        text,
    ))
    for_each = len(re.findall(r"for\s*\(\s*\w[\w<>, ]+\s+\w+\s*:\s*\w", text))
    for_idx  = len(re.findall(r"for\s*\(\s*int\s+\w+\s*=\s*0", text))
    human_loops = for_each + for_idx * 1.5

    total = stream_ops + human_loops
    if total == 0: return 0.35
    if stream_ops == 0 and human_loops > 3: return 0.08
    ratio = stream_ops / total
    if ratio > 0.70: return 0.85
    if ratio > 0.50: return 0.70
    if ratio > 0.30: return 0.50
    return 0.22


# ── Java: Empty catch / printStackTrace ───────────────────────────────────────

def empty_catch(text: str, lang: str) -> float:
    """
    Absence of empty catch blocks = AI-like.
    Empty catch / e.printStackTrace() = very human-like.
    """
    if lang not in ("Java", "Kotlin", "Scala"):
        return 0.40

    empty_blocks  = len(re.findall(r"catch\s*\([^)]+\)\s*\{\s*\}", text))
    print_stack   = len(re.findall(r"\.printStackTrace\s*\(\s*\)", text))
    comment_swallow = len(re.findall(r"catch\s*\([^)]+\)\s*\{\s*//[^\n]*\n\s*\}", text))

    human_score = empty_blocks + print_stack * 2 + comment_swallow
    if human_score >= 2: return 0.05
    if human_score == 1: return 0.15

    # Broad catch without log (line-based)
    lines = text.splitlines()
    broad_no_log = sum(
        1 for i, line in enumerate(lines)
        if re.search(r"catch\s*\(\s*Exception\s+\w+\s*\)", line)
        and all("log" not in lines[j] and "logger" not in lines[j]
                for j in range(i, min(i+8, len(lines))))
    )
    if broad_no_log > 0: return 0.22

    specific = len(re.findall(
        r"catch\s*\(\s*(?!Exception\b)[A-Z]\w*(?:Exception|Error)\s+\w+\s*\)", text
    ))
    log_rethrow = sum(
        1 for i, line in enumerate(lines)
        if re.search(r"(?:log|logger)\.\w+\(", line)
        and any("throw" in lines[j] for j in range(i+1, min(i+4, len(lines))))
    )
    if specific >= 3 and log_rethrow >= 1: return 0.78
    if specific >= 2: return 0.58
    return 0.40


# ── Java: private final fields ────────────────────────────────────────────────

def final_fields(text: str, lang: str) -> float:
    """Immutable private final fields = AI-like."""
    if lang not in ("Java", "Kotlin", "Scala"):
        return 0.40
    final_f   = len(re.findall(r"private\s+final\s+[\w<>\[\], ]+\s+\w+\s*[=;]", text))
    mutable_f = len(re.findall(r"private\s+(?!final\s|static\s)[\w<>\[\], ]+\s+\w+\s*[=;]", text))
    public_m  = len(re.findall(r"^\s+public\s+(?!final|static|class|interface|enum)\w", text, re.M))
    if public_m > 1: return 0.12
    total = final_f + mutable_f
    if total == 0: return 0.35
    ratio = final_f / total
    if ratio > 0.80: return 0.78
    if ratio > 0.60: return 0.60
    if ratio > 0.35: return 0.40
    return 0.20


# ── Java: Optional<T> usage ───────────────────────────────────────────────────

def optional_usage(text: str, lang: str) -> float:
    """Optional<T> + no null returns = AI-like."""
    if lang not in ("Java", "Kotlin", "Scala"):
        return 0.40
    opt_use    = len(re.findall(
        r"Optional\s*<|Optional\.of\s*\(|Optional\.empty\s*\(\s*\)|"
        r"Optional\.ofNullable\s*\(|\.orElse\s*\(|\.orElseThrow\s*\(", text,
    ))
    null_ret   = len(re.findall(r"\breturn\s+null\s*;", text))
    null_check = len(re.findall(r"==\s*null\b|!=\s*null\b", text))
    if opt_use >= 4: return 0.75
    if opt_use >= 2 and null_ret == 0: return 0.60
    if null_ret > 3: return 0.12
    if null_check > opt_use * 3: return 0.20
    return 0.38


# ── Java: Lombok / Spring annotations ────────────────────────────────────────

def lombok_annotations(text: str, lang: str) -> float:
    """Full annotation coverage = AI-like. Manual boilerplate = human."""
    if lang not in ("Java", "Kotlin", "Scala"):
        return 0.40
    ai_annots = len(re.findall(
        r"@(?:Builder|Data|Value|RequiredArgsConstructor|AllArgsConstructor|"
        r"NoArgsConstructor|Getter|Setter|Slf4j|Log4j2|"
        r"Service|Repository|Component|RestController|Controller|"
        r"Transactional|Cacheable|Validated|Valid|NotNull|NotBlank|"
        r"Column|Entity|Table|ManyToOne|OneToMany|JoinColumn)\b",
        text,
    ))
    manual_get = len(re.findall(r"public\s+[\w<>]+\s+get[A-Z]\w+\s*\(\s*\)\s*\{", text))
    manual_set = len(re.findall(r"public\s+void\s+set[A-Z]\w+\s*\(", text))
    boilerplate = manual_get + manual_set

    if boilerplate > 5: return 0.12
    lines = max(text.count("\n") + 1, 1)
    density = ai_annots / max(lines / 10, 1)
    if density > 3: return 0.80
    if density > 1.5: return 0.62
    if ai_annots >= 2: return 0.45
    return 0.25


# ── Dispatcher ────────────────────────────────────────────────────────────────

def compute_all(text: str, lang: str) -> dict:
    """Compute all applicable heuristic signals for a file."""
    return {
        "comment_density":      comment_density(text, lang),
        "docstring_quality":    docstring_quality(text, lang),
        "type_annotations":     type_annotations(text, lang),
        "exception_style":      exception_style(text, lang),
        "error_message_quality":error_message_quality(text, lang),
        "log_quality":          log_quality(text, lang),
        "function_name_length": function_name_length(text, lang),
        "stream_usage":         stream_usage(text, lang),
        "empty_catch":          empty_catch(text, lang),
        "final_fields":         final_fields(text, lang),
        "optional_usage":       optional_usage(text, lang),
        "lombok_annotations":   lombok_annotations(text, lang),
    }
