import time
import hmac
from requests import Request, Session, get


def get_account_info(key, secret, subaccount_name=""):
    url = 'https://ftx.com/api/account'
    resp = send_signed_request(url, key, secret, subaccount_name)
    if resp['success']:
        return resp['result']
    else:
        raise Exception(resp['error'])


def get_balances(key, secret, subaccount_name=""):
    url = 'https://ftx.com/api/wallet/balances'
    resp = send_signed_request(url, key, secret, subaccount_name)
    if resp['success']:
        return resp['result']
    else:
        raise Exception(resp['error'])


def get_account_usd_value(key, secret, subaccount_name=""):
    total_usd_value = 0
    balances = get_balances(key, secret, subaccount_name)
    for balance in balances:
        total_usd_value += balance['usdValue']
    return total_usd_value


def send_signed_request(url, key, secret, subaccount_name):
    ts = int(time.time() * 1000)
    request = Request('GET', url)
    prepared = request.prepare()
    signature_payload = f'{ts}{prepared.method}{prepared.path_url}'.encode()
    signature = hmac.new(secret.encode(),
                         signature_payload, 'sha256').hexdigest()

    prepared.headers['FTX-KEY'] = key
    prepared.headers['FTX-SIGN'] = signature
    prepared.headers['FTX-TS'] = str(ts)
    prepared.headers['FTX-SUBACCOUNT'] = subaccount_name
    session = Session()
    resp = session.send(prepared)
    return resp.json()


def get_ftx_borrow_rate(coin):
    resp = get('https://ftx.com/api/spot_margin/history')
    if resp.status_code == 200:
        for rate in resp.json()['result']:
            if rate['coin'] == coin:
                return rate['rate']
