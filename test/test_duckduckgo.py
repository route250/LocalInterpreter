import sys,os
import asyncio
from io import BytesIO
from duckduckgo_search import DDGS
import json

sys.path.append(os.getcwd())
import LocalInterpreter.utils.web as web

def sample():
    # クエリ
    with DDGS() as ddgs:
        results = list(ddgs.text(
            keywords='東京',      # 検索ワード
            region='jp-jp',       # リージョン 日本は"jp-jp",指定なしの場合は"wt-wt"
            safesearch='off',     # セーフサーチOFF->"off",ON->"on",標準->"moderate"
            timelimit=None,       # 期間指定 指定なし->None,過去1日->"d",過去1週間->"w",
                                # 過去1か月->"m",過去1年->"y"
            max_results=4         # 取得件数
        ))

    # レスポンスの表示
    for line in results:
        print(json.dumps(
            line,
            indent=2,
            ensure_ascii=False
        ))

    with DDGS() as ddgs:
        results = list(ddgs.news(
            keywords='東京',
            region='jp-jp',
            safesearch='off',
            timelimit=None,
            max_results=4
        ))
    # レスポンスの表示
    for line in results:
        print(json.dumps(
            line,
            indent=2,
            ensure_ascii=False
        ))

    with DDGS() as ddgs:
        results = ddgs.chat()
    print(results)

def bench():

    htmlfile = os.path.join( 'testData','web','dump0013_SLOW_raw.html' )
    with open( htmlfile, 'rb') as stream:
        html_bytes = stream.read()
    text = web.get_text_from_html( html_bytes, debug=True)

def main():
    messages=None
    print("---------------------------------------------")
    result = web.duckduckgo_search_json( '京都 八坂神社 歴史', messages=messages, num=5 )
    print(result)
    print("---------------------------------------------")
    messages=[]
    result = web.duckduckgo_search_json( '京都 八坂神社 歴史', messages=messages, num=5 )
    print(result)
    print("---------------------------------------------")
    messages=[
        {'role':'user','content':'八坂神社っていつごろできたの？'},
        {'role':'assistant','content':'ちょっと調べてみます。'},
    ]
    result = web.duckduckgo_search_json( '京都 八坂神社 歴史', messages=messages, num=5 )
    print(result)

async def amain():
    main()

if __name__ == "__main__":
    main()
    print("---------------------------------------------")
    #asyncio.run(amain())