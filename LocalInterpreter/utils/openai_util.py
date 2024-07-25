
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

from .logger_util import ApiLog
from .JsonStreamParser import JsonStreamParser

import logging
logger = logging.getLogger('OpenAIutil')

OPENAI_DEFAULT_MODEL='gpt-4o-mini'

def to_openai_llm_model( model:str|None=None ) ->str:
    if not isinstance(model,str) or len(model)==0:
        return OPENAI_DEFAULT_MODEL
    return model

def get_max_input_token( model:str|None ) ->int:
    model = to_openai_llm_model(model)
    if model.startswith('gpt-4'):
        return 128*1024
    if model.startswith('gpt-3.5'):
        return 16*1024

def setup_openai_api():
    """
    OpenAI APIをセットアップする関数です。
    .envファイルからAPIキーを読み込み、表示します。
    """
    dotenv_path = os.path.join(Path.home(), 'Documents', 'openai_api_key.txt')
    load_dotenv(dotenv_path)
    
    api_key = os.getenv("OPENAI_API_KEY")
    logger.info(f"OPENAI_API_KEY={api_key[:5]}***{api_key[-3:]}")

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

def count_token( text, model:str=None ) ->int:
    enc = tiktoken.encoding_for_model( to_openai_llm_model(model) )
    tokens = enc.encode(text)
    return len(tokens)

def count_message_token( m:dict, model:str=None ) ->int:
    return count_token( json.dumps(m,ensure_ascii=False), model=model )

def is_japanese_text( text:str ):
    # テキストが日本語かどうかを確認
    ret = all(ord(char) < 128 for char in text) == False
    return ret

def summarize_web_content( text:str, *, length:int=None, messages:list[dict]=None, model:str=None, debug=False ) ->str:
    logger.info(f"[SUMMARIZE] len:{len(text)}/{length} {text[:20]}")

    # テキストが日本語かどうかを確認
    is_japanese = is_japanese_text( text )
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

    return summarize_text( text, prompt=prompt, model=model )

def summarize_text( text:str, *, prompt:str, model:str=None):

    openai_llm_model = to_openai_llm_model(model)
    openai_timeout:Timeout = Timeout(180.0, connect=5.0, read=15.0)
    openai_max_retries=3

    request_messages = [
        { 'role':'user', 'content': prompt }
    ]
    for run in range(openai_max_retries):
        try:
            try:
                client:OpenAI = OpenAI(timeout=openai_timeout,max_retries=1)
                response = client.chat.completions.create(
                        messages=request_messages,
                        model=openai_llm_model,
                        temperature=0,
                )
                ApiLog.log( request_messages, response )
            except Exception as ex:
                ApiLog.log( request_messages, ex )
                raise ex
            summary = response.choices[0].message.content.strip()
            if len(summary)<len(text):
                return summary
            else:
                return text
        except APITimeoutError as ex:
            logger.error(f"[SUMMARIZE#{run}]ERROR OpenAI {ex.__class__.__name__} {ex}")
        except Exception as ex:
            logger.error(f"[SUMMARIZE#{run}]ERROR OpenAI {ex.__class__.__name__} {ex}")
            pass

    return text

KEY_SUMMARY_START="---Start conversation summary:"
KEY_SUMMARY_END="---End of conversation summary---"

