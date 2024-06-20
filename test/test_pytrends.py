import sys
import os
import platform
import time
import json

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

# Example usage
url = "/trends/explore?q=/m/012f86&date=2023-05-01+2023-06-01&geo=JP"
result = decode_and_parse_url(url)
print(result)


gtrend_list = ['gtrend']
def chk_gtrend(gtrend):
    startday = gtrend["startday"]
    endday = gtrend["endday"]
    keyword = gtrend["gtrend"]

    pytrends = TrendReq(hl='ja-JP', tz=-540 )
    kw_list = [keyword]
    pytrends.build_payload(kw_list, timeframe=f"{startday} {endday}", geo='JP')
    q = pytrends.related_queries()
    if q[kw_list[0]]['rising'] is not None:
        rising_data = q[kw_list[0]]['rising'].values.tolist()
    else:
        rising_data = []  # 'rising' のデータが存在しない場合、rising_data は空のリストになります
    gtrend_info = {
        "status": "success",
        "gtrend": gtrend,
        "rising": rising_data
    }
    gtrend_list.append(gtrend)
    return json.dumps(gtrend_info)

def keyword():
    pytrends:TrendReq = TrendReq(hl='ja-JP', tz=-540 )
    w = pytrends.trending_searches(pn='japan')
    print(w)

def today_searches():
    pytrends:TrendReq = TrendReq(hl='ja-JP', tz=-540 )
    w = pytrends.today_searches(pn='JP')
    print(w)

def related_keyword( *args ):
    # キーワードに関連するキーワードを取得する
    kw:list[str] = []
    if isinstance(args,(list,tuple)):
        for w in args:
            if isinstance(w,str):
                kw.append(w)
    if len(kw)==0:
        return []

    pytrends:TrendReq = TrendReq(hl='ja-JP', tz=-540 )
    pytrends.build_payload( kw_list=kw, timeframe='2023-05-01 2023-06-01', geo='JP' )
    queries = pytrends.related_queries()

    for w in kw:
        aa = queries[w]['top']
        print(aa)
        bb = queries[w]['rising']
        print(bb)

def related_topics( *args ):
    # キーワードに関連するキーワードを取得する
    kw:list[str] = []
    if isinstance(args,(list,tuple)):
        for w in args:
            if isinstance(w,str):
                kw.append(w)
    if len(kw)==0:
        return []

    pytrends:TrendReq = TrendReq(hl='ja-JP', tz=-540 )
    pytrends.build_payload( kw_list=kw, timeframe='2023-05-01 2023-06-01', geo='JP' )
    queries = pytrends.related_topics()

    mmm:list = {}
    for w in kw:
        aa:pd.DataFrame = queries[w]['top']
        for r, row in aa.iterrows():
            value = row['value']
            topic = row['topic_title']
            value = max( value, mmm.get(topic,0) )
            mmm[topic] = value
        bb = queries[w]['rising']
        for r, row in bb.iterrows():
            value = row['value']
            topic = row['topic_title']
            value = max( value, mmm.get(topic,0) )
            mmm[topic] = value
    # 辞書をintの降順でソートし、キーのリストを作成
    sorted_keys = [k for k, v in sorted(mmm.items(), key=lambda item: item[1], reverse=True)]
    return sorted_keys

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
    #pytrends.related_topics()
    #pytrends.related_queries()
    #pytrends.today_searches()
    #pytrends.top_charts()
    #pytrends.trending_searches()
    #pytrends.realtime_trending_searches()
    print(w)

def trending_searches():
    pytrends:TrendReq = TrendReq(hl='ja-JP', tz=-540 )
    w = pytrends.trending_searches( pn='japan' )
    print(w)

def suggestions( keyword ):
    pytrends:TrendReq = TrendReq(hl='ja-JP', tz=-540 )
    #w = pytrends.top_charts( date=2024, hl = 'ja_JP', tz=-540, geo='JP' )
    res:list[dict] = pytrends.suggestions( keyword )
    result_df = pd.DataFrame(res)
    result_df = result_df.drop(columns=['mid'])
    print(result_df)

#https://scrapbox.io/PythonOsaka/Python%E3%81%A7GoogleTrends%E3%81%AE%E3%83%87%E3%83%BC%E3%82%BF%E3%82%92%E5%8F%96%E5%BE%97%E3%81%97%E3%81%A6%E3%81%BF%E3%82%88%E3%81%86

# Googleトレンドは、クエリ(queries) と トピックス(topics) に分類されています。
# 		クエリ　ー 　検索クエリそのもの
# 		トピックス ー 　分類済みの話題
# これらがさらに、人気](top) と 注目(rising) に分類されます。
# 		人気　ー　検索ボリュームが多いもの
# 		注目 ー は検索ボリュームの上昇率が高いもの

def main():
    #trending_searches()
    # suggestions( "ハムスター")
    related_topics( "健康診断")
    # realtime_trending()
    #related_keyword( '科学技術' )
    # gtrend = {
    #     "startday": "2024-05-23",
    #     "endday": "2024-05-24",
    #     "gtrend": "OpenAI"
    # }
    # ret = chk_gtrend(gtrend)
    # print(ret)

if __name__ == "__main__":
    main()