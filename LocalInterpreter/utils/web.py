
import sys,os
import re
import json
from urllib import request

from bs4 import BeautifulSoup, Tag, Comment
from googleapiclient.discovery import build

ENV_GCP_API_KEY='GCP_API_KEY'
ENV_GCP_CSE_ID='GCP_CSE_ID'

def google_search( keyword, *,lang:str='ja', num:int=10, debug=False ):

    # API KEY
    api_key = os.environ.get(ENV_GCP_API_KEY)
    cse_id = os.environ.get(ENV_GCP_CSE_ID)
    if not api_key or not cse_id:
        return [ { 'error': 'invalid api key or custom search engine id.'} ]

    # 結果件数指定
    if isinstance(num,(int,float)):
        num = min( max(1,int(num)), 20 )
    else:
        num = 10
    # 言語指定
    if isinstance(lang,str) and lang.strip().lower() in ['','ja','jp','japan']:
        lr = 'lang_ja'
    else:
        lr = 'lang_en'

    try:
        # Google Customサーチ結果を取得
        api = build('customsearch', 'v1', developerKey = api_key)
        result_raw = api.cse().list(q = keyword, cx=cse_id, lr = lr, num = num, start = 1).execute()
    except Exception as e:
        return [ { 'error': f'{e}'} ]

    if debug:
        try:
            with open('search_result.json','w') as stream:
                # レスポンスをjson形式で保存
                json.dump( result_raw, stream, ensure_ascii=False, indent=4 )
        except:
            pass

    result_json=[]
    for item in result_raw.get('items',[]):
        title:str = item.get('title','')
        link:str = item.get('link','')
        snippet:str = item.get('snippet','')
        result_json.append( {'title':title, 'link':link, 'snippet': snippet })

    return result_json

def remove_symbols(text):
    if isinstance(text,str):
        # 記号を削除する正規表現（日本語文字を保持）
        # \u3000-\u303F：全角の記号や句読点。
        # \u3040-\u30FF：ひらがなとカタカナ。
        # \u4E00-\u9FFF：漢字。
        return re.sub(r'[^\w\s\u3040-\u30FF\u4E00-\u9FFF]', '', text).strip()
    else:
        return ''

def strip_tag_text(tag:Tag):
    if not isinstance(tag,Tag) or tag.name=='a' or tag.name=='button':
        return ''
    child:Tag
    text = ''
    for child in tag.children:
        if child.name=='a' or child.name=='button':
            continue
        text += remove_symbols(child.text)
    return text

def get_text_from_url(url, *, as_raw=False, as_html=False, debug=False):
    try:
        response = request.urlopen(url)
        soup:BeautifulSoup = BeautifulSoup(response,"html.parser")
        response.close()

        if debug:
            with open('original.html','w') as stream:
                stream.write( soup.prettify())

        if not as_raw:
            # コメントタグの除去
            for comment in soup(text=lambda x: isinstance(x, Comment)):
                comment.extract()

            tag:Tag = None
            # script,styleタグを除去
            for tag in soup(["script", "style", "meta"]):
                tag.decompose()
            # articleタグ
            articles = soup( ['article','main'] )
            if articles:
                uniq = []
                for tag in articles:
                    parent:Tag = tag.parent
                    while parent and not parent in articles:
                        parent = parent.parent
                    if not parent:
                        uniq.append(tag)
                if uniq:
                    body = soup.body
                    # bodyの中身をクリア
                    body.clear()
                    # 全てのarticle要素をbodyに追加
                    for article in uniq:
                        parent = article.parent
                        body.append(article)
                        body.append(soup.new_string('\n'))
            # aタグを除去
            for tag in soup(["a","button"]):
                text = strip_tag_text(tag.parent)
                if not text:
                    tag.decompose()
            # 子タグがなく、かつテキストが空ならタグを削除
            for tag in soup.find_all():
                while tag is not None and strip_tag_text(tag)=='':
                    t = tag
                    tag = tag.parent
                    t.decompose()
            # 子divの内容を親divに移動
            for tag in soup.find_all("div"):
                while tag is not None and tag.parent is not None:
                    children = [ c for c in tag.children if c.name or c.text.strip() ]
                    if len(children) == 1 and children[0].name == "div":
                        child_div = children[0]
                        tag.replace_with(child_div)
                        tag = child_div.parent
                    else:
                        break
            if debug:
                with open('output.html','w') as stream:
                    stream.write( soup.prettify())

        if as_html:
            return soup.prettify()
        
        raw_text=soup.get_text()
        lines = [ line.strip() for line in raw_text.splitlines()]
        text = "\n".join( line for line in lines if line)
        if debug:
            with open('output.txt','w') as stream:
                stream.write( text )
        return text

    except:
        print(f"error {url}")
    return None
