import sys
import os,shutil,platform
import re
import json
import asyncio
from asyncio import AbstractEventLoop as EvLoop
from asyncio.subprocess import Process, create_subprocess_exec, create_subprocess_shell, PIPE, DEVNULL
from concurrent.futures import ThreadPoolExecutor
from asyncio import Condition
import time
from uuid import UUID, uuid4
import tempfile
import glob

from LocalInterpreter.utils import web

import logging
logger = logging.getLogger('LocalCode')

TIMEFILE='.lastupdatetime'


def get_linux_info():
    # /etc/os-release から情報を取得
    try:
        with open("/etc/os-release") as f:
            info = {}
            for line in f:
                line = line.strip()
                if line:
                    key, value = line.split("=", 1)
                    info[key] = value.strip('"')
            os_name = info.get("NAME", "Unknown")
            os_version = info.get("VERSION_ID")
            if os_version is None:
                os_version = info.get("VERSION", "Unknown")
            return f"{os_name} {os_version}"
    except FileNotFoundError:
        return "Linux (info not available)"

def get_os_info():
    os_type = platform.system()

    if os_type == 'Linux':
        os_info = get_linux_info()
    elif os_type == 'Darwin':
        os_info = f"macOS {platform.mac_ver()[0]}"
    elif os_type == 'Windows':
        os_info = f"Windows {platform.win32_ver()[0]}"
    else:
        os_info = f"Unknown OS: {os_type}"

    return os_info

def get_python_info():
    version = platform.python_version()
    cpu = platform.processor()
    return f"Python {version} {cpu}"

def escape_control_chars(text):
    # 制御文字をエスケープ
    return re.sub(r'[\n\r\t]', lambda x: repr(x.group(0)).strip("'"), text)

async def arun( cmd: list[str], cwd:str|None=None ):
    proc:Process = await create_subprocess_exec( *cmd, stdout=PIPE, stderr=DEVNULL, cwd=cwd )
    stdout,stderr = await proc.communicate()
    retcode:int = proc.returncode if proc.returncode else 999
    return retcode, stdout.decode(), stderr.decode()

def write_to_textfile( filepath:str, content:list[str], mode:int|None=None ):
    if isinstance(content,list):
        with open( filepath, "w") as stream:
            for line in content:
                stream.write( line )
                stream.write( '\n' )
        if isinstance(mode,int):
            os.chmod(filepath,mode)

def read_time( dirpath:str ):
    try:
        filepath:str = os.path.join( dirpath, TIMEFILE)
        if os.path.exists(filepath):
            with open( filepath, mode='r' ) as stream:
                line:str = stream.readline()
            tm:float = float(line)
            return tm
    except:
        return None

def write_time( dirpath:str, tm:float|None=None ) ->float|None:
    ret:float|None = None
    try:
        if not isinstance(tm,float):
            tm = time.time()
        filepath:str = os.path.join( dirpath, TIMEFILE)
        with open( filepath, mode='w' ) as stream:
            stream.write( f"{tm}\n")
        ret = tm
    except:
        pass
    return ret

SCR_BUILD = 'build.sh'
SCR_SART = 'start.sh'
SCR_CLEAN = 'clean.sh'
script_map:dict = {
    SCR_BUILD: [ "#!/bin/bash",
            "set -ue",
            "exec 2>&1",
            "if [ ! -x .venv/bin/activate ]; then",
            "    python3 -m venv .venv",
            "fi",
            "source .venv/bin/activate",
            "python3 -m pip install -U pip setuptools",
        ],
    SCR_SART: [ "#!/bin/bash",
            "set -ue",
            "exec 2>&1",
            "source ../.venv/bin/activate",
            "exec python3 -q -u -m code",
        ],
}

