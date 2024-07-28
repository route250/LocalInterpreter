

def idt(lv:int) ->str:
    return "  "*lv

def to_yaml(indent: str, obj:dict[str,object]|list[object]|tuple[object], idx: int = -1):
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (str, int, float)):
                yield f"{indent}{key}: {value}"
            elif isinstance(value, bool):
                yield f"{indent}{key}: {str(value).lower()}"
            elif isinstance(value, dict):
                yield f"{indent}{key}:"
                yield from to_yaml(f"{indent}  ", value)
            elif isinstance(value, (list, tuple)):
                yield f"{indent}{key}:"
                for value2 in value:
                    if isinstance(value2, dict):
                        yield f"{indent}  -"
                        yield from to_yaml(f"{indent}    ", value2)
                    else:
                        yield f"{indent}  - {value2}"
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            if isinstance(item, (str, int, float)):
                yield f"{indent}- {item}"
            elif isinstance(item, bool):
                yield f"{indent}- {str(item).lower()}"
            elif isinstance(item, dict):
                yield f"{indent}-"
                yield from to_yaml(f"{indent}  ", item)
    else:
        raise TypeError(f"Unsupported type: {type(obj)}")

class ServiceParam:
    def __init__(self,name:str,type:str='string',description:str|None=None,example:str|None=None):
        self.name:str = name
        self.type:str = type
        self.description = description
        self.example = example

    def to_yaml(self, lv:int ):
        indent:str = idt(lv)
        yield f"{indent}{self.name}:"
        yield f"{indent}  type: {self.type}"
        yield f"{indent}  description: {self.description}"
        yield f"{indent}  example: {self.example}"

class ServiceResponse:
    def __init__(self, code:int, description:str):
        self.code:int = code
        self.description:str = description
        self.params:list[ServiceParam] = []

    def add_param( self, param:ServiceParam ):
        self.params.append(param)

    def to_yaml(self, lv:int ):
        indent:str = idt(lv)
        yield f"{indent}'{self.code}':"
        yield f"{indent}  description: {self.description}"
        yield f"{indent}  content:"
        yield f"{indent}    application/json:"
        yield f"{indent}      schema:"
        yield f"{indent}        type: object"
        yield f"{indent}        properties:"
        for param in self.params:
            yield from param.to_yaml( lv+5 )

class BaseService:
    def __init__(self, method:str ):
        self.method = method
        self.summary = ""
        self.description = ""
        self.params:list[ServiceParam] = []
        self.responses:dict[int,ServiceResponse] = {}

        p400:ServiceResponse = ServiceResponse( 400,'Invalid request' )
        p400.add_param( ServiceParam(
            'error', 'string',
            'Error message for invalid request.',
            '"No code provided"'
        ))
        p500:ServiceResponse = ServiceResponse( 500,'Internal server error' )
        p500.add_param( ServiceParam(
            'error', 'string',
            'Error message for server error.',
            '"Exception message"'
        ))
        self.add_response( p400 )
        self.add_response( p500 )

    def add_response(self, resp:ServiceResponse ):
        self.responses[ resp.code ] = resp

    def to_response_json(self, data:str|dict, code:int ) ->tuple[dict,int]:
        response_dict = {}
        response_list:ServiceResponse|None = self.responses.get(code)
        if response_list is None:
            pass
        elif isinstance(data,dict):
            for res_param in response_list.params:
                param_data = data.get(res_param.name)
                # ToDo 型を考慮しなくては
                response_dict[res_param.name] = param_data
        else:
            for res_param in response_list.params:
                response_dict[res_param.name] = f"{data}"
        return response_dict, code


    def to_yaml(self, lv:int ):
        indent:str = idt(lv)
        yield f"{indent}summary: {self.summary}"
        yield f"{indent}description: {self.description}"
        if self.params:
            yield f"{indent}requestBody:"
            yield f"{indent}  required: true"
            yield f"{indent}  content:"
            yield f"{indent}    application/json:"
            yield f"{indent}      schema:"
            yield f"{indent}        type: object"
            yield f"{indent}        properties:"
            for param in self.params:
                yield from param.to_yaml( lv+5 )
        yield f"{indent}responses:"
        for code, resp in sorted(self.responses.items()):
            yield from resp.to_yaml( lv+1 )

    def get_func_name(self)->str:
        return self.summary.replace(" ","_").replace("'","_")

    def to_func(self) ->dict:
        props = {}
        required = []
        for param in self.params:
            props[param.name] = { "type":param.type, "description": param.description }
            required.append(param.name)
        funcs = {
            "type": "function",
            "function": {
                "name": self.get_func_name(),
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": props,
                    "required": required,
                }
            }
        }
        return funcs

