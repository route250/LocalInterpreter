
from typing import TypedDict, Optional

import sys,os,traceback
import math
import re
import time
import json
import hashlib
import itertools
from urllib import request
from urllib.error import URLError, HTTPError
import mimetypes
import asyncio
from asyncio import Task
import ssl
import httpx
from httpx import Response

from io import BytesIO

from urllib.parse import urlparse, parse_qs, unquote
from lxml import etree
from lxml.etree import _ElementTree as ETree, _Element as Elem

from googleapiclient.discovery import build, Resource, HttpError
from duckduckgo_search import DDGS, AsyncDDGS
from duckduckgo_search.exceptions import DuckDuckGoSearchException, RatelimitException, TimeoutException

from LocalInterpreter.utils.openai_util import to_openai_llm_model, get_max_input_token, count_token, summarize_web_content, a_summarize_text
import LocalInterpreter.utils.lxml_util as Xu

import logging
logger = logging.getLogger('WebUtil')

ENV_GCP_API_KEY='GCP_API_KEY'
ENV_GCP_CSE_ID='GCP_CSE_ID'

def to_md5( *args ) ->str:
    text:str = '\n'.join( [str(s) for s in args] )
    md5_hash = hashlib.md5()
    md5_hash.update(text.encode('utf-8'))
    result:str = md5_hash.hexdigest()
    return result

class LinkInfo(TypedDict,total=False):
    title:str
    link:str
    snippet:str
    query: Optional[str]
    err: Optional[str]

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

def str_decode( b:bytes, enc ) ->str|None:
    try:
        return b.decode(enc)
    except:
        return None

async def a_fetch_html(url:str) ->tuple[str|bytes,str|None]:
    logger.info(f"a_fetch_html URL={url}")
    if not url or not url.startswith('http'):
        return b'','url is invalid.'
    aclient:httpx.AsyncClient|None = None
    try:
        to = 3.0

        async with httpx.AsyncClient( timeout=to, follow_redirects=True, max_redirects=2 ) as client:
            aclient = client
            response:Response = await client.get(url)
            if response.status_code != 200:
                return b'',f'http response code is {response.status_code}.'
            content_type = response.headers.get('Content-Type')
            charset_encoding = response.charset_encoding
            # BytesIOバッファを作成
            byte_buffer = BytesIO()

            # ストリームの内容をバイト列として読み込み、BytesIOに書き込む
            async for chunk in response.aiter_bytes():
                byte_buffer.write(chunk)

            # バッファの先頭にシーク
            byte_buffer.seek(0)
            bdata:bytes = byte_buffer.getvalue()
            await client.aclose()
            aclient = None
        for cs in [charset_encoding,'utf-8','Shift_JIS']:
            try:
                text = bdata.decode(cs)
                return text, None
            except:
                pass
        return bdata,None
    except httpx.ConnectTimeout as ex:
        return b'',f'ConnectTimeout {ex}'
    except httpx.ReadTimeout as ex:
        return b'',f'ReadTimeout {ex}'
    except httpx.TooManyRedirects as ex:
        logger.error(f"{ex.__class__.__name__} URL:{url}")
        return b'',f'{ex}'
    except httpx.HTTPError as ex: # httpxの例外はここに集約される
        logger.error(f"{ex.__class__.__name__} URL:{url}")
        return b'',f'{ex}'
    except ssl.SSLError as ex:
        logger.error(f"{ex.__class__.__name__} URL:{url}")
        return b'',f"{ex.__class__.__name__} URL:{url}"
    except Exception as ex:
        logger.exception(f"can not get from {url}")
        raise ex
    finally:
        try:
            if aclient is not None:
                await aclient.aclose()
        except:
            pass
def fetch_html(url:str) ->tuple[str|bytes,str|None]:
    return asyncio.run( a_fetch_html(url) )

