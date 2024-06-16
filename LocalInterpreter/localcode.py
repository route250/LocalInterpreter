import sys
import os
import subprocess

from subprocess import CompletedProcess
import time
from uuid import UUID, uuid4
import tempfile
import glob

SCR_BUILD = 'build.sh'
SCR_RUN = 'run.sh'
SCR_CLEAN = 'clean.sh'
scriptsss:dict = {
    SCR_BUILD: [ "#!/bin/bash",
            "set -ue",
            "python3 -m venv .venv",
            "source .venv/bin/activate",
            "python3 -m pip install -U pip setuptools",
        ],
    SCR_RUN: [ "#!/bin/bash",
            "set -ue",
            "python3 -m venv .venv",
            "source .venv/bin/activate",
            "python3 -m pip install -U pip setuptools",
        ],
    SCR_CLEAN: [],
}

class CodeRepo:
    def __init__(self, parent:str ):
        if not os.path.isdir( parent ):
            raise ValueError( f"parent dir {parent} is not directory")
        self.parent = os.path.abspath(parent)
        # 処理用スクリプト作成
        for name,content in scriptsss.items():
            if isinstance(content,list):
                scrpath = os.path.join( self.parent, name)
                with open( scrpath, "w") as stream:
                    for line in content:
                        stream.write( line )
                        stream.write( '\n' )
                os.chmod(scrpath,0o744)

        self.code_list = {}
        self.wd_list:list = []
        for p in glob.glob( os.path.join(self.parent,'**','.venv','bin','activate')):
            print(f"dir {p}")
            d_bin = os.path.dirname(p)
            d_venv = os.path.dirname(d_bin)
            dir = os.path.dirname(d_venv)
            self.wd_list.append(dir)

    def get_script(self, name ):
        if not os.path.isdir( self.parent ):
            raise ValueError( f"parent dir {self.parent} is not directory")
        content:list[str] = scriptsss.get(name)
        if not isinstance(content,list):
            raise ValueError( f"script {name} is not defined")
        scrpath = os.path.join( self.parent, name)
        if not os.path.exists( scrpath ):
            raise ValueError( f"script {name} is not defined")
        return scrpath

    def build_new_directory(self):
        if not os.path.isdir( self.parent ):
            raise ValueError( f"{self.parent} is not directory")
        uniq:str = uuid4().hex
        cwd = os.path.join( self.parent, uniq )
        os.makedirs( cwd, exist_ok=False )
        scrpath:str = self.get_script( SCR_BUILD )
        print(f"build dir {cwd}")
        result:CompletedProcess = subprocess.run([ scrpath ], cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print(result.stdout)
        print(result.stderr)
        result.check_returncode()
        return cwd

    def create(self):
        try:
            wd = self.wd_list.pop()
        except IndexError:
            wd = self.build_new_directory()
        code:CodeInter = CodeInter( self, wd )
        self.code_list[code.uid] = code
        return code

    def get_start_script(self):
        return self.get_script(SCR_RUN)

class CodeInter:
    def __init__(self, parent:CodeRepo, wd ):
        if not os.path.isdir( wd ):
            raise ValueError( f"parent dir {wd} is not directory")
        self.parent = parent
        self.cwd = wd
        self.process = None
        self.uid:str = uuid4().hex
        self.ps1 = ">>>"+self.uid+">>>"
        self.ps2 = "..."+self.uid+"..."
        self.lasttime:float = time.time()

    def start(self):
        if not os.path.isdir( self.cwd ):
            raise ValueError( f"cwd {self.cwd} is not directory")
        self.lasttime:float = time.time()
        scrpath:str = self.parent.get_start_script()
        self.process:subprocess.Popen = subprocess.Popen([ scrpath ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
        time.sleep(0.2)
        self.send_command( "import sys" )
        self.send_command( f"sys.ps2='\\n{self.ps2}\\n'" )
        self.send_command( f"sys.ps1='\\n{self.ps1}\\n'" )
        out = self.get_output()
        print(f"[OUT]{out}")

    def stop(self):
        # プロセスを終了
        self.process.stdin.write('exit()\n')
        self.process.stdin.flush()
        self.process.terminate()
        self.process = None

    def send_command(self,command):
        # コマンドを送信
        self.lasttime:float = time.time()
        self.process.stdin.write(command + '\n')
        self.process.stdin.flush()

    def get_output(self):    
        # 結果を取得
        stdout = []
        while True:
            self.lasttime:float = time.time()
            line = self.process.stdout.readline()
            self.lasttime:float = time.time()
            print(f"[dbg]{line}")
            sline=line.strip()
            if sline == self.ps2:
                line='...'
                self.process.stdin.flush()
            elif sline == self.ps1:
                break
            stdout.append(line)
        return ''.join(stdout)
