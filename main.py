import json
import re
import sys
from collections import Counter, defaultdict
from itertools import combinations

import cleaner
import scraper
import tools as t
from tagger import supertags


def deduplicate(source_file: str, search_mode: str, keywords: list[str],
                exclude: list[str], threshold: float) -> None:
    """Filter inventory items by keywords, parse it, collect attributes.
    Detect probable semantic duplicates and assign a ratio of similarity.
    """    
    
    # STAGE 1: BUILDING A PARSER
    
    def read_dump(filepath: str) -> dict[str, list[str]] | t.parser_type:
        """Read dump file and return a deserialized object. """
        with open(filepath, 'r', encoding='windows-1251') as file:
            obj = json.load(file)
        return obj
    
    
    # prepare tags collection, regex and scraper funcs parsers
    filenames = 'tagger.json', 'regex.json', 'funcs.json'
    tagger, regex, funcs = (read_dump('json/' + fname) for fname in filenames)    
    
    
    def get_tags_cloud() -> list[str]:
        """Collect tags of given keywords to a tags cloud. """
        tags_cloud = list(supertags)
        f = lambda tag: tag not in tags_cloud
        for keyword in keywords:
            if (keyword := keyword.lower()) in tagger:
                tags_cloud.extend(filter(f, tagger[keyword]))
        return tags_cloud
    
    
    tags_cloud = get_tags_cloud()
    
    
    def create_playlist(parser: t.parser_type) -> t.parser_type:
        """Filter parser records by tags cloud. """
        f = lambda rec: any(tag in rec['tags'] for tag in tags_cloud)
        return list(filter(f, parser))
    
    
    # schedule regex and scraper funcs
    playlists = [create_playlist(parser) for parser in (regex, funcs)]
    
    if exclude is None:
        exclude = []
        
    # get a sample of items to parse and a list of remaining items
    sample, next_source = t.get_sample(source_file, search_mode, 
                                       keywords, exclude)
    # extract normalized noun keywords from a list of remaining items
    next_keywords = t.get_next_keywords(next_source)
    
    
    def remove_clones(sample: list[str]) -> tuple[list[str], dict[str, int]]:
        """Count items in a sample and separate it from clones. """
        counter = Counter(sample)
        f = lambda item: item[1] > 1
        clones = dict(filter(f, counter.items()))
        for clone in clones:
            del counter[clone]
        sample = list(counter)
        return sample, clones
    
    
    sample, clones = remove_clones(sample)
    
    
    # STAGE 2: PARSING ITEMS, COLLECTING ATTRIBUTES
    
    def parse_inventory_items() -> t.parsed_type:
        """Parse items in a sample and collect items attributes to a dict. """
        
        parsed = {}
        expr_playlist, func_playlist = playlists
        
        for item in sample:
            parsed[item] = {}
            item_ = cleaner.remove_retired_mark(item)
            
            for expr in expr_playlist:
                attr = expr['attr_captured']
                m = re.match(expr['pattern'], item_)
                if m:
                    parsed[item][attr] = m.group(attr)
                    item_ = f"{m.group('head')} {m.group('tail')}"
                else: 
                    parsed[item][attr] = None
                    
            for func in func_playlist:
                f = getattr(scraper, func['func_name'])
                parsed[item][func['attr_captured']], item_ = f(item, item_)
            
            flag = len(tags_cloud) == len(supertags)
            parsed[item]['T'], parsed[item]['K'] = t.get_kits(item_, flag)
        
        return parsed
   
    
    attrs_captured = [rec['attr_captured'] for pl in playlists for rec in pl]
    
    
    def define_attrs_behavior() -> dict[str, str]:
        """Define attributes' behavior (mode of comparison). """
        
        modes = {'strong': 's', 'grouped': 'g', 'ignore': 'i'}
        behavior = defaultdict(list)
    
        print('\nDefine attributes behavior'
              '\n==========================')

        for key, val in modes.items():
            print(f'{key:_<23}: {val}')

        for attr in attrs_captured:
            while True:
                mode = input(f'{attr.upper():_>23}: ')
                if mode in modes.values():
                    break
            behavior[mode].append(attr)        
        
        return behavior
    
    
    parsed = parse_inventory_items()
    behavior = define_attrs_behavior()
    
    
    # STAGE 3: ATTRIBUTES COMPARISON
    
    def get_rated_pairs() -> t.duplic_type:
        """Compare parsed items pairwise and items' attributes modewise.
        Assign collected pairs a ratio of similarity. 
        """
        pairs = {}
        indic = {}
        
        for p, q in combinations(parsed.items(), 2):
            # item name, dict of its captured attributes
            x, a = p
            y, b = q
            
            if all(
                [   # trailing item does not become leading:
                    # everything it heads was brought by its own head
                    x not in indic,
                    
                    # see tools.get_ratio docstring for details
                    ratio := t.get_ratio(a, b, behavior, threshold)
                ]
            ):
                pairs[(x, y)] = ratio
                indic[y] = x
        
        return pairs
    
    
    pairs = get_rated_pairs()    
    
    
    # STAGE 4: RESULTS OUTPUT
    
    # prepare some info strings for reports filenames
    kw = f'{keywords}'.replace(' ', '') if len(keywords) < 6 else 'KW_TOO_LONG'
    ex = f'{exclude}'.replace(' ', '')
    n = int(re.search(r'\d+', source_file).group(0))
    query = f'{n}_{t.now}_{search_mode}_{kw}_{ex=}'
        
    # write PARSED collection
    path = t.csv_reports / f'{query}_1-parsed={len(parsed)}.csv'
    parsed_header = [f'SAMPLE {t.now} {source_file} {search_mode=} '
                     f'{keywords=} {exclude=}']
    t.write_csv_report(path, parsed_header, parsed)
    
    # write CLONES collection
    path = t.csv_reports / f'{query}_2-clones={sum(clones.values())}.csv'
    t.write_csv_report(path, ['CLONE', 'COUNT'], clones)

    # write pairs/clusters of duplicates report
    path = t.csv_reports / f'{query}_3-duplic={len(pairs)}.csv'
    t.write_csv_report(path, ['ITEM1', 'ITEM2', 'RATIO'], pairs)
    
    # write source file for the next parsing iteration
    path = t.csv_sources / f'{n+1}_fertoing_source.csv'
    t.write_csv_report(path, header=None, collection=next_source)
    
    # write keywords for the next parsing iteration
    path = t.csv_sources / f'{n+1}_fertoing_keywords.csv'
    t.write_csv_report(path, ['KEYWORD', 'COUNT'], next_keywords)



if __name__ == '__main__':
    options = t.get_options(sys.argv[1:])
    deduplicate(options.source_file, options.search_mode, 
                options.keywords, options.exclude, options.threshold)
