"""
_signal_metadata.py — Rule card metadata for each signal.

For each signal, provides:
  - description: human-readable description
  - category: signal category
  - alternative_explanations: (explanation, likelihood) tuples
  - tags: language/category tags

This is used to generate Finding objects with context.
Rule cards documented here support requirement #191 (rule cards).
"""
from __future__ import annotations

SIGNAL_METADATA = {
    "token_entropy": {
        "description": "Low token entropy — repetitive vocabulary pattern",
        "category": "lexical",
        "tags": ["lexical", "all"],
        "alternative_explanations": [
            ("DTO/data class with repeated field access patterns", "high"),
            ("Generated code (OpenAPI, Avro, Protobuf)", "high"),
            ("Strict formatter producing uniform token distribution", "moderate"),
        ],
    },
    "type_token_ratio": {
        "description": "Low type-token ratio — limited vocabulary diversity",
        "category": "lexical",
        "tags": ["lexical", "all"],
        "alternative_explanations": [
            ("Mapper or converter class with repeated field names", "high"),
            ("Domain object with symmetric getter/setter pattern", "moderate"),
        ],
    },
    "repetition_index": {
        "description": "High structural block repetition across the file",
        "category": "lexical",
        "tags": ["lexical", "all"],
        "alternative_explanations": [
            ("Domain entity with many similar field handlers", "moderate"),
            ("Generated or scaffolded code", "high"),
        ],
    },
    "comment_density": {
        "description": "Elevated comment-to-code ratio — over-commenting pattern",
        "category": "heuristic",
        "tags": ["heuristic", "all"],
        "alternative_explanations": [
            ("Team documentation standards requiring Javadoc on all public methods", "high"),
            ("Legacy code with educational comments for junior developers", "moderate"),
            ("Strict linting rules requiring docstrings", "moderate"),
        ],
    },
    "docstring_quality": {
        "description": "Structured docstrings with Args:/Returns: or @param/@return",
        "category": "heuristic",
        "tags": ["heuristic", "all"],
        "alternative_explanations": [
            ("Team enforces Sphinx or Javadoc documentation standards", "high"),
            ("Library code requiring public API documentation", "high"),
        ],
    },
    "type_annotations": {
        "description": "Comprehensive type annotation coverage (Python)",
        "category": "heuristic",
        "tags": ["heuristic", "Python"],
        "alternative_explanations": [
            ("Team enforces mypy/pyright with strict mode", "high"),
            ("Python 3.10+ codebase with modern typing standards", "moderate"),
        ],
    },
    "exception_style": {
        "description": "Specific exception types with reraise or from-chaining",
        "category": "heuristic",
        "tags": ["heuristic", "Python"],
        "alternative_explanations": [
            ("Senior developer with disciplined exception handling", "moderate"),
            ("Team coding standards requiring specific exception types", "moderate"),
        ],
    },
    "error_message_quality": {
        "description": "Rich, contextual error messages with variable interpolation",
        "category": "heuristic",
        "tags": ["heuristic", "all"],
        "alternative_explanations": [
            ("Team standards for structured error reporting", "moderate"),
            ("Service with user-facing error messages that require context", "moderate"),
        ],
    },
    "log_quality": {
        "description": "Parameterized/structured logging patterns (SLF4J, loguru)",
        "category": "heuristic",
        "tags": ["heuristic", "all"],
        "alternative_explanations": [
            ("Team logging standards enforcing parameterized logging", "high"),
            ("Structured logging framework requirement", "high"),
        ],
    },
    "function_name_length": {
        "description": "Long, descriptive method names (average > 14 characters)",
        "category": "heuristic",
        "tags": ["heuristic", "all"],
        "alternative_explanations": [
            ("Clean code standards enforcing descriptive method names", "high"),
            ("Domain-driven design with long ubiquitous language terms", "moderate"),
        ],
    },
    "stream_usage": {
        "description": "Heavy Stream API usage over traditional loops (Java)",
        "category": "heuristic",
        "tags": ["heuristic", "Java"],
        "alternative_explanations": [
            ("Senior Java developer with modern functional style preference", "moderate"),
            ("Team standard for functional-style collection processing", "moderate"),
        ],
    },
    "empty_catch": {
        "description": "Absence of empty catch blocks / printStackTrace (Java)",
        "category": "heuristic",
        "tags": ["heuristic", "Java"],
        "alternative_explanations": [
            ("Team standard prohibiting empty catch blocks", "moderate"),
            ("Code review processes that reject empty exception handlers", "moderate"),
        ],
    },
    "final_fields": {
        "description": "Consistent use of private final fields (Java)",
        "category": "heuristic",
        "tags": ["heuristic", "Java"],
        "alternative_explanations": [
            ("Team immutability standards for Java", "high"),
            ("SpotBugs or PMD rule enforcing final fields", "moderate"),
        ],
    },
    "optional_usage": {
        "description": "Optional<T> used consistently without null returns (Java)",
        "category": "heuristic",
        "tags": ["heuristic", "Java"],
        "alternative_explanations": [
            ("Team standard prohibiting null returns in service methods", "high"),
            ("Modern Java style guide requiring Optional for nullable returns", "moderate"),
        ],
    },
    "lombok_annotations": {
        "description": "High annotation density from Lombok and Spring",
        "category": "heuristic",
        "tags": ["heuristic", "Java"],
        "alternative_explanations": [
            ("Lombok is mandatory in project for reducing boilerplate", "high"),
            ("Spring Boot project requiring standard annotation patterns", "high"),
        ],
    },
    "ast_depth_uniformity": {
        "description": "Uniform AST nesting depth across functions (Python)",
        "category": "structural",
        "tags": ["structural", "Python"],
        "alternative_explanations": [
            ("Simple business logic with consistent complexity", "moderate"),
            ("Strict complexity linting (max nesting depth rule)", "moderate"),
        ],
    },
    "ast_type_diversity": {
        "description": "Low AST node type diversity — limited code construct variety",
        "category": "structural",
        "tags": ["structural", "Python"],
        "alternative_explanations": [
            ("Simple CRUD service with uniform data handling patterns", "moderate"),
            ("DTO or schema class with uniform field definitions", "high"),
        ],
    },
    "ast_avg_func_length": {
        "description": "Short average function length — focused single-responsibility methods",
        "category": "structural",
        "tags": ["structural", "Python"],
        "alternative_explanations": [
            ("Team standard limiting function length (e.g., max 20 lines)", "high"),
            ("Well-decomposed service layer with deliberate method separation", "moderate"),
        ],
    },
    "placeholder_density": {
        "description": "Placeholder code patterns (TODO/FIXME, pass, NotImplementedError)",
        "category": "heuristic",
        "tags": ["heuristic", "all"],
        "alternative_explanations": [
            ("Work in progress — developer added TODOs for future implementation", "high"),
            ("Iterative development with planned increments", "high"),
        ],
    },
    "prompt_residue": {
        "description": "LLM prompt residue: instructional comments or placeholder strings",
        "category": "heuristic",
        "tags": ["heuristic", "all"],
        "alternative_explanations": [
            ("Developer added explanatory comments for team members", "moderate"),
            ("Tutorial or example code written for documentation", "moderate"),
        ],
    },
    "test_assertion_quality": {
        "description": "Shallow test assertions (assertNotNull, assertTrue(x != null))",
        "category": "test",
        "tags": ["test", "all"],
        "alternative_explanations": [
            ("Quick unit tests focusing on basic contract verification", "moderate"),
            ("Team test standards with progressive test coverage", "moderate"),
        ],
    },
    "test_mock_abuse": {
        "description": "Excessive mocking relative to state assertions",
        "category": "test",
        "tags": ["test", "all"],
        "alternative_explanations": [
            ("Interaction-based testing approach (verifying behavior contracts)", "moderate"),
            ("Integration-style tests where mocks are necessary", "moderate"),
        ],
    },
    "test_fixture_realism": {
        "description": "Generic test fixtures (John Doe, test@example.com, dummy data)",
        "category": "test",
        "tags": ["test", "all"],
        "alternative_explanations": [
            ("Team standard for test data using generic values for privacy", "moderate"),
            ("Test data matches public documentation examples", "low"),
        ],
    },
    "motif_uniformity": {
        "description": "Low structural motif diversity — repeated code patterns",
        "category": "structural",
        "tags": ["structural", "all"],
        "alternative_explanations": [
            ("Domain layer with consistent validate-map-save patterns", "moderate"),
            ("Service layer with uniform error handling patterns", "moderate"),
        ],
    },
    "intra_file_variance": {
        "description": "Low variance in method structure within the file",
        "category": "structural",
        "tags": ["structural", "all"],
        "alternative_explanations": [
            ("API layer with consistent request-handler patterns", "moderate"),
            ("Generated CRUD service with uniform operation implementations", "high"),
        ],
    },
    "similarity_cluster": {
        "description": "High cross-file TF-IDF similarity within repository",
        "category": "lexical",
        "tags": ["lexical", "all"],
        "alternative_explanations": [
            ("Service layer with consistent patterns across similar services", "moderate"),
            ("Template-based project structure with intentional consistency", "high"),
        ],
    },
}
