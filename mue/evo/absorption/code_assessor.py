"""Code assessment module — domain-aware code quality scoring and pattern extraction.

Extracted from github_miner.py to stay under the 800-line anti-cancer limit.
"""

import ast
from typing import Optional


# ═══════════════════════════════════════════════════════════════
# Domain-specific keyword sets for scoring + file filtering
# ═══════════════════════════════════════════════════════════════

DOMAIN_KEYWORDS = {
    "trading": {
        "high": ["strategy", "signal", "order", "position", "risk", "execution",
                 "backtest", "indicator", "candle", "ohlc", "market", "broker",
                 "exchange", "portfolio", "drawdown", "sharpe", "volatility",
                 "momentum", "arbitrage", "hedge", "stop_loss", "take_profit"],
        "med": ["trade", "price", "volume", "spread", "slippage", "equity",
                "bar", "tick", "bid", "ask", "liquid", "margin", "leverage"],
        "penalty": ["marshmallow", "serializer", "html", "css", "template",
                    "form", "web", "http", "rest_api", "graphql", "oauth",
                    "cookie", "session", "middleware", "router", "view"],
    },
    "coding": {
        "high": ["algorithm", "optimize", "compiler", "parser", "ast", "transform",
                 "refactor", "lint", "static_analysis", "type_check",
                 "handler", "manager", "factory", "module", "component", "dispatch",
                 "delegate", "event", "worker", "pool", "callback"],
        "med": ["cache", "async", "generator", "decorator", "context_manager",
                "error", "status", "init", "create", "update", "process",
                "render", "config", "session", "connection"],
        "penalty": ["marshmallow", "serializer", "template", "html", "css",
                    "migration", "orm", "admin"],
    },
    "research": {
        "high": ["model", "train", "inference", "embedding", "transformer",
                 "neural", "gradient", "loss", "accuracy", "dataset", "tokenizer"],
        "med": ["tensor", "layer", "batch", "epoch", "hyperparameter"],
        "penalty": ["serializer", "template", "admin", "web", "http"],
    },
    "security": {
        "high": ["vulnerability", "exploit", "penetration", "payload", "injection",
                 "xss", "csrf", "auth", "token", "hash", "cipher", "encrypt"],
        "med": ["scan", "probe", "fuzz", "sandbox", "permission"],
        "penalty": ["serializer", "template", "admin"],
    },
    "creative": {
        "high": ["generate", "render", "compose", "style", "theme", "layout",
                 "design", "animate", "draw", "paint"],
        "med": ["color", "font", "canvas", "transform", "blend"],
        "penalty": [],
    },
}


def is_noise_file(filename: str, domain: str = "general") -> bool:
    """Reject files that are clearly irrelevant to the domain."""
    name_lower = filename.lower()
    noise_patterns = [
        "schema", "serializ", "migration", "admin", "config",
        "setup", "conftest", "fixture", "mock", "stub",
        "__init__", "version", "constants", "settings",
    ]
    for noise in noise_patterns:
        if noise in name_lower:
            return True
    if domain in DOMAIN_KEYWORDS:
        penalties = DOMAIN_KEYWORDS[domain].get("penalty", [])
        for penalty in penalties:
            if penalty in name_lower:
                return True
    return False


def filename_matches_domain(filename: str, domain: str = "general") -> bool:
    """Check if filename suggests domain relevance."""
    if domain == "general":
        return True
    if domain not in DOMAIN_KEYWORDS:
        return True
    name_lower = filename.lower()
    keywords = (DOMAIN_KEYWORDS[domain].get("high", []) +
                DOMAIN_KEYWORDS[domain].get("med", []))
    return any(kw in name_lower for kw in keywords)


