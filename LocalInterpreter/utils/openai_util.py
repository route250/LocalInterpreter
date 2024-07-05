
import sys,os
import re,traceback
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError, APITimeoutError
from httpx import Timeout

from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall,ChatCompletionChunk
from openai import Stream
import tiktoken

from .JsonStreamParser import JsonStreamParser

def setup_openai_api():
    """
    OpenAI APIをセットアップする関数です。
    .envファイルからAPIキーを読み込み、表示します。
    """
    dotenv_path = os.path.join(Path.home(), 'Documents', 'openai_api_key.txt')
    load_dotenv(dotenv_path)
    
    api_key = os.getenv("OPENAI_API_KEY")
    print(f"OPENAI_API_KEY={api_key[:5]}***{api_key[-3:]}")

def trim_json( data ):
    if isinstance( data, (list,tuple) ):
        # 新しいリストまたはタプルを作成し、再帰的に処理した要素を追加
        new_data = [trim_json(item) for item in data if item]
        return type(data)( [ item for item in new_data if item ] )
    elif isinstance( data, dict ):
        # 新しい辞書を作成し、再帰的に処理したキーと値を追加
        new_data = {}
        for key, value in data.items():
            trimmed_value = trim_json(value)
            if trimmed_value:
                new_data[key] = trimmed_value
        return new_data
    else:
        # データがリスト、タプル、辞書でない場合はそのまま返す
        return data

def count_token( text, model:str='gpt-3.5' ) ->int:
    enc = tiktoken.encoding_for_model( model )
    tokens = enc.encode(text)
    return len(tokens)

def summarize( text:str, *, length:int=None, debug=False ) ->str:
    print(f"[SUMMARIZE] len:{len(text)}/{length} {text[:20]}")
    openai_llm_model = 'gpt-3.5-turbo'
    openai_timeout:Timeout = Timeout(180.0, connect=5.0, read=15.0)
    openai_max_retries=3

    # テキストが日本語かどうかを確認
    is_japanese = all(ord(char) < 128 for char in text) == False
    # プロンプトの設定
    if is_japanese:
        if isinstance(length,int) and length>0:
            prompt = f"以下のテキストから目次や広告などを除いて、{length}トークン程度の文章に書き直して下さい。:\n\n{text}\n\n要約:"
        else:
            prompt = f"以下のテキストから目次や広告などを除いて、短い文章に書き直して下さい。:\n\n{text}\n\n要約:"
        
    else:
        if isinstance(length,int) and length>0:
            prompt = f"Summarize the following text about {length} tokens:\n\n{text}\n\nSummary:"
        else:
            prompt = f"Summarize the following text:\n\n{text}\n\nSummary:"

    request_messages = [
        { 'role':'user', 'content': prompt }
    ]
    for run in range(openai_max_retries):
        try:
            client:OpenAI = OpenAI(timeout=openai_timeout,max_retries=1)
            response = client.chat.completions.create(
                    messages=request_messages,
                    model=openai_llm_model,
                    temperature=0,
            )
            summary = response.choices[0].message.content.strip()
            if len(summary)<len(text):
                return summary
            else:
                return text
        except APITimeoutError as ex:
            print(f"[SUMMARIZE#{run}]ERROR OpenAI {ex.__class__.__name__} {ex}")
        except Exception as ex:
            print(f"[SUMMARIZE#{run}]ERROR OpenAI {ex.__class__.__name__} {ex}")
            pass

    return text


class OpenAI_stream_decorder:
    key_content:str = 'content'
    key_display:str = 'text_to_display'
    key_tts:str = 'text_to_speech'
    def __init__(self):
        # 区切り文字のリスト
        self.delimiters = ["。", "!", "！", "?", "？", "\n"]
        # 正規表現のパターンを作成
        self.pattern = '|'.join(map(re.escape, self.delimiters))
        self.stream_paths:dict[str,str] = {}
        self.json_mode:bool = False

    def add_stream_path(self, path:str ):
        if path:
            self.stream_paths[path] = ""
            self.json_mode = True

    def get_iter(self, stream:Stream=None,*,loadfile:str=None,savefile:str=None):
        return OpenAI_stream_iterator(parent=self,stream=stream,loadfile=loadfile,savefile=savefile)

