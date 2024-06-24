
from quart import request, Response, jsonify
from LocalInterpreter.service.local_service import QuartServiceBase, ServiceParam, ServiceResponse
from LocalInterpreter.interpreter.localcode import CodeRepo, CodeSession
import LocalInterpreter.utils.web as web

class PythonService(QuartServiceBase):
    def __init__(self, *, directory:str=None):
        super().__init__('post')
        self.summary = 'python interpreter'
        self.description = 'python interpreter'
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
            'The Python code to execute.',
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

    async def service(self,path):
        data_json = await self.request_get_json()
        sessionId:str = data_json.get('sessionId')
        cmd_code = data_json.get('code')
        download_url = data_json.get('download_url')

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

            return jsonify({
                'sessionId': session.sessionId,
                'stdout': '\n\n'.join(result_out),
            })

        except Exception as e:
            return jsonify({'error': str(e)}), 500