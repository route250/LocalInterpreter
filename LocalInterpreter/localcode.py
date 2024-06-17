import sys
import os
import re
import asyncio
from asyncio.subprocess import Process, create_subprocess_exec, create_subprocess_shell, PIPE, DEVNULL
from concurrent.futures import ThreadPoolExecutor
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
scriptsss:dict = {
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

def get_script( dirpath, name ):
    if not os.path.isdir( dirpath ):
        raise ValueError( f"parent dir {dirpath} is not directory")
    content:list[str] = scriptsss.get(name)
    if not isinstance(content,list):
        raise ValueError( f"script {name} is not defined")
    filepath = os.path.join( dirpath, name)
    if not os.path.exists( filepath ):
        raise ValueError( f"script {name} is not defined")
    return filepath

class CodeRepo:
    def __init__(self, parent:str ):
        if not os.path.isdir( parent ):
            raise ValueError( f"parent dir {parent} is not directory")
        self.pool:ThreadPoolExecutor = ThreadPoolExecutor( max_workers=1 )
        self.parent = os.path.abspath(parent)
        self._flg_setup:bool = False
        self.idle_code = {}
        self.used_code = {}
        self.wd_list:list = []

    async def get_script(self, name ):
        loop = asyncio.get_running_loop()
        filepath:str = await loop.run_in_executor( self.pool, get_script, self.parent,name )
        return filepath

    async def get_start_script(self):
        return await self.get_script(SCR_SART)

    async def setup(self):
        if self._flg_setup:
            return
        self._flg_setup = True
        # 処理用スクリプト作成
        loop = asyncio.get_running_loop()
        for name,content in scriptsss.items():
            scrpath = os.path.join( self.parent, name)
            await loop.run_in_executor( self.pool, write_to_textfile, scrpath, content, 0o744 )
        # python仮想環境を構築
        scrpath:str = await self.get_script( SCR_BUILD )
        print(f"build dir {scrpath}")
        proc:Process = await create_subprocess_exec( scrpath, stdout=PIPE, stderr=DEVNULL, cwd=self.parent )
        stdout,stderr = await proc.communicate()
        code:int = proc.returncode
        print(f"[STDOUT] {stdout.decode()}")
        print(f"[RETCODE] {code}")

        for dirpath in glob.glob( os.path.join(self.parent,'*')):
            tm:float = read_time(dirpath)
            if isinstance(tm,float) and tm>0:
                print(f"code directory {dirpath}")
                sid:str = os.path.basename(dirpath)
                self.wd_list.append( { 'sid':sid, 'tm': tm, 'path':dirpath} )

    def build_new_directory(self):
        if not os.path.isdir( self.parent ):
            raise ValueError( f"{self.parent} is not directory")
        uniq:str = uuid4().hex
        cwd = os.path.join( self.parent, uniq )
        os.makedirs( cwd, exist_ok=False )
        print(f"build dir {cwd}")
        return { 'sid': uniq, 'tm': time.time(), 'path':cwd }

    async def create(self):
        if not self._flg_setup:
            await self.setup()
        wd = self.build_new_directory()
        sid = wd['sid']
        cwd = wd['path']
        code:CodeInter = CodeInter( self, sid, cwd )
        await code.start()
        self.used_code[code.sid] = code
        return code

    async def get_session(self,sid):
        if not self._flg_setup:
            await self.setup()
        if isinstance(sid,str) and sid in self.idle_code:
            code = self.idle_code[sid]
            del self.idle_code[sid]
            self.used_code[sid] = code
            return code
        else:
            return await self.create()

    def return_session(self,code):
        if isinstance(code,CodeInter):
            if code.sid in self.used_code:
                del self.used_code[code.sid]
            self.idle_code[code.sid] = code

class CodeInter:
    def __init__(self, parent:CodeRepo, sid, wd ):
        if not os.path.isdir( wd ):
            raise ValueError( f"parent dir {wd} is not directory")
        self.parent:CodeRepo = parent
        self.sid:str = sid
        self.cwd = wd
        self.process = None
        self.ps1 = ">>>"+self.sid+">>>"
        self.ps2 = "..."+self.sid+"..."
        self.lasttime:float = time.time()

    async def start(self):
        if not os.path.isdir( self.cwd ):
            raise ValueError( f"cwd {self.cwd} is not directory")
        self.lasttime:float = time.time()
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
            self.process.terminate()
            self.process = None

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

    def stop(self):
        # プロセスを終了
        try:
            self.process.stdin.write('exit()\n'.encode())
            self.process.terminate()
        except:
            pass
        self.process = None
