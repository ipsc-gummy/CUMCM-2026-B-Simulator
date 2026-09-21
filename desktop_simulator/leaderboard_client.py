"""HTTPS-only Leaderboard client isolated from the local simulator runtime."""
from concurrent.futures import ThreadPoolExecutor
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, HTTPCookieProcessor, Request, build_opener
import json
import socket
import ssl
import threading
import uuid

from PySide6.QtCore import QObject, Signal


DEFAULT_BASE_URL = 'https://47.236.21.46'


class LeaderboardError(RuntimeError):
    def __init__(self, message, kind='request', status_code=None):
        super().__init__(message)
        self.kind = kind
        self.status_code = status_code


class HTTPSRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != 'https':
            raise LeaderboardError('排行榜拒绝了非 HTTPS 跳转。')
        return super().redirect_request(request, fp, code, msg, headers, newurl)


class LeaderboardAPI:
    """Small synchronous API used only from LeaderboardGateway worker threads."""
    def __init__(self, base_url=DEFAULT_BASE_URL, timeout=8, opener=None):
        base_url = base_url.rstrip('/')
        parsed = urlsplit(base_url)
        if parsed.scheme != 'https' or not parsed.netloc or parsed.path:
            raise ValueError('排行榜地址必须是 HTTPS origin')
        self.base_url = base_url
        self.timeout = timeout
        self.cookies = CookieJar()
        self.opener = opener or build_opener(HTTPCookieProcessor(self.cookies), HTTPSRedirectHandler())
        self.lock = threading.RLock()
        self.csrf_token = ''
        self.user = None

    def _request(self, path, method='GET', payload=None, text=False, raw_body=None, content_type=None, timeout=None):
        if not path.startswith('/'):
            raise ValueError('API path must start with /')
        url = urljoin(self.base_url + '/', path.lstrip('/'))
        headers = {'Accept': 'application/json', 'User-Agent': 'Q3Q4-Simulator/30.0'}
        body = None
        if payload is not None and raw_body is not None: raise ValueError('payload and raw_body are mutually exclusive')
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        elif raw_body is not None:
            body=raw_body;headers['Content-Type']=content_type
        if method != 'GET':
            headers['Origin'] = self.base_url
            headers['X-CSRF-Token'] = self.csrf_token
        try:
            with self.lock:
                with self.opener.open(Request(url, data=body, headers=headers, method=method), timeout=timeout or self.timeout) as response:
                    if hasattr(response,'geturl') and urlsplit(response.geturl()).scheme != 'https':
                        raise LeaderboardError('排行榜响应不是 HTTPS。')
                    raw = response.read()
                if text:
                    return raw.decode('utf-8')
                result = json.loads(raw.decode('utf-8'))
        except HTTPError as exc:
            try:
                detail = json.loads(exc.read().decode('utf-8')).get('detail')
            except Exception:
                detail = None
            if isinstance(detail, list):
                detail = '；'.join(item.get('msg', str(item)) if isinstance(item, dict) else str(item) for item in detail)
            if exc.code == 401 and path not in ('/api/auth/login', '/api/auth/register'):
                error = LeaderboardError('登录状态已失效，请重新登录。', 'auth', 401)
            elif exc.code == 413:
                error = LeaderboardError('上传文件超过大小限制。', 'upload_too_large', 413)
            elif exc.code == 429:
                error = LeaderboardError('操作过于频繁，请稍后再试。', 'rate_limited', 429)
            elif exc.code >= 500:
                error = LeaderboardError('排行榜服务暂时不可用，本地模拟器仍可正常使用。', 'service_unavailable', exc.code)
            else:
                error = LeaderboardError(str(detail or '排行榜请求未完成，请稍后重试。'), 'request', exc.code)
            raise error from exc
        except (URLError, TimeoutError, socket.timeout, ssl.SSLError, OSError) as exc:
            raise LeaderboardError('排行榜服务暂时不可用，本地模拟器仍可正常使用。', 'service_unavailable') from exc
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise LeaderboardError('排行榜返回了无法识别的数据。') from exc
        return result

    def session(self):
        result = self._request('/api/auth/session')
        self.csrf_token = result['csrf_token']
        self.user = result.get('user')
        return result

    def _authenticate(self, endpoint, username, password):
        if not self.csrf_token:
            self.session()
        result = self._request(endpoint, 'POST', {'username': username, 'password': password})
        self.csrf_token = result['csrf_token']
        self.user = result['user']
        return result

    def login(self, username, password):
        return self._authenticate('/api/auth/login', username, password)

    def register(self, username, password):
        return self._authenticate('/api/auth/register', username, password)

    def logout(self):
        result = self._request('/api/auth/logout', 'POST', {})
        self.csrf_token = ''
        self.user = None
        self.cookies.clear()
        return result

    def leaderboard(self, task):
        if task not in ('q3', 'q4'):
            raise ValueError('task must be q3 or q4')
        return self._request('/api/leaderboard?' + urlencode({'task': task}))

    def metadata(self):
        return self._request('/api/meta')

    def dashboard(self):
        return {'teams': self._request('/api/teams'), 'submissions': self._request('/api/me/submissions')}

    def create_personal_team(self, username):
        return self._request('/api/teams', 'POST', {'team_name': username})

    def submit_strategy(self, team_id, task, source_path, entrypoint, dependencies='', readme='', description='', open_source=False, consent=False):
        source=Path(source_path)
        if source.suffix.lower()!='.zip' or not source.is_file():raise LeaderboardError('请选择有效的 source.zip。')
        content=source.read_bytes()
        if len(content)>10*1024*1024:raise LeaderboardError('上传文件超过大小限制。','upload_too_large',413)
        sid=self._request('/api/submissions','POST',{'team_id':team_id,'task':task})['id']
        boundary='----Q3Q4'+uuid.uuid4().hex
        chunks=[]
        def field(name,value):
            chunks.extend([f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),str(value).encode('utf-8'),b'\r\n'])
        fields={'readme':readme,'entrypoint':entrypoint,'dependencies':dependencies,'description':description,
                'open_source':str(bool(open_source)).lower(),'consent':str(bool(consent)).lower()}
        for name,value in fields.items():field(name,value)
        chunks.extend([f'--{boundary}\r\nContent-Disposition: form-data; name="source"; filename="source.zip"\r\nContent-Type: application/zip\r\n\r\n'.encode(),content,b'\r\n',f'--{boundary}--\r\n'.encode()])
        result=self._request(f'/api/submissions/{sid}/source','POST',raw_body=b''.join(chunks),content_type='multipart/form-data; boundary='+boundary,timeout=60)
        return {'id':sid,**result}

    def code(self, submission_id):
        return self._request(f'/api/submissions/{quote(submission_id, safe="")}/code')

    def code_file(self, submission_id, path):
        query = urlencode({'path': path})
        return self._request(f'/api/submissions/{quote(submission_id, safe="")}/code/file?{query}', text=True)

    def owner_code(self, submission_id):
        return self._request(f'/api/submissions/{quote(submission_id, safe="")}/source')

    def owner_code_file(self, submission_id, path):
        query=urlencode({'path':path})
        return self._request(f'/api/submissions/{quote(submission_id, safe="")}/source/file?{query}',text=True)


class _ResultBus(QObject):
    finished = Signal(str, object, object)


class LeaderboardGateway(QObject):
    """Runs every remote call away from Qt and simulator threads."""
    def __init__(self, api=None, parent=None):
        super().__init__(parent)
        self.api = api or LeaderboardAPI()
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='leaderboard')
        self.bus = _ResultBus(self)
        self.bus.finished.connect(self._deliver)
        self.callbacks = {}
        self.closed = False

    def call(self, method, callback, *args):
        if self.closed:
            return None
        token = uuid.uuid4().hex
        self.callbacks[token] = callback

        def run():
            result = error = None
            try:
                result = getattr(self.api, method)(*args)
            except Exception as exc:
                error = exc if isinstance(exc, LeaderboardError) else LeaderboardError(str(exc))
            self.bus.finished.emit(token, result, error)

        self.pool.submit(run)
        return token

    def _deliver(self, token, result, error):
        callback = self.callbacks.pop(token, None)
        if callback and not self.closed:
            callback(result, error)

    def close(self):
        self.closed = True
        self.callbacks.clear()
        self.pool.shutdown(wait=False, cancel_futures=True)
