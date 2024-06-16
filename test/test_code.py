from code import InteractiveInterpreter, InteractiveConsole


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
    main()