
import subprocess
from quart import Quart, request, jsonify

from .localcode import CodeRepo, CodeInter

repo:CodeRepo = CodeRepo( './tmp' )
app = Quart(__name__)

@app.route('/execute', methods=['POST'])
async def execute():
    data = await request.get_json()
    cmd_code = data.get('code')
    if not cmd_code:
        return jsonify({'error': 'No code provided'}), 400
    sid:str = data.get('sessionId')

    try:
        # Execute the code and capture the stdout and stderr separately
        iter:CodeInter = await repo.get_session(sid)
        out = await iter.command( cmd_code )
        return jsonify({
            'sessionId': iter.sid,
            'stdout': out,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        repo.return_session( iter )

SCHEMA="""openapi: 3.0.0
info:
    title: Local Python REPL API
    version: 1.0.0
servers:
    - url: http://192.168.1.60:5000
    description: Local server
paths:
  /execute:
    post:
      summary: Execute Python code
      description: Executes Python code on the local machine's REPL.
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                sessionId:
                  type: string
                  description: REPL session id. create new session if not present.
                  example: "abc123"
                code:
                  type: string
                  description: The Python code to execute.
                  example: "print('Hello, World!')"
      responses:
        '200':
          description: Successful execution
          content:
            application/json:
              schema:
                type: object
                properties:
                  sessionId:
                    type: string
                    description: REPL session id. use next call.
                    example: "abc123"
                  stdout:
                    type: string
                    description: The standard output from the executed code.
                    example: "Hello, World!\n"
        '400':
          description: Invalid request
          content:
            application/json:
              schema:
                type: object
                properties:
                  error:
                    type: string
                    description: Error message for invalid request.
                    example: "No code provided"
        '500':
          description: Internal server error
          content:
            application/json:
              schema:
                type: object
                properties:
                  error:
                    type: string
                    description: Error message for server error.
                    example: "Exception message"
"""

@app.route('/', methods=['GET'])
async def get_yaml():
    try:
        return SCHEMA
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
