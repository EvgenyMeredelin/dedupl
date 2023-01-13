#coding:windows-1251

import argparse
import builtins
import csv
import re
from collections import Counter
from collections.abc import Iterator
from datetime import datetime
from functools import lru_cache
from itertools import groupby
from pathlib import Path
from typing import Any, Optional

from pymorphy2 import MorphAnalyzer
from typeguard import check_type

import cleaner


parser_type = list[dict[str, str | list[str]]]
parsed_cont = dict[str, str | Counter[str, int] | set | None]  # container
parsed_type = dict[str, parsed_cont]
duplic_type = dict[tuple[str, str], float]
collec_type = list[str] | dict[str, int] | parsed_type | duplic_type

fmt = '%Y-%m-%d_%H-%M-%S'
now = datetime.now().strftime(fmt)
csv_reports = Path('csv_reports')
csv_sources = Path('csv_sources')

if not csv_reports.exists():
    csv_reports.mkdir()
    
morph = MorphAnalyzer()


def get_options(argv: list[str]) -> argparse.Namespace:
    """Parse command line arguments. """

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter,
        description="Argument parser for Fertoing 'Deduplicate' project",
        epilog='Meredelin Evgeny, meredelin@pm.me, 2022'
    )
    
    parser.add_argument(
        'source_file', help='Input file with inventory items to parse.'
    )
    
    parser.add_argument(
        'search_mode', choices=['any', 'all'],
        help="Argument manages items pick basing on presence of KEYWORDS.\n"
             "Use corresponds to 'any' and 'all' builtins."
    )
    
    parser.add_argument(
        'keywords', nargs='+',
        help='List of words to pick items by.\n'
             'Lower case matches any case, upper case matches exact input.'
    )
    
    parser.add_argument(
        '-e', '--exclude', nargs='*',
        help='List of words to filter items out. Any word excludes item.\n'
             'Lower case matches any case, upper case matches exact input.'
    )
    
    parser.add_argument(
        '-t', '--threshold', type=float, default=0.01,
        help='Min ratio of similarity of items in report. Defaults to 0.01.'
    )
    
    return parser.parse_args(argv)


def get_sample(source_file: str, search_mode: str, keywords: list[str], 
               exclude: list[str]) -> tuple[list[str], list[str]]:
    """Filter inventory items by given keywords and fetch a sample of items 
    to parse. Collect remaining items for the next source file. 
    """

    if exclude is None:
        exclude = []

    sample = []
    next_source = []

    with open(source_file, 'r', encoding='windows-1251') as inventory:
        for item in inventory:
            item = item.rstrip()
            if all(
                [
                    getattr(builtins, search_mode)(
                        word in (item, item.lower())[word.islower()]
                        for word in keywords),

                    all(word not in (item, item.lower())[word.islower()]
                        for word in exclude)
                ]
            ):
                sample.append(item)
            else: 
                next_source.append(item)
    
    return sample, next_source


@lru_cache(None)
def get_normal_form(word: str, pos: str = '') -> Optional[str]:
    """Get normal form of a word. POS optional. """
    
    parse_objects = morph.parse(word)
    
    if not pos:
        return parse_objects[0].normal_form
    
    for obj in parse_objects:
        if obj.tag.POS == pos and obj.score > 0.1:
            return obj.normal_form


def get_keywords_iter(item: str) -> Iterator[str]:
    """Get an iterator of keywords (Russian nouns in normal form). """
    g = lambda string: get_normal_form(string.replace('ё', 'е'), 'NOUN')
    words = map(g, re.findall(r'[а-яё]{3,}', item.lower()))
    f = lambda word: word is not None and word not in cleaner.stopwords
    return filter(f, words)


def get_next_keywords(next_source: list[str]) -> dict[str, int]:
    """Extract and count keywords (Russian nouns in normal form) 
    from inventory items for the next parsing iteration. 
    """ 
    
    next_keywords = Counter()
    
    for item in next_source:
        item = cleaner.remove_retired_mark(item)
        next_keywords.update(get_keywords_iter(item))
    
    f = lambda item: (-item[1], item[0])
    return dict(sorted(next_keywords.items(), key=f))


