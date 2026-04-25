"""
analyzers/framework.py — Framework and boilerplate detection.

Detects framework-specific patterns that can produce AI-like signals
without the code being AI-generated. Framework context is used to
apply context adjustments to raw scores (adjusted score).

Supported detection:
  Java:   Spring Boot, JPA/Hibernate, Lombok, MapStruct, OpenAPI clients
  Python: FastAPI, Django, Flask, Pydantic, SQLAlchemy, Celery

Extension points:
  - Add new framework detectors by implementing _detect_* functions
  - Add framework-specific weight overrides via FrameworkContext.boilerplate_score

⚠ Framework context does NOT prove the file is not AI-assisted.
  It provides alternative explanations for elevated scores.
"""
from __future__ import annotations

import re
from typing import List

from ..domain import FrameworkContext


# ── Java: Spring Boot ─────────────────────────────────────────────────────────

_SPRING_ANNOTATIONS = re.compile(
    r"@(?:RestController|Controller|Service|Repository|Component|"
    r"Configuration|SpringBootApplication|EnableWebMvc|"
    r"RequestMapping|GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping|"
    r"Autowired|Value|Qualifier|Primary|Lazy|"
    r"Transactional|Cacheable|CacheEvict|"
    r"ConditionalOnProperty|ConditionalOnBean|"
    r"EnableScheduling|Scheduled|Async|EnableAsync)\b"
)

_SPRING_IMPORTS = re.compile(
    r"import\s+org\.springframework\."
)

_JPA_ANNOTATIONS = re.compile(
    r"@(?:Entity|Table|Column|Id|GeneratedValue|ManyToOne|OneToMany|"
    r"ManyToMany|OneToOne|JoinColumn|JoinTable|Embedded|Embeddable|"
    r"NamedQuery|NamedQueries|Inheritance|DiscriminatorColumn|"
    r"SequenceGenerator|MappedSuperclass|Version|Lob|Temporal|"
    r"ElementCollection|CollectionTable)\b"
)

_LOMBOK_ANNOTATIONS = re.compile(
    r"@(?:Data|Value|Builder|Getter|Setter|ToString|EqualsAndHashCode|"
    r"RequiredArgsConstructor|AllArgsConstructor|NoArgsConstructor|"
    r"Slf4j|Log4j2|NonNull|With|SuperBuilder|FieldDefaults|Accessors)\b"
)

_MAPSTRUCT_PATTERNS = re.compile(
    r"@(?:Mapper|Mapping|MappingTarget|AfterMapping|BeforeMapping|"
    r"BeanMapping|InheritConfiguration)\b|"
    r"import\s+org\.mapstruct\."
)

_OPENAPI_GENERATED = re.compile(
    r"@Schema\s*\(|@ApiModel|@ApiModelProperty|"
    r"@Operation\s*\(|@Parameter\s*\(|"
    r"import\s+io\.swagger\.|import\s+org\.openapitools\."
)


def _detect_spring(text: str, frameworks: List[str]) -> float:
    """Detect Spring Boot patterns. Returns boilerplate fraction."""
    if not _SPRING_IMPORTS.search(text):
        return 0.0

    frameworks.append("spring-boot")
    annot_count = len(_SPRING_ANNOTATIONS.findall(text))
    lines = max(text.count("\n") + 1, 1)
    density = annot_count / (lines / 10.0)

    if density > 3:
        return 0.50
    if density > 1.5:
        return 0.35
    if annot_count > 0:
        return 0.20
    return 0.0


def _detect_jpa(text: str, frameworks: List[str]) -> bool:
    if _JPA_ANNOTATIONS.search(text):
        frameworks.append("jpa")
        return True
    return False


def _detect_lombok(text: str, frameworks: List[str]) -> bool:
    count = len(_LOMBOK_ANNOTATIONS.findall(text))
    if count >= 2:
        frameworks.append("lombok")
        return True
    return False


def _detect_mapstruct(text: str, frameworks: List[str]) -> bool:
    if _MAPSTRUCT_PATTERNS.search(text):
        frameworks.append("mapstruct")
        return True
    return False


def _detect_openapi_java(text: str, frameworks: List[str]) -> bool:
    if _OPENAPI_GENERATED.search(text):
        frameworks.append("openapi")
        return True
    return False


# ── Python: FastAPI ───────────────────────────────────────────────────────────