def duckduckgo_search( keyword, *, max_length:int=800, messages:list[dict]|None=None, usage=None, lang:str='ja', num:int=5, debug=False ) ->str:
    result_json:list[LinkInfo] = duckduckgo_search_json( keyword, max_length=max_length, messages=messages, usage=usage, lang=lang, num=num, debug=debug)
    result_text = f"# Search keyword: {keyword}\n\n"
    result_text += "# Search result:\n\n"
    if isinstance(result_json,(list,tuple)):
        for i,item in enumerate(result_json):
            err:str|None = item.get('error')
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

def duckduckgo_search_json( keyword:str, *, messages:list[dict]|None=None, usage=None, max_length:int=800, lang:str='ja', num:int=5, debug=False ) ->list[LinkInfo]:
    # 非同期コンテキスト外の場合
    return asyncio.run( a_duckduckgo_search_json( keyword, max_length=max_length, messages=messages, usage=usage, lang=lang, num=num, debug=debug ) )
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

async def a_duckduckgo_search_json( keyword:str, *,max_length:int=800, messages:list[dict]|None=None, usage=None, lang:str='ja', num:int=5, debug=False ) ->list[LinkInfo]:
    debug = True
    t1:float = time.time()
    # 会話履歴
    prompt:str=""
    target:str=""
    if isinstance(messages,list):
        n=0
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
            prompt = f"# 会話履歴\n{prompt}\n\n"
            target="と会話履歴の内容"

    # キーワード分解
    keyword_group_list, timelimit = convert_keyword( keyword )
    
    # 短く要約する
    slen: int = max_length if isinstance(max_length,int) and max_length>100 else 100
    NOINFO='NoInfo'
    prompt = f"{prompt}# web検索キーワード\n{' '.join(keyword_group_list)}"
    prompt = f"{prompt}\n\n# 検索結果のURLから取得したテキスト\n```\n{{}}\n```"
    prompt = f"{prompt}\n\n# 判定処理\n"
    prompt = f"{prompt} 1. 会話履歴と検索キーワードから、どのような情報を探しているかを想定して下さい。\n"
    prompt = f"{prompt} 2. 取得したテキストに検索キーワードが含まれているか判断する。間違えやすいワードに注意\n"
    prompt = f"{prompt}   例) '東京都' と '京都' は異る地名\n"
    prompt = f"{prompt} 3. 取得したテキストに求められている具体的な情報が含まれているか判断する\n"
    prompt = f"{prompt}\n\n# 要約処理\n"
    prompt = f"{prompt} 4. 取得したテキストに、検索キーワード{target}に対応する具体的な情報が無ければ{NOINFO}だけ出力して終了。\n"
    prompt = f"{prompt} 5. 取得したテキストから、検索キーワード{target}に対応する情報だけを{slen}文字以内に要約して出力して下さい。\n"
    prompt = f"{prompt}    取得したテキストに含まれない情報を出力しないこと\n"
    prompt = f"{prompt}\n\n# 検索キーワード{target}に対応する具体的な情報:"
    # tasks = [ a_search_check( x, words ) for x in search_results ]

    # check_results = await asyncio.gather( *tasks )
    # results = [ r for r in check_results if r ]

    # 検索APIの結果件数
    search_num:int = min( num*4, 100 )

    duplicate:dict = {}
    search_results=[]

    search_interval:float = 1.0 # ddgsで検索する間隔(秒)
    limit1:float = 30
    limit2:float = 15

    t3:float = time.time()
    results:list[LinkInfo]=[]
    task_count:int = 0
    task_list:list[Task[tuple[LinkInfo|None,bool]]] = []
    ok_count:int = 0
    search_time:float = 0
    search_exception:Exception|None = None
    ddgs_total_time:float = 0
    while ok_count<num and ( len(task_list)>0 or len(search_results)>0 or (search_exception is None and len(keyword_group_list)>0 ) ):
        # 検索タスク
        now:float = time.time()
        # print(f"[DDGS] search_json count:{ok_count}<{num} keyword:{len(keyword_group_list)} result:{len(search_results)}")
        if search_exception is None and len(keyword_group_list)>0 and (now-search_time)>search_interval:
            try:
                # 検索する
                gk:str = keyword_group_list.pop(0)
                print(f"[DDGS] search_json start {gk}")
                t11:float = time.time()
                group_results:list[LinkInfo] = await _a_duckduckgo_search_api( gk, timelimit=timelimit, lang=lang, num=search_num, debug=debug )
                t12:float = time.time()
                if debug:
                    print(f"[DDGS] api {gk} time: {t12-t11:.3f}(sec)")
                ddgs_total_time += (t12-t11)
                search_time = t12
                # 検索結果をマージする
                ins:int=0
                for item in group_results:
                    link:str|None = item.get('link')
                    if link and link not in duplicate:
                        duplicate[link] = 'x'
                        search_results.insert( ins*2+1, item )
                        ins+=1
                print(f"[DDGS] search_json end {gk} result:{len(search_results)}")
            except Exception as ex:
                search_exception = ex
                print(f"[DDGS] search_json {str(ex)}")
        # テキスト化タスク
        while len(task_list)<3 and len(search_results)>0:
            item = search_results.pop(0)
            task_count+=1
            task:Task[tuple[LinkInfo|None,bool]] = asyncio.create_task( _a_th_duckduckgo_search_get_text( item, prompt_fmt=prompt, lang=lang, usage=usage, debug=debug ), name=f"T{task_count}" )
            task_list.append( task )
            print(f"[DDGS.TASK] append {task.get_name()} count:{len(task_list)}")
        # 結果集計
        new_task_list:list[Task[tuple[LinkInfo|None,bool]]] = []
        for task in task_list:
            if task.done():
                item,ok = task.result()
                if item:
                    if ok:
                        results.insert(ok_count,item)
                        ok_count += 1
                        if debug:
                            print(f"[DDGS2.TASK] reslt {task.get_name()} OK {ok_count}")
                    else:
                        results.append(item)
                        if debug:
                            print(f"[DDGS2.TASK] reslt {task.get_name()} NG {ok_count}")
            else:
                new_task_list.append( task )
        task_list = new_task_list

        t5 = time.time()
        tt:float = t5 - t3
        if ok_count>0:
            if tt>limit2:
                if debug:
                    print(f"[DDGS2.TASK] stop2 {ok_count} {tt:.3f}(sec)")
                break
        else:
            if tt>limit1:
                if debug:
                    print(f"[DDGS2.TASK] stop1 {ok_count} {tt:.3f}(sec)")
                break
        await asyncio.sleep(0.2)

    for task in task_list:
        if debug:
            print(f"[DDGS2.TASK] cancel {task.get_name()}")
        try:
            task.cancel()
            while not task.cancelled() and not task.done():
                await asyncio.sleep(0.02)
        except:
            pass

    # エラー情報
    if not isinstance(results,list) or len(results)==0:
        if search_exception:
            results = [ LinkInfo(
                title='aborted duckduckgo search.',
                link='https://duckduckgo.com',
                snippet=str(search_exception),
                err=str(search_exception)
            )]
        else:
            results = []

    t6 = time.time()
    if debug:
        print(f"[TASK] end result {len(results)} {ddgs_total_time:.3f}(sec) {t6-t3-ddgs_total_time:.3f}(sec) {t6-t1:.3f}(sec)")

    return results[:num]

