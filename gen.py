#!/usr/local/bin/python
# -*- coding: utf-8 -*-
# file: gen.py

import re
import pandas as pd
import tanakh as tn
from abnum.abnum import Abnum, hebrew
from abnum.abnum.remarkuple import table, helper as h

KtavIvri_Mapping = (
    [1, 'alef'], [2, 'beth'], [3, 'gimel'], 
    [3, 'shin'], [4, 'daleth'], [4, 'tau'],
    [5, 'he'], [6, 'vau'], [7, 'zayin'], 
    [8, 'heth'], [9, 'teth'], [10, 'yod'], 
    [20, 'kaph'], [30, 'lamed'], [40, 'mem'], 
    [50, 'nun'], [60, 'samekh'], [70, 'ayin'], 
    [80, 'pe'], [90, 'tsade'], [100, 'qoph'], 
    [200, 'resh'], [20, 'final_kaph'], [40, 'final_mem'], 
    [50, 'final_nun'], [80, 'final_pe'], [90, 'final_tsade']
)

g = Abnum(hebrew, KtavIvri_Mapping)

manuscript = 'hebrew_modern'

x = tn.get_variations([manuscript], {'orig_book_index': 'Genesis'})

gen = x[manuscript]['data']

# Index every character from the source text.
# This is done to make it possible to retrieve correct position of the search items.
chars = []

for i, row in gen.iterrows():
    w = 1
    for word in row.text.split():
        c = 1
        for char in word:
            chars.append({'character': char, 
                          'character_index': c, 
                          'word': word, 
                          'word_index': w, 
                          'verse_index': row.orig_verse, 
                          'chapter_index': row.orig_chapter})
            c += 1
        w += 1

chars = pd.DataFrame(chars)

def search(v, text):
    global chars
    # genesis text as a continuous character stream without any spaces...
    input_string = ''.join(text).replace(' ', '')
    # characters separated with empty space
    s = " ".join(input_string)
    hits = {}
    cols = ['chapter_index', 'verse_index', 'word_index', 'character_index', 'word']
    
    for x in set(g.find(s, v, True)):
        # remove empty spaces
        y = x.replace(' ', '')
        # find all indices from original input string
        indices = [m.start() for m in re.finditer(y, input_string)]
        for i in indices:
            h = chars[chars.index == i]
            hit = {'result': y}
            for d in cols:
                hit[d] = [_ for x, _ in h[d].items()][0]
            hit['start'] = "%s:%s:%s" % (hit['chapter_index'],
                                         hit['verse_index'],
                                         hit['word_index'])
            hit['end'] = ""
            if hit['word'] in y or y in hit['word']:
                # determine if hit ends with a complete word
                hit['ends_to_word'] = hit['word'] == y
                if len(hit['word']) < len(y) and y.index(hit['word']) == 0:
                    j = 0
                    word = hit['word']
                    y2 = y
                    while True:
                        j += len(word)
                        y2 = y2.replace(word, '', 1)
                        if y2:
                            h2 = chars[chars.index == i+j]
                            word = [_ for x, _ in h2['word'].items()][0]
                            hit['end'] = "%s:%s:%s" % ([_ for x, _ in h2['chapter_index'].items()][0],
                                                       [_ for x, _ in h2['verse_index'].items()][0],
                                                       [_ for x, _ in h2['word_index'].items()][0])
                            if word in y2:
                                hit['ends_to_word'] = True
                            else:
                                hit['ends_to_word'] = False
                                break
                        else:
                            break
                
                hit['span'] = "%s%s" % (hit['start'], "-%s" % hit['end'] if hit['end'] else '')
                hits[i] = hit

    return pd.DataFrame(hits).T

def f(x):
    return pd.Series(dict(count = len(x), 
                     span = "%s" % ', '.join(x['span'])))

def get(v, text = None, ends_to_word = True):
    global rev
    if text is None:
        text = gen.text
    res = search(v, text)
    if ends_to_word:
        res = res[res['ends_to_word'] == True]
    res.drop('character_index', axis=1, inplace=True)
    res.drop('ends_to_word', axis=1, inplace=True)
    res.drop('start', axis=1, inplace=True)
    res.drop('end', axis=1, inplace=True)
    res.drop('chapter_index', axis=1, inplace=True)
    res.drop('verse_index', axis=1, inplace=True)
    res = res.groupby('result').apply(f)
    res['gematria'] = v
    return res

def split_every_nth(n, s):
    return [ s[i:i+n] for i in range(0, len(s), n) ]

