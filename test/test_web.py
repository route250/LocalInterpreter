import sys
import os
sys.path.append(os.getcwd())
import LocalInterpreter.utils.web as web

def main():
    url="https://atmarkit.itmedia.co.jp/ait/articles/1910/18/news015.html"
    url = 'https://cat-press.com/cat-news/sara-ten-akubi'
    url = 'https://lsdblog.seesaa.net/article/503246391.html'
    url = 'https://wpb.shueisha.co.jp/news/politics/2024/06/14/123512/'
    #url = 'https://wpb.shueisha.co.jp/news/politics/2024/06/07/123479/'
    #web_to_text(url)

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
    main()