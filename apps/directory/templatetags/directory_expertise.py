from django import template

from apps.directory.services import (
    format_expertise_names,
    normalize_expertise_name,
    parse_expertise_names,
)

register = template.Library()


@register.simple_tag
def expertise_chip_query(current_value: str, term_name: str) -> str:
    selected_names = parse_expertise_names(current_value)
    normalized_term = normalize_expertise_name(term_name)
    remaining_names = [
        name for name in selected_names if normalize_expertise_name(name) != normalized_term
    ]
    if len(remaining_names) == len(selected_names):
        remaining_names.append(term_name)
    return format_expertise_names(remaining_names)


@register.simple_tag
def expertise_chip_selected(current_value: str, term_name: str) -> bool:
    normalized_term = normalize_expertise_name(term_name)
    return any(
        normalize_expertise_name(name) == normalized_term
        for name in parse_expertise_names(current_value)
    )