def colsplit(l, cols):
    rows = len(l) / cols
    if len(l) % cols:
        rows += 1
    m = []
    for i in range(int(rows)):
        m.append(l[i::int(rows)])
    return m

# q = pages (79)
# x = rows per page (43)
# m = chars per column (23)
# o = cols per page (3)
def book(q = 79, x = 43, m = 23, o = 3):
    global rev, chars

    n = x*m*o

    t = ''.join(gen.text).replace(' ', '')[:(n*q)]

    pages = split_every_nth(n, t)

    tbl = table(Class="gentable")

    p = n/m/o #=x?

    r = 0

    def cell(clr, n, r):
        c = chars[chars.index > n-m-1]
        c = c[c.index < n]
        a = []
        y = ""
        for _, w in c.T.iteritems():
            if w.character_index == 1 and y != "":
                r += 1
                a.append((y,g.value(y),clr,(chapter, verse, word),r))
                clr = 'black' if clr == 'darkred' else 'darkred'
                y = ""
            y += w.character
            chapter = w.chapter_index
            verse = w.verse_index
            word = w.word_index
        if y != "":
            r += 1
            a.append((y,g.value(y),clr,(chapter, verse, word),r))
        return clr, a, r

    clr = 'black'

    total = 0

    for i, page in enumerate(pages):
        
        lines = split_every_nth(m, page)
        l = int(len(lines)/o)
        
        l1, l2, l3 = [], [], []
        
        for j in range(l):
            nx = (n*i)+m*(j+1) if i else m*(j+1)
            clr, a, r = cell(clr, nx, r)
            l1.append(a)
        for j in range(l):
            nx = (n*i)+m*(j+1) if i else m*(j+1)
            clr, a, r = cell(clr, int(m*p+nx), r)
            l2.append(a)
        for j in range(l):
            nx = (n*i)+m*(j+1) if i else m*(j+1)
            clr, a, r = cell(clr, int((m*p)+(m*p)+nx), r)
            l3.append(a)
        
        s1, s2, s3 = 0, 0, 0
        old1, old2, old3 = None, None, None
        old11, old22, old33 = None, None, None
        page_total = 0
        trs = []
        
        for col1, col2, col3 in zip(*[l1, l2, l3]):
            td1, td2, td3 = h.td(), h.td(), h.td()
            v1, v2, v3 = 0, 0, 0
            for col in col1:
                td1 += h.span(col[0], order=col[4], 
                              index=':'.join(map(str, col[3])), value=col[1], 
                              roman=g.convert(col[0]), style="color:%s" % col[2], 
                              title="%s = %s" % (g.convert(col[0]), col[1]))
                v1 += col[1]
            if old1 != col[3][:2]:
                old11 = col[3][:2]
            else:
                old11 = ()
            old1 = col[3][:2]
            s1 += v1
            for col in col2:
                td2 += h.span(col[0], order=col[4],
                              index=':'.join(map(str, col[3])), value=col[1], 
                              roman=g.convert(col[0]), style="color:%s" % col[2], 
                              title = "%s = %s" % (g.convert(col[0]), col[1]))
                v2 += col[1]
            if old2 != col[3][:2]:
                old22 = col[3][:2]
            else:
                old22 = ()
            old2 = col[3][:2]
            s2 += v2
            for col in col3:
                td3 += h.span(col[0], order=col[4],
                              index=':'.join(map(str, col[3])), value=col[1], 
                              roman=g.convert(col[0]), style="color:%s" % col[2], 
                              title = "%s = %s" % (g.convert(col[0]), col[1]))
                v3 += col[1]
            if old3 != col[3][:2]:
                old33 = col[3][:2]
            else:
                old33 = ()
            old3 = col[3][:2]
            s3 += v3
            
            a = [td1, h.td(h.sup(':'.join(map(str, old11)))), 
                 td2, h.td(h.sup(':'.join(map(str, old22)))),
                 td3, h.td(h.sup(':'.join(map(str, old33))))]
            page_total += v1+v2+v3
            trs.append(h.tr(*a))
        
        total += page_total
        tbl.addBodyRow(h.tr(h.td(*[h.span('p.%s' % (i+1)), " ", h.div('Total: %s/%s' % (page_total, total), Class="totals")], colspan=8), Class="page-break"))
        tbl.addBodyRow(*trs)

    tbl.addCaption(h.span(
                          #'Selected: ', h.span(0, Id='selected'), " ", 
                          'Search: ', h.Input(Id="search", size="14", maxlength="10"), " ",
                          'Hits: ', h.span(Id="hits")))

    return tbl