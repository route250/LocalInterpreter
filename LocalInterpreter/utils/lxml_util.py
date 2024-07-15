
from typing import Iterator
from io import StringIO, BytesIO
import re
import lxml
from lxml import etree
from lxml.etree import _ElementTree as ETree, _Element as Elem

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

def is_empty( text:str ) ->bool:
    if isinstance(text,str) and len(text.strip())>0:
        return False
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

def remove_tag(elem:Elem):
    parent:Elem = elem.getparent()
    prev:Elem|None = elem.getprevious()
    if prev is None:
        parent.text = str_merge( parent.text, elem.tail )
    else:
        prev.tail = str_merge( prev.tail, elem.tail )
    parent.remove(elem)

def pop_tag(elem:Elem):
    parent:Elem = elem.getparent()
    index:int = parent.index(elem)
    children:list[Elem] = list(elem)
    parent.remove(elem)
    # テキスト
    if len(children)>0:
        first:Elem = children[0]
        first.text = str_merge( elem.text, first.text)
        last:Elem = children[-1]
        last.tail = str_merge( last.tail, elem.tail)
        for i, child in enumerate(children):
            parent.insert(index+i,child)
    else:
        parent.text = strip(parent.text) + strip(elem.text)
        parent.tail = strip(elem.tail) + strip(parent.tail)

def remove_symbols(text:str|None) ->str:
    if isinstance(text,str):
        # 記号を削除する正規表現（日本語文字を保持）
        # \u3000-\u303F：全角の記号や句読点。
        # \u3040-\u30FF：ひらがなとカタカナ。
        # \u4E00-\u9FFF：漢字。
        return re.sub(r'[^\w\s\u3040-\u30FF\u4E00-\u9FFF]', '', text).strip()
    else:
        return ''

def has_texts(text:str|None) ->bool:
    txt = remove_symbols(text)
    return txt is not None and len(txt)>0

def is_available(elem:Elem) ->bool:
    if has_texts( elem.text ):
        return True
    for child in elem:
        if is_available(child):
            return True
        if has_texts(child.tail):
            return True
    return False