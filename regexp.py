#coding:windows-1251

import json
from pathlib import Path
from typing import TypedDict


class RegexRecord(TypedDict):
    pattern: str
    attr_captured: str
    tags: list[str]


regex: list[RegexRecord] = []


def update_regex(
    *, pattern: str, attr_captured: str, tags: list[str]
) -> None:
    """Update regex.json with a new regex record. """
    
    regex.append(dict(pattern=pattern, 
                      attr_captured=attr_captured,
                      tags=tags))

    folder = Path('json')

    if not folder.exists():
        folder.mkdir()

    path = folder / 'regex.json'

    with path.open('w', encoding='windows-1251') as target:
        json.dump(regex, target, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    update_regex(pattern=(r'(?i)(?P<head>.*)'
                          r'din\s*(?P<din>\d+)'
                          r'(?P<tail>.*)'),
                 attr_captured='din',
                 tags=['din'])
    
    update_regex(pattern=(r'(?i)(?P<head>.*)'
                          r'гост\s*р?\s*(?P<gost>[0-9.–-]+)'
                          r'(?P<tail>.*)'),
                 attr_captured='gost',
                 tags=['гост'])

    update_regex(pattern=(r'(?i)(?P<head>.*)'
                          r'iso\s*(?P<iso>[0-9:–-]+)'
                          r'(?P<tail>.*)'),
                 attr_captured='iso',
                 tags=['iso'])

    update_regex(pattern=(r'(?i)(?P<head>.*)'
                          r'\s(артикул|арт\.?)\s*(?P<sku>.+)'
                          r'(?P<tail>)'),  # empty tail consistent with protocol
                 attr_captured='sku',
                 tags=['артикул изделия'])
    