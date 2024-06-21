
from urllib.parse import urlparse, parse_qs, unquote
import pandas as pd
from pytrends.request import TrendReq

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

def uniq_words( words ):
    # 部分文字列を排除
    result = []
    for s in words:
        if not any(s != other and s in other for other in words):
            result.append(s)
    return result

# Example usage
url = "/trends/explore?q=/m/012f86&date=2023-05-01+2023-06-01&geo=JP"
result = decode_and_parse_url(url)
print(result)

def today_searches():
    pytrends:TrendReq = TrendReq(hl='ja-JP', tz=-540 )
    w = pytrends.today_searches(pn='JP')
    result=[]
    for ww in w:
        params = decode_and_parse_url(ww)
        q=params.get('q')
        if q:
            result.append(q)
    return uniq_words( result )

def related_queries( *args ):
    return related_keyword_topics( *args, mode=False)

def related_topics( *args ):
    return related_keyword_topics( *args, mode=True)

def related_keyword_topics( *args, mode:bool=False ):
    # キーワードに関連するキーワードを取得する
    kw:list[str] = []
    if isinstance(args,(list,tuple)):
        for w in args:
            if isinstance(w,str):
                kw.append(w)
    if len(kw)==0:
        return []
    day1='2024-06-01'
    day2='2024-06-20'
    tf=f"{day1} {day2}"
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

def realtime_trending():
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

def trending_searches():
    pytrends:TrendReq = TrendReq(hl='ja-JP', tz=-540 )
    w = pytrends.trending_searches( pn='japan' )
    result = [w for w in w[0]]
    return uniq_words( result )

def suggestions( keyword ):
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
