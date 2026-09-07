from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def rupees(value):
    """Format a price with Indian digit grouping, as the original pages did:
    19999 -> 19,999 and 105731 -> 1,05,731 (last three digits, then pairs).
    """
    try:
        amount = int(Decimal(str(value)).quantize(Decimal("1")))
    except (TypeError, ValueError, InvalidOperation):
        return value

    sign = "-" if amount < 0 else ""
    digits = str(abs(amount))
    if len(digits) <= 3:
        return sign + digits

    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return sign + ",".join(groups + [tail])


@register.filter
def stagger(counter0, size=4):
    """Map a 0-based loop index onto the d-1..d-4 reveal delay classes, so a
    grid of any length keeps the same staggered animation as the static pages.
    """
    try:
        return int(counter0) % int(size) + 1
    except (TypeError, ValueError):
        return 1