async def _a_th_duckduckgo_search_get_text( item:LinkInfo, *, prompt_fmt:str|None=None, lang:str='ja', usage=None, debug=False ) ->tuple[LinkInfo|None,bool]:
    # 検索結果からURL
    link = item.get('link')
    if not link:
        return None, False
    # htmlを取得して本文を取り出す
    t1 = time.time()
    html_data,err = await a_fetch_html(link)
    if err or not html_data:
        logger.debug(f"_a_th_duckduckgo_search {err} URL={link}")
        item['err'] = err
        return item, False
    # キーワード分解
    query = item.get('query','')
    keyword:list[str] = query.split() if query else []
    if isinstance(html_data,str):
        # キーワードが含まれるか？
        Hit = False
        for w in keyword:
            if w in html_data:
                Hit=True
        if not Hit:
            err = 'NoKeyword'
            item['err'] = err
            logger.debug(f"_a_th_duckduckgo_search {err} URL={link}")
            return item, False
    # htmlからテキスト抽出
    text = get_text_from_html( html_data, url=link, keywords=keyword )
    t2 = time.time()
    logger.info( f"{link} get {t2-t1}(sec)")
    if not isinstance(text,str) or len(text.strip())==0:
        err = 'NoText'
        item['err'] = err
        logger.debug(f"_a_th_duckduckgo_search {err} URL={link}")
        return None, False

    if prompt_fmt is None:
        # 要約しないそのまま返信
        logger.debug(f"_a_th_duckduckgo_search PLAIN URL={link}")
        return item, True

    # 要約する

    # 原文を切り出し
    start_pos = 999999
    for w in keyword:
        p = text.find(w)
        if 0<=p and p<start_pos:
            start_pos = p
    if start_pos<len(text):
        while start_pos>0 and text[start_pos] in '.,。':
            start_pos -= 1
    else:
        start_pos = max( 0, int(len(text)/2)-1000)
    text = text[start_pos:start_pos+2000]
    title:str|None = item.get('title')
    if title:
        text = f"ContentTitle: {title}\n\nContentBody:\n\n{text}"

    # 短く要約する
    try:
        if '{}' in prompt_fmt:
            prompt = prompt_fmt.replace('{}',text)
        else:
            prompt = prompt_fmt
        digest = await a_summarize_text( text, prompt=prompt, usage=usage )
        t3 = time.time()
        # snippetを更新する
        ok = digest and not 'NoInfo' in digest
        if ok:
            item['snippet'] = digest
            logger.debug(f"_a_th_duckduckgo_search summarize {t3-t2}(sec) URL={link}")
            return item, ok
        else:
            logger.debug(f"_a_th_duckduckgo_search Fail {t3-t2}(sec) URL={link}")
            return None, False
    except Exception as ex:
        raise ex
    return None,False

