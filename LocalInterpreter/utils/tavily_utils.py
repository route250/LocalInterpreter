
import os
import re
import json
import hashlib
from typing import NamedTuple
from datetime import datetime, timedelta
import requests

from tavily import TavilyClient

class WebContent(NamedTuple):
    url: str = ''
    title: str = ''
    snippet: str = ''
    snippet_pos: int = -1
    content: str = ''
    timestamp: str = ''
    tm: float = 0.0

EMPTY_ITEM:WebContent = WebContent()

def n2b(value:str|None)->str:
    if isinstance(value,str):
        return value
    return ''

# 全角から半角への変換テーブル
ZENKAKU_TO_HANKAKU_TABLE = str.maketrans(
    '！＂＃＄％＆＇（）＊＋，－．／０１２３４５６７８９：；＜＝＞？＠ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ［＼］＾＿｀ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ｛｜｝～',
    '!\"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~'
)

def to_snippet( snippet:str, raw_content:str|None, chars:int=200 ) ->tuple[int,str]:

    # snippet = "Feb 26, 2024 · SNSがバズっていると話題の長崎バイオパークの広報に密着。動物の魅力を伝え、集客にもつなげるその活用法に迫ります. 短編動画の共有アプリ「TikTok（ ..."

    # raw_content = "Menu\nYouTube\n番組\nニュース\nイベント\nアナウンサー\nプレゼント\nプロジェクト\n会社概要\nNews\n日本一“バズる動物園”長崎バイオパーク SNSの活用法は？広報に密着\nＳＮＳがバズっていると話題の長崎バイオパークの広報に密着。動物の魅力を伝え、集客にもつなげるその活用法に迫ります\n短編動画の共有アプリ「ＴｉｋＴｏｋ（ティックトック）」に投稿された動物たちの「ほのぼの動画」。中には再生回数が５０００万回を超えるものもあります。フォロワーはおよそ１９０万人。去年とおととし、国内で活躍したクリエイターを表彰するティックトックアワードの「Ａｎｉｍａｌ　Ｃｒｅａｔｏｒ　ｏｆ　ｔｈｅ　ｙｅａｒ（アニマル　クリエイター　オブ　ザ　イヤー）」に２年連続でノミネートされました。\n世界最大の動画共有サービス「ＹｏｕＴｕｂｅ（ユーチューブ）」のチャンネル登録数は５０万人を超えています。こうしたＳＮＳの反響もあり、コロナ禍が収束した去年（２０２３年）の入園者数は過去１５年で最多に。ＳＮＳがきっかけでバイオパークに入社した飼育員もいます。\n“日本一バズっている動物園”と言われるバイオパーク。その秘密に迫ります。\nＳＮＳを担当するのは、長崎バイオパークの広報、春岡俊彦（はるおか・としひこ）さん２７歳と取締役ＣＭＯ＝最高マーケティング責任者の神近公孝（かみちか・きみたか）さん４８歳です。\nバイオパークは２００７年に公式ユーチューブチャンネルを開設し、その翌年（よくねん）ごろから神近さんはＳＮＳの運用に携わってきました。\n当時は動物園のイベントの告知用に動画を上げていただけでしたが、５年ほど前からは本格的な“映像コンテンツ”としてＳＮＳに力を入れています。そのきっかけとなった一つが、２０１４年８月１７日に投稿したカバがスイカを豪快に頬張る映像がバズり（話題が拡散し注目が集まる）９年５カ月後の現在およそ１億６９００万回再生されています。\n一方、元々飼育員として２０歳からバイオパークで働く春岡さん（２７）。コロナ禍で県外から来られなくなったお客さんに「ＳＮＳを通じて動物の魅力を発信したい」と４年前（２０２０）広報に異動しました。\n春岡さんの加勢もあり、コロナ禍で急激にフォロワー数がアップ。ティックトックの公式アカウントのフォロワーは２０２０年４月時点のおよそ３０万人から現在のおよそ１９０万人に。\nインスタグラムの公式アカウントのフォロワーはおよそ３０００人から６万人を超えました。\n元飼育員だからこそ分かる動物との安全な距離感で、それぞれの生き物の魅力を最大限とらえています。ユーチューブ用の長尺の動画撮影に同行させてもらいました。\n春岡さんは、出演者側にも回ります。今人気だと言うビーバー。そのお散歩動画を撮影します。飼育所から外に出て、枯れ木を拾って帰っていくビーバーたち。ひたすらカメラで回します。編集は映像制作会社に委託しています。柵や檻がなく来園者が通る通路に動物を放すことができるバイオパークだからこその撮影風景です。\n動画をバズらせる秘訣は、その魅力を高めようと努める２人の日常的な“雑談”にもありました。\n「（神近）最近の（ユーチューブ）動画で最初の動きの再生時間が長いのは、ビーバーが出てきている動画であったりとか、お世話動画が最近良いかな」\n「（春岡）積極的に飼育員に出てもらいたい」\n「（神近）園長の動画なんかも結構いいもんね。　（春岡）ずば抜けていいです。虫のコンテンツ全然伸びないのに園長が出たら伸びるっていうね。　（神近）人っていうキャラが応援したくなるとか、そこに共感するとかそういう部分が重要なのかな」】\n「（神近）非常に重要な基礎の部分。それを日常的にやれているというのがうまくポイント」\n「（春岡）きのうの動画は？って感じ」\n「（神近）とりあえず伸びが気になるから見て、気になったことをここで言ってる。他の作業しながらとか」】\n動画コンテンツが大好きな２人。春岡さんはプライベートでもユーチューバーとして、休日、出掛けた時の動画を自身のＹｏｕＴｕｂｅチャンネル「飼育員の休日」にあげています。\n春岡さんは、出勤した日は必ず午後０時半から１時間園内の動物たちの様子を生中継で見ることができる長崎バイオパークの「インスタライブ」に取り組んでいます。\n園内を周って、視聴者に園全体の魅力も届けています。動物の生活がより詳しく分かる飼育員の解説。しかし、こうした飼育員の出演調整は簡単ではないと言います。\nこうしたＳＮＳの活用の仕方について、県の内外の動物園や水族館から問い合わせもあるそうです。４頭のジャイアントパンダが見られる和歌山県の「アドベンチャーワールド」もその一つです。\n春岡さんたちの継続力と分析力とともに、園一体となって魅力を発信するバイオパーク。２０２４年の展望は？\n春岡俊彦さん（２７）「今年は飼育員が『これやりたいんだけどできない？」っていうのを企画としてやる」「飼育員の『やりたいんだけどできない』っていうのをかなえながら『バイオパークってこういうことやってるよ』っていうのを視聴者の方に見ていただけたら」\nRelated News\n1/29(月) 18:52\nカピバラの長風呂対決　長崎バイオパーク初Ｖに密着！\n12/18(月) 18:36\n【長崎】カピバラほっこり「ざぼん湯」癒やしの光景　長崎バイオパークの冬至\n2/23(金) 19:19\n“日本一かわいい”高校一年生・世古乙羽さん（１６）がドローン資格に挑戦！\n9/11(月) 19:25\n「めっちゃかわいい！」県立長崎北高校と長崎南高校の制服が来年度リニューアル　文化祭でお披露目\nNCC News\nANN News\nCopyright(C) NCC 長崎文化放送 . All rights reserved.\nThis programme includes material which is copyright of Reuters Limited and other material which is copyright of Cable News Network LP, LLLP (CNN) and which may be captioned in each text. All rights reserved.\n"

    if not isinstance(raw_content,str) or len(raw_content)==0:
        return -1,snippet[:chars]

    snippet = snippet.translate(ZENKAKU_TO_HANKAKU_TABLE)
    raw_content = raw_content.translate(ZENKAKU_TO_HANKAKU_TABLE)
    # print(raw_content)
    # 正規表現でsnippetを分割する
    # raw_contentの中の改行とかがピリオドとか中点になっているため
    split_result:list[str] = re.split(r'[·・.()]+', snippet.strip())

    regex_parts = []
    last_pos:int = -1
    start_pos:int = -1
    end_pos:int = len(raw_content)
    # raw_contentに含まれないキーワードもあるのでフィルタリングする
    for w in split_result:
        w=w.strip()
        if len(w)==0:
            continue
        p:int = raw_content.find( w, max(0,last_pos) )
        if last_pos<p:
            regex_parts.append( re.escape(w) )
            last_pos = p + len(w)
            if start_pos<0:
                start_pos = p
    if start_pos<0:
        return -1, snippet[:chars]
    end_pos = min(start_pos+chars,len(raw_content))
    # キーワードが複数あったら、それを正規表現にして検索
    if len(regex_parts)>0:
        regex:str = '.*?'.join(regex_parts) + '[^.。\r\n]*'
        match = re.search(regex,raw_content,re.DOTALL)
        if match:
            start_pos = match.start()
            end_pos = min(start_pos+chars,match.end())
    if start_pos>=0:
        # snippetが本文に見つかったので、その部分から切り出す
        return start_pos,raw_content[start_pos:end_pos]
    else:
        # 見つからなかったので、snippetをそのまま
        return -1,snippet[:chars]

