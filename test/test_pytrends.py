import sys
import os
sys.path.append(os.getcwd())
import LocalInterpreter.utils.trends as trends

def main():
    # trending_searches()
    trends.suggestions( "ハムスター")
    # related_topics( "健康診断")
    # realtime_trending()
    #related_keyword( '科学技術' )
    # gtrend = {
    #     "startday": "2024-05-23",
    #     "endday": "2024-05-24",
    #     "gtrend": "OpenAI"
    # }
    # ret = chk_gtrend(gtrend)
    # print(ret)
    # today_searches()

if __name__ == "__main__":
    main()