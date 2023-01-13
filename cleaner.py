#coding:windows-1251

import re
from functools import partial
from string import punctuation

from nltk.corpus import stopwords


stopwords_rus = stopwords.words('russian')

stopwords_custom = [
    'арт', 'артик', 'артикул', 'раз', 'разм', 'размер', 'цвет', 'гост', 'станд',
    'стандарт', 'группа', 'тип', 'типоразмер', 'класс', 'род', 'вид', 'кат',
    'категория', 'сер', 'серия', 'ном', 'номер', 'марка', 'сбор', 'сборка',
    'набор', 'комплект', 'упак', 'упаковка', 'пара', 'кор', 'бокс', 'бухта',
    'мама', 'папа', 'мини', 'плюс', 'минус', 'люкс', 'диам', 'диаметр', 'длина',
    'толщ', 'толщина', 'объем', 'объём', 'обьем', 'обьём', 'емкость', 'ёмкость', 
    'мкм', 'мкф', 'мгц', 'гбит', 'бар', 'атм', 'мин', 'сек', 'тыс', 'дог'
]

stopwords = set(stopwords_rus + stopwords_custom)

retired = '_НЕ_ИСПОЛЬЗУЕТСЯ'
retired = [retired[:stop] for stop in range(len(retired), 1, -1)] + ['_ДУБЛЬ']
retired = dict.fromkeys(retired, '')
retired = dict((re.escape(key), val) for key, val in retired.items())
pat_ret = re.compile('|'.join(retired.keys()))

punc = dict.fromkeys(list(punctuation) + ['№'] + ['«'] + ['»'] + ['–'], ' ')
punc['ё'] = 'е'
punc = dict((re.escape(key), val) for key, val in punc.items())
pat_punc = re.compile('|'.join(punc.keys()))


def remove_chars(string: str, pattern: re.Pattern, repl: dict[str, str]):
    """Abstract func for multiple replacements in a string in a single run. """
    return pattern.sub(lambda m: repl[re.escape(m.group(0))], string)


remove_retired_mark = partial(remove_chars, pattern=pat_ret, repl=retired)
remove_punctuation = partial(remove_chars, pattern=pat_punc, repl=punc)
