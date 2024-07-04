import re
import json

PRE_KEY=1
IN_KEY=2
AFTER_KEY=3
PRE_VALUE=4
IN_QSTR=5
AFTER_VALUE=6
IN_NUMBER=7
IN_NULL=8
FREE_STR=9
END=999
SEP='.'

class JsonStreamParseError(ValueError):
    def __init__(self,msg,pos):
        super().__init__(msg)
        self.pos=pos


class JsonStreamParser:
    UPD='update'
    END='end'
    ERR='error'
    """ストリーミングでパースできるJSONパーサ簡易版"""
    def __init__(self):
        self._full_text:str = ""
        self._pos=0
        self._stack = []
        self._phase=PRE_VALUE
        self._obj=None
        self._key=None
        self._val=None
        self._esc=0
        self._ucode=""
        self._lines=1
        self._cols=1

    def _push(self, new_obj, new_phase ):
        if self._obj is None:
            self._obj = new_obj
        elif isinstance(self._obj,dict):
            self._obj[self._key] = new_obj
        elif isinstance(self._obj,list):
            if self._key is None:
                self._key = len(self._obj)
            else:
                if self._key+1 != len(self._obj):
                   print(f"invalid index len(obj):{len(self._obj)} key:{self._key}")
                self._key = len(self._obj)
            self._obj.append(new_obj)
        else:
            raise ValueError(f"invalid index obj:{self._obj} key:{self._key}")
        self._stack.append( (self._phase,self._obj,self._key) )
        self._phase = new_phase
        self._obj = new_obj
        self._key=None if not isinstance(new_obj,list) else -1
        self._val=None

    def _pop(self):
        if self._stack:
            self._phase, self._obj, self._key = self._stack.pop()
            self._val = None
            if self._stack:
                return True
        return False

    def get(self,path=None):
        obj = None
        if self._stack:
            obj = self._stack[0][1]
        elif self._obj:
            obj = self._obj
        else:
            obj = self._val
        return JsonStreamParser.get_value(obj,path)

    def _obj_to_path(self, obj, key, depth ):
        if key is not None:
            if isinstance(obj,dict):
                if depth<1:
                    return key
                return f"{SEP}{key}"
            elif isinstance(obj,list):
                return f"[{key}]"
            else:
                raise ValueError("invalid key {key} for object {obj}")
        else:
            if depth>0 and obj is not None:
                raise ValueError("invalid key {key} for object {obj}")
            return ""

    def _get_current_path(self):
        paths:list = [ self._obj_to_path(s[1],s[2], i) for i,s in enumerate(self._stack[1:])]
        paths.append( self._obj_to_path( self._obj,self._key, len(paths)))
        return ''.join(paths) if len(paths)>0 else ''

    def put(self, text:str, *, end=False ):
        try:
            if not isinstance(text,str):
                text = ""
            atext = text
            if end:
                atext = text + " "
            self._full_text += text
            if self._phase == END:
                return
            for cc in atext:
                try:
                    for ret in self._put_char(cc):
                        yield ret
                except JsonStreamParseError as ex:
                    self._phase = END
                    yield (JsonStreamParser.ERR,"",f"{ex}")
                    break
        except Exception as ex:
            self._phase = END
            raise
    
    def _put_char( self, cc:str ):
        try:
            if self._esc==0 and cc=="\\" and ( self._phase==IN_QSTR or self._phase==IN_KEY):
                self._esc=1
                return
            elif self._esc==1:
                if "r"==cc:
                    cc="\r"
                elif "n"==cc:
                    cc="\n"
                elif "t"==cc:
                    cc="\t"
                elif "\""==cc:
                    cc="\"x"
                elif "\\"==cc:
                    cc="\\"
                elif "u"==cc:
                    self._esc=2
                    self._ucode="\\u"
                    return
                else:
                    raise JsonStreamParseError(f"invalid escape secence \"\\{cc}",self._pos)
                self._esc=0
            elif self._esc>=2:
                self._ucode+=cc
                if len(self._ucode)<6:
                    return
                self._esc=0
                try:
                    cc = self._ucode.encode().decode('unicode-escape')
                except:
                    raise JsonStreamParseError(f"invalid escape secence \"{self._ucode}",self._pos)
                self._ucode=""

            if self._phase==PRE_KEY:
                # pre key
                if cc=="\"":
                    self._phase=IN_KEY
                    self._key=""
                elif cc=="}":
                    for ret in self._put_after_value(cc): yield ret
                elif cc>" ":
                    raise JsonStreamParseError(f"Expecting property name enclosed in double quotes: line {self._lines} column {self._cols} (char {self._pos})",self._pos)
            elif self._phase==IN_KEY:
                # in key
                if cc=="\"":
                    self._phase=AFTER_KEY
                else:
                    self._key += cc[0]
            elif self._phase==AFTER_KEY:
                # after key
                if cc==":":
                    self._obj[self._key] = None
                    self._phase=PRE_VALUE
                elif cc>" ":
                    raise JsonStreamParseError(f"invalid char in after key \"{cc}\"",self._pos)
            elif self._phase==PRE_VALUE:
                # pre value
                if cc=="{":
                    self._push( {}, PRE_KEY)
                elif cc=="}" and isinstance(self._obj,dict):
                    for ret in self._put_after_value(cc): yield ret
                elif cc=="[":
                    self._push( [], PRE_VALUE )
                elif cc=="]" and isinstance(self._obj,list):
                    for ret in self._put_after_value(cc): yield ret
                elif cc=="\"":
                    self._phase=IN_QSTR
                    self._val=""
                    if isinstance(self._obj,dict):
                        self._obj[self._key] = self._val
                    elif isinstance(self._obj,list):
                        self._key = len(self._obj)
                        self._obj.append(self._val)
                elif cc=="+" or cc=="-" or cc=="." or "0"<=cc and cc<="9":
                    self._phase=IN_NUMBER
                    self._val=cc
                    if isinstance(self._obj,dict):
                        self._obj[self._key] = None
                    else:
                        pass
                elif cc=="n":
                    self._phase=IN_NULL
                    self._val=cc
                    if isinstance(self._obj,dict):
                        self._obj[self._key] = None
                    else:
                        pass
                elif cc>" ":
                    if self._obj is None and self._key is None and self._val is None:
                        self._phase = FREE_STR
                        self._obj = cc
                    else:
                        raise JsonStreamParseError(f"invalid char in before value \"{cc}\"",self._pos)
            elif self._phase==IN_QSTR:
                # in value
                if cc=="\"":
                    self._phase=AFTER_VALUE
                    yield (JsonStreamParser.END, self._get_current_path(), self._val )
                    self._key=None
                    if not isinstance(self._obj,(dict,list)):
                        self._phase = END
                    else:
                        self._val=None
                else:
                    self._val += cc[0]
                    if isinstance(self._obj,dict):
                        self._obj[self._key] = self._val
                    elif isinstance(self._obj,list):
                        self._obj[-1] = self._val
                    yield (JsonStreamParser.UPD, self._get_current_path(), self._val )
            elif self._phase==IN_NUMBER:
                # in number
                if cc=="." or cc=="+" or cc=="-" or cc=="e" or "0"<=cc and cc<="9":
                    self._val+=cc
                elif cc<=" " or cc=="," or cc=="}" or cc=="]":
                    num = JsonStreamParser.parse_number(self._val)
                    self._phase=AFTER_VALUE
                    if isinstance(self._obj,dict):
                        self._obj[self._key] = num
                        self._val=None
                    elif isinstance(self._obj,list):
                        self._key=len(self._obj)
                        self._obj.append(num)
                        self._val=None
                    else:
                        self._phase=END
                    yield (JsonStreamParser.END, self._get_current_path(), num )
                    for ret in self._put_after_value(cc): yield ret
                else:
                    raise JsonStreamParseError(f"invalid char in number value \"{cc}\"",self._pos)
            elif self._phase==IN_NULL:
                if cc=="u" or cc=="l":
                    self._val+=cc
                elif cc<=" " or cc=="," or cc=="}" or cc=="]":
                    if isinstance(self._obj,dict):
                        pass
                    elif isinstance(self._obj,list):
                        self._key = len(self._obj)
                        self._obj.append(None)
                    else:
                        pass
                    self._phase=AFTER_VALUE
                    yield (JsonStreamParser.END, self._get_current_path(), self._val )
                    self._key=None
                    self._val=None
                    for ret in self._put_after_value(cc): yield ret
                else:
                    raise JsonStreamParseError(f"invalid char in null value \"{cc}\"",self._pos)

            elif self._phase==AFTER_VALUE:
                # after value
                for ret in self._put_after_value(cc): yield ret

            elif self._phase==FREE_STR:
                self._obj += cc

            elif self._phase==END:
                # end
                #if cc>" ":
                #    raise JsonStreamParseError(f"invalid char in after value \"{cc}\"",self._pos)
                pass # ignore after json data
            else:
                raise JsonStreamParseError(f"invalid phase {self._phase} \"{cc}\"",self._pos)
        finally:
            self._pos+=1
            self._cols+=1
            if cc=="\n":
                self._lines+=1
                self._cols=1

    def _put_after_value(self,cc):
        # after value
        if cc==",":
            if isinstance(self._obj,dict):
                self._phase = PRE_KEY
            elif isinstance(self._obj,list):
                self._key = len(self._obj)
                self._phase = PRE_VALUE
            else:
                raise JsonStreamParseError()
        elif cc=="}":
            val = self._obj
            if self._pop():
                self._phase = AFTER_VALUE
                yield (JsonStreamParser.END, self._get_current_path(), val )
            else:
                self._phase = END
                yield (JsonStreamParser.END, self._get_current_path(), self._obj )
        elif cc=="]":
            val = self._obj
            if self._pop():
                self._phase = AFTER_VALUE
                yield (JsonStreamParser.END, self._get_current_path(), val )
            else:
                self._phase = END
                yield (JsonStreamParser.END, self._get_current_path(), self._obj )
        elif cc>" ":
            raise JsonStreamParseError(f"invalid char in after value \"{cc}\"",self._pos)

    @staticmethod
    def parse_number( text ):
        if not text:
            return 0
        if "." in text:
            try:
                return float(text)
            except:
                return 0.0
        else:
            try:
                return int(text)
            except:
                return 0

    @staticmethod
    def get_value(obj,path):
        if not isinstance(path,str) or path=="":
            return obj
        for key in path.split(SEP):
            idx=-1
            match = re.match(r'(.*)\[(\d+)\]', key)
            if match:
                key = match.group(1)
                # 番号部分を整数化して比較
                idx = int(match.group(2))
            if key:
                if not isinstance(obj,dict):
                    return None
                obj = obj.get(key)
                if obj is None:
                    return None
            if idx>=0:
                if not isinstance(obj,list) or idx>=len(obj):
                    return None
                obj = obj[idx]
        return obj

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

def test_invalid_1():
    input="{\n  \"text_to_speech\": \"やぁ、なにブラザー？\"\n}\n{\n  \"text_to_speech\": \"お疲れ様、なにか用かい？\"\n}"
    print(f"INPUT:{input}")
    try:
        orig = json.loads( input )
        print(f"JSON:{orig}")
    except Exception as ex:
        print(f"ERROR:{ex}")
    parser:JsonStreamParser = JsonStreamParser()
    for cc in input:
        print(f"{cc}", end="")
        parser.put(cc)
        k,v = parser.get_parts()
        if k is not None:
            print( f" /* {k}: {v} */ ", end="")
    ret = parser.get()
    print(ret)

# if __name__ == "__main__":
#     test_invalid_1()