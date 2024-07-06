import sys
import os
sys.path.append(os.getcwd())
import json
from LocalInterpreter.utils.openai_util import setup_openai_api, summarize_conversation

def test_summary():

    setup_openai_api()

    prompt_list = [
        { "role": "system", "content": "あなたは会話AIです。ユーザと会話してなんとかして下さい。"}
    ]
    message_list = [
        { "role": "user", "content": "おはよう" },
        { "role": "assistant", "content": "おはようございます。" },
        { "role": "user", "content": "今日の天気はどうですか？" },
        { "role": "assistant", "content": "今日の天気は晴れです。" },
        { "role": "user", "content": "今日は何をする予定ですか？" },
        { "role": "assistant", "content": "今日は新しいプログラムを開発する予定です。" },
        { "role": "user", "content": "どんなプログラムですか？" },
        { "role": "assistant", "content": "会話要約コードのテストデータを作成するプログラムです。" },
        { "role": "user", "content": "面白そうですね。" },
        { "role": "assistant", "content": "そうですね。頑張って良いものを作ります。" },
        { "role": "user", "content": "ありがとう、楽しみにしています。" },
        { "role": "assistant", "content": "どういたしまして。素敵な一日をお過ごしください。" },
        { "role": "user", "content": "今日は忙しいですか？" },
        { "role": "assistant", "content": "少し忙しいですが、時間はあります。" },
        { "role": "user", "content": "助かります。実は相談があります。" },
        { "role": "assistant", "content": "もちろん、どうぞ。" },
        { "role": "user", "content": "新しいプロジェクトで困っていて、アドバイスが欲しいです。" },
        { "role": "assistant", "content": "どんなプロジェクトですか？" },
        { "role": "user", "content": "AIを使った自動化システムの開発です。" },
        { "role": "assistant", "content": "具体的にはどの部分で困っていますか？" },
        { "role": "user", "content": "データベースとの連携部分です。" },
        { "role": "assistant", "content": "データベースの種類は何ですか？" },
        { "role": "user", "content": "PostgreSQLです。" },
        { "role": "assistant", "content": "それなら、ORMを使うのがおすすめです。" },
        { "role": "user", "content": "ORMですか、例えば何が良いでしょうか？" },
        { "role": "assistant", "content": "SQLAlchemyなどが良いでしょう。" },
        { "role": "user", "content": "なるほど、試してみます。" },
        { "role": "assistant", "content": "うまくいくと良いですね。" },
        { "role": "user", "content": "他にも何かアドバイスはありますか？" },
        { "role": "assistant", "content": "テストをしっかり行うことが重要です。" },
        { "role": "user", "content": "分かりました、ありがとうございます。" },
        { "role": "assistant", "content": "どういたしまして、頑張ってください。" }
    ]

    new_mesgs = summarize_conversation( prompt_list, message_list, max_tokens=500, summary_tokens=200, keep_tokens=200, keep_num=5 )

    print(new_mesgs)

if __name__ == "__main__":

    test_summary()

