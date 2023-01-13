#coding:windows-1251

import json
from collections import defaultdict
from itertools import product
from pathlib import Path


tagger: dict[str, list] = defaultdict(list)
supertags = ['гост', 'iso', 'артикул изделия']


def update_tagger(*, keywords: list[str], tags: list[str]) -> None:
    """Update tagger.json with a new record. """

    for keyword, tag in product(keywords, tags):
        if not tagger[keyword].__contains__(tag):
            tagger[keyword].append(tag)

    folder = Path('json')

    if not folder.exists():
        folder.mkdir()

    path = folder / 'tagger.json'

    with path.open('w', encoding='windows-1251') as target:
        json.dump(tagger, target, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    update_tagger(keywords=['болт', 'винт', 'гайка', 'шайба', 'шпилька'],
                  tags=['материал/покрытие крепежа', 
                        'класс прочности крепежа', 'din'])
