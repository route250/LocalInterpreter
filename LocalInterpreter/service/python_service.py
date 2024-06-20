


from quart import request, Response, jsonify
from LocalInterpreter.service.local_service import QService, ServiceParam, ServiceResponse
from LocalInterpreter.interpreter.localcode import CodeRepo, CodeSession

class PythonService(QService):
    def __init__(self):
        super().__init__('POST')
        self.repo:CodeRepo = CodeRepo( './tmp' )
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

    async def setup(self):
        await self.repo.setup()

    async def service(self,path):
        data = await request.get_json()
        cmd_code = data.get('code')
        if not cmd_code:
            return jsonify({'error': 'No code provided'}), 400
        sessionId:str = data.get('sessionId')

        try:
            # Execute the code and capture the stdout and stderr separately
            iter:CodeSession = await self.repo.get_session(sessionId)
            out = await iter.command( cmd_code )
            return jsonify({
                'sessionId': iter.sessionId,
                'stdout': out,
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500