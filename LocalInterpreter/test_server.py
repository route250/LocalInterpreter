
import sys,os
sys.path.append(os.getcwd())
from LocalInterpreter.service.local_service import QServer, QService
from LocalInterpreter.service.python_service import PythonService
from LocalInterpreter.service.web_service import WebSearchService, WebGetService, WebTrendService

def test():
    app = QServer(__name__)
    pys:PythonService = PythonService()
    app.add_service( '/pythoninterpreter', pys )
    webs:WebSearchService = WebSearchService()
    app.add_service( '/websearch', webs )
    webg:WebGetService = WebGetService()
    app.add_service( '/webget', webg )
    trendswd:WebTrendService = WebTrendService()
    app.add_service( '/today_search', trendswd )

    for line in app.to_yaml( request_url='http://127.0.0.1:5000'):
        print( line )

    app.run(host='0.0.0.0', port=5000)

if __name__ == '__main__':
    test()