def assess_code(code: str, filename: str, domain: str = "general") -> dict:
    """Domain-aware code quality assessment.

    Files matching the current domain get up to +0.35 bonus.
    Files matching penalty keywords get -0.50 penalty (effectively rejected).

    Supports multiple languages — Python, Rust, Go, JavaScript/TypeScript, etc.
    Language-specific keywords are recognized for base scoring.
    """
    lines = code.split("\n")
    code_lower = code.lower()
    filename_lower = filename.lower()

    # Detect language from file extension
    is_py = filename.endswith(".py")
    is_rs = filename.endswith(".rs")
    is_go = filename.endswith(".go")
    is_js_ts = any(filename.endswith(e) for e in (".js", ".jsx", ".ts", ".tsx"))
    is_c_cpp = any(filename.endswith(e) for e in (".cpp", ".hpp", ".h", ".c", ".cc", ".cxx", ".hh", ".hxx", ".tcc", ".ipp"))
    is_java = any(filename.endswith(e) for e in (".java", ".kt"))

    value = 0.15
    # Language-agnostic quality indicators
    # Size maturity (graduated — no binary cutoff penalty for large files)
    if len(lines) >= 30:
        value += 0.05  # non-trivial file
    if len(lines) >= 100:
        value += 0.03  # substantial file
    if len(lines) >= 500:
        value += 0.02  # large file
    if "async " in code_lower or "await " in code_lower:
        value += 0.05
    if "cache" in code_lower or "lru" in code_lower:
        value += 0.04  # was 0.07 — reduced to avoid cache-file bias
    if "retry" in code_lower or "fallback" in code_lower:
        value += 0.05
    if "error" in code_lower or "result" in code_lower:
        value += 0.03

    # Python-specific
    if is_py:
        if "class " in code:
            value += 0.10
        if "def " in code:
            value += 0.08
        if "yield" in code_lower or "generator" in code_lower:
            value += 0.05
        if any(kw in code for kw in ("@property", "@staticmethod", "@classmethod")):
            value += 0.04

    # Rust-specific
    if is_rs:
        if "fn " in code:
            value += 0.08
        if "struct " in code or "enum " in code:
            value += 0.06
        if "impl " in code:
            value += 0.06
        if "trait " in code:
            value += 0.06
        if "unsafe " in code:
            value += 0.04
        if "pub " in code:
            value += 0.04
        if "match " in code:
            value += 0.03
        if "#[derive" in code or "#[allow" in code:
            value += 0.03
        if "use " in code:
            value += 0.02

    # Go-specific
    if is_go:
        if "func " in code:
            value += 0.08
        if "type " in code or "struct " in code:
            value += 0.06
        if "interface " in code:
            value += 0.06
        if "package " in code:
            value += 0.02
        if "defer " in code:
            value += 0.04
        if "go func" in code or "goroutine" in code_lower:
            value += 0.04

    # JS/TS-specific
    if is_js_ts:
        if "function " in code or "=>" in code:
            value += 0.08
        if "class " in code:
            value += 0.08
        if "interface " in code or "type " in code:
            value += 0.06
        if "import " in code or "export " in code:
            value += 0.04
        if "async " in code_lower or "await " in code_lower:
            value += 0.04
        if "const " in code or "let " in code:
            value += 0.03

    # C/C++-specific
    if is_c_cpp:
        if "class " in code:
            value += 0.10
        if "template " in code:
            value += 0.08
        if "virtual " in code:
            value += 0.06
        if "constexpr " in code or "noexcept" in code or "static_assert" in code:
            value += 0.06
        if "override" in code or "final" in code:
            value += 0.04
        if "namespace " in code:
            value += 0.04
        if "#include" in code or "#pragma" in code:
            value += 0.03
        if "std::" in code:
            value += 0.03

    # Java/Kotlin-specific
    if is_java:
        if "class " in code:
            value += 0.10
        if "interface " in code:
            value += 0.07
        if "extends " in code or "implements " in code:
            value += 0.06
        if "@Override" in code or "@Deprecated" in code or "@SuppressWarnings" in code:
            value += 0.05
        if "record " in code or "sealed " in code or "permits " in code:
            value += 0.06
        if "throws " in code or "Exception" in code:
            value += 0.04
        if "import " in code:
            value += 0.03
        if "package " in code:
            value += 0.02
        if "this." in code or "super." in code:
            value += 0.03

    # Domain-specific keyword scoring & penalties
    high_hits = 0
    if domain in DOMAIN_KEYWORDS:
        kw = DOMAIN_KEYWORDS[domain]
        high_hits = sum(1 for k in kw["high"] if k in code_lower or k in filename_lower)
        value += min(0.35, high_hits * 0.05)
        med_hits = sum(1 for k in kw["med"] if k in code_lower or k in filename_lower)
        value += min(0.15, med_hits * 0.03)
        penalty_hits = sum(1 for k in kw["penalty"] if k in code_lower or k in filename_lower)
        value -= penalty_hits * 0.10

    value = max(0.0, min(1.0, value))
    extracted = extract_key_pattern(code)

    ptype = "function"
    if "class " in code:
        ptype = "architecture"
    if "algorithm" in code_lower:
        ptype = "algorithm"
    if len(code) < 100 and ("trick" in code_lower or "hack" in code_lower):
        ptype = "trick"

    desc = f"Absorbed {ptype} from {filename}"
    if high_hits > 0:
        desc += f" [{domain} relevance: high]"

    return {
        "value": value,
        "type": ptype,
        "extracted": extracted,
        "description": desc,
    }


def extract_key_pattern(code: str) -> str:
    """Extract full function/class bodies using AST, not just signatures.

    The old approach only captured def/class signatures + decorators.
    This extracts the complete definition including all logic, which is
    what makes absorption actually useful for evolution.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError:
        lines = [l for l in code.split("\n") if l.strip()][:100]
        return "\n".join(lines)

    extracted = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef):
            try:
                body = ast.unparse(node)
                body_lines = body.split("\n")
                if len(body_lines) > 80:
                    body = "\n".join(body_lines[:80]) + "\n    # ... (truncated)"
                extracted.append(body)
            except Exception:
                extracted.append(f"def {node.name}(...): ...")
        elif isinstance(node, ast.ClassDef):
            try:
                body = ast.unparse(node)
                body_lines = body.split("\n")
                if len(body_lines) > 120:
                    body = "\n".join(body_lines[:120]) + "\n    # ... (truncated)"
                extracted.append(body)
            except Exception:
                extracted.append(f"class {node.name}: ...")
        elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            pass
        else:
            try:
                stmt = ast.unparse(node)
                if len(stmt) < 500:
                    extracted.append(stmt)
            except Exception:
                pass

    if not extracted:
        lines = [l for l in code.split("\n") if l.strip() and not l.strip().startswith(("import ", "from "))][:80]
        if lines:
            return "\n".join(lines)
        lines = [l for l in code.split("\n") if l.strip()][:80]
        return "\n".join(lines) if lines else "# [empty gene — extraction failed]"

    return "\n\n".join(extracted)
