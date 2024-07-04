import sys,os
import asyncio
from asyncio import subprocess
from asyncio.subprocess import create_subprocess_exec, create_subprocess_shell, PIPE, DEVNULL, Process

async def arun( cmd: list[str]=None, cwd:str=None ):
    proc:Process = await create_subprocess_exec( *cmd, stdin=DEVNULL, stdout=PIPE, stderr=PIPE, cwd=cwd )
    stdout,stderr = await proc.communicate()
    retcode:int = proc.returncode
    print(stdout.decode())
    print(stderr.decode())
    print(f"retcode:{retcode}")

async def aexec( cmd: list[str]=None, cwd:str=None ):
    proc:Process = await create_subprocess_exec( "python3", '-q', '-i', '-u', stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=cwd )
    proc.stdin.write("a=3\n".encode())
    proc.stdin.write("b=5\n".encode())
    proc.stdin.write("print(f\"a+b={a+b}\")\n".encode())
    proc.stdin.write("exit()\n".encode())

    while True:
        if proc.stdout.at_eof() and proc.stderr.at_eof():
            break

        stdout = (await proc.stdout.readline()).decode()
        if stdout:
            print(f'[stdout] {stdout}', end='', flush=True)
        stderr = (await proc.stderr.readline()).decode()
        if stderr:
            print(f'[sdterr] {stderr}', end='', flush=True, file=sys.stderr)

        await asyncio.sleep(1)

    await proc.communicate()

    retcode:int = proc.returncode
    print(f"retcode:{retcode}")

async def main():
    print(f"hello wold")
    await arun( ["ls","-l"])
    await aexec( ["x"] )

if __name__ == "__main__":
    asyncio.run( main() )