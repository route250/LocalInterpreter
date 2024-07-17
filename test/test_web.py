import sys
import os
sys.path.append(os.getcwd())
import LocalInterpreter.utils.web as web

# テスト用の関数
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
    # url = 'https://nihon.matsu.net/nf_folder/nf_mametisiki/nf_animal/nf_animal_tubame.html'
    url = 'https://tenki.jp/forecast/6/30/6200/27210/1hour.html'
    print( "-----------------------------")
    text = web.get_text_from_url(url)
    print( "-----------------------------")
    print(text)
    print( "-----------------------------")
    summary = web.get_summary_from_text(text, context_size=500, overlap=10)
    print( "-----------------------------")
    print(summary)

def test_get_text_from_testdata():
    input_dir = os.path.join( 'testData','web' )
    output_dir = os.path.join( 'tmp', 'web' )
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
        #
        text = web.get_text_from_html( html_bytes )
        #
        output_file=os.path.join( output_dir, f"{case_name}.txt" )
        with open( output_file, 'w' ) as stream:
            stream.write(text)

def test_decode_and_parse_url():
    # Example usage
    url = "/trends/explore?q=/m/012f86&date=2023-05-01+2023-06-01&geo=JP"
    result = web.decode_and_parse_url(url)
    print(result)

def main():
    from dotenv import load_dotenv, find_dotenv
    load_dotenv( find_dotenv('.env_google') )
    search_result = web.google_search( 'OpenAI',num=3 )
    for res in search_result:
        title = res.get('title')
        link = res.get('link')
        snippet = res.get('snippet')
        print("==========================================")
        print(f"# {title} {link}\n{snippet}")
        content = web.get_text_from_url(link)
        print(f"## content\n{content}")

if __name__ == "__main__":
    test_get_text_from_testdata()