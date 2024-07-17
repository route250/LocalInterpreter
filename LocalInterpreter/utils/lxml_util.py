
from typing import Iterator
from io import StringIO, BytesIO
import re
import lxml
from lxml import etree
from lxml.etree import _ElementTree as ETree, _Element as Elem

import logging
logger = logging.getLogger('LxmlUtil')

def esc( text:str ) ->str:
    if text is None:
        return "{None}"
    text = text.replace("\n","\\n").replace("\r","\\r").replace("\t","\\t")
    return text

def s( text:str|None ) ->str:
    return text if isinstance(text,str) else ''

def trimS( text:str|None ) ->str:
    if isinstance(text,str):
        text = re.sub(r'[\s\r\n]+',' ',text)
        if text.strip()=='':
            return ' '
        else:
            return text
    return ''

def strip( text:str|None ) ->str:
    if isinstance(text,str):
        return text.strip()
    return ''

def stripE( text:str|None ) ->str:
    if is_empty(text):
        return ''

def eq( a:str|None,b:str|None) ->bool:
    if not isinstance(a,str):
        a=''
    if not isinstance(b,str):
        b=''
    return a==b

def is_empty( text:str ) ->bool:
    if isinstance(text,str) and len(text.strip())>0:
        return False
    return True

def is_blank_or_space( text:str|None ) ->bool:
    if isinstance(text,str):
        return 0==(len(text.strip()))
    return True

def join( a:str|None, b:str|None ) -> str:
    if is_empty(a):
        if is_empty(b):
            return ''
        return b
    else:
        if is_empty(b):
            return a
        return a+b

def str_merge( a:str|None, b:str|None ) ->str:
    if isinstance(a,str) and len(a)>0:
        if not isinstance(b,str):
            return a
        if is_empty(b) and len(b)>0 and a.endswith(b):
            return a
        if len(b)>0:
            return a+b
        else:
            return a
    else:
        if isinstance(b,str):
            return b
    return ''        

def get_text( elem:Elem ) -> str:
    text = trimS( elem.text )
    for child in elem:
        text = join(text, get_text(child) )
        text = join(text, trimS(child.tail) )
    return text

def get_elem( elem:Elem, name:str|list|tuple ) -> Elem:
    if isinstance(name,str):
        for child in elem:
            if child.tag == name:
                return child
    elif isinstance(name,list|tuple):
        for child in elem:
            if child.tag in name:
                return child

def get_elem_list( elem:Elem, name:str ) ->Iterator[Elem]:
    for child in elem:
        if child.tag == name:
            yield child

def xs( text:str|None ) ->str:
    if isinstance(text,str) and len(text)>0:
        return text
    return None

def xs_len( text:str|None ) ->str:
    if isinstance(text,str):
        return len(text)
    return 0

def xs_is_empty( text:str|None ) ->bool:
    if isinstance(text,str) and len(text)>0:
        return False
    return True

def xs_is_space( text:str|None ) ->bool:
    if isinstance(text,str) and len(text.strip())>0:
        return False
    return True

def xs_strip(text:str|None ) ->str:
    if isinstance(text,str) and len(text)>0:
        text = text.strip()
        if len(text)>0:
            return text
    return None

re_space_replace1:re.Pattern = re.compile(r'[ \t] +')
re_space_replace2:re.Pattern = re.compile(r'\n[ \t]*')
re_space_replace3:re.Pattern = re.compile(r'\n+')
re_space_replace4:re.Pattern = re.compile(r'^[\s]*')
re_space_replace:re.Pattern = re.compile(r'\s+')

def xs_trimA( text:str|None ) ->str:
    if isinstance(text,str):
        # atext = re_space_replace1.sub(' ',text)
        # atext = re_space_replace2.sub('\n',atext)
        # atext = re_space_replace3.sub('\n',atext)
        # atext = re_space_replace3.sub('',atext)
        atext = re_space_replace1.sub(' ',text).strip()
        if atext:
            return atext
    return None


