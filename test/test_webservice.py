import sys,os
import logging
sys.path.append(os.getcwd())

from openai.types.chat import ChatCompletionMessageParam, ChatCompletionToolParam

from openai.types.chat.chat_completion_tool_message_param import ChatCompletionToolMessageParam
from openai.types.chat.chat_completion_user_message_param import ChatCompletionUserMessageParam
from openai.types.chat.chat_completion_system_message_param import ChatCompletionSystemMessageParam
from openai.types.chat.chat_completion_function_message_param import ChatCompletionFunctionMessageParam
from openai.types.chat.chat_completion_assistant_message_param import ChatCompletionAssistantMessageParam

from LocalInterpreter.service.local_service import QuartServerBase, QuartServiceBase
from LocalInterpreter.service.python_service import PythonService
from LocalInterpreter.service.web_service import WebSearchService, WebGetService, WebTrendService


def test_service():

    messages:list[ChatCompletionMessageParam] = [
        ChatCompletionUserMessageParam( role='user', content='あした神戸にいくんだが。' ),
        ChatCompletionAssistantMessageParam( role='assistant', content='ああ、神戸か。いいなぁ、ブラザー。神戸はおしゃれなところが多いし、美味しいものもたくさんあるだろう。何しに行くわけ？' ),
        ChatCompletionUserMessageParam( role='user', content='天気どうだろうか？' )
    ]
    args = {
        "keyword":"三宮 天気予報 2024年8月13日"
    }

    webg:WebSearchService = WebSearchService()
    webg.call( args, messages=messages,debug=True )

if __name__ == "__main__":
    test_service()