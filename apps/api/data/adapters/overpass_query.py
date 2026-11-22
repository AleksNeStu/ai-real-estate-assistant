"""
The Overpass QL the neighbourhood adapters ask.

Overpass QL has two rules that are easy to break, and the provider answers
a broken query with HTTP 400 and a parse error - never with data, and never
with an error the caller can read:

* **A union term names its element type every time.** `way["a"] | ["b"]` is a
  parse error: after the first term the element type has to be named again.
* **A filter on the existence of a key is not a filter on its value.**
  `["school"]` means "has a tag NAMED school"; the intent is `amenity=school`.

The provider's own accepted forms are the contract, and this module builds
them: one statement per element type and per filter, each with a value
filter, and no comments - Overpass QL has no comment syntax, so a `#` in the
query is a parse error of its own.
"""

from typing import Sequence


def tag_regex_filter(key: str, values: Sequence[str]) -> str:
    """
    A filter that matches the VALUE of a tag against a list of values.

    The list is anchored at both ends, so `shop` does not match
    `supermarket` and `park` does not match `parking`.
    """
    return '["{}"~"^({})$"]'.format(key, "|".join(values))


def tag_exact_filter(key: str, value: str) -> str:
    """A filter that matches one tag with one value."""
    return '["{}"="{}"]'.format(key, value)


def element_statement(element_type: str, tag_filter: str, around: str) -> str:
    """
    One statement: an element type, a filter and the area it is looked for in.

    Args:
        element_type: The element type - `node`, `way` or `relation`.
        tag_filter: The filter, from `tag_regex_filter` or `tag_exact_filter`.
        around: The area - `radius,lat,lon`.
    """
    return "{}{}(around:{});".format(element_type, tag_filter, around)


def build_query(statements: Sequence[str]) -> str:
    """
    The Overpass QL document: the statements in one union, then the output.

    The output asks for the tags and the centre, so that a `way` or a
    `relation` carries the coordinates the adapters read.
    """
    body = "\n".join("  " + statement for statement in statements)
    return "[out:json][timeout:25];\n(\n{}\n);\nout tags center;".format(body)


def build_area_query(
    area_filter: str,
    statements: Sequence[str],
    area_name: str = "searchArea",
) -> str:
    """
    The Overpass QL document for a query scoped to a NAMED area.

    The area statement is not a union term: it resolves the name to the
    boundary that carries the name, and the union below reads that
    boundary back by name. A place that is named but not located still
    has a boundary, and the provider can count inside it - which is the
    only honest way to measure a place nobody gave coordinates for.

    The statements are the same statements the radius queries use; only
    the scope differs, and the scope is read from the area set.
    """
    body = "\n".join("  " + statement for statement in statements)
    return (
        "[out:json][timeout:60];\n{area_filter}->.{area_name};\n(\n{body}\n);\nout tags center;"
    ).format(area_filter=area_filter, area_name=area_name, body=body)
