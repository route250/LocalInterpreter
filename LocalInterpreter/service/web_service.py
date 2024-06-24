
from quart import request, Response, jsonify
from LocalInterpreter.service.local_service import QuartServiceBase, ServiceParam, ServiceResponse
import LocalInterpreter.utils.web as web
import LocalInterpreter.utils.trends as trends

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

    async def service(self,path):
        data_json = await self.request_get_json()
        keyword = data_json.get(INP_KEYWORD)
        if not keyword:
            return jsonify({'error': f'No {INP_KEYWORD} provided'}), 400

        try:
            result:list[dict] = web.google_search( keyword )
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

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

    async def before_serving(self):
        pass

    async def service(self,path):
        data_json = await self.request_get_json()
        url = data_json.get(INP_URL)
        if not url:
            return jsonify({'error': f'No {INP_URL} provided'}), 400
        limit = 1000
        try:
            result:str = web.get_text_from_url( url )
            if not result or len(result)==0:
                result = f"Can not extracted from {url}."
            elif len(result)<limit:
                result = f"Text extracted from {url}.\n\n{result}"
            elif len(result)>limit:
                summary_text = web.get_summary_from_text( result, length=limit )
                result = f"Text summarized from {url}.\n\n{summary_text}"
            return result
        except Exception as e:
            return jsonify({'error': str(e)}), 500

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

    async def before_serving(self):
        pass

    async def service(self,path):
        try:
            result:list[str] = trends.today_searches()
            return ' '.join(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500