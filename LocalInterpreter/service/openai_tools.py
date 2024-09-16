
import traceback
import json

from openai.types.completion_usage import CompletionUsage
from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall, Function
from openai.types.shared_params.function_definition import FunctionDefinition
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall, ChoiceDeltaToolCallFunction

from LocalInterpreter.service.schema import ServiceSchema, BaseService
from LocalInterpreter.service.local_service import QuartServiceBase
#from LocalInterpreter.service.web_service import WebGetService, WebSearchService, WebTrendService

import logging
logger = logging.getLogger('OpenAIsrv')

class OpenAITools(ServiceSchema):

    def __init__(self):
        super().__init__()

    def add_service(self,service:QuartServiceBase):
        ServiceSchema.add_service(self,f"x{len(self.path_dict)}",service)

    def call( self, fname, args, *, messages:list[dict]|None=None, usage:CompletionUsage|None=None ) ->tuple[dict,int]:
        for path,method_dict in self.path_dict.items():
            for method,service in method_dict.items():
                if isinstance(service,QuartServiceBase):
                    if fname==service.name:
                        ret,code = service.call(args, messages=messages, usage=usage )
                        return ret,code
        raise ValueError(f"not found tool {fname}")

    def get_service( self, fname:str ) ->QuartServiceBase|None:
        for path,method_dict in self.path_dict.items():
            for method,service in method_dict.items():
                if isinstance(service,QuartServiceBase):
                    if fname==service.name or fname==service.get_func_name():
                        return service

    def tool_run( self, call_id, tool_name, tool_args, *, messages:list[dict]|None=None, usage:CompletionUsage|None=None ) ->dict:
        logger.info(f"[TOOL_RUN]{call_id} {tool_name} {tool_args}")
        service:QuartServiceBase|None = self.get_service( tool_name )
        if not service:
            return {'role':'tool', 'tool_call_id':call_id, 'content':f"ERROR: tool not found."}
        try:
            args = json.loads( tool_args )
        except Exception as ex:
            return {'role':'tool', 'tool_call_id':call_id, 'content':f"ERROR: Can not parse arguments: {ex}"}
        try:
            res_data,code = service.call( args, messages=messages, usage=usage )
            if isinstance(res_data,dict):
                # dictならそのままテキスト化
                res_text = json.dumps( res_data, ensure_ascii=True )
            elif isinstance(res_data,str):
                if code != 200 and 'error' not in res_data[:10].lower():
                    # strで200でなければエラーなので、Errorがなければ付ける
                    res_text = f"Error: {res_data}"
                else:
                    res_text = res_data
            else:
                # 想定外なので、とりあえずブランク
                res_text = ''
            return {'role':'tool', 'tool_call_id':call_id, 'content':res_text }
        except Exception as ex:
            logger.exception('error on tool')
            return {'role':'tool', 'tool_call_id':call_id, 'content':f"ERROR: {ex.__class__.__name__}: {ex}"}
        
    def tool_call( self, chatcomp:ChatCompletion, *, messages:list[dict]|None=None, usage:CompletionUsage|None=None ) ->list[dict]:
        if not isinstance(chatcomp,ChatCompletion):
            raise ValueError('invalid arguments')
        result=[]
        tools=[]
        try:
            tool_calls = chatcomp.choices[0].message.tool_calls
            if not tool_calls:
                return []
            tool:ChatCompletionMessageToolCall
            for tool in tool_calls:
                fid:str = tool.id
                fname:str = ''
                err:str = f"tool not found."
                try:
                    func:Function = tool.function
                    fname:str = func.name
                    err:str = f"tool not found: '{fname}'"
                    args:dict = json.loads(func.arguments)
                    service:QuartServiceBase|None = self.get_service( fname )
                    if service:
                        logger.info(f"id:{fid} Func:{service.name} args:{args}")
                        tools.append( (fid, service, args) )
                        continue
                except:
                    err = f"tool not found: '{fname}'"
                result.append( {'role':'tool', 'tool_call_id':fid, 'content':err} )
        except:
            pass

        for fid, service, args in tools:
            ret = service.call(args, messages=messages, usage=usage)
            result.append( {'role':'tool', 'tool_call_id':fid, 'content':ret} )
        return result

    def tool_chunk( self, chunk:ChoiceDeltaToolCall ):
        fid = chunk.id
        f:ChoiceDeltaToolCallFunction = chunk.function
        fname = f.name
        args:dict = json.loads(f.arguments) if f.arguments else {}
        service:QuartServiceBase = self.get_service( fname )
        ret,code = service.call( args )
        return {'role':'tool', 'tool_call_id':fid, 'content':ret}

# def test_to_json():
#     top:OpenAITools = OpenAITools()
#     x:WebSearchService = WebSearchService()
#     y:WebGetService = WebGetService()
#     z:WebTrendService = WebTrendService()
#     top.add_service( x )
#     top.add_service( y )
#     top.add_service( z )
#     j:dict = top.to_tools()
#     xx:str = json.dumps(j, ensure_ascii=False, indent=2 )
#     logger.info(xx)

# if __name__ == "__main__":
#     test_to_json()
