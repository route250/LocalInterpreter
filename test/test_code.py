
import sys,os

import logging
sys.path.append(os.getcwd())
from LocalInterpreter.service.local_service import QuartServerBase, QuartServiceBase
from LocalInterpreter.service.python_service import PythonService
from LocalInterpreter.interpreter.localcode import CodeRepo, CodeSession
from code import InteractiveInterpreter, InteractiveConsole


def test_code():

    code_list = []
    code_list.append( 'print("hello wold!")' )
   # code_list.append( """for i in range(10): print( f"{i}" ) """ )
    code_list.append( """
    print( "foo!" )
    print( "bar!" )
    """ )
    code_list.append( """
    current_directory = os.getcwd()
    print(f"Current Directory: {current_directory}")
    files = os.listdir(current_directory)    
    print("Files in the current directory:")
    for file in files:
        print(file)
    """)
    
    pys:PythonService = PythonService()

    for prg in code_list:
        param = {
            'code': prg
        }
        res_dict, code = pys.call( param )
        print(res_dict)
        sessionId = res_dict.get('sessionId')
        output = res_dict.get('stdout')
        print(f"\n---------------\nsessionId:{sessionId} code:{code}")
        print(f"{output}")
        print("-------------------------")

class BPython(InteractiveInterpreter):
    def __init__(self, locals=None):
        super().__init__( locals )
        self.output = []

    def write( self, data ):
        super().write(data)
        self.output.append( data )

    def submit(self, command):
        self.output= []
        more:bool = self.runsource( command )
        if more:
            self.write( "不完全なコマンド")
        else:
            print( f"[done]")

    def flush(self):
        for line in self.output:
            print("[SUB]{line}")

def main():

    it = BPython( locals=locals() )


    it.submit( 'a=3')
    it.flush()
    it.submit( 'b="bbb"')
    it.submit( 'print(f"a={a} b={b}")')
    it.flush()


if __name__ == "__main__":
    test_code()
    #main()