def summarize_conversation( prompts:list[dict], messages:list[dict], *, max_tokens:int=8000, summary_tokens:int=2000, keep_tokens:int=1000, keep_num:int=10, model:str=None ):

    model = to_openai_llm_model(model)

    n_prompt = 0
    for m in prompts:
        n_prompt += count_message_token(m,model=model)

    old_hists:list[dict] = [ m for m in messages ]
    new_hists:list[dict] = []

    # 直近の会話
    n_keep = 0
    while len(old_hists)>0:
        tk = count_message_token( old_hists[-1], model=model )
        if len(new_hists)>=keep_num and (n_keep+tk)>keep_tokens:
            break
        m = old_hists.pop()
        n_keep += tk
        new_hists.insert(0,m)

    # 余裕分の会話
    target = max_tokens - n_prompt - summary_tokens - n_keep
    n_hists = 0
    while len(old_hists)>0:
        tk = count_message_token( old_hists[-1],model=model )
        if (n_hists+tk)>target:
            break
        m = old_hists.pop()
        n_hists += tk
        new_hists.insert(0,m)

    # tool_callが対応しない箇所を削除
    call_list={} # 呼び出されたid
    for m in new_hists:
        x=m.get("tool_calls",[])
        if x:
            logger.info(f"[summarize] tool_calls {x}")
            for t in x:
                cid = t.get("id")
                if cid:
                    logger.info(f"[summarize] cid {cid}")
                    call_list[cid]=1
    for i in range( len(new_hists)-1,-1,-1):
        m = new_hists[i]
        xid = m.get("tool_call_id") # 実行結果のid
        if xid:
            if call_list.get(xid) is None:
                logger.info(f"[summarize] {xid} remove ")
                new_hists.pop(i)
            else:
                logger.info(f"[summarize] {xid} keep ")

    if not old_hists:
        return new_hists
    
    # 残りを要約する
    mesg = []
    for m in old_hists:
        role = m.get('role')
        content = m.get('content')
        content = content.replace(KEY_SUMMARY_START,"").replace(KEY_SUMMARY_END,"").strip() if isinstance(content,str) else ''
        if not content or ( role != 'user' and role != 'assistant' ):
            continue
        if KEY_SUMMARY_START in content:
            mesg.append( f"{KEY_SUMMARY_START}\n{content}\n{KEY_SUMMARY_END}" )
        else:
            mesg.append( f"{role}:\n{content}")
    if not mesg:
        return new_hists

    text:str = "\n\n".join(mesg)

    target = summary_tokens-len(KEY_SUMMARY_START+KEY_SUMMARY_END)
    target2 = int( target*0.8 )
    if target2<=1:
        return new_hists

    for i in range(2):
        tk = count_message_token( text, model=model)
        if tk < target:
            break

        x_pr:str = f"""# Prompt
        あなたは小説の編集者である。以下の手順で要約せよ。
        1. 以下の会話から、人物の考えや感情、意味や関係性の要点だけを、Assistantの視点で、簡潔に{target2}文字以内で要約。まだ出力しない。
        2. 要約が、{target2}文字以内であるか検証し、{target2}文字以内になるように修正する
        3. 要約を出力する。
        
        # 会話内容:
        {text}

        # 要約出力:
        {KEY_SUMMARY_START}"""
        x_pr:str = f"""# Prompt
        あなたは小説の編集者である。以下の手順で要約せよ。
        1. 以下の会話から、人物の考えや感情、意味や関係性の要点だけを、Assistantの視点で、簡潔に{target2}文字以内で要約。まだ出力しない。
        2. 要約が、{target2}文字以内であるか検証し、{target2}文字以内になるように修正する
        3. 要約を出力する。
        
        # 会話内容:
        {text}

        # 要約出力:
        {KEY_SUMMARY_START}"""

        sum = summarize_text( text, prompt=x_pr, model=model )
        text = sum.replace(KEY_SUMMARY_START,"").replace(KEY_SUMMARY_END,"").strip() if isinstance(sum,str) else ''

    if tk>target:
        over = tk-target
        text = text[over:]

    new_hists.insert( 0, {'role': 'assistant', 'content': KEY_SUMMARY_START+"\n"+ text+"\n"+KEY_SUMMARY_END })

    return new_hists

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
            if isinstance(savefile,list):
                self.savebuffer = savefile
            elif savefile:
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
                                logger.error(f"ERROR: buffer: {path} {new_value}")
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
            logger.exception('stream parser error')
            raise ex

    def get_value(self, path):
        if self.json_parser:
            data = trim_json( self.json_parser.get() )
            if data:
                return data.get(path)
        return None

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
