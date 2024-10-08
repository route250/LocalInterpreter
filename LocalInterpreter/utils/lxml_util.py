
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

def eq( a:str|None,b:str|None) ->bool:
    if not isinstance(a,str):
        a=''
    if not isinstance(b,str):
        b=''
    return a==b

def is_empty( text:str|None ) ->bool:
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

def xs( text:str|None ) ->str|None:
    if isinstance(text,str) and len(text)>0:
        return text
    return None

def xs_len( text:str|None ) ->int:
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

def xs_strip(text:str|None ) ->str|None:
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

def xs_trimA( text:str|None ) ->str|None:
    if isinstance(text,str):
        # atext = re_space_replace1.sub(' ',text)
        # atext = re_space_replace2.sub('\n',atext)
        # atext = re_space_replace3.sub('\n',atext)
        # atext = re_space_replace3.sub('',atext)
        atext = re_space_replace1.sub(' ',text).strip()
        if atext:
            return atext
    return None


def xs_join( a:str|None, b:str|None ) -> str|None:
    if xs_is_empty(a):
        return b if not xs_is_empty(b) else None
    elif xs_is_empty(b):
        return a
    return f"{a}{b}"

def md_join( a:str|None, b:str|None ) -> str|None:
    """markdownを意識したjoin"""
    if xs_is_empty(a):
        return b if not xs_is_empty(b) else None
    elif xs_is_empty(b):
        return a
    if b and len(b)>0 and b[0] in "#|`":
        b = f"\n{b}"
    return f"{a}{b}"
    
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


class HtmlTableCell:

    def __init__(self,text, th=False, cols=None, rows=None):

        self.th = th
        self.text = text
        self.cols = cols
        self.rows = rows
    def __str__(self):
        return f"\"{self.text}\""

def cell_to_text(cell: HtmlTableCell):
    if cell is None or cell.text is None:
        return ""
    text = cell.text.replace("\n","</br>")
    return text

def line_to_text(line: list[HtmlTableCell], width: int=0):
    # Convert each cell to text and fill missing cells with empty strings
    cells = [cell_to_text(cell) for cell in line] + [""] * (width - len(line))
    markdown = "|" + "|".join(cells) + "|"
    return markdown

def parseInt(value,default:int=1) ->int:
    try:
        return int(value)
    except:
        return default