def xs_join( a:str|None, b:str|None ) -> str:
    if xs_is_empty(a):
        return b if not xs_is_empty(b) else None
    elif xs_is_empty(b):
        return a
    return a+b

"""
タグを削除するパターン
1.
<h1>{h1.text:
  }<strong>{strong.text:
     あいうえお
  }</strong>{strong.tail:
}</h1>

h1.text = h1.text + trim(strong.text) + strong.tail

<h1></h1>

2.
<h1>{h1.text:
  }<strong>{strong.text:
     あいうえお
  }</strong>{strong.tail:
  }<b>{b.text:
     かきくけこ
  }</b>{b.tail:
}</h1>

h1.text = h1.text + trim(strong.text) + strong.tail

<h1>
  <b>
    かきくけこ
  </b>
</h1>

3.
<h1>{h1.text:
  }<strong>{strong.text:
     あいうえお
  }</strong>{strong.tail:
  }<b>{b.text:
     かきくけこ
  }</b>{b.tail:
}</h1>

strong.tail = strong.tail + trim(b.text) + b.tail

<h1>
  <strong>
    あいうえお
  </strong>
</h1>

"""
def remove_tag(elem:Elem):
    parent:Elem = elem.getparent()
    prev:Elem|None = elem.getprevious()
    if prev is None:
        if not xs_is_space(elem.tail):
            parent.text = xs_join( parent.text, elem.tail )
    else:
        if not xs_is_space(elem.tail):
            prev.tail = xs_join( prev.tail, elem.tail )
    parent.remove(elem)

"""
タグを削除するパターン
1.
<h1>{h1.text:
  }<strong>{strong.text:
     あいうえお
  }</strong>{strong.tail:
}</h1>

h1.text = h1.text + trim(strong.text) + strong.tail

<h1>
  あいうえお
</h1>

2.
<h1>{h1.text:
  }<strong>{strong.text:
     あいうえお
  }</strong>{strong.tail:
  }<b>{b.text:
     かきくけこ
  }</b>{b.tail:
}</h1>

h1.text = h1.text + trim(strong.text) + strong.tail

<h1>
  あいうえお
  <b>
    かきくけこ
  </b>
</h1>

3.
<h1>{h1.text:
  }<strong>{strong.text:
     あいうえお
  }</strong>{strong.tail:
  }<b>{b.text:
     かきくけこ
  }</b>{b.tail:
}</h1>

strong.tail = strong.tail + trim(b.text) + b.tail

<h1>
  <strong>
    あいうえお
  </strong>
  かきくけこ
</h1>

"""

def pop_tag(elem:Elem):
    parent:Elem = elem.getparent()
    prev:Elem|None = elem.getprevious()
    children:list[Elem] = list(elem)
    if len(children)==0:
        if prev is None:
            parent.text = xs_join( parent.text, xs_join( xs_strip(elem.text), elem.tail ) )
        else:
            prev.tail = xs_join( prev.tail, xs_join( xs_strip(elem.text), elem.tail ) )
        parent.remove(elem)
        return
    
    index:int = parent.index(elem)
    parent.remove(elem)
    # elem.textをひとつ前の要素の押し付ける
    if prev is None:
        if xs_is_space(parent.text):
            parent.text = xs( elem.text )
        elif not xs_is_space(elem.text):
            parent.text = xs_join(parent.text, xs_strip(elem.text) )
    else:
        if xs_is_space(prev.tail):
            prev.tail = xs( elem.text )
        elif not xs_is_space(elem.text):
            prev.tail = xs_join(prev.tail, xs_strip(elem.text) )
    # elem.tailを最後の子要素に押し付ける
    last:Elem = children[-1]
    if xs_is_space(last.tail):
        last.tail = xs( elem.tail )
    elif not xs_is_space(elem.tail):
        last.tail = xs_join( last.tail, elem.tail )
    # 子要素を追加
    for i, child in enumerate(children):
        parent.insert(index+i,child)

# re_symbol_replace:re.Pattern = re.compile(r'[^\w\s\u3040-\u30FF\u4E00-\u9FFF]')