class oldPythonService(BaseService):
    def __init__(self):
        super().__init__('post')
        self.params.append( ServiceParam(
            'sessionId', 'string', 
            'The session ID for maintaining the execution context. If left blank, a new session will be created and the session ID will be returned as part of the response. If provided, it should be the session ID from the previous call. Sessions expire after a certain period, and if an expired session ID is provided, a new session will be created and its ID will be returned.',
            '\"e2d21d32917941f78af7a1103a010daa\"',
            ))
        self.params.append( ServiceParam(
            'code', 'string',
            'The Python code to execute.',
            '\"print(\'Hello, World!\')\"',
        ) )
        p200:ServiceResponse = ServiceResponse( 200, 'Successful execution' )
        p200.add_param( ServiceParam(
            'sessionId', 'string',
            'The session ID for maintaining the execution context.',
            '"e2d21d32917941f78af7a1103a010daa"'
        ))
        p200.add_param( ServiceParam(
            'stdout', 'string',
            'The standard output from the executed code.',
            '"Hello, World!"'
        ))
        self.add_response( p200 )
    
class ServiceSchema:
    def __init__(self, title:str=""):
        self.title:str = title
        self.version:str = '0.0.1'
        self.servers:dict = {}
        self.path_dict:dict[str,dict[str,BaseService]] = {}
    
    def init(self):
        self.servers['http://127.0.0.1:5000'] = 'localserver'

    def add_service(self, path:str, service:BaseService):
        method_dict:dict[str,BaseService]|None = self.path_dict.get(path)
        if method_dict is None:
            method_dict = {}
            self.path_dict[path] = method_dict
        method_dict[service.method] = service

    def to_yaml(self, request_url:str|None=None):
        yield "openai: 3.0.0"
        yield "info:"
        yield f"  title: {self.title}"
        yield f"  version: {self.version}"
        yield "servers:"
        for server_url,description in self.servers.items():
            yield f"  - url: {server_url}"
            yield f"    description: {description}"
            if server_url==request_url:
                request_url = None
        if request_url:
            yield f"  - url: {request_url}"
            yield f"    description: end point"
        yield "paths:"
        for path,method_dict in self.path_dict.items():
            yield f"  {path}:"
            for method,service in method_dict.items():
                yield f"    {method}:"
                yield from service.to_yaml( 3 )

    def to_tools(self) ->list[dict]:
        tools = []
        for path,method_dict in self.path_dict.items():
            for method,service in method_dict.items():
                tools.append( service.to_func() )
        return tools

def main():
    # テスト用の辞書データ
    data:dict[str,object] = {
        'name': 'AI',
        'active': True,
        'details': {
            'age': 4,
            'features': ['intelligent', 'adaptive', True]
        },
        'scores': [95, 82, 76],
        'servers': [
            {'url': 'http://127.0.0.1:5000', 'memo': 'sample'},
            {'url': 'http://127.0.0.1:80', 'memo': 'web'}
        ]
    }

    # YAML出力
    #yaml_output = list(to_yaml("", data))
    #yaml_output

    sh:ServiceSchema = ServiceSchema()
    sh.init()
    sh.add_service( 'execute', oldPythonService() )

    for line in sh.to_yaml():
        print( line )

if __name__ == "__main__":
    main()