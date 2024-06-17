import sys
import os
import asyncio

sys.path.append(os.getcwd())
from LocalInterpreter.localcode import CodeRepo, CodeInter

async def main():
    repo:CodeRepo = CodeRepo( './tmp' )
    await repo.setup()
    code:CodeInter = await repo.create()
    await code.send_command('print("Hello from custom prompt!")')
    out = await code.get_output()
    print(f"[OUT]{out}")
    out = await code.command('x = 5')
    print(f"[OUT]{out}")
    out = await code.command('print(f"x is {x}")')
    print(f"[OUT]{out}")

    code.stop()

async def main2():
    repo:CodeRepo = CodeRepo( './tmp' )
    sid:str = None
    code:CodeInter = await repo.get_session( sid )
    sid = code.sid
    await code.send_command('print("Hello from custom prompt!")')
    out = await code.get_output()
    print(f"[OUT]{out}")
    out = await code.command('x = 5')
    print(f"[OUT]{out}")
    repo.return_session( code )

    code2:CodeInter = await repo.get_session( sid )
    out = await code2.command('print(f"x is {x}")')
    print(f"[OUT]{out}")

    code.stop()

if __name__ == "__main__":
    asyncio.run( main2() )