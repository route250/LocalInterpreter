import sys
import os
import asyncio
sys.path.append(os.getcwd())
import LocalInterpreter.utils.web as web

# テスト用の関数
def get_html():
    link = 'https://tenki.jp/past/2024/07/weather'
    link = 'https://tenki.jp/past/2024/07/weather/'
    keyword = '天気'
    html_bytes,err = web.fetch_html(link)
    text = web.get_text_from_html( html_bytes, url=link, keywords=keyword )
    print(text)

def test_split_text_with_overlap():
    test_text = "123456789012345abcde123456789012345678901234567890"
    test_text = "abcdefghijklmnopqrstabcdefghijklmnopqrstabcdefghij"
    expected_chunks = [
        "abcdefghijklmnopqrst",
        "pqrstabcdefghijklmno",
        "klmnopqrstabcdefghij",
        "345678901234567890"
    ]

    chunks = web.text_to_chunks(test_text, 20, 5)

    # 結果を検証
    for i, chunk in enumerate(chunks):
        print(f"Chunk {i+1}: {chunk} : {expected_chunks[i]}")

def test_get_text_from_url():
    url="https://atmarkit.itmedia.co.jp/ait/articles/1910/18/news015.html"
    url = 'https://cat-press.com/cat-news/sara-ten-akubi'
    url = 'https://lsdblog.seesaa.net/article/503246391.html'
    url = 'https://wpb.shueisha.co.jp/news/politics/2024/06/14/123512/'
    url = 'https://wpb.shueisha.co.jp/news/politics/2024/06/07/123479/'
    # url = 'https://nihon.matsu.net/nf_folder/nf_mametisiki/nf_animal/nf_animal_tubame.html' # URL Error: [SSL: DH_KEY_TOO_SMALL] dh key too small (_ssl.c:1007)
    url = 'https://tenki.jp/forecast/6/30/6200/27210/1hour.html'
    url = 'https://jp.tradingview.com/symbols/NASDAQ-NVDA/'
    print( "-----------------------------")
    text = web.get_text_from_url(url, debug=True)
    print( "-----------------------------")
    print(text)
    print( "-----------------------------")
    summary = web.get_summary_from_text(text, context_size=500, overlap=10)
    print( "-----------------------------")
    print(summary)

def test_get_text_from_testdata():
    input_dir = os.path.join( 'testData','web' )
    output_dir = os.path.join( 'tmp', 'testData', 'web' )
    os.makedirs( output_dir, exist_ok=True )
    files = [file for file in os.listdir( input_dir ) if file.startswith('case') and file.endswith('.html')]
    for file in files:
        case_name,_ = os.path.splitext(os.path.basename(file))
        print("-----------------------------------------------------")
        print(case_name)
        print("-----------------------------------------------------")
    
        input_file = os.path.join( input_dir, file )
        with open( input_file, 'rb') as stream:
            html_bytes = stream.read()
        input_text = input_file.replace(".html",".md")
        actual_text = None
        if os.path.exists(input_text):
            with open( input_text, 'r' ) as stream:
                actual_text = stream.read()
        #
        dump_file=os.path.join( output_dir, f"{case_name}" )
        text:str|None = web.get_text_from_html( html_bytes, url=input_file, debug=False, dump_file=dump_file )
        if text is None:
            print( "ERROR" )
            continue
        #
        output_file=os.path.join( output_dir, f"{case_name}.md" )
        with open( output_file, 'w' ) as stream:
            stream.write(text)
        if actual_text is None:
            print( "NO DATA")
        else:
            if actual_text != text:
                print( "ERROR!" )
            else:
                print( "SUCCESS!" )

def test_decode_and_parse_url():
    # Example usage
    url = "/trends/explore?q=/m/012f86&date=2023-05-01+2023-06-01&geo=JP"
    result = web.decode_and_parse_url(url)
    print(result)

def test_searchx():
    keyword:str = '京都の天気予報 2024年7月26日'
    messages:list[dict] = [
        {'role': 'assistant', 'content': '{"text_to_speech": "よお、おひるだぜ。今日は蒸し暑いな、ブラザー。そんなとこで何してんの？"}'},
        {'role': 'user', 'content': 'ぼーっとな'},
        {'role': 'assistant', 'content': '{"text_to_speech": "ぼーっとしてるか。ったく、ブラザーも暇だな。何か面白いことでも考えたらどうなんだ？俺なんか今日、昼飯に何食うかずっと悩んでたぜ。そんな感じで無駄に時間を浪費するのもどうかと思うが、どうする？"}'},
        {'role': 'user', 'content': 'うーん、明日の京都の天気ってわかる？'}
    ]

    text:str = web.duckduckgo_search( keyword, messages=messages, debug=True )

    print(text)

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
    #get_html()
    #test_searchx()
    # test_get_text_from_url()
    test_get_text_from_testdata()


#    京都の天気予報 2024年7月26日

#[{'role': 'assistant', 'content': '{"text_to_speech": "よお、おひるだぜ。今日は蒸し暑いな、ブラザー。そんなとこで何してんの？"}'}, {'role': 'user', 'content': 'ぼーっとな'}, {'role': 'assistant', 'content': '{"text_to_speech": "ぼーっとしてるか。ったく、ブラザーも暇だな。何か面白いことでも考えたらどうなんだ？俺なんか今日、昼飯に何食うかずっと悩んでたぜ。そんな感じで無駄に時間を浪費するのもどうかと思うが、どうする？"}'}, {'role': 'user', 'content': 'うーん、明日の京都の天気ってわかる？'}]


#https://tenki.jp/past/2024/07/weather テキストが文字化ける

# messagesから会話だけ抽出すること