def get_kits(item: str, flag: bool) -> tuple[Counter[str, int], set[str]]:
    """Get item's tester kit and a set of keywords (normalized Rus nouns).
     
    FLAG is True means tags cloud never extended and consists only of
    supertags, i.e. items processed with no specific parser prepared.
    
    EXTRAS are Russian title-cased words (abbreviations and names). 
    '[км]?' for kilo/mega prefixes.
    
    TESTER collects mandatory matches: size-like sequences, latin words
    of length > 1 (this ignores 'D' for diameter, 'x' for times, etc.),
    optional extras. Digits and latin words captured separately to avoid 
    making mixed greedy sequences mandatory.
    
    KWORDS are Russian nouns in normal form. Subtract extras to avoid 
    doubling matches in ratio evaluation. Example. 'Холодильник Бирюса': 
    both words are keywords and 'Бирюса' is an extra as well.
    """
    extras = re.findall(r'[км]?[А-Я][А-Яа-яё]*', item) if flag else []
    tester = Counter(re.findall(r'[0-9.,]+|[a-z]{2,}', item.lower()) + extras)
    kwords = set(get_keywords_iter(item)) - set(map(str.lower, extras))
    return tester, kwords


def get_ratio(a: parsed_cont, b: parsed_cont, behavior: dict[str, str],
              threshold: float) -> float | bool:
    """Perform STRONG and GROUPED tests. If tests passed get items 
    ratio of similarity if ratio exceeds given threshold, else False. 
    
    STRONG test: 
        * if items' tester kits are equal (see get_kits for details) and 
        * all attributes demanding strong comparison are equal pairwise.
    
    Strong test accepts any equal attributes, including None and None,
    but ratio counts only meaningful ones (assigned a non-None value). 
    This differs data of different quality.
    
    GROUPED test:
        * if at least one meaningful pair of attributes accepting 
        grouped comparison are equal.
    """
    
    if a['T'] != b['T']:
        # strong test failed
        return False
    
    tmatch = len(a['T'])
    smatch = stotal = gmatch = gtotal = 0
    
    if 's' in behavior:
        for attr in behavior['s']:
            if a[attr] != b[attr]:
                # strong test failed
                return False
            if a[attr] is not None:
                smatch += 1
        stotal = len(behavior['s'])
        
    if 'g' in behavior:
        gtotal = len(behavior['g'])
        for attr in behavior['g']:
            if a[attr] == b[attr]:
                if a[attr] is None:
                    gtotal -= 1
                else: 
                    gmatch += 1
        if not gmatch:
            # grouped test failed
            return False
    
    # one match granted one point
    numer = len(a['K'] & b['K']) + smatch + gmatch + tmatch
    denom = len(a['K'] | b['K']) + stotal + gtotal + tmatch
    ratio = round(numer / denom, 2) if denom else 0
    
    if ratio > threshold:
        return ratio
    
    return False


def check_type_mod(obj: Any, *expected_types: Any) -> bool:
    """Boolify typeguard.check_type output. """
    
    # tested: joining types with a pipe is not an option
    # so we check the any-condition quitting on 1st True
    
    for type_ in expected_types:
        try:
            check_type('', obj, type_)
            return True
        except TypeError:
            pass
            
    return False


def write_csv_report(target_path: str, header: Optional[list[str]], 
                     collection: collec_type) -> None:
    """Write results collection to a csv report. """
        
    with target_path.open('w', encoding='windows-1251', newline='') as target:
        writer = csv.writer(target)
        if header is not None:
            writer.writerow(header)
        
        # write next_source file
        if check_type_mod(collection, list[str]):
            for item in collection:
                writer.writerow([item])
                
        # write parsed/clones reports
        elif check_type_mod(collection, parsed_type, dict[str, int]):
            for item in collection.items():
                writer.writerow(item)
                
        # write pairs/clusters of duplicates report
        elif check_type_mod(collection, duplic_type):
            g = lambda item: item[0][0]
            for _, group in groupby(collection.items(), key=g):
                f = lambda item: (-item[1], item[0][1])
                for pair, rate in sorted(group, key=f):
                    writer.writerow([*pair, rate])
                writer.writerow([])
        else: 
            assert False
            