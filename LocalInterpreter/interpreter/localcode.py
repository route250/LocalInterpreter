import sys
import os,shutil
import re
import asyncio
from asyncio.subprocess import Process, create_subprocess_exec, create_subprocess_shell, PIPE, DEVNULL
from concurrent.futures import ThreadPoolExecutor
from asyncio import Condition
import time
from uuid import UUID, uuid4
import tempfile
import glob

TIMEFILE='.lastupdatetime'

def escape_control_chars(text):
    # 制御文字をエスケープ
    return re.sub(r'[\n\r\t]', lambda x: repr(x.group(0)).strip("'"), text)

async def arun( cmd: list[str]=None, cwd:str=None ):
    proc:Process = await create_subprocess_exec( *cmd, stdout=PIPE, stderr=DEVNULL, cwd=cwd )
    stdout,stderr = await proc.communicate()
    retcode:int = proc.returncode
    return retcode, stdout.decode(), stderr.decode()

def write_to_textfile( filepath:str, content:list[str], mode:int=None ):
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

def write_time( dirpath:str, tm:float=None ):
    ret:float = None
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
        self.pool:ThreadPoolExecutor = ThreadPoolExecutor( max_workers=1 )
        self.word_dir_top = os.path.abspath(parent)
        self._flg_setup:bool = False
        self.max_session:int = 30
        self.timer_inverval:float = 10
        self.session_live_sec:float = 5.0*60.0
        self.session_delete_sec:float = 60.0 * 60.0
        self.session_list:dict[str,CodeSession] = {}

    def _th_setup_scripts(self):
        print(f"[Repo]setup scripts {self.word_dir_top}")
        for name,content in script_map.items():
            scrpath = os.path.join( self.word_dir_top, name)
            write_to_textfile( scrpath, content, 0o744 )

    def _th_get_script(self, name ):
        if not os.path.isdir( self.word_dir_top ):
            raise ValueError( f"parent dir {self.word_dir_top} is not directory")
        content:list[str] = script_map.get(name)
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
            tm:float = read_time(dirpath)
            if isinstance(tm,float) and tm>0:
                print(f"[Repo]reload {dirpath}")
                sessionId:str = os.path.basename(dirpath)
                session:CodeSession = CodeSession( self, sessionId, dirpath, tm )
                self.session_list[sessionId] = session

    async def _timer(self):
        while True:
            await asyncio.sleep(self.timer_inverval)
            dellist:list[CodeSession] = []
            async with self.lock:
                # print( "[Repo] timer ")
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
            loop = asyncio.get_running_loop()
            await loop.run_in_executor( self.pool, self._th_setup_scripts )
            # python仮想環境を構築
            scrpath:str = await self.get_script( SCR_BUILD )
            print(f"[Repo]exec {scrpath}")
            proc:Process = await create_subprocess_exec( scrpath, stdout=PIPE, stderr=DEVNULL, cwd=self.word_dir_top )
            stdout,stderr = await proc.communicate()
            code:int = proc.returncode
            print(f"{stdout.decode()}")
            print(f"exit:{code}")
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

    async def get_session(self,sessionId:str=None):
        await self.setup()
        async with self.lock:
            # 既存にあるか？
            session = self.session_list.get(sessionId)
            if session is None or not isinstance(session,CodeSession):
                # 無いから新規作成
                loop = asyncio.get_running_loop()
                new_id, cwd = await loop.run_in_executor( self.pool, self._th_build_new_directory )
                print(f"[Repo]new session {new_id} {cwd}")
                session:CodeSession = CodeSession( self, new_id, cwd )
                self.session_list[new_id] = session
            await session.start()
            return session

class CodeSession:
    def __init__(self, parent:CodeRepo, sessionId, wd, tm:float=None ):
        if not os.path.isdir( wd ):
            raise ValueError( f"parent dir {wd} is not directory")
        self.lock:Condition = Condition()
        self.parent:CodeRepo = parent
        self.sessionId:str = sessionId
        self.cwd = wd
        self.process = None
        self.ps1 = ">>>"+self.sessionId+">>>"
        self.ps2 = "..."+self.sessionId+"..."
        self.lasttime:float = tm if isinstance(tm,float) else time.time()

    async def start(self):
        if not os.path.isdir( self.cwd ):
            raise ValueError( f"cwd {self.cwd} is not directory")
        self.lasttime:float = time.time()
        async with self.lock:
            if isinstance(self.process,Process):
                return

            print(f"[Session:{self.sessionId}] start")
            scrpath:str = await self.parent.get_start_script()
            try:
                self.process:Process = await create_subprocess_exec( scrpath, stdin=PIPE, stdout=PIPE, stderr=DEVNULL, cwd=self.cwd)
                await self.send_command( "import sys" )
                await self.send_command( f"sys.ps2='\\n{self.ps2}\\n'" )
                await self.send_command( f"sys.ps1='\\n{self.ps1}\\n'" )
                out = await self.get_output()
                print(f"[OUT]{out}")
                self.lasttime:float = time.time()
            except:
                await self.stop()

    def th_send_command(self,command):
        # コマンドを送信
        self.lasttime:float = time.time()
        self.process.stdin.write(command.encode())
        self.process.stdin.write('\n'.encode())

    async def send_command(self,command):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor( self.parent.pool, self.th_send_command, command )

    async def get_output(self):
        # 結果を取得
        stdout = []
        while True:
            self.lasttime:float = time.time()
            if self.process.stdout.at_eof():
                break
            line = (await self.process.stdout.readline()).decode()
            self.lasttime:float = time.time()
            print(f"[dbg]{escape_control_chars(line)}")
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

    async def command(self, command ):
        await self.send_command( command )
        out = await self.get_output()
        return out

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
            print(f"[Session:{self.sessionId}] stop")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor( self.parent.pool, self._th_stop_1, process )

    async def cleanup(self):
        await self.stop()
        if os.path.isdir( self.cwd ):
            print(f"[Session:{self.sessionId}] cleanup")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor( self.parent.pool, shutil.rmtree, self.cwd )
