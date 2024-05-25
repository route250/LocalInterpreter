from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

@app.route('/execute', methods=['POST'])
def execute():
    data = request.json
    code = data.get('code')
    if not code:
        return jsonify({'error': 'No code provided'}), 400

    try:
        # Execute the code and capture the stdout and stderr separately
        result = subprocess.run(
            ['python3', '-c', code],
            capture_output=True,
            text=True
        )
        return jsonify({
            'stdout': result.stdout,
            'stderr': result.stderr
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
                  stdout:
                    type: string
                    description: The standard output from the executed code.
                    example: "Hello, World!\n"
                  stderr:
                    type: string
                    description: The error output from the executed code.
                    example: "SyntaxError: invalid syntax\n"
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
def get_yaml():
    try:
        return SCHEMA
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
