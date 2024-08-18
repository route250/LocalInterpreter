import sys
import os
import asyncio
import json
import time
from datetime import datetime, timedelta
sys.path.append(os.getcwd())
import LocalInterpreter.utils.web as web
from LocalInterpreter.utils.web import LinkInfo

def test_searchx():
    t = datetime.now() + timedelta(days=1)
    day = t.strftime('%Y年%m月%d日')
    keyword:str = f'京都の天気予報 {day}'
    messages:list[dict] = [
        {'role': 'assistant', 'content': '{"text_to_speech": "よお、おひるだぜ。今日は蒸し暑いな、ブラザー。そんなとこで何してんの？"}'},
        {'role': 'user', 'content': 'ぼーっとな'},
        {'role': 'assistant', 'content': '{"text_to_speech": "ぼーっとしてるか。ったく、ブラザーも暇だな。何か面白いことでも考えたらどうなんだ？俺なんか今日、昼飯に何食うかずっと悩んでたぜ。そんな感じで無駄に時間を浪費するのもどうかと思うが、どうする？"}'},
        {'role': 'user', 'content': 'うーん、明日の京都の天気ってわかる？'}
    ]

    st:float = time.time()
    result:list[LinkInfo] = web.duckduckgo_search_json( keyword, messages=messages, num=20, debug=True )
    et:float = time.time()
    total_time:float = et-st

    for l in result:
        line:str = json.dumps(l,ensure_ascii=False)
        print(line)
    print(f"num: {len(result)}")
    print(f"time: {total_time:.3f}(sec)")

def main():
    from dotenv import load_dotenv, find_dotenv
    load_dotenv( find_dotenv('.env_google') )
    search_result = web.google_search_json( 'OpenAI',num=3 )
    for res in search_result:
        title:str|None = res.get('title')
        link:str|None = res.get('link')
        snippet:str|None = res.get('snippet')
        print("==========================================")
        print(f"# {title} {link}\n{snippet}")
        if link:
            content = web.get_text_from_url(link)
            print(f"## content\n{content}")

if __name__ == "__main__":
    test_searchx()

#    京都の天気予報 2024年7月26日

#[{'role': 'assistant', 'content': '{"text_to_speech": "よお、おひるだぜ。今日は蒸し暑いな、ブラザー。そんなとこで何してんの？"}'}, {'role': 'user', 'content': 'ぼーっとな'}, {'role': 'assistant', 'content': '{"text_to_speech": "ぼーっとしてるか。ったく、ブラザーも暇だな。何か面白いことでも考えたらどうなんだ？俺なんか今日、昼飯に何食うかずっと悩んでたぜ。そんな感じで無駄に時間を浪費するのもどうかと思うが、どうする？"}'}, {'role': 'user', 'content': 'うーん、明日の京都の天気ってわかる？'}]


#https://tenki.jp/past/2024/07/weather テキストが文字化ける

# messagesから会話だけ抽出すること
