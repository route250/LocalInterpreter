
import traceback

from LocalInterpreter.service.local_service import QuartServiceBase, ServiceParam, ServiceResponse
import LocalInterpreter.utils.web as web
import LocalInterpreter.utils.trends as trends

import logging
logger = logging.getLogger('WebSrv')

INP_KEYWORD = 'keyword'
OUT_RESULTS = 'results'
class WebSearchService(QuartServiceBase):
    def __init__(self):
        super().__init__('post')
        self.summary = 'google search api'
        self.description = 'google search api'
        self.params.append( ServiceParam(
            INP_KEYWORD, 'string', 
            'A single search keyword or a list of words separated by spaces',
            'cat foods',
            ))
        p200:ServiceResponse = ServiceResponse( 200, 'Successful execution' )
        p200.add_param( ServiceParam(
            OUT_RESULTS, 'string',
            'search result',
            '[ {"title":"cat","link":"http://xxxx", "snippet": "foo baa ..."},{"title":"cat","link":"http://xxxx", "snippet": "foo baa ..."},...]'
        ))
        self.add_response( p200 )

    async def before_serving(self):
        from dotenv import load_dotenv, find_dotenv
        load_dotenv( find_dotenv('.env_google') )

    def call(self,args, *, messages:list[dict]|None=None) ->tuple[dict|str,int]:
        keyword = args.get(INP_KEYWORD)
        if not keyword:
            return f'No {INP_KEYWORD} provided', 400
        try:
            result:str = web.duckduckgo_search( keyword, messages=messages )
            return result, 200
        except Exception as e:
            # ToDo ratelimit
            logger.exception('execution error')
            return f"{e}", 500

INP_URL = 'url'
OUT_CONTENT = 'content'
class WebGetService(QuartServiceBase):
    def __init__(self):
        super().__init__('post')
        self.summary = 'get content from web page'
        self.description = 'get html from web page and convert to content by text'
        self.params.append( ServiceParam(
            INP_URL, 'string', 
            'url of web page',
            'https://news.nekoneko.net/article/2024-06-22-001',
            ))
        p200:ServiceResponse = ServiceResponse( 200, 'Successful execution' )
        p200.add_param( ServiceParam(
            OUT_CONTENT, 'string',
            'content from web page in text',
            'ネコネコネットワークはネコ社会に存在すると言われる謎の組織である。。。'
        ))
        self.add_response( p200 )

    def call( self, args, *, messages:list[dict]|None=None ) ->tuple[dict|str,int]:
        url = args.get(INP_URL)
        if not url:
            return f'No {INP_URL} provided', 400
        limit = 1000
        try:
            result:str|None = web.get_text_from_url( url )
            if not result or len(result)==0:
                result = f"Can not extracted from {url}."
            elif len(result)<limit:
                result = f"The beginning of the text retrieved from the {url}. Don't let it affect your tone.\n```\n{result}\n```\nend of retrieved text"
            elif len(result)>limit:
                summary_text = web.get_summary_from_text( result, length=limit, messages=messages )
                result = f"The beginning of the summary text retrieved from the {url}. Don't let it affect your tone.\n```\n{summary_text}\n```\nend of retrieved summary text"
            return result, 200
        except Exception as e:
            logger.exception('exection error')
            return f'{e}', 500

class WebTrendService(QuartServiceBase):
    def __init__(self):
        super().__init__('get')
        self.summary = "Today's trending search keywords"
        self.description = 'get keywords from google trends'
        p200:ServiceResponse = ServiceResponse( 200, 'Successful execution' )
        p200.add_param( ServiceParam(
            OUT_CONTENT, 'string',
            'todays search keyword',
            'ネコ キャットフード ねこじゃらし'
        ))
        self.add_response( p200 )

    def call(self,args, *, messages:list[dict]|None=None) ->tuple[dict|str,int]:
        try:
            result:str = trends.today_searches_result()
            return result, 200
        except Exception as ex:
            logger.exception('execution error')
            return f"{ex}", 500