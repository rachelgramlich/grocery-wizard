"""Tiny CSS cascade resolver for theme regression tests.

Parses ``app_theme.css`` and answers "what color / background does this element end up
with?" for a hand-built DOM chain, so tests can catch the failure CI cannot see in a
browser: a Streamlit widget that no rule targets falls through to a generic rule such as
``.stApp p`` and renders, say, dark text on the dark primary fill.

Supported selector syntax: type, ``*``, ``.class``, ``#id``, ``[attr]``, ``[attr=v]``,
``[attr^=v]``, ``[attr$=v]``, ``[attr*=v]``, descendant and ``>`` combinators. Selectors
with pseudo-classes (``:hover``, ``:has()``, ``:not()``, ...) are treated as
non-matching, so coverage must come from plain selectors. ``@media`` bodies are
flattened and applied unconditionally (stricter than a real browser).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_VAR_RE = re.compile(r"var\(\s*(--[\w-]+)\s*\)")
_ATTR_RE = re.compile(r'\[\s*([\w-]+)\s*(?:([\^$*~|]?=)\s*("[^"]*"|\'[^\']*\'|[^\]\s]*))?\s*\]')
_SIMPLE_RE = re.compile(r"\*|[A-Za-z][\w-]*|\.[\w-]+|#[\w-]+")

INHERITED_PROPERTIES = frozenset({"color", "-webkit-text-fill-color"})


@dataclass(frozen=True, slots=True)
class Compound:
    tag: str | None = None
    classes: tuple[str, ...] = ()
    ids: tuple[str, ...] = ()
    attrs: tuple[tuple[str, str | None, str | None], ...] = ()
    unsupported: bool = False

    def specificity(self) -> tuple[int, int, int]:
        return (len(self.ids), len(self.classes) + len(self.attrs), 1 if self.tag else 0)


@dataclass(frozen=True, slots=True)
class Selector:
    # (combinator-to-previous, compound); first combinator is ""
    parts: tuple[tuple[str, Compound], ...]
    raw: str = ""

    def specificity(self) -> tuple[int, int, int]:
        totals = [0, 0, 0]
        for _, compound in self.parts:
            for index, value in enumerate(compound.specificity()):
                totals[index] += value
        return (totals[0], totals[1], totals[2])


@dataclass(frozen=True, slots=True)
class Rule:
    selectors: tuple[Selector, ...]
    declarations: tuple[tuple[str, str, bool], ...]  # (property, value, important)
    order: int


@dataclass(eq=False)
class Element:
    tag: str
    classes: tuple[str, ...] = ()
    attrs: dict[str, str] = field(default_factory=dict)
    parent: Element | None = None

    def child(
        self,
        tag: str,
        *,
        classes: tuple[str, ...] = (),
        attrs: dict[str, str] | None = None,
    ) -> Element:
        return Element(tag, classes, dict(attrs or {}), self)

    def path(self) -> str:
        names = []
        node: Element | None = self
        while node is not None:
            testid = node.attrs.get("data-testid")
            names.append(node.tag + (f'[data-testid="{testid}"]' if testid else ""))
            node = node.parent
        return " > ".join(reversed(names))


def _split_top_level(text: str, separator: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    start = 0
    for index, char in enumerate(text):
        if char in "([":
            depth += 1
        elif char in ")]":
            depth -= 1
        elif char == separator and depth == 0:
            parts.append(text[start:index])
            start = index + 1
    parts.append(text[start:])
    return [part.strip() for part in parts if part.strip()]


def _parse_compound(text: str) -> Compound:
    tag: str | None = None
    classes: list[str] = []
    ids: list[str] = []
    attrs: list[tuple[str, str | None, str | None]] = []
    index = 0
    while index < len(text):
        if text[index] == "[":
            match = _ATTR_RE.match(text, index)
            if match is None:
                return Compound(unsupported=True)
            name, operator, raw = match.groups()
            value = raw.strip("\"'") if raw is not None else None
            attrs.append((name, operator, value))
            index = match.end()
            continue
        if text[index] == ":":
            return Compound(unsupported=True)
        match = _SIMPLE_RE.match(text, index)
        if match is None:
            return Compound(unsupported=True)
        token = match.group(0)
        if token.startswith("."):
            classes.append(token[1:])
        elif token.startswith("#"):
            ids.append(token[1:])
        elif token != "*":
            tag = token
        index = match.end()
    return Compound(tag, tuple(classes), tuple(ids), tuple(attrs))


def parse_selector(text: str) -> Selector:
    parts: list[tuple[str, Compound]] = []
    combinator = ""
    buffer = ""
    depth = 0

    def flush() -> None:
        nonlocal buffer, combinator
        if buffer:
            parts.append((combinator, _parse_compound(buffer)))
            buffer = ""
            combinator = " "

    for char in text.strip():
        if char in "([":
            depth += 1
        elif char in ")]":
            depth -= 1
        if depth == 0 and char.isspace():
            flush()
            continue
        if depth == 0 and char == ">":
            flush()
            combinator = ">"
            continue
        buffer += char
    flush()
    return Selector(tuple(parts), text.strip())


def _parse_declarations(body: str) -> tuple[tuple[str, str, bool], ...]:
    declarations = []
    for chunk in body.split(";"):
        if ":" not in chunk:
            continue
        prop, value = chunk.split(":", 1)
        value = value.strip()
        important = value.endswith("!important")
        if important:
            value = value[: -len("!important")].strip()
        declarations.append((prop.strip().lower(), value, important))
    return tuple(declarations)


def parse_css(css: str) -> list[Rule]:
    text = _COMMENT_RE.sub("", css)
    rules: list[Rule] = []

    def walk(start: int, end: int) -> None:
        index = start
        while index < end:
            open_brace = text.find("{", index, end)
            if open_brace == -1:
                return
            depth = 1
            close = open_brace + 1
            while close < end and depth:
                depth += (text[close] == "{") - (text[close] == "}")
                close += 1
            prelude = text[index:open_brace].strip()
            body_end = close - 1
            if prelude.startswith("@"):
                walk(open_brace + 1, body_end)
            elif prelude:
                selectors = tuple(parse_selector(part) for part in _split_top_level(prelude, ","))
                body = text[open_brace + 1 : body_end]
                rules.append(Rule(selectors, _parse_declarations(body), len(rules)))
            index = close

    walk(0, len(text))
    return rules


def root_variables(rules: list[Rule]) -> dict[str, str]:
    """Custom properties declared on ``:root`` (later declarations win)."""
    return {
        prop: value
        for rule in rules
        if any(selector.raw == ":root" for selector in rule.selectors)
        for prop, value, _ in rule.declarations
        if prop.startswith("--")
    }


def _attr_matches(element: Element, name: str, operator: str | None, expected: str | None) -> bool:
    actual = element.attrs.get(name)
    if actual is None:
        return False
    if operator is None or expected is None:
        return True
    return {
        "=": actual == expected,
        "^=": actual.startswith(expected),
        "$=": actual.endswith(expected),
        "*=": expected in actual,
    }.get(operator, False)


def _compound_matches(element: Element, compound: Compound) -> bool:
    if compound.unsupported:
        return False
    if compound.tag is not None and compound.tag != element.tag:
        return False
    if any(name not in element.classes for name in compound.classes):
        return False
    if any(element.attrs.get("id") != value for value in compound.ids):
        return False
    return all(_attr_matches(element, *attr) for attr in compound.attrs)


def _match_from(element: Element | None, parts: tuple[tuple[str, Compound], ...]) -> bool:
    if element is None:
        return False
    combinator, compound = parts[-1]
    if not _compound_matches(element, compound):
        return False
    if len(parts) == 1:
        return True
    rest = parts[:-1]
    if combinator == ">":
        return _match_from(element.parent, rest)
    ancestor = element.parent
    while ancestor is not None:
        if _match_from(ancestor, rest):
            return True
        ancestor = ancestor.parent
    return False


def selector_matches(selector: Selector, element: Element) -> bool:
    return bool(selector.parts) and _match_from(element, selector.parts)


class Stylesheet:
    def __init__(self, css: str) -> None:
        self.rules = parse_css(css)
        self.variables = root_variables(self.rules)

    def resolve(self, value: str) -> str:
        for _ in range(8):
            replaced = _VAR_RE.sub(lambda m: self.variables.get(m.group(1), m.group(0)), value)
            if replaced == value:
                break
            value = replaced
        return value.strip().lower()

    def own_value(self, element: Element, prop: str) -> str | None:
        best_key: tuple[bool, tuple[int, int, int], int] | None = None
        best_value: str | None = None
        for rule in self.rules:
            specificities = [
                selector.specificity()
                for selector in rule.selectors
                if selector_matches(selector, element)
            ]
            if not specificities:
                continue
            specificity = max(specificities)
            for name, value, important in rule.declarations:
                if name != prop:
                    continue
                key = (important, specificity, rule.order)
                if best_key is None or key > best_key:
                    best_key, best_value = key, value
        return self.resolve(best_value) if best_value is not None else None

    def computed(self, element: Element, prop: str) -> str | None:
        node: Element | None = element
        while node is not None:
            value = self.own_value(node, prop)
            if value is not None:
                return value
            if prop not in INHERITED_PROPERTIES:
                return None
            node = node.parent
        return None
