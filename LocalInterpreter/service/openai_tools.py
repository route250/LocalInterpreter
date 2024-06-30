
import traceback
import json

from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion import ChatCompletion, Choice
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall, Function
from openai.types.shared_params.function_definition import FunctionDefinition
from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall, ChoiceDeltaToolCallFunction

from LocalInterpreter.service.schema import ServiceSchema, BaseService
from LocalInterpreter.service.local_service import QuartServiceBase
from LocalInterpreter.service.web_service import WebGetService, WebSearchService, WebTrendService

class OpenAITools(ServiceSchema):

    def __init__(self):
        super().__init__()

    def add_service(self,service:QuartServiceBase):
        ServiceSchema.add_service(self,f"x{len(self.path_dict)}",service)

    def call( self, fname, args ):
        for path,method_dict in self.path_dict.items():
            service:QuartServiceBase
            for method,service in method_dict.items():
                if fname==service.name:
                    ret:str = service.call(args)
                    return ret

    def get_service( self, fname:str ) ->QuartServiceBase:
        for path,method_dict in self.path_dict.items():
            service:QuartServiceBase
            for method,service in method_dict.items():
                if fname==service.name or fname==service.get_func_name():
                    return service

    def tool_run( self, call_id, tool_name, tool_args ):
        print(f"[TOOL_RUN]{call_id} {tool_name} {tool_args}")
        service = self.get_service( tool_name )
        if not service:
            return {'role':'tool', 'tool_call_id':call_id, 'content':f"ERROR: tool not found."}
        try:
            args = json.loads( tool_args )
        except Exception as ex:
            return {'role':'tool', 'tool_call_id':call_id, 'content':f"ERROR: Can not parse arguments: {ex}"}
        try:
            ret = service.call( args )
            return {'role':'tool', 'tool_call_id':call_id, 'content':ret }
        except Exception as ex:
            traceback.print_exc()
            return {'role':'tool', 'tool_call_id':call_id, 'content':f"ERROR: {ex.__class__.__name__}: {ex}"}
        
    def tool_call( self, chatcomp:ChatCompletion ) ->list[dict]:
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
                fname:str = None
                args:dict = None
                err:str = f"tool not found."
                try:
                    func:Function = tool.function
                    fname:str = func.name
                    err:str = f"tool not found: '{fname}'"
                    args:dict = json.loads(func.arguments)
                    service:QuartServiceBase = self.get_service( fname )
                    if service:
                        print(f"id:{fid} Func:{service.name} args:{args}")
                        tools.append( (fid, service, args) )
                        continue
                except:
                    err = f"tool not found: '{fname}'"
                result.append( {'role':'tool', 'tool_call_id':fid, 'content':err} )
        except:
            pass

        for fid, service, args in tools:
            ret = service.call(args)
            result.append( {'role':'tool', 'tool_call_id':fid, 'content':ret} )
        return result

    def tool_chunk( self, chunk:ChoiceDeltaToolCall ):
        fid = chunk.id
        f:ChoiceDeltaToolCallFunction = chunk.function
        fname = f.name
        args:dict = json.loads(f.arguments) if f.arguments else {}
        service:QuartServiceBase = self.get_service( fname )
        ret = service.call( args )
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
#     print(xx)

# if __name__ == "__main__":
#     test_to_json()
