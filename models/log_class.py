import json

class Log:
    def __init__(self, url: str):
        self.url       = url
        self.jcontent  = None
        self.pjcontent = None
    
    def set_jcontent(self, http_response):       
        content        = http_response.content.decode("utf-8")
        # I edited this part for the log to work why did variable names change holy fuck kys
        java_data_text = content.split('const _logData = ')[1].split('const _crData = ')[0].rsplit(';', 1)[0].strip()
        #java_data_text = content.split('var _logData = ')[1].split('var logData = _logData;')[0].rsplit(';', 1)[0].strip()
        self.jcontent  = json.loads(java_data_text)

    def set_pjcontent(self, http_response):
        # Guard against None responses (network error) and invalid JSON
        if http_response is None:
            print(f"set_pjcontent: http_response is None for url={self.url}")
            self.pjcontent = None
            return

        try:
            self.pjcontent = http_response.json()
        except Exception as e:
            # Could be requests.exceptions.JSONDecodeError or ValueError
            resp_info = getattr(http_response, 'url', '<no-url>')
            status = getattr(http_response, 'status_code', '<no-status>')
            print(f"Failed to parse JSON from response (url={resp_info}, status={status}): {e}")
            # Fallback: mark as None so downstream code (BossFactory) will skip this log
            self.pjcontent = None