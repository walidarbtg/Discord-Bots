import hmac
import time
import hashlib
import requests
from urllib.parse import urlencode

API_URL = 'https://api.binance.com'
FAPI_URL = 'https://fapi.binance.com'

def hashing(secret, query_string):
    return hmac.new(secret.encode('utf-8'), query_string.encode('utf-8'), hashlib.sha256).hexdigest()


def get_timestamp():
    return int(time.time() * 1000)


def dispatch_request(key, http_method):
    session = requests.Session()
    session.headers.update({
        'Content-Type': 'application/json;charset=utf-8',
        'X-MBX-APIKEY': key
    })
    return {
        'GET': session.get,
        'DELETE': session.delete,
        'PUT': session.put,
        'POST': session.post,
    }.get(http_method, 'GET')


# used for sending request requires the signature
def send_signed_request(base, api, http_method, url_path, payload={}):
    query_string = urlencode(payload, True)

    if query_string:
        query_string = "{}&timestamp={}".format(query_string, get_timestamp())
    else:
        query_string = 'timestamp={}'.format(get_timestamp())

    url = base + url_path + '?' + query_string + '&signature=' + hashing(api['secret'], query_string)
    params = {'url': url, 'params': {}}
    response = dispatch_request(api['key'], http_method)(**params)

    try:
        return response.json()
    except:
        return response


def get_isolated_margin_data(api):
    response = send_signed_request(API_URL, api, 'GET', '/sapi/v1/margin/isolatedMarginData')
    if type(response) != list:
        error = 'Fetch Isolated Margin data error: ' + response
        raise RuntimeError(error)
    else:
        return response


def get_mark_prices(api):
    response = send_signed_request(FAPI_URL, api, 'GET', '/fapi/v1/premiumIndex')
    if type(response) != list:
        error = 'Fetch mark prices data error: ' + response
        raise RuntimeError(error)
    else:
        return response