class CodeRepo:
    def __init__(self, parent:str ):
        if not os.path.isdir( parent ):
            raise ValueError( f"parent dir {parent} is not directory")
        self.lock:Condition = Condition()
        self.loop:EvLoop = None
        self.pool:ThreadPoolExecutor = ThreadPoolExecutor( max_workers=1 )
        self.word_dir_top = os.path.abspath(parent)
        self._flg_setup:bool = False
        self.max_session:int = 30
        self.timer_inverval:float = 10
        self.session_live_sec:float = 5.0*60.0
        self.session_delete_sec:float = 60.0 * 60.0
        self.session_list:dict[str,CodeSession] = {}

    def _th_setup_scripts(self):
        logger.info(f"[Repo]setup scripts {self.word_dir_top}")
        for name,content in script_map.items():
            scrpath = os.path.join( self.word_dir_top, name)
            write_to_textfile( scrpath, content, 0o744 )

    def _th_get_script(self, name ):
        if not os.path.isdir( self.word_dir_top ):
            raise ValueError( f"parent dir {self.word_dir_top} is not directory")
        content:list[str]|None = script_map.get(name)
        if not isinstance(content,list):
            raise ValueError( f"script {name} is not defined")
        filepath = os.path.join( self.word_dir_top, name)
        if not os.path.exists( filepath ):
            raise ValueError( f"script {name} is not defined")
        return filepath

    async def get_script(self, name ):
        loop = asyncio.get_running_loop()
        filepath:str = await loop.run_in_executor( self.pool, self._th_get_script, name )
        return filepath

    async def get_start_script(self):
        return await self.get_script(SCR_SART)

    def _th_reload_session(self):
        for dirpath in glob.glob( os.path.join(self.word_dir_top,'*')):
            tm:float|None = read_time(dirpath)
            if isinstance(tm,float) and tm>0:
                logger.info(f"[Repo]reload {dirpath}")
                sessionId:str = os.path.basename(dirpath)
                session:CodeSession = CodeSession( self, sessionId, dirpath, tm )
                self.session_list[sessionId] = session

    async def _timer(self):
        while True:
            await asyncio.sleep(self.timer_inverval)
            dellist:list[CodeSession] = []
            async with self.lock:
                logger.debug( "[Repo] timer ")
                for sessionId,session in self.session_list.items():
                    t = time.time() - session.lasttime
                    if t>self.session_live_sec:
                        await session.stop()
                        if t>self.session_delete_sec:
                            dellist.append( session )
                for session in dellist:
                    del self.session_list[session.sessionId]
            for session in dellist:
                await session.cleanup()

    async def setup(self):
        async with self.lock:
            if self._flg_setup:
                return
            self._flg_setup = True
            # 処理用スクリプト作成
            self.loop = loop = asyncio.get_running_loop()
            await loop.run_in_executor( self.pool, self._th_setup_scripts )
            # python仮想環境を構築
            scrpath:str = await self.get_script( SCR_BUILD )
            logger.debug(f"[Repo]exec {scrpath}")
            proc:Process = await create_subprocess_exec( scrpath, stdout=PIPE, stderr=DEVNULL, cwd=self.word_dir_top )
            stdout,stderr = await proc.communicate()
            code:int = proc.returncode if proc.returncode else 999
            logger.debug(f"{stdout.decode()}")
            logger.debug(f"exit:{code}")
            # セッションディレクトリをリロード
            await loop.run_in_executor( self.pool, self._th_reload_session )
            # タイマー開始
            self._timer_task = asyncio.create_task( self._timer())

    def _th_build_new_directory(self):
        if not os.path.isdir( self.word_dir_top ):
            raise ValueError( f"{self.word_dir_top} is not directory")
        uniq:str = uuid4().hex
        cwd = os.path.join( self.word_dir_top, uniq )
        os.makedirs( cwd, exist_ok=False )
        return (uniq,cwd)

    def get_event_loop(self,sessionId:str|None) ->EvLoop|None:
        # session:CodeSession|None = self.session_list.get(sessionId) if sessionId else None
        return self.loop # if session else None

    async def get_session(self,sessionId:str|None=None):
        await self.setup()
        async with self.lock:
            # 既存にあるか？
            session:CodeSession|None = self.session_list.get(sessionId) if sessionId else None
            if session is None or not isinstance(session,CodeSession):
                # 無いから新規作成
                loop = asyncio.get_running_loop()
                new_id, cwd = await loop.run_in_executor( self.pool, self._th_build_new_directory )
                logger.info(f"[Repo]new session {new_id} {cwd}")
                session = CodeSession( self, new_id, cwd )
                self.session_list[new_id] = session
            await session.start()
            return session

    async def run_in_executor(self, func, *args ):
        return await self.loop.run_in_executor( self.pool, func, *args )