def convert_keyword( expression:str|list[str] ) ->tuple[list[str],str|None]:
    """google風検索条件を変換する"""
    tokens:list[str] = []
    if isinstance(expression,str):
        tokens = [ w.strip() for w in expression.split(' ') if w.strip() ]
    elif isinstance(expression,list):
        tokens = [ w.strip() for w in expression if isinstance(w,str) ]
    after:str|None = None
    before:str|None = None
    grp_words:list[str] = []
    groups:list[list[str]] = [grp_words]
    for t in tokens:
        if t.startswith('before:'):
            before = t[len('before:'):]
        elif t.startswith('after:'):
            after = t[len('after:'):]
        elif t == "(" or t ==")" or t.upper=="AND":
            continue
        elif t.upper()=="OR":
            grp_words = []
            groups.append(grp_words)
        else:
            grp_words.append(t)

    # 'の'で分割
    idx:int = 0
    while idx<len(groups):
        grp_words = groups[idx]
        update = False
        new_words = []
        for t in grp_words:
            p:int = t.find('の')
            if 2<=p and p<len(t)-2:
                # 「の」で分割して部分を追加
                for n in t.split('の'):
                    if len(n.strip())>0:
                        new_words.append(n.strip())
                        update = True
            else:
                new_words.append(t)
        idx+=1
        if update:
            groups.insert(idx,new_words)
            idx+=1

    new_expression:list[str] = [ ' '.join(grp_words) for grp_words in groups if grp_words ]

    #timelimitの値をYYYY-MM-DD..YYYY-MM-DD形式で、開始日と終了日を指摘することで、任意の期間の検索結果を取得できる。
    timelimit:str|None = None
    if after:
        if before:
            timelimit = after+".."+before
        else:
            timelimit = after+".."
    elif before:
        timelimit = ".." + before
    return new_expression, timelimit

