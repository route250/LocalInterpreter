
import sys,os,traceback
import math
import re
import time
import json
import itertools
from urllib import request
from urllib.error import URLError, HTTPError
import mimetypes
import asyncio
import ssl
import httpx
from httpx import Response

from io import BytesIO

from urllib.parse import urlparse, parse_qs, unquote
from lxml import etree
from lxml.etree import _ElementTree as ETree, _Element as Elem

from googleapiclient.discovery import build, Resource, HttpError
from duckduckgo_search import DDGS

from LocalInterpreter.utils.openai_util import count_token, summarize_web_content, summarize_text
import LocalInterpreter.utils.lxml_util as Xu

import logging
logger = logging.getLogger('WebUtil')

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

async def a_fetch_html(url:str) ->bytes:
    logger.info(f"a_fetch_html URL={url}")
    if not url or not url.startswith('http'):
        return b'','url is invalid.'
    try:
        to = 3.0

        async with httpx.AsyncClient( timeout=to, follow_redirects=True, max_redirects=2 ) as client:
            response:Response = await client.get(url)
            if response.status_code != 200:
                return b'',f'http response code is {response.status_code}.'
            # BytesIOバッファを作成
            byte_buffer = BytesIO()

            # ストリームの内容をバイト列として読み込み、BytesIOに書き込む
            async for chunk in response.aiter_bytes():
                byte_buffer.write(chunk)

            # バッファの先頭にシーク
            byte_buffer.seek(0)
            return byte_buffer.getvalue(),None
    except httpx.ConnectTimeout as ex:
        return b'',f'{ex}'
    except httpx.ReadTimeout as ex:
        return b'',f'{ex}'
    except ssl.SSLCertVerificationError as ex:
        logger.error(f"{ex.__class__.__name__} URL:{url}")
        return b'',f"{ex.__class__.__name__} URL:{url}"
    except Exception as ex:
        logger.exception(f"can not get from {url}")
        raise ex

def duckduckgo_search( keyword, *, messages:list[dict]=None, lang:str='ja', num:int=5, debug=False ) ->str:
    result_json:list[dict] = duckduckgo_search_json( keyword, messages=messages, lang=lang, num=num, debug=debug)
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

def duckduckgo_search_json( keyword:str, *, messages:list[dict]=None, lang:str='ja', num:int=5, debug=False ) ->list[dict]:
    # 非同期コンテキスト外の場合
    return asyncio.run( a_duckduckgo_search_json( keyword, messages=messages, lang=lang, num=num, debug=debug ) )
    # try:
    #     # 現在のイベントループを取得
    #     loop = asyncio.get_running_loop()
    # except RuntimeError:
    #     # 非同期コンテキスト外の場合
    #     return asyncio.run( a_search_and_scan( keyword, lang=lang, num=num, debug=debug ) )
    # except Exception as ex:
    #     raise ex
    # # 非同期関数の場合
    # return loop.run_until_complete( a_duckduckgo_search( keyword, lang=lang, num=num, debug=debug ) )

