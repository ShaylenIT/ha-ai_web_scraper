"""CSS strikethrough detection for DOM-mode scraping.

Extracts CSS ``text-decoration: line-through`` rules from ``<style>`` blocks
and injects ``~~`` Markdown markers around matching elements in the raw HTML.
This catches strikethroughs in DOM mode (no Browserless) that would otherwise
be missed because no browser computes the CSS.
"""

from __future__ import annotations

import re


def strikethrough_from_css(html_text: str) -> str:
    """Inject ~~ markers around elements targeted by CSS line-through rules.

    Handles: .class, tag, tag.class, .parent .child descendants, and
    inline style="text-decoration: line-through".
    """
    if not isinstance(html_text, str) or "line-through" not in html_text:
        return html_text

    # --- Step 1: inline style="text-decoration: line-through" ---
    html_text = re.sub(
        r"(?is)(<[a-z][^>]*?style=[\"'])(?:[^\"']*?)text-decoration\s*:\s*line-through[^\"']*?([\"'][^>]*>)(.*?)(</[a-z]+>)",
        lambda m: m.group(1) + m.group(2) + "~~" + m.group(3) + "~~" + m.group(4),
        html_text,
    )

    # --- Step 2: extract CSS rules from <style> blocks ---
    style_blocks = re.findall(r"(?is)<style[^>]*>(.*?)</style>", html_text)

    selectors: list[str] = []
    for block in style_blocks:
        rules = re.findall(
            r"(?is)([^@{}]*?)\s*\{[^}]*?text-decoration\s*:\s*line-through[^}]*?\}",
            block,
        )
        for rule in rules:
            for raw_sel in re.split(r"\s*,\s*", rule.strip()):
                sel = raw_sel.strip()
                if sel:
                    clean_sel = re.sub(r":{1,2}[a-z-]+(?:\([^)]*\))?", "", sel).strip()
                    if clean_sel:
                        selectors.append(clean_sel)

    if not selectors:
        return html_text

    # --- Step 3: apply each selector ---
    for selector in selectors:
        parts = re.split(r"\s*(?:>|\s)\s*", selector)
        target = parts[-1]
        ancestors = parts[:-1]

        target_tag, target_class = _parse_target(target)
        ancestor_classes = _parse_ancestors(ancestors)

        class_attr = _build_class_attr(target_class)
        tag_pattern = re.escape(target_tag) if target_tag != "[a-z0-9]+" else target_tag

        if ancestor_classes:
            for anc_cls in ancestor_classes:
                anc_pattern = _ancestor_pattern(anc_cls, tag_pattern, class_attr)
                html_text = _apply_with_loop(anc_pattern, html_text, _ancestor_replacer)
        else:
            pattern = _direct_pattern(tag_pattern, class_attr)
            html_text = _apply_with_loop(pattern, html_text, _direct_replacer)

    return html_text


def _parse_target(target: str) -> tuple[str, str]:
    """Parse a CSS selector into (tag_name, class_name)."""
    if target.startswith("."):
        return "[a-z0-9]+", target[1:]
    if "." in target:
        parts = target.split(".", 1)
        return parts[0], parts[1]
    return target, ""


def _parse_ancestors(ancestors: list[str]) -> list[str]:
    """Extract class names from ancestor selector parts."""
    result: list[str] = []
    for anc in ancestors:
        if anc.startswith("."):
            result.append(anc[1:])
        elif "." in anc:
            result.append(anc.split(".", 1)[1])
    return result


def _build_class_attr(target_class: str) -> str:
    """Build a regex snippet matching ``class="...target_class..."``."""
    if not target_class:
        return ""
    escaped = re.escape(target_class)
    return 'class="[^"]*\\b' + escaped + '\\b[^"]*"'


def _ancestor_pattern(anc_cls: str, tag_pattern: str, class_attr: str) -> str:
    """Build regex for a target element inside an ancestor with a given class."""
    escaped = re.escape(anc_cls)
    return (
        r'(<[a-z0-9]+[^>]*class="[^"]*\b'
        + escaped
        + r'\b[^"]*"[^>]*>)(.*?)'
        + "(<"
        + tag_pattern
        + r"(?:\s+[^>]*"
        + class_attr
        + r"[^>]*)?>)"
        + "(.*?)"
        + "(</"
        + tag_pattern
        + ">)"
    )


def _direct_pattern(tag_pattern: str, class_attr: str) -> str:
    """Build regex for a target element anywhere (no ancestor constraint)."""
    return (
        "(<"
        + tag_pattern
        + r"(?:\s+[^>]*"
        + class_attr
        + r"[^>]*)?>)"
        + "(.*?)"
        + "(</"
        + tag_pattern
        + ">)"
    )


def _ancestor_replacer(m: re.Match) -> str:
    """Replacement for ancestor-constrained matches — preserves all groups."""
    return (
        m.group(1)  # ancestor opening tag
        + m.group(2)  # text between ancestor and target
        + m.group(3)  # target opening tag
        + ("~~" if "~~" not in m.group(4) else "")
        + m.group(4)  # content inside target
        + ("~~" if "~~" not in m.group(4) else "")
        + m.group(5)  # target closing tag
    )


def _direct_replacer(m: re.Match) -> str:
    """Replacement for direct-selector matches."""
    return (
        m.group(1)
        + ("~~" if "~~" not in m.group(2) else "")
        + m.group(2)
        + ("~~" if "~~" not in m.group(2) else "")
        + m.group(3)
    )


def _apply_with_loop(pattern: str, html_text: str, replacer) -> str:
    """Apply re.sub up to 5 times until no more changes occur."""
    for _ in range(5):
        new_text = re.sub(
            pattern,
            replacer,
            html_text,
            count=0,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if new_text == html_text:
            break
        html_text = new_text
    return html_text