_FASTAPI_PATTERNS = re.compile(
    r"from\s+fastapi\s+import|import\s+fastapi|"
    r"@app\.\w+\s*\(|@router\.\w+\s*\(|"
    r"FastAPI\s*\(|APIRouter\s*\("
)

_PYDANTIC_PATTERNS = re.compile(
    r"from\s+pydantic\s+import|import\s+pydantic|"
    r"class\s+\w+\s*\(\s*BaseModel\s*\)|"
    r"Field\s*\(|validator\s*\(|field_validator\s*\("
)

_DJANGO_PATTERNS = re.compile(
    r"from\s+django\.|import\s+django\.|"
    r"class\s+\w+\s*\(\s*models\.Model\s*\)|"
    r"django\.db\.models|django\.views|"
    r"@login_required|@permission_required"
)

_FLASK_PATTERNS = re.compile(
    r"from\s+flask\s+import|import\s+flask|"
    r"@app\.route\s*\(|@blueprint\.\w+\s*\("
)

_SQLALCHEMY_PATTERNS = re.compile(
    r"from\s+sqlalchemy|import\s+sqlalchemy|"
    r"class\s+\w+\s*\(\s*Base\s*\)|Column\s*\(|"
    r"relationship\s*\(|declarative_base"
)

_CELERY_PATTERNS = re.compile(
    r"from\s+celery\s+import|@(?:app|celery)\.task|"
    r"@shared_task\b"
)


def _detect_fastapi(text: str, frameworks: List[str]) -> float:
    if _FASTAPI_PATTERNS.search(text):
        frameworks.append("fastapi")
        return 0.35
    return 0.0


def _detect_pydantic(text: str, frameworks: List[str]) -> float:
    if _PYDANTIC_PATTERNS.search(text):
        frameworks.append("pydantic")
        # Pydantic models are naturally regular — significant boilerplate
        pydantic_fields = len(re.findall(
            r"^\s+\w+\s*:\s*(?:Optional\[|List\[|Dict\[|str|int|float|bool)",
            text, re.M,
        ))
        if pydantic_fields >= 3:
            return 0.55
        return 0.30
    return 0.0


def _detect_django(text: str, frameworks: List[str]) -> float:
    if _DJANGO_PATTERNS.search(text):
        frameworks.append("django")
        return 0.35
    return 0.0


def _detect_flask(text: str, frameworks: List[str]) -> float:
    if _FLASK_PATTERNS.search(text):
        frameworks.append("flask")
        return 0.25
    return 0.0


def _detect_sqlalchemy(text: str, frameworks: List[str]) -> float:
    if _SQLALCHEMY_PATTERNS.search(text):
        frameworks.append("sqlalchemy")
        return 0.40
    return 0.0


# ── DTO / plain data class detection ─────────────────────────────────────────

_DTO_JAVA_PATTERN = re.compile(
    r"(?:class|record)\s+\w+(?:Dto|DTO|Request|Response|Payload|View|VO|"
    r"Command|Event|Message|Transfer)\b"
)

_DTO_PYTHON_PATTERN = re.compile(
    r"class\s+\w+(?:Dto|DTO|Schema|Request|Response|Payload)\s*\("
)

_GETTER_SETTER_DENSITY = re.compile(
    r"public\s+\w+\s+(?:get|set)[A-Z]\w+\s*\("
)


def _is_dto_class(text: str, lang: str) -> bool:
    if lang in ("Java", "Kotlin"):
        if _DTO_JAVA_PATTERN.search(text):
            return True
        # Java class with only getters/setters and no business logic
        lines = text.count("\n") + 1
        gs = len(_GETTER_SETTER_DENSITY.findall(text))
        if gs > 3 and gs / max(lines / 10, 1) > 1.5:
            return True
    elif lang == "Python":
        if _DTO_PYTHON_PATTERN.search(text):
            return True
    return False


# ── Main detector ─────────────────────────────────────────────────────────────

