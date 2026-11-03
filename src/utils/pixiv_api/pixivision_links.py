"""Normalize relative and absolute Pixivision links before model validation."""

import re
from urllib.parse import urljoin, urlsplit


def parse_pixivision_link(href: str, root_url: str, kind: str) -> tuple[int, str]:
    url = urljoin(root_url.rstrip('/') + '/', href)
    parsed = urlsplit(url)
    root = urlsplit(root_url)
    if parsed.scheme not in {'http', 'https'} or parsed.hostname != root.hostname:
        raise ValueError(f'Invalid Pixivision link host: {href!r}')
    matched = re.fullmatch(rf'/[a-z]{{2}}/{re.escape(kind)}/([0-9]+)/?', parsed.path)
    if matched is None:
        raise ValueError(f'Invalid Pixivision {kind} link path: {href!r}')
    return int(matched.group(1)), url
