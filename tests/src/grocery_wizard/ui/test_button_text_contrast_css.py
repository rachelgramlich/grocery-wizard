"""Button label vs fill contrast, resolved from the injected theme CSS (WCAG AA, 4.5:1).

Streamlit buttons nest their label as ``<p>`` inside the button element. Global rules such as
``.stApp p { color: var(--gw-text) }`` can repaint that ``<p>`` dark on a maroon fill even when the
button itself sets white text. This test builds a tiny model of each button's DOM, applies the
rules in ``app_theme.css`` (specificity, ``!important``, source order, inheritance, ``var()``),
and checks the label color against the fill color.

Limits: only simple selectors are matched (type, class, attribute, ``:hover``, ``:disabled``,
``:not(<compound>)``, descendant and child combinators). Rules using ``:has``, other pseudo
classes, or ``@media`` blocks are skipped. Native Streamlit colors are approximated from
``.streamlit/config.toml`` when the CSS does not set a fill.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pytest

from src.grocery_wizard.ui.theme import APP_THEME_STATIC_CSS, MIN_CONTRAST_RATIO_AA, contrast_ratio
from tests.repo_paths import REPO_ROOT

if TYPE_CHECKING:
    from collections.abc import Iterator

STREAMLIT_CONFIG = REPO_ROOT / ".streamlit" / "config.toml"

_TEXT_PROPS = ("-webkit-text-fill-color", "color")
_FILL_PROPS = ("background-color", "background")


@dataclass(frozen=True)
class Rule:
    selector: str
    declarations: tuple[tuple[str, str, bool], ...]
    order: int


@dataclass(eq=False)
class Node:
    tag: str
    classes: tuple[str, ...] = ()
    attrs: dict[str, str] = field(default_factory=dict)
    parent: Node | None = None
    state: frozenset[str] = frozenset()


def _strip_comments(css: str) -> str:
    return re.sub(r"/\*.*?\*/", "", css, flags=re.DOTALL)


def _top_level_blocks(css: str) -> Iterator[tuple[str, str]]:
    depth = 0
    start = 0
    prelude_start = 0
    prelude = ""
    for i, ch in enumerate(css):
        if ch == "{":
            if depth == 0:
                prelude = css[prelude_start:i].strip()
                start = i + 1
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                yield prelude, css[start:i]
                prelude_start = i + 1


def _split_top_level(text: str, sep: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in text:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == sep and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def _parse_declarations(body: str) -> tuple[tuple[str, str, bool], ...]:
    decls: list[tuple[str, str, bool]] = []
    for chunk in _split_top_level(body, ";"):
        if ":" not in chunk:
            continue
        name, value = chunk.split(":", 1)
        value = value.strip()
        important = value.lower().endswith("!important")
        if important:
            value = value[: -len("!important")].strip()
        decls.append((name.strip().lower(), value, important))
    return tuple(decls)


def parse_css(css: str) -> list[Rule]:
    rules: list[Rule] = []
    for prelude, body in _top_level_blocks(_strip_comments(css)):
        if prelude.startswith("@"):
            continue
        decls = _parse_declarations(body)
        for selector in _split_top_level(prelude, ","):
            rules.append(Rule(selector, decls, len(rules)))
    return rules


def css_variables(rules: list[Rule]) -> dict[str, str]:
    variables: dict[str, str] = {}
    for rule in rules:
        if rule.selector == ":root":
            variables.update({n: v for n, v, _ in rule.declarations if n.startswith("--")})
    return variables


_COMPOUND_TOKEN = re.compile(
    r"""
    (?P<tag>^[a-zA-Z][\w-]*|\*)
    |\.(?P<cls>[\w-]+)
    |\[(?P<attr>[\w-]+)(?:=(?P<quote>["']?)(?P<val>.*?)(?P=quote))?\]
    |:(?P<pseudo>[\w-]+)(?:\((?P<arg>[^()]*)\))?
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class Compound:
    tag: str | None
    classes: tuple[str, ...]
    attrs: tuple[tuple[str, str | None], ...]
    pseudos: tuple[tuple[str, str | None], ...]


def _parse_compound(text: str) -> Compound | None:
    tag = None
    classes: list[str] = []
    attrs: list[tuple[str, str | None]] = []
    pseudos: list[tuple[str, str | None]] = []
    pos = 0
    while pos < len(text):
        m = _COMPOUND_TOKEN.match(text, pos)
        if not m or m.end() == pos:
            return None
        if m.group("tag"):
            tag = None if m.group("tag") == "*" else m.group("tag")
        elif m.group("cls"):
            classes.append(m.group("cls"))
        elif m.group("attr"):
            attrs.append((m.group("attr"), m.group("val")))
        else:
            pseudos.append((m.group("pseudo"), m.group("arg")))
        pos = m.end()
    return Compound(tag, tuple(classes), tuple(attrs), tuple(pseudos))


def _split_selector(selector: str) -> list[tuple[str, str]] | None:
    """Return [(combinator, compound_text)] left to right; combinator is ' ' or '>'."""
    parts: list[tuple[str, str]] = []
    combinator = " "
    depth = 0
    current: list[str] = []

    def flush() -> None:
        nonlocal combinator
        if current:
            parts.append((combinator, "".join(current)))
            current.clear()
            combinator = " "

    for ch in selector:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if depth == 0 and ch.isspace():
            flush()
        elif depth == 0 and ch == ">":
            flush()
            combinator = ">"
        else:
            current.append(ch)
    flush()
    return parts or None


def _matches_compound(node: Node, comp: Compound) -> bool:
    if comp.tag and node.tag != comp.tag:
        return False
    if any(c not in node.classes for c in comp.classes):
        return False
    for name, value in comp.attrs:
        if name not in node.attrs or (value is not None and node.attrs[name] != value):
            return False
    for name, arg in comp.pseudos:
        if name == "hover":
            if "hover" not in node.state:
                return False
        elif name == "disabled":
            if "disabled" not in node.attrs:
                return False
        elif name == "not" and arg:
            inner = _parse_compound(arg.strip())
            if inner is None or _matches_compound(node, inner):
                return False
        else:
            return False
    return True


def _supported(selector: str) -> list[tuple[str, Compound]] | None:
    parts = _split_selector(selector)
    if not parts:
        return None
    parsed: list[tuple[str, Compound]] = []
    for combinator, text in parts:
        comp = _parse_compound(text)
        if comp is None:
            return None
        parsed.append((combinator, comp))
    return parsed


def _match_chain(node: Node, parsed: list[tuple[str, Compound]]) -> bool:
    combinator, comp = parsed[-1]
    if not _matches_compound(node, comp):
        return False
    rest = parsed[:-1]
    if not rest:
        return True
    ancestor = node.parent
    if combinator == ">":
        return ancestor is not None and _match_chain(ancestor, rest)
    while ancestor is not None:
        if _match_chain(ancestor, rest):
            return True
        ancestor = ancestor.parent
    return False


def _specificity(parsed: list[tuple[str, Compound]]) -> tuple[int, int, int]:
    classes = types = 0
    for _, comp in parsed:
        classes += len(comp.classes) + len(comp.attrs) + len(comp.pseudos)
        types += 1 if comp.tag else 0
    return 0, classes, types


def _cascade(
    node: Node, props: tuple[str, ...], rules: list[Rule]
) -> dict[str, tuple[str, tuple[bool, tuple[int, int, int], int]]]:
    winners: dict[str, tuple[str, tuple[bool, tuple[int, int, int], int]]] = {}
    for rule in rules:
        parsed = _supported(rule.selector)
        if parsed is None or not _match_chain(node, parsed):
            continue
        spec = _specificity(parsed)
        for name, value, important in rule.declarations:
            if name not in props:
                continue
            rank = (important, spec, rule.order)
            if name not in winners or rank >= winners[name][1]:
                winners[name] = (value, rank)
    return winners


def _resolve_var(value: str, variables: dict[str, str], depth: int = 0) -> str:
    def repl(m: re.Match[str]) -> str:
        name, fallback = m.group(1), (m.group(2) or "").strip()
        resolved = variables.get(name, fallback)
        return _resolve_var(resolved, variables, depth + 1) if depth < 10 else resolved

    return re.sub(r"var\(\s*(--[\w-]+)\s*(?:,\s*([^)]*))?\)", repl, value.strip())


def to_hex(value: str) -> str | None:
    value = value.strip().lower()
    m = re.fullmatch(r"#([0-9a-f]{3})", value)
    if m:
        return "#" + "".join(c * 2 for c in m.group(1))
    if re.fullmatch(r"#[0-9a-f]{6}", value):
        return value
    m = re.fullmatch(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", value)
    if m:
        return "#{:02x}{:02x}{:02x}".format(*(int(g) for g in m.groups()))
    return {"white": "#ffffff", "black": "#000000"}.get(value)


def label_color(node: Node, rules: list[Rule], variables: dict[str, str]) -> str | None:
    """Computed text color, honouring inheritance and -webkit-text-fill-color."""
    current: Node | None = node
    while current is not None:
        won = _cascade(current, _TEXT_PROPS, rules)
        for prop in _TEXT_PROPS:
            if prop in won:
                color = to_hex(_resolve_var(won[prop][0], variables))
                if color:
                    return color
        current = current.parent
    return None


def fill_color(node: Node, rules: list[Rule], variables: dict[str, str]) -> str | None:
    won = _cascade(node, _FILL_PROPS, rules)
    if not won:
        return None
    value, _ = max(won.values(), key=lambda item: item[1])
    return to_hex(_resolve_var(value, variables))


def native_fill(node: Node, config: dict[str, str]) -> str:
    """Approximate Streamlit's own fill when the theme CSS leaves it unset."""
    kind = node.attrs.get("kind", "")
    if kind.startswith("primary") and "disabled" not in node.attrs:
        return config["primaryColor"]
    return config["backgroundColor"]


@dataclass(frozen=True)
class ButtonVariant:
    name: str
    container_class: str
    tag: str
    testid: str
    kind: str


BUTTON_VARIANTS = (
    ButtonVariant("button primary", "stButton", "button", "stBaseButton-primary", "primary"),
    ButtonVariant("button secondary", "stButton", "button", "stBaseButton-secondary", "secondary"),
    ButtonVariant(
        "download primary", "stDownloadButton", "button", "stBaseButton-primary", "primary"
    ),
    ButtonVariant(
        "download secondary", "stDownloadButton", "button", "stBaseButton-secondary", "secondary"
    ),
    ButtonVariant("link primary", "stLinkButton", "a", "stBaseLinkButton-primary", "primary"),
    ButtonVariant("link secondary", "stLinkButton", "a", "stBaseLinkButton-secondary", "secondary"),
    ButtonVariant(
        "form submit primary",
        "stFormSubmitButton",
        "button",
        "stBaseButton-primaryFormSubmit",
        "primaryFormSubmit",
    ),
    ButtonVariant(
        "form submit secondary",
        "stFormSubmitButton",
        "button",
        "stBaseButton-secondaryFormSubmit",
        "secondaryFormSubmit",
    ),
)

STATES = ("default", "hover", "disabled")


def build_label(variant: ButtonVariant, state: str) -> tuple[Node, Node]:
    """Return (button element, label ``<p>``) for one variant and interaction state."""
    node_state = frozenset({"hover"}) if state == "hover" else frozenset()
    app = Node("div", ("stApp",), state=node_state)
    container = Node("div", (variant.container_class,), parent=app, state=node_state)
    attrs = {"data-testid": variant.testid, "kind": variant.kind}
    if state == "disabled":
        attrs["disabled"] = ""
    button = Node(variant.tag, attrs=attrs, parent=container, state=node_state)
    inner = Node("div", parent=button, state=node_state)
    outer_span = Node("span", attrs={"data-has-shortcut": "false"}, parent=inner, state=node_state)
    inner_span = Node("span", parent=outer_span, state=node_state)
    markdown = Node(
        "div", attrs={"data-testid": "stMarkdownContainer"}, parent=inner_span, state=node_state
    )
    label = Node("p", parent=markdown, state=node_state)
    return button, label


def button_contrast(css: str, variant: ButtonVariant, state: str) -> tuple[float, str, str]:
    rules = parse_css(css)
    variables = css_variables(rules)
    config = tomllib.loads(STREAMLIT_CONFIG.read_text(encoding="utf-8"))["theme"]
    button, label = build_label(variant, state)
    fg = label_color(label, rules, variables)
    bg = fill_color(button, rules, variables) or native_fill(button, config)
    assert fg is not None, f"{variant.name} [{state}]: no label color resolved"
    return contrast_ratio(fg, bg), fg, bg


THEME_CSS = APP_THEME_STATIC_CSS.read_text(encoding="utf-8")


@pytest.mark.parametrize("state", STATES)
@pytest.mark.parametrize("variant", BUTTON_VARIANTS, ids=lambda v: v.name)
def test_button_label_contrast_meets_wcag_aa(variant: ButtonVariant, state: str) -> None:
    ratio, fg, bg = button_contrast(THEME_CSS, variant, state)
    assert ratio >= MIN_CONTRAST_RATIO_AA, (
        f"{variant.name} [{state}]: label {fg} on fill {bg} has contrast {ratio:.2f}, "
        f"needs {MIN_CONTRAST_RATIO_AA}"
    )


def test_checker_flags_dark_label_on_maroon_fill() -> None:
    css = """
    :root { --accent: #8b1a5c; --text: #5c1040; }
    .stApp p { color: var(--text); }
    .stLinkButton a { background-color: var(--accent) !important; color: #fff !important; }
    """
    variant = next(v for v in BUTTON_VARIANTS if v.name == "link primary")
    ratio, fg, bg = button_contrast(css, variant, "default")
    assert (fg, bg) == ("#5c1040", "#8b1a5c")
    assert ratio < MIN_CONTRAST_RATIO_AA


def test_checker_passes_when_label_rule_wins() -> None:
    css = """
    :root { --accent: #8b1a5c; --text: #5c1040; }
    .stApp p { color: var(--text); }
    .stLinkButton a { background-color: var(--accent) !important; color: #fff !important; }
    .stLinkButton a * { color: #fff !important; }
    """
    variant = next(v for v in BUTTON_VARIANTS if v.name == "link primary")
    ratio, fg, _ = button_contrast(css, variant, "default")
    assert fg == "#ffffff"
    assert ratio >= MIN_CONTRAST_RATIO_AA