async def a_duckduckgo_search_json( keyword:str, *, messages:list[dict]=None, lang:str='ja', num:int=5, debug=False ) ->list[dict]:

    search_results:list[dict] = await _a_duckduckgo_search_api( keyword, lang=lang, num=num, debug=debug )
    if not isinstance(search_results,list) or len(search_results)==0:
        return []

    # キーワード分解
    words = []
    for w in keyword.split():
        if w.startswith('-') or w.startswith('after:') or w.startswith('before:'):
            continue
        if w == '(' or w == ')' or w=='AND' or w=='OR':
            continue
        words.append(w)
    # 会話履歴
    prompt = None
    if isinstance(messages,list):
        n=0
        prompt=""
        target=""
        for i in range(len(messages)-1,-1,-1):
            m = messages[i]
            role = m.get('role')
            content = m.get('content')
            if (role!='user' and role!='assistant') or not content:
                continue
            prompt=f"{role}: {content}\n{prompt}"
            n+=1
            if n>=4:
                break
        if n>0:
            prompt = f"# 会話履歴\n{prompt}\n"
            target="と会話履歴"

        # 短く要約する
        prompt = f"{prompt}# web検索キーワード\n{' '.join(keyword)}\n\n# 検索結果のURLから取得したテキスト\n```\n{{}}\n```\n\n# 要約処理\n\n検索キーワード{target}に対応する情報を200文字以内で要約して出力して下さい.\n\n# 出力:"


    # tasks = [ a_search_check( x, words ) for x in search_results ]

    # check_results = await asyncio.gather( *tasks )
    # results = [ r for r in check_results if r ]

    results=[]
    for item in search_results:
        res = await _a_th_duckduckgo_search( item, words, prompt_fmt=prompt, lang=lang, num=num, debug=debug )
        if res:
            results.append(res)
            if len(results)>=num:
                break

    return results

async def _a_th_duckduckgo_search( item:dict, keyword:list[str], *, prompt_fmt:str|None=None, lang:str='ja', num:int=5, debug=False ):
    # 検索結果からURL
    link = item.get('link')
    logger.debug(f"_a_th_duckduckgo_search URL={link}")
    if not link:
        return None
    # htmlを取得して本文を取り出す
    t1 = time.time()
    html_bytes,err = await a_fetch_html(link)
    if err:
        item['err'] = err
        return item
    # キーワードが含まれるか？
    # html_text = html_bytes.decode()
    # Hit = False
    # for w in keyword:
    #     if w in html_text:
    #         Hit=True
    # if not Hit:
    #     return item
    # htmlからテキスト抽出
    text = get_text_from_html( html_bytes, keywords=keyword )
    t2 = time.time()
    logger.info( f"{link} get {t2-t1}(sec)")
    if not isinstance(text,str) or len(text.strip())==0:
        return None

    if prompt_fmt is None:
        # 要約しないそのまま返信
        return item

    # 要約する

    # 原文を切り出し
    start_pos = 999999
    for w in keyword:
        p = text.find(w)
        if 0<=p and p<start_pos:
            start_pos = p
    while start_pos>0 and text[start_pos] in '.,。':
        start_pos -= 1
    text = text[start_pos:start_pos+2000]

    # 短く要約する
    prompt = prompt_fmt.format(text)
    digest = summarize_text( text, prompt=prompt )
    t3 = time.time()
    logger.info( f"{link} summarize {t3-t2}(sec)")
    # snippetを更新する
    if digest:
        item['snippet'] = digest
    return item

def convert_keyword( keyword ):
    www = []
    if isinstance(keyword,str):
        www = [ w.strip() for w in keyword.split(' ') if w.strip() ]
    elif isinstance(keyword,list):
        www = [ w.strip() for w in keyword if isinstance(w,str) ]
    words = []
    groups = [words]
    after = None
    before = None
    for w in www:
        if w.startswith('before:'):
            before = w[len('before:'):]
        elif w.startswith('after:'):
            after = w[len('after:'):]
        elif w == "(" or w ==")" or w.upper=="AND":
            continue
        elif w.upper()=="OR":
            words = []
            groups.append(words)
        else:
            words.append(w)
    aaa = [ ' '.join(g) for g in groups if g ]
    return aaa, after, before

