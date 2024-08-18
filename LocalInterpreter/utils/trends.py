from datetime import datetime,timedelta
import pandas as pd
from pytrends.request import TrendReq
from LocalInterpreter.utils import web
from LocalInterpreter.utils.web import LinkInfo

import logging
logger = logging.getLogger('TrendsUtil')

def uniq_words( words:list[str] ) ->list[str]:
    # 部分文字列を排除
    result = []
    for s in words:
        if not any(s != other and s in other for other in words):
            result.append(s)
    return result

def today_searches() ->list[str]:
    pytrends:TrendReq = TrendReq(hl='ja-JP', tz=-540 )
    w = pytrends.today_searches(pn='JP')
    result=[]
    for ww in w:
        params = web.decode_and_parse_url(ww)
        q=params.get('q')
        if q:
            result.append(q)
    return uniq_words( result )

def related_queries( *args ):
    return related_keyword_topics( *args, mode=False)

def related_topics( *args ):
    return related_keyword_topics( *args, mode=True)

def related_keyword_topics( *args, mode:bool=False ) ->list[str]:
    # キーワードに関連するキーワードを取得する
    kw:list[str] = []
    if isinstance(args,(list,tuple)):
        for w in args:
            if isinstance(w,str):
                kw.append(w)
    if len(kw)==0:
        return []

    today = datetime.now()
    yesterday = today - timedelta(days=1)
    today_str:str = today.strftime("%Y-%m-%d")
    yesterday_str:str = yesterday.strftime("%Y-%m-%d")
    day1='2024-06-01'
    day2='2024-06-20'
    tf=f"{yesterday_str} {today_str}"
    pytrends:TrendReq = TrendReq(hl='ja-JP', tz=-540 )
    pytrends.build_payload( kw_list=kw, timeframe=tf, geo='JP' )
    if mode:
        queries = pytrends.related_topics()
    else:
        queries = pytrends.related_queries()

    topic_dict:list = {}
    for w in kw:
        aa:pd.DataFrame = queries[w]['top']
        for r, row in aa.iterrows():
            value = row['value']
            topic = row.get('query') or row.get('topic_title')
            value = max( value, topic_dict.get(topic,0) )
            topic_dict[topic] = value
        bb = queries[w]['rising']
        for r, row in bb.iterrows():
            value = row['value']
            topic = row.get('query') or row.get('topic_title')
            value = max( value, topic_dict.get(topic,0) )
            topic_dict[topic] = value
    # 辞書をintの降順でソートし、キーのリストを作成
    sorted_keys = [k for k, v in sorted(topic_dict.items(), key=lambda item: item[1], reverse=True)]
    # 部分文字列を排除
    return uniq_words( sorted_keys )

def realtime_trending() ->list[str]:
    # category
    # all:全てのカテゴリ
    #  e: エンタテイメント
    #  s: スポーツ
    #  h: トップニュース
    #  b: ビジネス
    #  m: 健康
    #  t: テクノロジー
    pytrends:TrendReq = TrendReq(hl='ja-JP', tz=-540 )
    w = pytrends.realtime_trending_searches( pn='JP', cat='all', count=5 )

    result = []
    for r, row in w.iterrows():
        names = row['entityNames']
        for name in names:
            result.append(name)
    return uniq_words(result)

def trending_searches() ->list[str]:
    pytrends:TrendReq = TrendReq(hl='ja-JP', tz=-540 )
    w = pytrends.trending_searches( pn='japan' )
    result = [w for w in w[0]]
    return uniq_words( result )

def suggestions( keyword ) ->list[str]:
    pytrends:TrendReq = TrendReq(hl='ja-JP', tz=-540 )
    #w = pytrends.top_charts( date=2024, hl = 'ja_JP', tz=-540, geo='JP' )
    res:list[dict] = pytrends.suggestions( keyword )
    result_df = pd.DataFrame(res)
    title_list = result_df['title']
    result = [w for w in title_list]
    return uniq_words(result)

#https://scrapbox.io/PythonOsaka/Python%E3%81%A7GoogleTrends%E3%81%AE%E3%83%87%E3%83%BC%E3%82%BF%E3%82%92%E5%8F%96%E5%BE%97%E3%81%97%E3%81%A6%E3%81%BF%E3%82%88%E3%81%86

# Googleトレンドは、クエリ(queries) と トピックス(topics) に分類されています。
# 		クエリ　ー 　検索クエリそのもの
# 		トピックス ー 　分類済みの話題
# これらがさらに、人気](top) と 注目(rising) に分類されます。
# 		人気　ー　検索ボリュームが多いもの
# 		注目 ー は検索ボリュームの上昇率が高いもの


def today_searches_result( *, lang='ja', num=10, debug=False):
    word_list:list[str] = today_searches()
    search_keywords = " OR ".join([ f"\"{w}\"" for w in word_list])
    yesterday = datetime.now() - timedelta(days=3)
    yesterday_str:str = yesterday.strftime("%Y-%m-%d")
    query = f"( {search_keywords} ) after:{yesterday_str}"
    result_all_list:list[LinkInfo] = web.duckduckgo_search_json( query, lang=lang, num=20, debug=debug)
    # {'title':title, 'link':link, 'snippet': snippet }

    counter = {}
    for hit_word in word_list:
        counter[hit_word] = 0

    result_json = []
    uniq:dict = {}
    nn:int = 3
    skip_get = 1
    for mode in range(skip_get,2):
        for item in result_all_list:
            title:str = item.get('title')
            link:str = item.get('link')
            if link in uniq:
                continue
            snippet:str = item.get('snippet')
            if mode==0:
                content:str = web.get_text_from_url(link)
            else:
                content = snippet
            hit_word:str = None
            for k,v in counter.items():
                if k in content:
                    if v>=nn:
                        hit_word = None
                        break
                    elif hit_word is None:
                        hit_word = k
            if hit_word:
                counter[hit_word] += 1
                if mode==0:
                    item['content'] = content
                result_json.append(item)
                uniq[link] = 0

    word_lines = '\n'.join( [ f" - {w}" for w in word_list ])
    result_text = f"# Today's popular search keywords:\n{word_lines}\n\n"
    result_text += "# Search results for today's popular search keywords:\n\n"
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
