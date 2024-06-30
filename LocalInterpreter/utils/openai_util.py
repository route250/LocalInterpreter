
import sys,os
import re
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError, APITimeoutError
from httpx import Timeout

from openai.types.chat.chat_completion_chunk import ChoiceDeltaToolCall,ChatCompletionChunk
from openai import Stream
import tiktoken

def setup_openai_api():
    """
    OpenAI APIをセットアップする関数です。
    .envファイルからAPIキーを読み込み、表示します。
    """
    dotenv_path = os.path.join(Path.home(), 'Documents', 'openai_api_key.txt')
    load_dotenv(dotenv_path)
    
    api_key = os.getenv("OPENAI_API_KEY")
    print(f"OPENAI_API_KEY={api_key[:5]}***{api_key[-3:]}")

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
        self.mesg:dict = None
        self.created = None
        self.id = None
        self.model = None
        self.service_tier = None
        self.system_fingerprint = None
        self.usage = None
    def __iter__(self):
        return self
    def __next__(self):
        if not self.eof:
            try:
                while True:
                    chunk:ChatCompletionChunk = self.base.__next__()
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
                    choice = chunk.choices[0]
                    if choice.finish_reason:
                        self.finish_reason = choice.finish_reason
                    if choice.delta is None:
                        continue
                    delta = choice.delta
                    if delta.content:
                        delta_content:str = delta.content
                        print(delta_content, end="", flush=True) # the extra stuff at the end makes it so it updates as fast as possible, and doesn't create new lines for each chunk it gets
                        if self.mesg is None:
                            self.content = ""
                            self.buffer = ""
                        self.content += delta_content
                        self.buffer += delta_content
                        # 最初に一致した部分を検索
                        match = re.search(self.parent.pattern, self.buffer)
                        if match:
                            p = match.start()
                            seg = self.buffer[:p+1]
                            self.buffer = self.buffer[p+1:]
                            return ("", OpenAI_stream_decorder.key_content,seg)
                        continue

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
        if self.buffer:
            seg = self.buffer
            self.buffer = ""
            return seg
        raise StopIteration()

    def to_json(self):
        j:dict = { "role": "assistant", "content": self.content }
        if self.tools_call:
            a = []
            for tool_id, tool_name, tool_args in self.tools_call:
                a.append( {
                        "id": tool_id,
                        "function": { "name": tool_name, "arguments": tool_args, },
                        "type": "function"
                    } )
            j["tool_calls"] = a
        return j