class HtmlTableData:

    def __init__(self):
        self._current_row=-1
        self._current_col=0
        self._tbl:list[list[HtmlTableCell]] = []

    def get(self, col, row ):
        if 0<=row and 0<col:
            if row<len(self._tbl):
                line = self._tbl[row]
                if line and col<len(line):
                    return line[col]
        return None

    def tr(self):
        self._current_row += 1
        self._current_col = 0

    def add(self, text, th=False, cols=1, rows=1):
        cols = cols if isinstance(cols,int) and cols>1 else 1
        rows = rows if isinstance(rows,int) and rows>1 else 1

        cell = HtmlTableCell(text, th=th, cols=cols, rows=rows)

        # rowを作る
        if self._current_row<0:
            self._current_row = 0
        rs = self._current_row
        re = rs + rows - 1
        while len(self._tbl) <= re:
            self._tbl.append([])
        # 追加するカラム位置を決める
        cs = self._current_col
        while cs<len(self._tbl[rs]) and self._tbl[rs][cs] is not None:
            cs+=1
        ce = cs + cols - 1
        # セルを埋める
        for r in range(rs, re + 1):
            while len(self._tbl[r]) <= ce:
                self._tbl[r].append(None)
            for c in range(cs, ce + 1):
                self._tbl[r][c] = cell
        self._current_col = ce + 1

    def parse(self, elem:Elem ):
        if elem is None or elem.tag!='table':
            return ""
        for child in elem:
            self.parse_tr(child)

    def parse_tr(self, elem:Elem ):
        if elem is None or elem.tag!='tr':
            return
        self.tr()
        for child in elem:
            self.parse_td(child)

    def parse_td(self, elem:Elem):
        if elem is not None:
            th = False
            if elem.tag == 'th':
                th=True
            elif elem.tag != 'td':
                return
            cols = parseInt(elem.attrib.get('colspan'),1)
            rows = parseInt(elem.attrib.get('rowspan'),1)
            text = to_text(elem)
            self.add( text, th=th, cols=cols, rows=rows )

    def is_separated_pos( self, r:int ) ->bool:
        """行位置rが、rowspanを考慮して全部切れているか？"""
        if r<=0 or len(self._tbl)<=r:
            return True # 先頭と最後なら切れてる
        before_line = self._tbl[r-1]
        after_line = self._tbl[r]
        max_cols = max( len(before_line), len(after_line) )
        for c in range(max_cols):
            before_cell = before_line[c] if c<len(before_line) else None
            after_cell = after_line[c] if c<len(after_line) else None
            if before_cell is not None and after_cell is not None and before_cell is after_cell:
                return False # 切れてない
        return True # 切れてる
    
        
    def row_merge(self, row:int ) ->int:
        """rowspanが横一行全部同じなら結合する処理。結合する場合は、セルの値を<br/>で区切る"""
        line:list[HtmlTableCell] = self._tbl[row]
        head_rows:int = line[0].rows if len(line)>0 else 1
        if head_rows<=1:
            return row+head_rows# 2列以下 1列目がrowspan=1なら何もしない
        if not self.is_separated_pos(row) or not self.is_separated_pos(row+head_rows ):
            return row+head_rows # 1列目の前後で分離できないから何もしない
        # 結合する対象Lineだけ抜き出す
        grp:list[list[HtmlTableCell]] = self._tbl[row:row+head_rows]
        # 最大列幅を調べる
        max_cols:int = max( len(line) for line in grp )
        # 改行を含んでないか確認する
        for line in grp:
            for cell in line[1:]:
                if cell is not None and "\n" in cell.text:
                    return row+head_rows # セル内で改行があるので何もしない
        # 行マージ可能
        new_line = [ grp[0][0] ]
        for c in range(1,max_cols):
            before_cell:HtmlTableCell|None = None
            text2:list[str] = []
            for line in grp:
                cell:HtmlTableCell|None = line[c] if c<len(line) else None
                if cell and cell is before_cell:
                    cell = None # 前の行と同じセルならブランクとする
                text2.append( cell.text if cell and cell.text else "" )
                before_cell = cell
            cell = HtmlTableCell( "\n".join(text2) )
            new_line.append( cell )
        self._tbl[row] = new_line
        for r in range(row+1, row+head_rows):
            del self._tbl[row+1]
        return row+1

    def to_markdown(self):
        if len(self._tbl)==0:
            return ""

        # マージできる行はマージする
        r = 0
        while r<len(self._tbl):
            r = self.row_merge(r)

        # 列幅
        max_cols = max( len(line) for line in self._tbl )
        # ヘッダ
        header = self._tbl[0]
        r = 1 if all(cell is not None and cell.th for cell in header) else 0
        if r == 0:
            header = []

        markdown = ""
        # write header
        markdown = line_to_text( header, max_cols )
        # Add the markdown header separator
        markdown += "\n" + "|" + "|".join(["---"] * max_cols) + "|"
        # data
        for r in range(r,len(self._tbl)):
            markdown += "\n" + line_to_text( self._tbl[r] )

        return "\n\n" + markdown + "\n\n"

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
}
def to_text(elem:Elem|None) ->str:
    if elem is None:
        return ''
    if elem.tag == 'table':
        tbl:HtmlTableData = HtmlTableData()
        tbl.parse(elem)
        return tbl.to_markdown()
    try:
        # if elem.tag in md_h_map:
        #     text = child_to_text("",elem)
        #     return md_h_map[elem.tag]+trimA(text)+"\n"

        pre:str|None = md_pre_map.get(elem.tag)
        text = xs_strip( child_to_text("",elem) )
        if elem.tag == 'a':
            href:str|None = elem.get('href',None)
            if href and ( href.startswith('https://') or href.startswith('http://')):
                text = f"[{text}]({href.replace(' ','%20')})"
        post:str|None = md_post_map.get(elem.tag)
        atext = xs_join(pre,text)
        atext = xs_join(atext,post)
        return atext
    except Exception as ex:
        raise ex

def child_to_text( text:str, elem:Elem ) ->str:
    text = xs_join(text,xs_trimA(elem.text))
    for child in elem:
        text = md_join(text,to_text(child))
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
