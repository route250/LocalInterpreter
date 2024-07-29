import json
import asyncio
from asyncio import AbstractEventLoop as EvLoop

from LocalInterpreter.service.local_service import QuartServiceBase, ServiceParam, ServiceResponse
from LocalInterpreter.interpreter.localcode import get_os_info, get_python_info, CodeRepo, CodeSession
import LocalInterpreter.utils.web as web

import logging
logger = logging.getLogger('PythonSrv')

class PythonService(QuartServiceBase):
    def __init__(self, *, directory:str|None=None):
        super().__init__('post')
        self.summary = 'python interpreter'
        self.os_info = get_os_info()
        self.python_info = get_python_info()
        self.description = f"python interpreter of {self.python_info} {self.os_info}.\n"
        if not isinstance(directory,str):
            directory = './tmp'
        self.repo:CodeRepo = CodeRepo( directory )
        self.params.append( ServiceParam(
            'sessionId', 'string', 
            'The session ID for maintaining the execution context. If left blank, a new session will be created and the session ID will be returned as part of the response. If provided, it should be the session ID from the previous call. Sessions expire after a certain period, and if an expired session ID is provided, a new session will be created and its ID will be returned.',
            '\"e2d21d32917941f78af7a1103a010daa\"',
            ))
        self.params.append( ServiceParam(
            'code', 'string',
            'The specified code is executed by the exec(...) function in the Python interpreter.',
            '\"print(\'Hello, World!\')\"',
        ) )
        self.params.append( ServiceParam(
            'download_url', 'string',
            'Download a file from a URL to the session directory using the http get method.Blank if not needed',
            'https://sample.domain.com/data/file.gz',
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

    async def before_serving(self):
        await self.repo.setup()

    async def acall(self,args, *, messages:list[dict]|None=None) ->tuple[dict|str,int]:
        # args = await self.request_get_json()
        sessionId:str|None = args.get('sessionId')
        cmd_code:str|None = args.get('code')
        download_url:str|None = args.get('download_url')

        try:
            result_out:list[str] = []
            session:CodeSession = await self.repo.get_session(sessionId)
            if download_url:
                filename, mesg = await session.download_from_url( download_url )
                result_out.append( mesg )
            # Execute the code and capture the stdout and stderr separately
            if cmd_code:
                out = await session.command( cmd_code )
                result_out.append(out)

            return {
                'sessionId': session.sessionId,
                'stdout': '\n\n'.join(result_out),
            }, 200

        except Exception as ex:
            logger.exception('execution error')
            return f"{ex}",500

    def call(self,args, *, messages:list[dict]|None=None) ->tuple[dict|str,int]:
        sessionId:str|None = args.get('sessionId')
        loop:EvLoop = self.repo.get_event_loop(sessionId)
        if loop is None:
            try:
                loop = asyncio.get_running_loop()
            except:
                loop = asyncio.new_event_loop()
        return loop.run_until_complete(self.acall(args, messages=messages))