_ddgs_rate_limit_time:float = 0

async def _a_duckduckgo_search_api( keyword, *, lang:str|None=None, timelimit:str|None=None, num:int=10, debug=False ) ->list[LinkInfo]:
    global _ddgs_rate_limit_time

    # リージョン
    if not isinstance(lang,str) or 'JA' in lang.upper() or 'JP' in lang.upper():
        region = 'jp-jp'
    else:
        region = 'us-en'

    logger.info(f"[DUCKDUCKGO] query:{keyword} timelimit:{timelimit} num:{num} region:{region}")
    # クエリ
    with AsyncDDGS() as ddgs:
        query = f"{keyword} -site:youtube.com -site:facebook.com -site:instagram.com -site:twitter.com"
        max_r:int = 3
        for r in range(max_r):
            try:
                key:str = to_md5( query, region, timelimit, num )
                cache_file:str = os.path.join( 'tmp','ddgs_cache', key)
                if os.path.exists(cache_file):
                    try:
                        with open(cache_file,'r',encoding='utf-8') as stream:
                            results = json.load(stream)
                        break
                    except:
                        os.remove(cache_file)
                #----
                tt0:float = time.time()
                print(f"### ddgs {query} max_results={num}")
                results = await ddgs.atext(
                    keywords=query,      # 検索ワード
                    region=region,       # リージョン 日本は"jp-jp",指定なしの場合は"wt-wt"
                    safesearch='moderate',     # セーフサーチOFF->"off",ON->"on",標準->"moderate"
                    timelimit=timelimit,       # 期間指定 指定なし->None,過去1日->"d",過去1週間->"w",過去1か月->"m",過去1年->"y"
                    max_results=num         # 取得件数
                )
                _ddgs_rate_limit_time = 0.0
                tt1:float = time.time()
                print(f"### ddgs {query} max_results={num} time {tt1-tt0:.3f}(sec)")
                os.makedirs( os.path.dirname(cache_file), exist_ok=True )
                with open(cache_file,'w',encoding='utf-8') as stream:
                    json.dump(results,stream,ensure_ascii=False,indent=4)
                break
            except Exception as ex:
                if isinstance(ex,RatelimitException) and _ddgs_rate_limit_time<=1:
                    _ddgs_rate_limit_time = time.time()
                if r+1 < max_r:
                    if isinstance(ex,RatelimitException) or isinstance(ex,TimeoutException):
                        print(f"ddgs RateLimit sleep")
                        await asyncio.sleep(1.2)
                        ddgs._exception_event.clear()
                        continue
                raise ex
    # 変換
    result_json:list[LinkInfo] = []
    for item in results:
        link:str = item.get('href','')
        title:str = item.get('title','')
        snippet:str = item.get('body','')
        result_json.append( {'title':title, 'link':link, 'snippet': snippet, 'query': keyword })

    return result_json

def google_search_json( keyword, *, lang:str='ja', num:int=5, debug=False ) ->list[LinkInfo]:

    # API KEY
    api_key = os.environ.get(ENV_GCP_API_KEY)
    cse_id = os.environ.get(ENV_GCP_CSE_ID)
    if not api_key or not cse_id:
        return [ { 'err': 'invalid api key or custom search engine id.'} ]

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
        return [ { 'err': f'{e.reason}'} ]
    except Exception as e:
        return [ { 'err': f'{e}'} ]

    if debug:
        try:
            with open('search_result.json','w') as stream:
                # レスポンスをjson形式で保存
                json.dump( result_raw, stream, ensure_ascii=False, indent=4 )
        except:
            pass

    result_json:list[LinkInfo]=[]
    for item in result_raw.get('items',[]):
        title:str = item.get('title','')
        link:str = item.get('link','')
        snippet:str = item.get('snippet','')
        result_json.append( {'title':title, 'link':link, 'snippet': snippet })

    return result_json


