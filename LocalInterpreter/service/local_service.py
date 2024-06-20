import sys,os
from quart import Quart, request, Response, jsonify
sys.path.append(os.getcwd())
from LocalInterpreter.service.schema import ServiceSchema, BaseService, ServiceParam, ServiceResponse

class QService(BaseService):
    def __init__(self,method):
        BaseService.__init__(self,method)
        self.summary = ""
        self.description = ""

    async def before_serving(self):
        pass

    async def service(self,subpath):
        print( f"[QServ] path:{subpath} baseurl:{request.base_url}")

class QServer(Quart,ServiceSchema):

    def __init__(self,import_name):
        Quart.__init__(self,import_name)
        ServiceSchema.__init__(self,import_name)
        self._service_ref:dict[str,QService] = {}
        @self.before_serving
        async def _xx_before():
            await self._x_before_serving()
        @self.route('/<path:subpath>',methods=['GET','POST'])
        async def _xx_serv(subpath):
            return await self._serve(subpath)
        @self.route('/')
        async def _xx_rserv():
            return await self._serve('/')

    def add_service(self, path:str, service:QService):
        ServiceSchema.add_service(self, path, service )
        key:str = f"{service.method}!!{path}"
        self._service_ref[key] = service

    async def _x_before_serving(self):
        # サーバーがリクエストを受け付ける前に実行される処理
        print("Server is starting up, executing before_serving tasks")
        for service in self._service_ref.values():
            await service.before_serving()

    async def _serve(self,subpath):
        print( f"[Serv] path:{subpath} baseurl:{request.base_url}")
        key:str = f"{request.method}!!{subpath}"
        service:QService = self._service_ref.get(key)
        if service:
            return await service.service(subpath)
        else:
            return await self.default()

    async def default(self):
        try:
            xbase = request.base_url
            yaml = ""
            for line in self.to_yaml( request_url=xbase):
                yaml = f"{yaml}{line}\n"
            response:Response = Response( response=yaml, status=200)
            return response
        except Exception as e:
            response:Response = Response( response=jsonify({'error': str(e)}), status=500, content_type="application/json")
            return response             
