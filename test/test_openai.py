import sys
import os
sys.path.append(os.getcwd())

import json
from concurrent.futures import ThreadPoolExecutor,Future
import time

from openai import OpenAI
# from openai.types.chat import ChatCompletionToolParam
from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall, Function
# from openai.types.shared_params.function_definition import FunctionDefinition
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall,ChatCompletionChunk
from openai import Stream

# from LocalInterpreter.service.schema import ServiceSchema
from LocalInterpreter.service.web_service import WebGetService, WebSearchService, WebTrendService
from LocalInterpreter.service.openai_tools import OpenAITools
from LocalInterpreter.utils.openai_util import OPENAI_DEFAULT_MODEL, OpenAI_stream_decorder, OpenAI_stream_iterator

def test_tools_call():
    client:OpenAI = OpenAI()
    tool_list = [
        {
            "type": "function",
            "function": {
                "name": "get_trends",
                "description": "googleのトレンド検索キーワードを取得します",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "words": {
                            "type": "string",
                            "description": "関連キーワード",
                        }
                    },
                    "required": ["words"]
                }

            }
        },
    ]
    request_messages = []
    request_messages.append( { 'role':'system', 'content':'今日のトレンドは？' } )
    stream:ChatCompletion = client.chat.completions.create(
            messages=request_messages,
            model=OPENAI_DEFAULT_MODEL, max_tokens=1000,
            tools=tool_list,
    )
    j=stream.to_json(indent=2)
    print(j)
    choice:Choice = stream.choices[0]
    finish_resason = choice.finish_reason
    msg:ChatCompletionMessage = choice.message
    res_content = msg.content
    print( f"{res_content}" )
    if isinstance(msg.tool_calls,list):
        x:ChatCompletionMessageToolCall
        for x in msg.tool_calls:
            f:Function = x.function
            fname:str = f.name
            args:dict = json.loads(f.arguments)
            print(f"Func:{fname} {args}")
        pass

def test_to_func():
    top:OpenAITools = OpenAITools()
    x:WebSearchService = WebSearchService()
    y:WebGetService = WebGetService()
    z:WebTrendService = WebTrendService()
    top.add_service( x )
    top.add_service( y )
    top.add_service( z )

    client:OpenAI = OpenAI()
    tool_list = top.to_tools()
    # print( json.dumps( tool_list, ensure_ascii=False, indent=2))
    request_messages = []
    request_messages.append( { 'role':'system', 'content':'今日のトレンドは？' } )

    for ii in range(3):
        print("===REQUEST===")
        print( json.dumps( request_messages, ensure_ascii=False, indent=4 ))
        comp:ChatCompletion = client.chat.completions.create(
                messages=request_messages,
                model=OPENAI_DEFAULT_MODEL, max_tokens=1000,
                tools=tool_list, tool_choice="auto",
        )
        print("===REQSPONSE===")
        print(comp.to_json(indent=4))
        print("===")
        choice:Choice = comp.choices[0]
        finish_resason = choice.finish_reason
        msg:ChatCompletionMessage = choice.message
        request_messages.append( msg.to_dict() )
        res_content = msg.content
        print( f"{res_content}" )
        tool_res = top.tool_call( comp )
        if not tool_res:
            break
        for m in tool_res:
            request_messages.append(m)

def test_to_func_stream():
    top:OpenAITools = OpenAITools()
    x:WebSearchService = WebSearchService()
    y:WebGetService = WebGetService()
    z:WebTrendService = WebTrendService()
    top.add_service( x )
    top.add_service( y )
    top.add_service( z )

    thpool:ThreadPoolExecutor = None
    client:OpenAI = OpenAI()
    decorder:OpenAI_stream_decorder = OpenAI_stream_decorder()
    save_cnt:int = 0
    tool_list = top.to_tools()
    # print( json.dumps( tool_list, ensure_ascii=False, indent=2))
    request_messages = []
    request_messages.append( {
        'role':'system',
        'content':"""# Instruction
Please perform the following actions.
1. Write an overview of the specified tool in markdown text and output it in the JSON format below.
  { "content": "markdown text" }
2. After writing the overview, run all the tools at the same time to check if they work.
""" } )

    print("===REQUEST===")
    print( json.dumps( request_messages, ensure_ascii=False, indent=4 ))
    max_try:int = 3
    for ii in range(3):
        try:        
            stream:Stream = client.chat.completions.create(
                messages=request_messages,
                model=OPENAI_DEFAULT_MODEL, max_tokens=1000,
                tools=tool_list, tool_choice="auto", parallel_tool_calls=True,
                stream=True, stream_options={'include_usage':True},
                response_format={ "type": "json_object" },
            )
            break
        except Exception as ex:
            if ii+1==max_try:
                raise ex
        #openai.APIError: The server had an error processing your request. Sorry about that! You can retry your request, or contact us through our help center at help.openai.com if you keep seeing this error.
    try:
        print("===REQSPONSE===")
        futures:list[Future] = []
        save_cnt+=1
        savefile = f"./tmp/openai_stream_{save_cnt:04}.json"
        itr:OpenAI_stream_iterator = decorder.get_iter(stream,savefile=savefile)
        for tool_id, tool_name, tool_args in itr:
            if not tool_id:
                if OpenAI_stream_decorder.key_content == tool_name:
                    print(f"[CONTENT]{tool_args}")
            else:
                if thpool is None:
                    thpool = ThreadPoolExecutor( max_workers=1 )
                #print(chunk)
                # call_list.append(chunk)
                print(f"[TOOL_CALL] {tool_id} {tool_name} {tool_args}")
                futures.append( thpool.submit( top.tool_run, tool_id, tool_name, tool_args ) )
        print("===")
        request_messages.append(itr.to_json())
    except Exception as ex:
        print(f"ERROR: {ex}")
        futures = None
        raise ex
    finally:
        if futures:
            print("=== get result")
            for f in futures:
                try:
                    ret = f.result()
                    print(ret)
                    request_messages.append(ret)
                except Exception as ex:
                    print( f"ERROR: {ex.__class__.__name__} {ex}" )
        if thpool is not None:
            thpool.shutdown(wait=False)
        print("===")

def online_test():
    from LocalInterpreter.utils.openai_util import setup_openai_api
    setup_openai_api()
    from dotenv import load_dotenv, find_dotenv
    load_dotenv( find_dotenv('.env_google') )
    test_to_func_stream()

def offline_test():
    TEST_CASE_LIST = [
        [ "testData/openai_stream_0001.json", "" ],
        [ "testData/openai_stream_0002.json", "" ],
        [ "testData/openai_stream_0003.json", "content" ],
    ]
    for loadfile, path in TEST_CASE_LIST:
        if not os.path.exists(loadfile):
            break
        print(f"")
        print(f"DATA:{loadfile}")
        decorder:OpenAI_stream_decorder = OpenAI_stream_decorder()
        if path:
            decorder.add_stream_path( path )
        itr:OpenAI_stream_iterator = decorder.get_iter(loadfile=loadfile)
        for tool_id, tool_name, tool_args in itr:
            text:str = json.dumps(tool_args,ensure_ascii=False)
            print( f"{tool_id} {tool_name} {text}" )

if __name__ == "__main__":
    offline_test()

    # online_test()
