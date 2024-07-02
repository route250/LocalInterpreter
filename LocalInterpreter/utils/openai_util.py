
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

    def get_iter(self, stream:Stream):
        return OpenAI_stream_iterator(parent=self,stream=stream)

class OpenAI_stream_iterator:
    def __init__(self,parent:OpenAI_stream_decorder,stream:Stream):
        self.parent = parent
        self.base = stream
        self.content:str = None
        self.buffer:str = None
        self.tools_call:list = []
        self.eof:bool = False
        self.tool_idx:int = 0
        self.tool_id:str = ""
        self.tool_name:str = ""
        self.tool_args:str = ""
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
        return self

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

    def __next__(self):
        if not self.eof:
            try:
                while True:
                    chunk:ChatCompletionChunk = self.base.__next__()
                    #
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
                    if len(chunk.choices)==0:
                        continue
                    #
                    choice = chunk.choices[0]
                    if choice.finish_reason:
                        self.finish_reason = choice.finish_reason
                    if choice.delta is None:
                        continue
                    #
                    delta = choice.delta
                    if delta.content:
                        delta_content:str = delta.content
                        # print(delta_content, end="", flush=True) # the extra stuff at the end makes it so it updates as fast as possible, and doesn't create new lines for each chunk it gets
                        self.dbg_content += delta_content
                        if self.content is None:
                            self.content = ""
                            self.buffer = ""
                        self.content += delta_content
                        self.buffer += delta_content

                        try:
                            if self.json_parser:
                                self.json_parser.put(delta_content)
                                for path,pos in self.json_buffers.items():
                                    new_value = self.json_parser.get_value(path)
                                    new_pos, delta = self._split2( new_value, pos )
                                    if new_pos>pos:
                                        self.json_buffers[path] = new_pos
                                        return ("", path, delta )
                                continue
                        except Exception as ex:
                            # traceback.print_exc()
                            print(f"ERROR: buffer: {self.buffer}")
                            print(f"ERROR: {ex}")
                            self.json_parser = None

                        # 最初に一致した部分を検索
                        a,b = self._split(self.buffer)
                        if a:
                            self.buffer = b
                            return ("", OpenAI_stream_decorder.key_content,a)
                        continue
                    #
                    if delta.tool_calls:
                        ret = None
                        for tc in delta.tool_calls:
                            if self.tool_idx != tc.index:
                                if self.tool_id:
                                    ret = (self.tool_id,self.tool_name,self.tool_args)
                                    self.tools_call.append(ret)
                                self.tool_idx = tc.index
                                self.tool_id = ""
                                self.tool_name = ""
                                self.tool_args = ""
                            f = tc.function
                            if tc.id:
                                self.tool_id += tc.id
                            if f.name:
                                self.tool_name += f.name
                            if f.arguments:
                                self.tool_args += f.arguments
                            # print(tc)
                        if ret:
                            return ret
            except StopIteration:
                self.eof=True
        #----------
        if self.tool_id:
            ret = (self.tool_id,self.tool_name,self.tool_args)
            self.tools_call.append(ret)
            self.tool_id = ""
            return ret
        if self.json_parser:
            for path,pos in self.json_buffers.items():
                new_value = self.json_parser.get_value(path)
                new_pos, delta = self._split2( new_value, pos )
                if new_pos>pos:
                    self.json_buffers[path] = new_pos
                    return ("", path, delta )
        elif self.buffer:
            seg = self.buffer
            self.buffer = ""
            return ("", OpenAI_stream_decorder.key_content,seg)
        raise StopIteration()

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