async def _a_duckduckgo_search_api( keyword, *, lang:str=None, num:int=10, debug=False ) ->list[dict]:
    # google風検索条件を変換する
    keyword_groups, after, before = convert_keyword( keyword )
    # リージョン
    if not isinstance(lang,str) or 'JA' in lang.upper() or 'JP' in lang.upper():
        region = 'jp-jp'
    else:
        region = 'us-en'
    #timelimitの値をYYYY-MM-DD..YYYY-MM-DD形式で、開始日と終了日を指摘することで、任意の期間の検索結果を取得できる。
    timelimit = None
    if after:
        if before:
            timelimit = after+".."+before
        else:
            timelimit = after+".."
    elif before:
        timelimit = ".." + before
    logger.info(f"[DUCKDUCKGO] region:{region} input keyword:{keyword}")
    logger.info(f"[DUCKDUCKGO] search keyword:{keyword_groups} {after}..{before}")
    # クエリ
    group_results=[]
    with DDGS() as ddgs:
        for grp in keyword_groups:
            query = f"{grp} -site:youtube.com -site:facebook.com -site:instagram.com -site:twitter.com"
            logger.info(f"[DUCKDUCKGO] group:{query} {after}..{before}")
            results = ddgs.text(
                keywords=query,      # 検索ワード
                region=region,       # リージョン 日本は"jp-jp",指定なしの場合は"wt-wt"
                safesearch='moderate',     # セーフサーチOFF->"off",ON->"on",標準->"moderate"
                timelimit=timelimit,       # 期間指定 指定なし->None,過去1日->"d",過去1週間->"w",過去1か月->"m",過去1年->"y"
                max_results=num         # 取得件数
            )
            group_results.append(results)
    # 結合
    join_results = []
    maxlen = max( [len(grp) for grp in group_results])
    for i in range(maxlen):
        for grp in group_results:
            if i<len(grp):
                join_results.append(grp[i])
    # 変換
    result_json=[]
    for item in join_results:
        title:str = item.get('title','')
        link:str = item.get('href','')
        snippet:str = item.get('body','')
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
        logger.exception('download error')
        return None, f"ERROR: {ex}"