class CodeSession:
    def __init__(self, parent:CodeRepo, sessionId:str, wd:str, tm:float|None=None ):
        if not os.path.isdir( wd ):
            raise ValueError( f"parent dir {wd} is not directory")
        self.lock:Condition = Condition()
        self.parent:CodeRepo = parent
        self.sessionId:str = sessionId
        self.cwd:str = wd
        self.process:Process|None = None
        self.ps1 = ">>>"+self.sessionId+">>>"
        self.ps2 = "..."+self.sessionId+"..."
        self.lasttime:float = tm if isinstance(tm,float) else time.time()

    async def start(self):
        if asyncio.get_running_loop() == self.parent.loop:
            await self._th_start()
        else:
            await self.parent.run_in_executor( self._th_start )

    async def _th_start(self):
        if not os.path.isdir( self.cwd ):
            raise ValueError( f"cwd {self.cwd} is not directory")
        self.lasttime:float = time.time()
        async with self.lock:
            if isinstance(self.process,Process):
                return

            logger.info(f"[Session:{self.sessionId}] start")
            scrpath:str = await self.parent.get_start_script()
            try:
                self.process = await create_subprocess_exec( scrpath, stdin=PIPE, stdout=PIPE, stderr=DEVNULL, cwd=self.cwd)
                await self.send_command( "import sys,os,json" )
                await self.send_command( f"sys.ps2='\\n{self.ps2}\\n'" )
                await self.send_command( f"sys.ps1='\\n{self.ps1}\\n'" )
                out = await self.get_output()
                logger.debug(f"[OUT]{out}")
                self.lasttime:float = time.time()
            except:
                await self.stop()

    def th_send_command(self,command:str):
        # コマンドを送信
        self.lasttime:float = time.time()
        if self.process:
            self.process.stdin.write(command.encode())
            self.process.stdin.write('\n'.encode())

    async def send_command(self,command:str):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor( self.parent.pool, self.th_send_command, command )

    async def get_output(self) ->str:
        self.lasttime:float = time.time()
        if self.process:
            if asyncio.get_running_loop()==self.parent.loop:
                data = await self._th_get_outputs()
            else:
                data = await self.parent.run_in_executor( self._th_get_outputs )
            return data
        else:
            return ''

    async def _th_get_outputs(self) ->str:
        # 結果を取得
        stdout = []
        while True:
            self.lasttime:float = time.time()
            if self.process.stdout.at_eof():
                break
            data:bytes =  await self.process.stdout.readline()
            line = data.decode()
            self.lasttime:float = time.time()
            logger.debug(f"[dbg]{escape_control_chars(line)}")
            sline=line.strip()
            if sline == self.ps2:
                line='...'
                self.process.stdin.flush()
            elif sline == self.ps1:
                if stdout[-1]=='\n':
                    stdout.pop()
                break
            stdout.append(line)
        return ''.join(stdout)

    async def command(self, command ) ->str:
        if command and '\n' in command:
            cmd = json.dumps(command,ensure_ascii=False)
            command = f"exec({cmd})"
        await self.send_command( command )
        out = await self.get_output()
        return out

    async def download_from_url(self, url:str ) ->tuple[str|None,str]:
        loop = asyncio.get_running_loop()
        filename, mesg = await loop.run_in_executor( self.parent.pool, web.download_from_url, url, self.cwd  )
        return filename, mesg

    @staticmethod
    def _th_stop_1(process:Process):
        try:
            process.stdin.write('exit()\n'.encode())
        except:
            pass
        time.sleep(0.2)
        try:
            process.terminate()
        except:
            pass

    async def stop(self):
        async with self.lock:
            process = self.process
            self.process = None
        # プロセスを終了
        if process is not None:
            logger.info(f"[Session:{self.sessionId}] stop")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor( self.parent.pool, self._th_stop_1, process )

    async def cleanup(self):
        await self.stop()
        if os.path.isdir( self.cwd ):
            logger.info(f"[Session:{self.sessionId}] cleanup")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor( self.parent.pool, shutil.rmtree, self.cwd )
