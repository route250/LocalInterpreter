import sys
import os
import re
import json
import traceback
sys.path.append(os.getcwd())
from LocalInterpreter.utils.JsonStreamParser import JsonStreamParser, JsonStreamParseError

def test_get_path():
    TEST_LIST = [
        [ 123, None, 123 ],
        [ {'k1':123}, "k1", 123 ],
        [ {'k1':123}, "k2", None ],
        [ [123,456,789], "[1]", 456 ],
        [ [123,456,789], "[3]", None ],
        [ {'k2':[123,456,789]}, "k2", [123,456,789] ],
        [ {'k2':[123,456,789]}, "k2[0]", 123 ],
        [ [{'k1':123},{'k2':456},{'k3':789}], "[2]", {'k3':789} ],
        [ [{'k1':123},{'k2':456},{'k3':789}], "[2].k3", 789 ],
    ]
    for obj,path,act in TEST_LIST:
        print(f"obj:{obj}")
        print(f"path:{path}")
        val=JsonStreamParser.get_value(obj,path)
        if val == act:
            print(f"value:{val}")
        else:
            print(f"ERROR: value:{val} actual:{act}")   

def test_by_test_data():
    import os,sys,re
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
    testdata_list = [
        '65535', '3.141592', '"abc123"', '{"key": 123}', '{"key": 4.56}', '{"key": "value"}',
        testdata,
        """[{"a1":"v1"},{"a2":"v2"}]""", """{"b1":[{"a1":"v1"},{"a2":"v2"}]}""",
        "{\n  \"text_to_speech\": \"やぁ、なにブラザー？\"\n}\n{\n  \"text_to_speech\": \"お疲れ様、なにか用かい？\"\n}",

        '[ 12, 0.12, .12 ]',
        '[ "abc", "def", "ghi" ]',
        '[ {"k1":"abc"}, {"k2":"def"}, {"k3":"ghi"} ]',
        '[ [12, 0.12], [+34, +3.4], [-56], [-0.056, .1, +.2, -.3] ]',
        '[ 123, "abc" ]',
        '[ 123, [456,789], {"k1":"abc"} ]',
        '[ "abc", 123 ]',
        '[ "abc", {"k1":"def"}, [456,789] ]',
        '[ {"k1":"abc"}, 123 ]',
        '[ {"k1":"abc"}, "def", [987,654,321] ]',
        '[ [987,654,321], 852, {"k1":"abc"} ]',
        '[ [987,654,321], "abc" ]',

        '{ "p1":12, "p2":0.12, "p3":.12 }',
        '{ "p1":"abc", "p2":"def", "p3":"ghi" }',
        '{ "p1":{"k1":"abc"}, "p2":{"k2":"def"}, "p3":{"k3":"ghi"} }',
        '{ "p1":[12, 0.12], "p2":[+34, +3.4], "p3":[-56], "p4":[-0.056, .1, +.2, -.3] }',
        '{ "p1":123, "p2":"abc" }',
        '{ "p1":123, "p2":[456,789], "p3":{"k1":"abc"} }',
        '{ "p1":"abc", "p2":123 }',
        '{ "p1":"abc", "p2":{"k1":"def"}, "p3":[456,789] }',
        '{ "p1":{"k1":"abc"}, "p2":123 }',
        '{ "p1":{"k1":"abc"}, "p2":"def", "p3":[987,654,321] }',
        '{ "p1":[987,654,321], "p2":852, "p3":{"k1":"abc"} }',
        '{ "p1":[987,654,321], "p2":"abc" }',

    ]

    input_dir = "./testData/jsonparser"
    output_dir="./tmp/jsonparser"
    os.makedirs( output_dir, exist_ok=True )

    test_case_list = {}
    # ディレクトリ内のファイルをループ
    max_case_num = -1  # 初期値を-1に設定
    for filename in os.listdir(input_dir):
        # case[0-9]+.jsonに一致するファイルを探す
        match = re.match(r'case(\d+)\.json', filename)
        if match:
            # 番号部分を整数化して比較
            number = int(match.group(1))
            if number > max_case_num:
                max_case_num = number
            # ファイルを読み込んでJSONオブジェクトとしてロード
            with open(os.path.join(input_dir, filename), 'r', encoding='utf-8') as f:
                case_data = json.load(f)
            test_case_list[filename] = case_data
    # 追加
    for case_text in testdata_list:
        found = False
        for k,v in test_case_list.items():
            if case_text == v.get('input'):
                found = True
                continue
        if not found:
            max_case_num+=1
            filename=f"case{max_case_num:04}.json"
            case_data = { 'input': case_text }
            test_case_list[filename] = case_data

    for filename, case_data in test_case_list.items():
        result:str = ""
        logfile = os.path.join(output_dir,filename)
        input_text:str = case_data.get('input')
        acutual = case_data.get('output')
        with open(logfile,'wt') as log:
            try:
                print("")
                print("-----------------------------------------------------------")
                print(input_text)

                log.write("{\n")
                log.write('  "input":     ')
                log.write( json.dumps( input_text, ensure_ascii=False ) )
                log.write(",\n")

                print("--output--")
                log.write('  "output": [')
                i=0
                try:
                    parser:JsonStreamParser = JsonStreamParser()
                    for st,key,val in parser.put(input_text,end=True):
                        out = [st,key,val]
                        val_text = json.dumps( out, ensure_ascii=False )
                        print(f"{i:04}: {val_text}")
                        if acutual:
                            act_text = json.dumps( acutual[i], ensure_ascii=False ) if i<len(acutual) else ''
                            if val_text != act_text:
                                print(f"ERROR {act_text}")
                                result = "NG"
                        if i>0:
                            log.write(",")
                        log.write("\n")
                        vtxt=json.dumps( val, ensure_ascii=False )
                        log.write( f'    [ "{st}", "{key}", {vtxt} ]')
                        i+=1
                finally:
                    if i>1:
                        log.write("\n")
                    log.write('  ]\n')
                if acutual and i<len(acutual):
                    result = "NG"
                    for j in range(i,len(acutual)):
                        act_text = json.dumps( acutual[j], ensure_ascii=False ) if i<len(acutual) else ''
                        print(f"{j:04}:" )
                        print(f"ERROR {act_text}")

                print("--result--")
                ret = parser.get()
                print(ret)
                if result == "":
                    print("--Success--")
                else:
                    print("--Fail--")
                    break
            finally:
                log.write("}\n")

if __name__ == "__main__":
    test_get_path()
    test_by_test_data()