def get_text_from_url(url, *, as_raw=False, as_html=False, debug=False):
    response = None
    try:
        response = request.urlopen(url)
        html_bytes = response.read()
        return get_text_from_html(html_bytes, as_raw=as_raw, as_html=as_html, debug=debug )
    except HTTPError as e:
        logger.error(f"HTTP Error: {e.code} - {e.reason}")
    except URLError as e:
        logger.error(f"URL Error: {e.reason}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    except Exception as ex:
        raise ex
    finally:
        try:
            response.close()
        except:
            pass

def get_number( filename ):
    """ファイル名から数字を取り出す"""
    name,_ = os.path.splitext(filename)
    num = re.sub(r'\D', '', name ).strip()
    return int(num) if num else 0

def get_next_filename(directory, prefix='dump'):
    """次のファイル名を決める"""
    existing_files = [f for f in os.listdir(directory) if f.startswith(prefix)]
    if not existing_files:
        return os.path.join( directory, f"{prefix}0001" )
    max_num = max( get_number(f) for f in existing_files)
    return os.path.join( directory, f"{prefix}{max_num + 1:04d}" )

def cleanup_tags(elem:Elem):
    if elem is None:
        return
    if elem.tag == "br":
        return True
    # if elem.tag in {'a', 'button'}:
    #     elem.clear()
    #     return False

    keep:int = 0
    remove_list:list[Elem] = []
    for child in elem:
        if cleanup_tags(child):
            keep += 1
        # elif child.tag not in {'a', 'br'} and len(child):
        else:
            remove_list.append(child)
    if keep>0:
        for e in remove_list:
            Xu.remove_tag(e)
        if keep==1 and elem.tag in ('div','span'):
            child = list(elem)[0]
            if child.tag == elem.tag:
                Xu.pop_tag(child)
        return True
    if Xu.has_texts(elem.text):
        for e in remove_list:
            Xu.remove_tag(e)
        elem.text = Xu.xs_strip(elem.text)
        return True
    return False

def strip_tag_text(elem:Elem) ->bool:
    if elem.tag=='a' or elem.tag=='button':
        return False
    if Xu.has_texts(elem.text):
        return True
    for child in elem:
        if child.tag=='a' or child.tag=='button':
            continue
        if Xu.is_available(child) or Xu.has_texts(child.tail):
            return True
    return False

def get_text_from_html(html_text, *, as_raw=False, as_html=False, keywords=None, debug=False):
    try:
        tmpdir = os.path.join('tmp', 'htmldump')

        if debug:
            os.makedirs(tmpdir, exist_ok=True)
            if isinstance(html_text,bytes):
                with open( os.path.join(tmpdir,'original.html' ), 'wb') as stream:
                    stream.write(html_text)
            if isinstance(html_text,str):
                with open( os.path.join(tmpdir,'original.html' ), 'w') as stream:
                    stream.write(html_text)

        raw_buffer = BytesIO(html_text)
        raw_buffer.seek(0)
        enc='UTF-8'
        try:
            head_text = raw_buffer.read(1000).decode('ISO-8859-1').lower()
            if "shift_jis" in head_text or "shift-jis" in head_text:
                enc="cp932"
        except:
            pass
        parser = etree.HTMLParser(encoding=enc,remove_comments=True)
        tree = etree.parse(raw_buffer, parser)
        root = tree.getroot()

        time_list = [time.time()]
        if not as_raw and root is not None:
            # 絶対不要なタグを削除
            etree.strip_elements(root, "script", "style", "meta", with_tail=False)
            time_list.append(time.time())  # 1
            # もしarticleタグmainタグが見つかれば、それ以外を消す
            articles = [ elem for elem in root.xpath('//article|//main') if Xu.count(elem,100) ]
            if articles:
                body = root.find('body')
                body.clear()
                for article in articles:
                    body.append(article)
            time_list.append(time.time())  # 2
            # <b>と<strong>を解除
            for elem in root.xpath('//b|//strong'):
                Xu.pop_tag(elem)
            time_list.append(time.time())  # 3
            # aタグ、buttonタグの周囲に何も無ければ広告とみなして削除
            for element in root.xpath('//a|//button'):
                parent = element.getparent()
                if not strip_tag_text(parent):
                    Xu.remove_tag(element)
            time_list.append(time.time())  # 4

            cleanup_tags(root)
            time_list.append(time.time())  # 5

            if debug:
                with open(os.path.join(tmpdir,'output.html'), 'w') as stream:
                    if root is not None:
                        stream.write(etree.tostring(root, pretty_print=True, encoding='unicode'))
            time_list.append(time.time())  # 6

        if as_html:
            if root is not None:
                return etree.tostring(root, pretty_print=True, encoding='unicode')
            return ''

        # raw_text = ''.join(root.itertext())
        #lines = [line.strip() for line in raw_text.splitlines()]
        #text = "\n".join(line for line in lines if line)
        text = Xu.to_text(root)

        time_list.append(time.time())  # 7
        t_all = time_list[-1] - time_list[0]
        if debug:
            with open(os.path.join(tmpdir,'output.txt'), 'w') as stream:
                stream.write(text)

        if debug or t_all > 0.1 or (keywords and not any(w in text for w in keywords)):
            if debug or t_all > 0.1:
                logger.debug(f"Text time {t_all}sec")
                for i in range(1, len(time_list)):
                    logger.debug(f" {i} {time_list[i] - time_list[i - 1]}sec")
            bbb = "" if t_all < 1.0 else "_SLOW"
            os.makedirs(tmpdir, exist_ok=True)
            filename = os.path.join(tmpdir,'dump') #get_next_filename(dir, prefix='dump')
            with open(f'{filename}{bbb}_raw.html', 'wb') as stream:
                stream.write(html_text)
            with open(f'{filename}{bbb}_strip.html', 'w') as stream:
                if root is not None:
                    stream.write(etree.tostring(root, pretty_print=True, encoding='unicode'))
            with open(f'{filename}{bbb}.txt', 'w') as stream:
                stream.write(text)

        return text

    except Exception as ex:
        logger.exception('can not get text')
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
                summary = summarize_web_content( text, length=target_length, debug=debug )
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
