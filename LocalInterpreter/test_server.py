
import sys,os
import logging
sys.path.append(os.getcwd())
from LocalInterpreter.service.local_service import QuartServerBase, QuartServiceBase
from LocalInterpreter.service.python_service import PythonService
from LocalInterpreter.service.web_service import WebSearchService, WebGetService, WebTrendService

import LocalInterpreter.utils.logger_util as log_util
logger = logging.getLogger('TestServer')

log_util.setup_logger( lv=logging.DEBUG, log_dir=os.path.join('tmp','logs') )

def test():
    app = QuartServerBase(__name__)
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
