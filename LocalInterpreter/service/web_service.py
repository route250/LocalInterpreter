


from quart import request, Response, jsonify
from LocalInterpreter.service.local_service import QService, ServiceParam, ServiceResponse
import LocalInterpreter.utils.web as web

INP_KEYWORD = 'keyword'
OUT_RESULTS = 'results'
class WebSearchService(QService):
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

    async def setup(self):
        pass

    async def service(self,path):
        data = await request.get_json()
        keyword = data.get(INP_KEYWORD)
        if not keyword:
            return jsonify({'error': f'No {INP_KEYWORD} provided'}), 400

        try:
            result:list[dict] = web.google_search( keyword )
            return jsonify(result)
        except Exception as e:
            return jsonify({'error': str(e)}), 500

INP_URL = 'url'
OUT_CONTENT = 'content'
class WebGetService(QService):
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

    async def setup(self):
        pass

    async def service(self,path):
        data = await request.get_json()
        url = data.get(INP_URL)
        if not url:
            return jsonify({'error': f'No {INP_URL} provided'}), 400

        try:
            result:str = web.get_text_from_url( url )
            return result
        except Exception as e:
            return jsonify({'error': str(e)}), 500