def xgoogle_search( keyword, *,lang:str='ja', num:int=5, debug=False ) ->str:
    result_json:list[LinkInfo] = google_search_json( keyword, lang=lang, num=num, debug=debug)
    result_text = f"# Search keyword: {keyword}\n\n"
    result_text += "# Search result:\n\n"
    if isinstance(result_json,(list,tuple)):
        for i,item in enumerate(result_json):
            err:str|None = item.get('err')
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

def google_search( keyword, *,lang:str='ja', num:int=5, debug=False ) ->str:
    result_json:list[LinkInfo] = google_search_json( keyword, lang=lang, num=num, debug=debug)
    result_text = f"# Search keyword: {keyword}\n\n"
    result_text += "# Search result:\n\n"
    if isinstance(result_json,(list,tuple)):
        for i,item in enumerate(result_json):
            err:str|None = item.get('err')
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

def download_from_url(url:str, *, directory:str, file_name:str|None=None) -> tuple[str|None,str]:
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

def get_text_from_url(url:str, *, as_raw=False, as_html=False, debug=False) ->str|None:
    """urlからhtmlをget"""
    response = None
    try:
        response = request.urlopen(url)
        html_bytes = response.read()
        return get_text_from_html(html_bytes, url=url, as_raw=as_raw, as_html=as_html, debug=debug )
    except HTTPError as e:
        logger.error(f"HTTP Error: {e.code} - {e.reason}")
    except URLError as e:
        logger.error(f"URL Error: {e.reason}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    # except Exception as ex:
    #     raise ex
    finally:
        try:
            if response:
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

def update_list_with_value(lst, start_index, value):
    """指定したインデックスからリストの要素を指定した値で更新します。"""
    if len(lst)<=start_index:
        last = lst[-1] if len(lst)>0 else 0
        while( len(lst)<=start_index):
            lst.append(last)
        lst.append(value)
    else:
        lst[start_index:] = [value] * (len(lst) - start_index)

def detect_encoding( buffer:bytes ):
    if b'Shift' in buffer or b'shift' in buffer:
        if b'JIS' in buffer or b'jis' in buffer:
            return 'Shift_JIS'
    if b'UTF-8' in buffer or b'utf-8' in buffer:
        return 'UTF-8'
    return None

def get_text_from_html(html_data:str|bytes, *, url:str, as_raw=False, as_html=False, keywords=None, debug=False, dump_file:str|None=None) ->str|None:
    try:
        tmpdir = os.path.join('tmp', 'htmldump')
        root = None
        text = None
        result = ''
        postfix:str|None = None if not debug and not dump_file else "DBG"
        time_list = [time.time()]
        try:
            if isinstance(html_data,str):
                parser = etree.HTMLParser(remove_comments=True, no_network=True)
                root = etree.fromstring(html_data, parser)
            else:
                raw_buffer = BytesIO(html_data)
                raw_buffer.seek(0)
                enc = detect_encoding( raw_buffer.getvalue()[:1000] )
                parser = etree.HTMLParser(encoding=enc, remove_comments=True, no_network=True)
                tree = etree.parse(raw_buffer, parser)
                root = tree.getroot()

            update_list_with_value(time_list,1,time.time())
            if root is not None:
                if not as_raw:
                    # 絶対不要なタグを削除
                    etree.strip_elements(root, "script", "style", "meta", with_tail=False)
                    update_list_with_value(time_list,2,time.time())
                    # もしarticleタグmainタグが見つかれば、それ以外を消す
                    articles = [ elem for elem in root.xpath('//article|//main') if Xu.count(elem,100) ]
                    if articles:
                        body = root.find('body')
                        body.clear()
                        for article in articles:
                            body.append(article)
                    update_list_with_value(time_list,3,time.time())
                    # <b>と<strong>を解除
                    for elem in root.xpath('//b|//strong'):
                        Xu.pop_tag(elem)
                    update_list_with_value(time_list,4,time.time())
                    # aタグ、buttonタグの周囲に何も無ければ広告とみなして削除
                    for element in root.xpath('//a|//button'):
                        parent = element.getparent()
                        if not strip_tag_text(parent):
                            Xu.remove_tag(element)
                    update_list_with_value(time_list,5,time.time())

                    cleanup_tags(root)

                update_list_with_value(time_list,6,time.time())

                if as_html:
                    htxt = etree.tostring(root, pretty_print=True, encoding='unicode')
                    result = htxt
                else:
                    text = Xu.to_text(root)
                    result = text
                    if text is None or len(text.strip())==0:
                        postfix = "EMPTY"
                    elif (keywords and not any(w in text for w in keywords)):
                        postfix = "NOWORD"
        except Exception as ex:
            err:str = str(ex).lower()
            if "unicode" in err or "encode" in err:
                logger.error(f"{err} {url}")
                postfix = "ENCODE"
            else:
                logger.exception(f'can not summary html? {url}')
                postfix = "ERR"

        update_list_with_value(time_list,7,time.time())
        t_all = time_list[-1] - time_list[0]
        #----------
        if t_all>0.1:
            if postfix is None:
                postfix = "SLOW"
            if debug:
                logger.debug(f"Text time {t_all}sec")
                for i in range(1, len(time_list)):
                    logger.debug(f" {i} {time_list[i] - time_list[i - 1]}sec")
        if postfix is not None:
            os.makedirs(tmpdir, exist_ok=True)
            # filename = os.path.join(tmpdir,'dump')
            filename = get_next_filename(tmpdir, prefix='dump') if dump_file is None else dump_file
            filename = f"{filename}{postfix}"
            try:
                mode = 'w' if isinstance(html_data,str) else 'wb'
                with open(f'{filename}_raw.html', mode) as stream:
                    stream.write(html_data)
            except Exception as ex:
                logger.error( f"{ex}" )
            try:
                if root is not None:
                    with open(f'{filename}_strip.html', 'w') as stream:
                        stream.write(etree.tostring(root, pretty_print=True, encoding='unicode'))
            except Exception as ex:
                logger.error( f"{ex}" )
            try:
                if text is not None:
                    with open(f'{filename}.txt', 'w') as stream:
                        stream.write(text)
            except Exception as ex:
                logger.error( f"{ex}" )

        return result

    except Exception as ex:
        logger.exception(f'can not get text {url}')
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

def get_summary_from_text( text:str|None,length:int=1024, *, context_size:int|None=None, overlap:int=500, messages:list[dict]|None=None, usage=None, model:str|None=None, debug=False) ->str:

    if not text or not isinstance(text,str):
        return ""

    if not os.environ.get('OPENAI_API_KEY'):
        return text[:length]

    max_input = int( get_max_input_token( model ) * 0.7 )
    if isinstance(context_size,int) and context_size>1:
        context_size = min( context_size, max_input )
    else:
        context_size = max_input

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
                summary = summarize_web_content( text, length=target_length, messages=messages, usage=usage, model=model, debug=debug )
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

def get_summary_from_url(url:str, length:int=1024, *, messages:list[dict]|None=None, usage=None, model:str|None=None, debug=False):
    """urlからhtmlをgetしてテキスト抽出して要約する"""
    text:str|None = get_text_from_url( url, debug=debug )
    
    return get_summary_from_text( text, length=length, messages=messages, usage=usage, model=model, debug=debug)
