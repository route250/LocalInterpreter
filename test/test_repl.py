import sys
import os
import subprocess

from subprocess import CompletedProcess
import time
from uuid import UUID, uuid4
import tempfile
import glob

sys.path.append(os.getcwd())
from LocalInterpreter.localcode import CodeRepo, CodeInter

def main():
    repo:CodeRepo = CodeRepo( './tmp' )
    code:CodeInter = repo.create()
    code.start()
    code.send_command('print("Hello from custom prompt!")')
    out = code.get_output()
    print(f"[OUT]{out}")
    code.send_command('x = 5')
    out = code.get_output()
    print(f"[OUT]{out}")
    code.send_command('print(f"x is {x}")')
    out = code.get_output()
    print(f"[OUT]{out}")

    code.stop()

if __name__ == "__main__":
    main()