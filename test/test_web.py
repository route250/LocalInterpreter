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
    #url = 'https://wpb.shueisha.co.jp/news/politics/2024/06/07/123479/'
    url = 'https://nihon.matsu.net/nf_folder/nf_mametisiki/nf_animal/nf_animal_tubame.html'
    print( "-----------------------------")
    text = web.get_text_from_url(url)
    print( "-----------------------------")
    print(text)
    print( "-----------------------------")
    summary = web.get_summary_from_text(text, context_size=500, overlap=10)
    print( "-----------------------------")
    print(summary)

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
    test_get_text_from_url()