#coding:windows-1251

import json
import re
from pathlib import Path
from typing import Optional, TypedDict


class FuncsRecord(TypedDict):
    func_name: str
    attr_captured: str
    tags: list[str]


funcs: list[FuncsRecord] = []


def update_funcs(
    *, func_name: str, attr_captured: str, tags: list[str]
) -> None:
    """Update funcs.json with a new function record. """

    funcs.append(dict(func_name=func_name,
                      attr_captured=attr_captured,
                      tags=tags))

    folder = Path('json')

    if not folder.exists():
        folder.mkdir()

    path = folder / 'funcs.json'

    with path.open('w', encoding='windows-1251') as target:
        json.dump(funcs, target, ensure_ascii=False, indent=4)


def get_fastener_plating(item: str, item_: str) -> tuple[Optional[str], str]:
    """Capture plating/material of a fastener item and normalize it. """

    item = item.lower()

    plating = (
        'ZN' if any(item.__contains__(x) for x in (
            'цинк', 'zinc', 'zn', ' оц ', ' оц.', ' ц ')) else
        'A1' if any(item.__contains__(x) for x in ('а1', 'a1')) else
        'A2' if any(item.__contains__(x) for x in ('а2', 'a2')) else
        'A4' if any(item.__contains__(x) for x in ('а4', 'a4')) else
        'SS' if 'нерж' in item else
        'ST' if any(item.__contains__(x) for x in (
            'ч/м', 'б/п', 'без покр')) else
        'BR' if 'латун' in item else
        'PA' if 'полиам' in item else
        
        # back to ZN: practical decision based on some
        # pre-knowledge and highly-likely factors
        'ZN' if any(item.__contains__(x) for x in (
            'din', 'iso', 'гост', 'анкер', 'самоконтр', 
            'стопор', 'насеч', 'фланец', 'фланц', 'бурт'))
        
        else None
    )

    item_cleaned = ''

    for word in item_.split():
        if all(
            [
                all(not word.lower().__contains__(x) for x in (
                    'цинк', 'zinc', 'оц.', 'ч/м', 'б/п',
                    'а2', 'a2', 'а4', 'a4', 'нерж',
                    'латун', 'никел', 'полиам', 'стал',
                    'покрыт', 'plat')),
                    
                all(word.lower() != x for x in ('zn', 'оц', 'ц', 'без', 'ni'))
            ]
        ):
            item_cleaned += word + ' '

    return plating, item_cleaned


def get_fastener_class(_: str, item: str) -> tuple[Optional[str], str]:
    """Capture fastener class and normalize it. """
    
    pattern = (r'(?i)(?P<head>.*?\s)'
               r'(класс|кл\.?)?\s*(пр\.?)?\s*'
               r'(?P<class>([3-689]|10|12)[.,]\d)'
               r'(?P<tail>\s.*)')
    
    fastener_class, item_ = None, item
    
    if m := re.match(pattern, item):
        fastener_class = m.group('class').replace(',', '.')
        item_ = f"{m.group('head')} {m.group('tail')}"
    
    return fastener_class, item_


if __name__ == '__main__':
    update_funcs(func_name='get_fastener_plating',
                 attr_captured='fastener_plating',
                 tags=['материал/покрытие крепежа'])
    
    update_funcs(func_name='get_fastener_class',
                 attr_captured='fastener_class',
                 tags=['класс прочности крепежа'])
