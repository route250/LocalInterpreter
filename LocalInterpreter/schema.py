def to_yaml(indent: str, obj, idx: int = -1):
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

class Serv:
    def __init__(self, method, path):
        self.method = method
        self.path = path
        self.summary = ""
        self.description = ""
        self.params:dict = {}
        self.responses:dict = {}

    def to_yaml(self, indent ):
        yield f"{indent}summary: {self.summary}"
        yield f"{indent}description: {self.description}"
        yield f"{indent}requestBody:"
        yield f"{indent}  required: true"
        yield f"{indent}  content:"
        yield f"{indent}    application/json:"
        yield f"{indent}      schema:"
        yield f"{indent}        type: object"
        yield f"{indent}        properties:"
        for p,ppp in self.params.items():
            yield f"{indent}          {p}:"
            yield f"{indent}            type: {ppp.get('type', '')}"
            yield f"{indent}            description: {ppp.get('description', '')}"
            yield f"{indent}            example: \"{ppp.get('example', '')}\""

class PythonServ(Serv):
    def __init__(self,path):
        super().__init__('post',path)
        self.params['sessionId'] = {
            'type': 'string',
            'description': 'The session ID for maintaining the execution context. If left blank, a new session will be created and the session ID will be returned as part of the response. If provided, it should be the session ID from the previous call. Sessions expire after a certain period, and if an expired session ID is provided, a new session will be created and its ID will be returned.',
            'example': '\"e2d21d32917941f78af7a1103a010daa\"',
            }
        self.params['code'] = {
            'type': 'string',
            'description': 'The Python code to execute.',
            'example': '\"print(\'Hello, World!\')\"',
            }
        self.responses[200]= {
            'description': 'Successful execution',
            'params': {
                'sessionId': {
                    'type': 'string',
                    'description': 'The session ID for maintaining the execution context.',
                    'example': '"e2d21d32917941f78af7a1103a010daa"'
                },
                'stdout': {
                    'type': 'string',
                    'description': 'The standard output from the executed code.',
                    'example': '"Hello, World!"'
                }
            }
        }
    
class Schema:
    def __init__(self):
        self.title = "Local Python REPL API"
        self.servers:dict = {}
        self.paths:dict = {}
    
    def init(self):
        self.servers['http://127.0.0.1:5000'] = 'localserver'
        self.add( PythonServ( 'execute' ) )

    def add(self, serv:Serv):
        x:dict = self.paths.get(serv.path)
        if x is None:
            x = {}
            self.paths[serv.path] = x
        x[serv.method] = serv

    def to_yaml(self):
        yield "openai: 3.0.0"
        yield "info:"
        yield "servers:"
        for url,description in self.servers.items():
            yield f"  - url: {url}"
            yield f"    description: {description}"
        yield "paths:"
        for path,xx in self.paths.items():
            yield f"  {path}:"
            for m,serv in xx.items():
                yield f"    {m}:"
                yield from serv.to_yaml( "      " )

def main():
    # テスト用の辞書データ
    data = {
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

    sh:Schema = Schema()
    sh.init()

    for line in sh.to_yaml():
        print( line )


if __name__ == "__main__":
    main()