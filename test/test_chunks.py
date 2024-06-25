import sys
import os
sys.path.append(os.getcwd())
from LocalInterpreter.utils import web

def test():

    text_size = 30
    chunk_size = 15
    overlap=3
    input_text:str = ("0123456789abcdefghijklmnopqrstuvwxyz"*10)[:text_size]
    chunks:list = web.simple_text_to_chunks( input_text, chunk_size, overlap )
    print( f" chunks:{len(chunks)} {len(chunks[0])} {len(chunks[-1])}")
    for c in chunks:
        print( f"{c} {len(c)}")
    x1:int = len(chunks[-1])
    chunks = web.text_to_chunks( input_text, chunk_size, overlap )
    for c in chunks:
        print( f"{c} {len(c)}")

if __name__ == "__main__":
    test()