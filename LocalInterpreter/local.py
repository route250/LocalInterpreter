
import sys,os
from quart import Quart, request, Response, jsonify
sys.path.append(os.getcwd())
from LocalInterpreter.localcode import CodeRepo, CodeSession

repo:CodeRepo = CodeRepo( './tmp' )
app = Quart(__name__)

@app.before_serving
async def before_serving():
    # バックグラウンドでstartup_taskを実行
    app.add_background_task( repo.setup )

@app.route('/execute', methods=['POST'])
async def execute():
    data = await request.get_json()
    cmd_code = data.get('code')
    if not cmd_code:
        return jsonify({'error': 'No code provided'}), 400
    sessionId:str = data.get('sessionId')

    try:
        # Execute the code and capture the stdout and stderr separately
        iter:CodeSession = await repo.get_session(sessionId)
        out = await iter.command( cmd_code )
        return jsonify({
            'sessionId': iter.sessionId,
            'stdout': out,
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

BASE_URL="@@@@@@"
SCHEMA=f"""openapi: 3.0.0
info:
  title: Local Python REPL API
  version: 1.0.0
servers:
  - url: {BASE_URL}
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
                  description: The session ID for maintaining the execution context. If left blank, a new session will be created and the session ID will be returned as part of the response. If provided, it should be the session ID from the previous call. Sessions expire after a certain period, and if an expired session ID is provided, a new session will be created and its ID will be returned.
                  example: "e2d21d32917941f78af7a1103a010daa"
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
                    description: The session ID for maintaining the execution context.
                    example: "e2d21d32917941f78af7a1103a010daa"
                  stdout:
                    type: string
                    description: The standard output from the executed code.
                    example: "Hello, World!"
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

# @app.route('/', methods=['GET'])
# async def get_yaml():
#     try:
#         xaddr = request.remote_addr
#         xbase = request.base_url
#         print( f"remote_addr:{xaddr}")
#         yaml:str = SCHEMA.replace( BASE_URL, xbase )
#         response:Response = Response( response=yaml, status=200)
#         return response
#     except Exception as e:
#         response:Response = Response( response=jsonify({'error': str(e)}), status=500, content_type="application/json")
#         return response

@app.route('/<path:path>', methods=['GET'])
async def do_get( path ):
    try:
        xaddr = request.remote_addr
        xbase = request.base_url
        print( f"remote_addr:{xaddr}")
        yaml:str = SCHEMA.replace( BASE_URL, xbase )
        response:Response = Response( response=yaml, status=200)
        return response
    except Exception as e:
        response:Response = Response( response=jsonify({'error': str(e)}), status=500, content_type="application/json")
        return response

@app.route('/', methods=['POST'])
async def do_post():
    try:
        raddr = request.remote_addr
        xbase = request.base_url
        request.path
        yaml:str = SCHEMA.replace( BASE_URL, xbase )
        response:Response = Response( response=yaml, status=200)
        return response
    except Exception as e:
        response:Response = Response( response=jsonify({'error': str(e)}), status=500, content_type="application/json")
        return response      

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
