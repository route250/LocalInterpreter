import sys
import os
import json
import traceback
sys.path.append(os.getcwd())
from LocalInterpreter.utils.JsonStreamParser import JsonStreamParser, JsonStreamParseError

class TestData:

    def __init__(self, input, actual ):
        self._result:bool=None
        self.ex = None
        self.input=input
        if isinstance(actual,(dict,list,int,float)):
            self.actual=actual
        else:
            self.actual = json.loads( actual )

    def get_input(self):
        if isinstance(self.input,str):
            return self.input
        return None

    def set_result(self, result):
        if isinstance(result,Exception):
            self.ex = result
            self._result = False
        if isinstance(result,(dict,list)):
            a = json.dumps(result,ensure_ascii=False)
            b = json.dumps(self.actual,ensure_ascii=False)
            self._result = a==b
        else:
            self._result = False
        print(f"Result: {self._result}")
        print(f"{result}")
        return self._result

TEST_CASE_01 = [
    TestData( 
        """ {"start":"0",
            "test": "sample",
            "key111": {
                "key222": "value222"
            },
            "key333": {
                "key444": ["a","b",5,null],
                "key555": 5,
                "key666": null
            },"key777":{"key888":"value888"}
            }""",
            {
                "start":"0",
                "test": "sample",
                "key111": { "key222": "value222" },
                "key333": {
                    "key444": ["a","b",5,None],
                    "key555": 5,
                    "key666": None
                },
                "key777":{ "key888": "value888" }
            }
    ),
    TestData(
        "{\n  \"text_to_speech\": \"やぁ、なにブラザー？\"\n}\n",
        {  "text_to_speech": "やぁ、なにブラザー？" }
    ),
    TestData(
        "{\n  \"text_to_speech\": \"やぁ、なにブラザー？\"\n}\n{\n  \"text_to_speech\": \"お疲れ様、なにか用かい？\"\n}",
        {  "text_to_speech": "やぁ、なにブラザー？" }
    ),
]
def test_case_01():
    try:
        for case in TEST_CASE_01:
            parser:JsonStreamParser = JsonStreamParser()
            try:
                for cc in case.get_input():
                    parser.put(cc)
                ret = parser.get()
                case.set_result(ret)
            except Exception as ex:
                case.set_result(ex)
            full = parser._full_text
            if full != case.get_input():
                print(f"ERROR:missmach full_text")
    except:
        traceback.print_exc()

def test():
    testdata=""" {"start":"0",
  "test": "sample",
  "key111": {
    "key222": "value222"
  },
  "key333": {
    "key444": ["a","b",5,null],
    "key555": 5,
    "key666": null
  },"key777":{"key888":"value888"}
}"""
    parser:JsonStreamParser = JsonStreamParser()
    for cc in testdata:
        print(f"{cc}", end="")
        parser.put(cc)
        k,v = parser.get_parts()
        if k is not None:
            print( f" /* {k}: {v} */ ", end="")
    ret = parser.get()
    print(ret)
    for k in ("key111.key222",):
        v = parser.get_value(k)
        print(f"get_value {k}={v}")

if __name__ == "__main__":
    test_case_01()