# def remove_symbols(text:str|None) ->str:
#     if isinstance(text,str):
#         # 記号を削除する正規表現（日本語文字を保持）
#         # \u3000-\u303F：全角の記号や句読点。
#         # \u3040-\u30FF：ひらがなとカタカナ。
#         # \u4E00-\u9FFF：漢字。
#         return re_symbol_replace.sub( '', text).strip()
#         #return re.sub(r'[^\w\s\u3040-\u30FF\u4E00-\u9FFF]', '', text).strip()
#     else:
#         return ''

# re_symbol_check:re.Pattern = re.compile( r'[\w\u3040-\u30FF\u4E00-\u9FFF]' )

# def has_texts(text:str|None) ->bool:
#     if isinstance(text,str):
#         m = re_symbol_check.search( text )
#         return m is not None
#     return False

def has_texts(text: str | None) -> bool:
    if isinstance(text, str):
        for cc in text:
            code = ord(cc)
            if 0x30<=code and code<=0x39:
                return True
            if 0x41<=code and code<=0x5a:
                return True
            if 0x61<=code and code<=0x7a:
                return True
            if 0xff < code:
                return True
    return False

def is_available(elem:Elem) ->bool:
    if has_texts( elem.text ):
        return True
    for child in elem:
        if is_available(child):
            return True
        if has_texts(child.tail):
            return True
    return False
md_h_map = {
    'h1':"\n\n# ",
    'h2':"\n\n## ",
    'h3':"\n\n### ",
    'h4':"\n\n#### ",
}
md_pre_map = {
    'footer': "\n---\n",
    'title': "\n",
    'div': "\n",
    'h1': "\n# ",
    'h2': "\n## ",
    'h3': "\n### ",
    'h4': "\n#### ",
    'table': "\n<table>\n",
    "tr": "\n<tr>\n",
    'td': "<td>",
    'th': "<th>",
}
md_post_map = {
    'br': "\n",
    'head': "\n---\n",
    'title': "\n",
    'div': "\n",
    'p': "\n",
    'li': "\n",
    'h1': "\n",
    'h2': "\n",
    'h3': "\n",
    'h4': "\n",
    'table': "\n</table>\n",
    'tr': "\n</tr>\n",
    "td": "</td>",
    "th": "</th>"
}
def to_text(elem:Elem):
    if elem is None:
        return ''
    try:
        # if elem.tag in md_h_map:
        #     text = child_to_text("",elem)
        #     return md_h_map[elem.tag]+trimA(text)+"\n"

        pre:str = md_pre_map.get(elem.tag)
        if elem.tag=='th' or elem.tag=='td':
            pre="<"+elem.tag
            cs = elem.get('colspan')
            if cs:
                pre += f" colspan=\"{cs}\""
            rs = elem.get('rowspan')
            if rs:
                pre += f" colspan=\"{rs}\""
            pre+=">"
        text = xs_strip( child_to_text("",elem) )
        if elem.tag == 'a':
            href:str = elem.get('href')
            if href and ( href.startswith('https://') or href.startswith('http://')):
                text = f"[{text}]({href})"
        post:str = md_post_map.get(elem.tag)
        atext = xs_join(pre,text)
        atext = xs_join(atext,post)
        return atext
    except Exception as ex:
        raise ex

def child_to_text( text:str, elem:Elem ) ->str:
    text = xs_join(text,xs_trimA(elem.text))
    for child in elem:
        text = xs_join(text,to_text(child))
        text = xs_join(text, xs_trimA(child.tail) )
    return text

def xs_count( elem:Elem, limit:int, n:int=0 ) ->int:
    n += xs_len( xs_trimA(elem.text) )
    if n<limit:
        for child in elem:
            n += xs_count( child, limit, n )
            if n>limit:
                return n
            n += xs_len( xs_trimA(child.tail) )
            if n>limit:
                return n
    return n

def count( elem:Elem, limit:int ) ->bool:
    if xs_count( elem, limit, 0 )>limit:
        return True
    return False