class WebContentCache:
    def __init__(self, cache_dir:str, expiration_seconds:int=3600):
        self._tavily_api_key = api_key = os.getenv("TAVILY_API_KEY")
        # キャッシュディレクトリの指定と作成
        self.cache_dir:str = cache_dir
        self.expiration_seconds:int = expiration_seconds
        os.makedirs(cache_dir, exist_ok=True)

    def _get_cache_file_path(self, url:str):
        # URLをハッシュ化してファイル名に変換
        url_hash = hashlib.md5(url.encode()).hexdigest()
        base:str = os.path.join(self.cache_dir, f"{url_hash}")
        return base+".json", base+".html", base+".txt"

    def _is_cache_valid(self, cache_data:WebContent|None, limit:float|None=None):
        if isinstance(cache_data,WebContent):
            # キャッシュの取得日時を確認し、期限内かどうかをチェック
            current_time = datetime.now().timestamp()
            expiration_seconds = limit if isinstance(limit,float|int) and limit>0 else self.expiration_seconds
            if current_time - cache_data.tm < expiration_seconds:
                return True
        return False

    def _load_json(self, url:str) ->WebContent|None:
        # URLに対応するキャッシュを読み込む
        try:
            json_path, html_path, text_path = self._get_cache_file_path(url)
            if os.path.exists(json_path):
                with open(json_path, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    cache_item:WebContent = WebContent(**cache_data)
                    return cache_item
        except:
            pass
        return None

    def register(self, url:str, *, 
                 title:str|None,
                 snippet:str|None=None, snippet_pos:int|None=None,
                 content:str|None=None, html:str|None=None,
                 t:datetime|None=None) ->WebContent:

        json_path, html_path, text_path = self._get_cache_file_path(url)
        cache_item:WebContent|None = self._load_json(url)
        cache_data:dict = cache_item._asdict() if cache_item else EMPTY_ITEM._asdict()

        cache_data['url'] = url
        if title is not None:
            cache_data['title']=title
        if snippet is not None:
            cache_data['snippet']=snippet
        if snippet_pos is not None:
            cache_data['snippet_pos']=snippet_pos
        if content is not None:
            cache_data['content']=content

        if not isinstance(t,datetime):
            t = datetime.now()
        now:float = t.timestamp()
        timestamp = t.isoformat()
        cache_data['timestamp']=timestamp
        cache_data['tm']=now

        # キャッシュデータを保存する
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=4)
        if isinstance(html,str):
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html)
        item:WebContent = WebContent(**cache_data)
        return item
        
    def retrieve(self, url, limit:float|None=None) ->WebContent|None:
        # URLに対応するキャッシュを読み込む
        cache_item:WebContent|None = self._load_json(url)
        if self._is_cache_valid(cache_item,limit=limit):
            return cache_item
        return None

    def update_text(self, url, new_text):
        # キャッシュのtextフィールドを更新
        json_path,_,_ = self._get_cache_file_path(url)
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)

            # textフィールドを更新し、キャッシュファイルに保存
            cache_data['text'] = new_text
            cache_data['timestamp'] = datetime.now().isoformat()  # 更新日時も更新

            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=4)

            print(f"Updated text for {url}")
        else:
            print(f"No cache found for {url}")

    def query(self, query:str ) ->list[WebContent]:

        tavily_client = TavilyClient(api_key=self._tavily_api_key)

        exd=('youtube.com','facebook.com')
        # query = '明日の京田辺市の天気は？'
        # query = 'latest animal-related news and updates cover a range of topics'
        # query = '動物関連の最新ニュース animal-related news or topics'

        search_result = tavily_client.search( query, include_answer=True,include_raw_content=True, exclude_domains=exd )

        now:datetime = datetime.now()
        result:list[WebContent] = []
        q:str|None = search_result.get('query')
        anser:str|None = search_result.get('answer')
        if anser and q:
            item = self.register( q, t=now, title=q, snippet=anser )
            result.append(item)
        for res in search_result.get('results',[]):
            url:str = res.get('url')
            title:str = res.get('title')
            snippet:str = res.get('content')
            raw_content:str = res.get('raw_content')
            score:float = res.get('score')
            snippet_pos, snippet = to_snippet(snippet,raw_content)
            item = self.register( url, t=now, title=title,
                                 snippet=snippet, snippet_pos=snippet_pos,
                                 content=raw_content)
            result.append(item)
        return result

    def query_as_text(self, keyword:str, messages:list[dict]|None=None, usage=None, debug:bool=False ) ->str:

        result:list[WebContent] = self.query( keyword )
        result_text = f"# Search keyword: {keyword}\n\n"
        result_text += "# Search result:\n\n"

        if len(result)>0:
            for i,item in enumerate(result):
                err:str|None = None # item.error
                title:str = item.title
                link:str = item.url
                snippet:str = item.snippet
                if err:
                    result_text += f"ERROR: {err}\n\n"
                if link:
                    result_text += f"{i+1}. [{title}]({link})\n"
                    result_text += f"  {snippet}\n\n"
        else:
            result_text += "  no results.\n"
        return result_text

    def get_text_from_url(self, url, limit:float|None=None ) ->str|None:
        item:WebContent|None = self.retrieve( url, limit )
        if item is None:
            return None
        return item.content


def main():

    cache = WebContentCache('tmp/web_cache_dir', expiration_seconds=3600)  # 1時間のキャッシュ有効期限

    query = '明日の京田辺市の天気は？'
    query = 'latest animal-related news and updates cover a range of topics'
    query = '動物関連の最新ニュース animal-related news or topics'
    query = 'Metaphor search engine company'

    search_result = cache.query( query )

    for res in search_result:
        url:str = res.url
        title:str = res.title
        snippet:str = res.snippet
        raw_content:str = res.content
        print("---")
        print(f"{url}")
        print(f"{title}")
        print(f"{snippet}")

    dmp = json.dumps(search_result,ensure_ascii=False, indent=0 )
    print(dmp)

    print('----------------------------------')

if __name__ == "__main__":
    #pos,snippet = to_snippet("","")
    #print(pos)
    #print(snippet)
    main()
