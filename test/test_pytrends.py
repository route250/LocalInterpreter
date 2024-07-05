import sys
import os
sys.path.append(os.getcwd())
import LocalInterpreter.utils.trends as trends

def test_search():
    q='女神のカフェテラス'
    ret:list = trends.related_topics(q)
    #ret:list = trends.related_queries(q)
    print(ret)

def main():
    #ret = trends.trending_searches()
    # realtime_trending()
    ret = trends.today_searches()

    # trends.suggestions( "ハムスター")
    # trends.related_topics( "健康診断")
    #related_keyword( '科学技術' )
    # gtrend = {
    #     "startday": "2024-05-23",
    #     "endday": "2024-05-24",
    #     "gtrend": "OpenAI"
    # }
    # ret = chk_gtrend(gtrend)
    # print(ret)
    # today_searches()
    print(ret)

if __name__ == "__main__":
    test_search()
    # main()