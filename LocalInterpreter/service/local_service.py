import sys,os
import json
import traceback
import asyncio
from quart import Quart, request, Response, jsonify
sys.path.append(os.getcwd())
from LocalInterpreter.service.schema import ServiceSchema, BaseService, ServiceParam, ServiceResponse
import logging
logger = logging.getLogger('LocalSrv')

class QuartServiceBase(BaseService):
    def __init__(self,method):
        BaseService.__init__(self,method)
        self.name = ""
        self.description = ""

    async def before_serving(self):
        pass

    async def time_service(self):
        pass

    async def request_get_json(self):
        try:
            testb:bytes = await request.get_data()
            # text:str = testb.decode()
            data_json = json.loads( testb )
            #data_json = await request.get_json()
            if data_json:
                return data_json
        except:
            logger.exception('invalid requests')
        return {}

    async def service(self,subpath:str) ->tuple[dict,int]:
        logger.info( f"[QServ] path:{subpath} baseurl:{request.base_url}")
        data_json = {}
        if self.method == "post":
            data_json = await self.request_get_json()
        res_data, code = await self.acall( data_json )
        res_json, code = self.to_response_json( res_data, code )
        return res_json, code

    async def acall(self,args:dict, *, messages:list[dict]|None=None) ->tuple[dict|str,int]:
        return self.call(args, messages=messages )

    def call(self,args:dict, *, messages:list[dict]|None=None) ->tuple[dict|str,int]:
        # asyncio.run(self.acall(args))
        raise NotImplementedError()

class QuartServerBase(Quart,ServiceSchema):

    def __init__(self,import_name):
        Quart.__init__(self,import_name)
        ServiceSchema.__init__(self,import_name)
        self._service_ref:dict[str,QuartServiceBase] = {}
        @self.before_serving
        async def _xx_before():
            await self._x_before_serving()
        @self.route('/<path:subpath>',methods=['GET','POST'])
        async def _xx_serv(subpath):
            return await self._serve(subpath)
        @self.route('/')
        async def _xx_rserv():
            return await self._serve('/')

    def add_service(self, path:str, service:QuartServiceBase):
        ServiceSchema.add_service(self, path, service )
        key:str = f"{service.method.upper()}!!{path}"
        self._service_ref[key] = service

    async def _x_before_serving(self):
        # サーバーがリクエストを受け付ける前に実行される処理
        logger.info("Server is starting up, executing before_serving tasks")
        for service in self._service_ref.values():
            await service.before_serving()

    async def _serve(self,subpath) ->Response:
        logger.info( f"[Serv] path:{subpath} baseurl:{request.base_url}")
        key:str = f"{request.method.upper()}!!/{subpath}"
        service:QuartServiceBase|None = self._service_ref.get(key)
        if service:
            try:
                res_json,code = await service.service(subpath)
                return jsonify( res_json, status=code )
            except Exception as ex:
                logger.exception(f'execution error {subpath}:{service}')
                return jsonify({'error': f"{ex}"}, status=500)
        else:
            return await self.default()

    async def default(self) ->Response:
        try:
            xbase = request.base_url
            yaml = ""
            for line in self.to_yaml( request_url=xbase):
                yaml = f"{yaml}{line}\n"
            response:Response = Response( response=yaml, status=200)
            return response
        except Exception as e:
            response:Response = jsonify({'error': str(e)}, status=500)
            return response             
