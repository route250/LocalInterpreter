import sys
import os
import platform
import time
import json

from pytrends.request import TrendReq

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
    print(w)

def main():
    realtime_trending()
    # gtrend = {
    #     "startday": "2024-05-23",
    #     "endday": "2024-05-24",
    #     "gtrend": "OpenAI"
    # }
    # ret = chk_gtrend(gtrend)
    # print(ret)

if __name__ == "__main__":
    main()