import sys
import os
import asyncio

sys.path.append(os.getcwd())
from LocalInterpreter.interpreter.localcode import CodeRepo, CodeSession

async def main():
    work_dir = './tmp/test_repl'
    os.makedirs( work_dir, exist_ok=True)
    repo:CodeRepo = CodeRepo( work_dir )
    await repo.setup()
    code:CodeSession = await repo.create()
    await code.send_command('print("Hello from custom prompt!")')
    out = await code.get_output()
    print(f"[OUT]{out}")
    out = await code.command('x = 5')
    print(f"[OUT]{out}")
    out = await code.command('print(f"x is {x}")')
    print(f"[OUT]{out}")

    code.stop()

async def main2():
    work_dir = './tmp/test_repl'
    os.makedirs( work_dir, exist_ok=True)
    repo:CodeRepo = CodeRepo( work_dir )
    repo.timer_inverval = 1
    repo.session_live_sec = 5
    repo.session_delete_sec = 10
    sessionId:str = None
    session:CodeSession = await repo.get_session( sessionId )
    sessionId = session.sessionId
    await session.send_command('print("Hello from custom prompt!")')
    out = await session.get_output()
    print(f"[OUT]{out}")
    out = await session.command('x = 5')
    print(f"[OUT]{out}")

    for s in [ 0, repo.session_live_sec-1, repo.session_live_sec+1 ]:
        if s>0:
            print( f"Sleep {s}s")
            await asyncio.sleep(s)

        code2:CodeSession = await repo.get_session( sessionId )
        out = await code2.command('print(f"x is {x}")')
        print(f"[OUT]{out}")

    s = repo.session_delete_sec + 1
    print( f"Sleep {s}s")
    await asyncio.sleep(s)

if __name__ == "__main__":
    asyncio.run( main2() )