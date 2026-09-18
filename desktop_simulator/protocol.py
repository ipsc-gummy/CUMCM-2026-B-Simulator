"""Attachment 2 wire validation. Validation never touches the core."""
import json
import math
import unicodedata

PATHS = {'/enter', '/measure', '/clear', '/exit'}
BASE = {'arena_id', 'robot_id', 'request_id'}

class HTTPError(ValueError):
    def __init__(self, status):
        self.status = status


def identifier(value, limit):
    if not isinstance(value, str):
        return False
    try:
        return 1 <= len(value.encode('utf-8')) <= limit and not any(
            unicodedata.category(c) in ('Cc', 'Cf') for c in value)
    except UnicodeEncodeError:
        return False


def decode(body):
    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj:
                raise HTTPError(400)
            obj[key] = value
        return obj
    def bad_constant(value):
        raise HTTPError(400)
    def finite_float(value):
        number = float(value)
        if not math.isfinite(number):
            raise HTTPError(400)
        return number
    def depth(obj, level=1):
        if isinstance(obj, (dict, list)):
            if level > 16:
                raise HTTPError(400)
            for value in (obj.values() if isinstance(obj, dict) else obj):
                depth(value, level + 1)
    try:
        obj = json.loads(body.decode('utf-8'), object_pairs_hook=pairs, parse_constant=bad_constant, parse_float=finite_float)
        if not isinstance(obj, dict):
            raise HTTPError(400)
        depth(obj)
        return obj
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise HTTPError(400) from exc


def validate(path, obj):
    required = BASE | ({'position', 'channel'} if path in ('/measure', '/clear') else set())
    if not required <= obj.keys():
        raise HTTPError(400)
    if not isinstance(obj['arena_id'], str) or not identifier(obj['robot_id'], 64) or not identifier(obj['request_id'], 128):
        raise HTTPError(400)
    unknown = bool(obj.keys() - required)
    if 'position' in required:
        p, ch = obj['position'], obj['channel']
        if not isinstance(p, dict) or not {'x', 'y'} <= p.keys():
            raise HTTPError(400)
        unknown |= bool(p.keys() - {'x', 'y'})
        for value in (p['x'], p['y']):
            if type(value) not in (int, float) or not -2000000 <= value <= 2000000:
                raise HTTPError(400)
        if type(ch) not in (int, float) or not 1 <= ch <= 20 or int(ch) != ch:
            raise HTTPError(400)
    return not unknown


def media_type(headers):
    if len(headers.get_all('Content-Type', [])) != 1 or len(headers.get_all('Content-Encoding', [])) > 1:
        raise HTTPError(415)
    parts = [p.strip().lower() for p in headers.get('Content-Type', '').split(';')]
    if parts not in (['application/json'], ['application/json', 'charset=utf-8']):
        raise HTTPError(415)
    if headers.get('Content-Encoding', 'identity').strip().lower() != 'identity':
        raise HTTPError(415)
