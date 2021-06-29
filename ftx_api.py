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


def get_fills_history(key, secret, subaccount_name, market):
    url = 'https://ftx.com/api/fills?market={}&limit=1000'.format(market)
    resp = send_signed_request(url, key, secret, subaccount_name)
    if resp['success']:
        return resp['result']
    else:
        raise Exception(resp['error'])


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


def get_lending_rate(coin):
    resp = get('https://ftx.com/api/spot_margin/history')
    if resp.status_code == 200:
        for rate in resp.json()['result']:
            if rate['coin'] == coin:
                return rate['rate']
    else:
        raise Exception(resp.reason)


def get_price(market):
    resp = get('https://ftx.com/api/markets/{}'.format(market)).json()
    if resp['success']:
        return resp['result']['last']
    else:
        raise Exception(resp['error'])


def get_positions(key, secret, subaccont_name):
    url = 'https://ftx.com/api/positions?showAvgPrice=true'
    resp = send_signed_request(url, key, secret, subaccont_name)
    if resp['success']:
        return resp['result']
    else:
        raise Exception(resp['error'])


def get_orderbook(market):
    url = 'https://ftx.com/api/markets/{}/orderbook?depth=100'.format(market)
    resp = get(url)
    if resp.status_code == 200:
        return resp.json()['result']
    else:
        raise Exception(resp.reason)


def get_funding_payments(key, secret, subaccount_name, start_time='', end_time='', market=''):
    url = 'https://ftx.com/api/funding_payments'
    if start_time:
        url += '?start_time={}'.format(start_time)
    if end_time:
        if '?' in url:
            url += '&end_time={}'.format(end_time)
        else:
            url += '?end_time={}'.format(end_time)
    if market:
        if '?' in url:
            url += '&future={}'.format(market)
        else:
            url += '?future={}'.format(market)

    resp = send_signed_request(url, key, secret, subaccount_name)

    if resp['success']:
        return resp['result']
    else:
        raise Exception(resp['error'])


def get_borrow_history(key, secret, subaccount_name, start_time='', end_time=''):
    url = 'https://ftx.com/api/spot_margin/borrow_history'
    if start_time:
        url += '?start_time={}'.format(start_time)
    if end_time:
        if '?' in url:
            url += '&end_time={}'.format(end_time)
        else:
            url += '?end_time={}'.format(end_time)

    resp = send_signed_request(url, key, secret, subaccount_name)

    if resp['success']:
        return resp['result']
    else:
        raise Exception(resp['error'])


def get_historical_prices(market, resolution, start_time):
    url = 'https://ftx.com/api/markets/{}/candles?resolution={}&start_time={}'.format(market, resolution, start_time)
    resp = get(url)
    if resp.status_code == 200:
        return resp.json()['result']
    else:
        raise Exception(resp.reason)