def detect_framework_context(text: str, lang: str) -> FrameworkContext:
    """
    Detect framework and boilerplate context for a file.
    Returns a FrameworkContext with all detected signals.

    This is an always-on step that runs before scoring to provide
    context adjustments. See scoring/adjusted.py for adjustment logic.
    """
    frameworks: List[str] = []
    boilerplate_score = 0.0

    is_spring   = False
    is_jpa      = False
    is_lombok   = False
    is_mapstruct = False
    is_openapi  = False
    is_pydantic = False
    is_fastapi  = False
    is_django   = False
    is_dto      = False

    if lang in ("Java", "Kotlin", "Scala"):
        spring_bp = _detect_spring(text, frameworks)
        boilerplate_score = max(boilerplate_score, spring_bp)
        is_spring = spring_bp > 0.0
        is_jpa    = _detect_jpa(text, frameworks)
        is_lombok = _detect_lombok(text, frameworks)
        is_openapi = _detect_openapi_java(text, frameworks)
        if is_openapi:
            boilerplate_score = max(boilerplate_score, 0.75)
        is_mapstruct = _detect_mapstruct(text, frameworks)
        if is_mapstruct:
            boilerplate_score = max(boilerplate_score, 0.80)
        if is_jpa:
            boilerplate_score = max(boilerplate_score, 0.50)
        is_dto = _is_dto_class(text, lang)
        if is_dto:
            boilerplate_score = max(boilerplate_score, 0.65)

    elif lang == "Python":
        pydantic_bp = _detect_pydantic(text, frameworks)
        boilerplate_score = max(boilerplate_score, pydantic_bp)
        is_pydantic = pydantic_bp > 0.0
        fastapi_bp = _detect_fastapi(text, frameworks)
        boilerplate_score = max(boilerplate_score, fastapi_bp)
        is_fastapi = fastapi_bp > 0.0
        django_bp  = _detect_django(text, frameworks)
        boilerplate_score = max(boilerplate_score, django_bp)
        is_django = django_bp > 0.0
        _detect_flask(text, frameworks)
        _detect_sqlalchemy(text, frameworks)
        is_dto = _is_dto_class(text, lang)
        if is_dto:
            boilerplate_score = max(boilerplate_score, 0.55)

    return FrameworkContext(
        detected_frameworks  = frameworks,
        is_spring_component  = is_spring,
        is_jpa_entity        = is_jpa,
        is_lombok_heavy      = is_lombok,
        is_pydantic_model    = is_pydantic,
        is_fastapi_route     = is_fastapi,
        is_django_model      = is_django,
        is_mapstruct_mapper  = is_mapstruct,
        is_openapi_generated = is_openapi,
        is_dto_class         = is_dto,
        boilerplate_score    = min(boilerplate_score, 0.95),
    )


# ── Alternative explanation generator ────────────────────────────────────────

def get_alternative_explanations(ctx: FrameworkContext) -> list:
    """
    Return framework-based alternative explanations for elevated AI-like signals.
    These are included in Finding objects to prevent over-interpretation.
    """
    from ..domain import AlternativeExplanation
    explanations = []

    if ctx.is_spring_component:
        explanations.append(AlternativeExplanation(
            "Spring Boot framework enforces regular annotation patterns and class structure.",
            "high",
        ))
    if ctx.is_jpa_entity:
        explanations.append(AlternativeExplanation(
            "JPA/Hibernate entity classes require annotation-heavy, regular field definitions.",
            "high",
        ))
    if ctx.is_lombok_heavy:
        explanations.append(AlternativeExplanation(
            "Lombok reduces manual boilerplate but produces annotation-dense code regardless of author.",
            "high",
        ))
    if ctx.is_mapstruct_mapper:
        explanations.append(AlternativeExplanation(
            "MapStruct mapper interfaces are by design symmetric, regular, and annotation-driven.",
            "high",
        ))
    if ctx.is_openapi_generated:
        explanations.append(AlternativeExplanation(
            "OpenAPI/Swagger-generated client code is mechanically produced and not hand-written.",
            "high",
        ))
    if ctx.is_pydantic_model:
        explanations.append(AlternativeExplanation(
            "Pydantic models require uniform field definitions with type annotations by design.",
            "high",
        ))
    if ctx.is_fastapi_route:
        explanations.append(AlternativeExplanation(
            "FastAPI route files use decorator patterns and type-annotated parameters by convention.",
            "moderate",
        ))
    if ctx.is_django_model:
        explanations.append(AlternativeExplanation(
            "Django models follow a fixed structure with field definitions and Meta class.",
            "high",
        ))
    if ctx.is_dto_class:
        explanations.append(AlternativeExplanation(
            "DTO/data class files are inherently regular with field definitions and minimal logic.",
            "high",
        ))

    return explanations
