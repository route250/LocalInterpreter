
import sys,os
import math
import re
import json
from urllib import request
import mimetypes

from urllib.parse import urlparse, parse_qs, unquote
from bs4 import BeautifulSoup, Tag, Comment
from googleapiclient.discovery import build, Resource, HttpError

from LocalInterpreter.utils.openai_util import count_token, summarize

ENV_GCP_API_KEY='GCP_API_KEY'
ENV_GCP_CSE_ID='GCP_CSE_ID'

# MIMEタイプと拡張子の対応表
mimetypes.init()
mimetypes.add_type('text/html', '.html')
mimetypes.add_type('text/plain', '.txt')
mimetypes.add_type('application/pdf', '.pdf')
mimetypes.add_type('image/jpeg', '.jpg')
mimetypes.add_type('image/png', '.png')
mimetypes.add_type('image/gif', '.gif')
mimetypes.add_type('application/zip', '.zip')
mimetypes.add_type('application/octet-stream', '.bin')

def decode_and_parse_url(url):
    # Parse the URL
    parsed_url = urlparse(url)
    # Decode the query part
    decoded_query = unquote(parsed_url.query)
    # Parse the decoded query part into a dictionary
    query_params = parse_qs(decoded_query)
    # Convert query parameters to a simple dictionary (not lists of values)
    query_params_dict = {k: v[0] for k, v in query_params.items()}

    return query_params_dict

def google_search_json( keyword, *, lang:str='ja', num:int=5, debug=False ) ->list[dict]:

    # API KEY
    api_key = os.environ.get(ENV_GCP_API_KEY)
    cse_id = os.environ.get(ENV_GCP_CSE_ID)
    if not api_key or not cse_id:
        return [ { 'error': 'invalid api key or custom search engine id.'} ]

    # 結果件数指定
    if isinstance(num,(int,float)):
        num = min( max(1,int(num)), 10 )
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
    except HttpError as e:
        return [ { 'error': f'{e.reason}'} ]
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

def google_search( keyword, *,lang:str='ja', num:int=5, debug=False ) ->str:
    result_json:list[dict] = google_search_json( keyword, lang=lang, num=num, debug=debug)
    result_text = f"# Search keyword: {keyword}\n\n"
    result_text += "# Search result:\n\n"
    if isinstance(result_json,(list,tuple)):
        for i,item in enumerate(result_json):
            err:str = item.get('error')
            title:str = item.get('title','')
            link:str = item.get('link','')
            snippet:str = item.get('snippet','')
            if err:
                result_text += f"ERROR: {err}\n\n"
            if link:
                result_text += f"{i+1}. [{title}]({link})\n"
                result_text += f"  {snippet}\n\n"
    else:
        result_text += "  no results.\n"
    return result_text


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


def download_from_url(url, *, directory, file_name:str=None) -> tuple[str,str]:
    try:
        # フォルダが存在しない場合
        if not os.path.exists(directory):
            return None, f"\"{directory}\" is not directory."

        # HTTPヘッダー情報を取得するためにリクエストを送信
        with request.urlopen(url) as response:
            # ヘッダーからファイル名を取得
            content_filename = None
            content_type = response.info().get('Content-Type')
            content_disposition = response.info().get('Content-Disposition')
            if content_disposition:
                file_name_match = re.findall('filename="(.+)"', content_disposition)
                if file_name_match:
                    content_filename = file_name_match[0]
                    if not content_filename:
                        content_filename = None
            # Content-Typeから拡張子を推定
            content_ext = ''
            if content_type:
                ext = mimetypes.guess_extension(content_type.split(';')[0])
                if ext:
                    if ext.startswith('.'):
                        content_ext = ext
                    else:
                        content_ext = f".{content_ext}"
            # ファイル名を決める
            dst_filename = file_name
            if not dst_filename:
                dst_filename = content_filename
            if not dst_filename:
                dst_filename = os.path.basename(url)
            if not dst_filename:
                for num in range(1000):
                    dst_filename = f"data{num:03}{content_ext}"
                    if not os.path.exists( os.path.join(directory, dst_filename ) ):
                        break
            # 上書きフラグ
            dst_path = os.path.join(directory,dst_filename)
            dst_exists:bool = os.path.exists( dst_path )    

            # ファイルを保存
            with open(dst_path, 'wb') as stream:
                stream.write(response.read())

        if dst_exists:
            msg = f"The downloaded file has been overwritten and saved as \"{dst_filename}\"."
        else:
            msg = f"The downloaded file is newly saved as \"{dst_filename}\"."

        if content_type:
            msg = f"{msg} content-type is {content_type}."
        if content_disposition:
            msg = f"{msg} content-disposition is {content_disposition}."

        return dst_filename, msg

    except Exception as ex:
        return None, f"ERROR: {ex}"

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

def text_to_chunks( text:str, chunk_size:int=2000, overlap:int=100 ) ->list[str]:
    text_size:int = len(text)
    if text_size<chunk_size:
        return [text]
    
    # チャンク数を計算
    # 最初のチャンクで S 要素を消費し、それ以降は S - O 要素ごとに新たなチャンクが必要
    num_chunks:int = 1 + math.ceil((text_size - chunk_size) / (chunk_size - overlap))
    # 最後のチャンクのサイズを計算
    last_start = (num_chunks - 1) * (chunk_size - overlap)
    last_chunk_size = text_size - last_start
    remainder = ( chunk_size - last_chunk_size ) // 2
    if remainder > num_chunks-1:
        off = math.ceil(remainder/(num_chunks-1))
    else:
        remainder = 0
        off = 0

    # print( f" chunks:{num_chunks} last_start:{last_start} size:{last_chunk_size}")
    chunks = []
    start = 0
    while start < len(text):
        step = chunk_size
        if remainder>0:
            step -= min( remainder, off )
            remainder -= min( remainder, off )
        end = min(start + step, len(text))
        chunks.append(text[start:end])
        if end==len(text):
            break
        start = end - overlap
    return chunks

def simple_text_to_chunks( text, chunk_size=2000, overlap=100 ):
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end==len(text):
            break
        start = end - overlap
    return chunks

def get_summary_from_text( text,length:int=1024, *, context_size:int=14000, overlap:int=500, debug=False):

    if not text or not isinstance(text,str):
        return text

    if not os.environ.get('OPENAI_API_KEY'):
        return text[:length]

    summary_text =  text

    n:int = 0 # 少なくとも一回は要約処理する
    while n==0 or len(summary_text)>length:
        n+=1
        input_list:list[str] = text_to_chunks( summary_text, context_size, overlap )
        if length<=context_size:
            target_length:int = int(context_size/len(input_list)) if len(input_list)>1 else length
        else:
            target_length:int = int(context_size/len(input_list))
        output_list:list[str] = []
        update:bool = False
        for text in input_list:
            if len(text)>target_length:
                summary = summarize( text, length=target_length, debug=debug )
                output_list.append( summary )
                update = True
            else:
                output_list.append( text )
        input_size = sum( len(chunk) for chunk in input_list )
        output_size = sum( len(chunk) for chunk in output_list )
        if update and output_size>=input_size:
            break
        summary_text = '\n'.join(output_list)

    return summary_text[:length]

def get_summary_from_url(url, length:int=1024, *, debug=False):
    text:str = get_text_from_url( url, debug=debug )
    return get_summary_from_text( text, debug=debug)