class OpenAI_stream_iterator:
    def __init__(self,parent:OpenAI_stream_decorder,stream:Stream=None,*,loadfile:str=None,savefile:str=None):
        self.parent = parent
        self.savefile:str = None
        self.savebuffer:list[dict] = None
        if loadfile:
            self.loadfile = loadfile
            buffer = []
            with open(loadfile,'r') as fs:
                data:list[dict] = json.load(fs)
                for obj in data:
                    buffer.append( ChatCompletionChunk(**obj) )
            self.stream = iter(buffer)
        elif stream:
            self.stream = stream
            if savefile:
                self.savefile = savefile
                self.savebuffer = []
        else:
            raise ValueError("Either stream or loadfile must be provided")

        self.content:str = None
        self.buffer:str = None
        self.tools_call:list = []
        self.eof:bool = False
        self.json_buffers:dict[str,int] = {k:0 for k in parent.stream_paths.keys()}
        self.json_parser:JsonStreamParser = JsonStreamParser() if parent.json_mode else None
        self.created = None
        self.id = None
        self.model = None
        self.service_tier = None
        self.system_fingerprint = None
        self.usage = None
        self.dbg_content:str = ""

    def __iter__(self):
        return self._parse()

    def _split(self,text):
        # 最初に一致した部分を検索
        match = re.search(self.parent.pattern, text)
        if match:
            p = match.start()
            return text[:p+1], text[p+1:] 
        return "",text

    def _split2(self,flltext:str,ii:int):
        if not isinstance(flltext,str):
            return 0, ""
        text:str = flltext[ii:]
        # 最初に一致した部分を検索
        match = re.search(self.parent.pattern, text)
        if match:
            p = match.start()
            return ii+p+1, text[:p+1]
        else:
            return ii, ""

    def _parse(self):
        if self.eof:
            return
        try:
            in_content:int = 0
            content_buffer:str = ""
            in_tools:int = 0
            tool_idx = ""
            tool_id = ""
            tool_name = ""
            tool_args = ""

            while not self.eof:

                delta_content:str = None
                delta_tool_calls = None

                # get next chunk
                try:
                    chunk:ChatCompletionChunk = next( self.stream )
                    if isinstance(self.savebuffer,list):
                        self.savebuffer.append( chunk.to_dict() )
                    # get data from chunk
                    if chunk.created:
                        self.created = chunk.created
                    if chunk.id:
                        self.id = chunk.id
                    if chunk.model:
                        self.model = chunk.model
                    if chunk.service_tier:
                        self.service_tier = chunk.service_tier
                    if chunk.system_fingerprint:
                        chunk.system_fingerprint
                    if chunk.usage:
                        self.usage = chunk.usage
                    if len(chunk.choices)>0 and chunk.choices[0] is not None:
                        choice = chunk.choices[0]
                        if choice.finish_reason:
                            self.finish_reason = choice.finish_reason
                        if choice.delta is not None:
                            delta_content = choice.delta.content
                            delta_tool_calls = choice.delta.tool_calls
                except StopIteration:
                    self.eof = True
                    if self.savefile and self.savebuffer:
                        with open(self.savefile,'w') as stream:
                            json.dump( self.savebuffer, stream, ensure_ascii=False, indent=2 )
                # process content
                if in_content==1 or delta_content:
                    if delta_content:
                        in_content = 1
                        content_buffer += delta_content
                        self.dbg_content += delta_content
                        if self.content is None:
                            self.content = delta_content
                        else:
                            self.content += delta_content
                    else:
                        delta_content = ""
                        in_content = 2
                    
                    # json mode
                    if self.json_parser is not None:
                        for id, path, new_value in self.json_parser.put( delta_content, end=in_content==2 ):
                            if JsonStreamParser.ERR == id:
                                self.json_parser = None
                                print(f"ERROR: buffer: {path} {new_value}")
                                break
                            pos = self.json_buffers.get(path)
                            if isinstance(pos,int):
                                new_pos, delta = self._split2( new_value, pos )
                                if new_pos>pos:
                                    self.json_buffers[path] = new_pos
                                    yield ("", path, delta )

                    # plain text mode
                    if self.json_parser is None:
                        if in_content==1:
                            before, after = self._split(content_buffer)
                            content_buffer = after
                        else:
                            before = content_buffer
                            content_buffer = ""
                        if before:
                            yield ("", OpenAI_stream_decorder.key_content,before)
                #
                if in_tools==1 or delta_tool_calls:
                    if delta_tool_calls:
                        in_tools=1
                        for tc in delta_tool_calls:
                            if tool_idx != tc.index:
                                if tool_id:
                                    # flush tool
                                    ret = (tool_id,tool_name,tool_args)
                                    self.tools_call.append(ret)
                                    yield ret
                                # init tool
                                tool_idx = tc.index
                                tool_id = tool_name = tool_args = ""
                            if tc.id:
                                tool_id += tc.id
                            fnc = tc.function
                            if fnc:
                                if fnc.name:
                                    tool_name += fnc.name
                                if fnc.arguments:
                                    tool_args += fnc.arguments
                    else:
                        in_tools=2
                        if tool_id and tool_name:
                            # flush tool
                            ret = (tool_id,tool_name,tool_args)
                            self.tools_call.append(ret)
                            yield ret
                        tool_id = tool_name = tool_args = ""
        except Exception as ex:
            self.eof=True
            self.json_parser = None
            traceback.print_exc()
            raise ex

    def to_json(self):
        if self.json_parser:
            content_json = trim_json( self.json_parser.get() )
            content:str = json.dumps( content_json, ensure_ascii=False )
        else:
            content:str = self.content
        result_json:dict = { "role": "assistant", "content": content }
        if self.tools_call:
            a = []
            for tool_id, tool_name, tool_args in self.tools_call:
                a.append( {
                        "id": tool_id,
                        "function": { "name": tool_name, "arguments": tool_args, },
                        "type": "function"
                    } )
            result_json["tool_calls"] = a
        return result_json
