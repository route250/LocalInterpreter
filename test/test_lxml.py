import sys,os
from io import StringIO, BytesIO
from lxml import etree
from lxml.etree import _ElementTree as ETree, _Element as Elem

sys.path.append(os.getcwd())
import LocalInterpreter.utils.lxml_util as Xu

def test_remove_comment():
    """コメントが削除されることを確認"""
    htmltxt:str = """<html lang="ja">
<!-- comment -->
<header>
    <!-- comment -->
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>test</title>
</header>
<body>
    <!-- comment -->
    <div>あいうえお</div>
</body>
</html>
"""
    buf = StringIO(htmltxt) #BytesIO(htmltxt.encode())
    parser = etree.HTMLParser( remove_comments=True, remove_blank_text=False, strip_cdata=True, no_network=True, recover=True, compact=True)
    tree:ETree = etree.parse(buf, parser)
    root:Elem = tree.getroot()

    result = etree.tostring(root, pretty_print=True, encoding='unicode')
    print(result)


def test_elem_tail():
    """textとtailを確認する"""
    htmltxt:str = """<html lang="ja">
<!-- comment -->
<header>
    <!-- comment -->
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>test</title>
</header>
<body>1
    2<div>a1
      a2<div>b</div>c1
      c2<div>d</div>e1
      e2<div>f</div>g1
    g2</div>h1
h2</body>
</html>
"""
    buf = StringIO(htmltxt) #BytesIO(htmltxt.encode())
    parser = etree.HTMLParser( remove_comments=True, remove_blank_text=False, strip_cdata=True, no_network=True, recover=True, compact=True)
    tree:ETree = etree.parse(buf, parser)
    root:Elem = tree.getroot()

    body:Elem = Xu.get_elem(root,'body')
    for d1 in Xu.get_elem_list(body,'div'):
        print(f"text:{Xu.esc(d1.text)} tail:{Xu.esc(d1.tail)}")
        for d2 in Xu.get_elem_list(d1,'div'):
            print(f"text:{Xu.esc(d2.text)} tail:{Xu.esc(d2.tail)}")

def test_text():
    case = [
        [ " a  b  c ", " a b c " ],
        [ "\n    ", "" ],
        [ "a    b", "a b" ],
    ]
    for a,b in case:
        c = Xu.trimS(a)
        print(f"input:\"{Xu.esc(a)}\" output:\"{Xu.esc(c)}\" act:\"{Xu.esc(b)}\"")

if __name__ == "__main__":
    test_text()
    test_elem_tail()