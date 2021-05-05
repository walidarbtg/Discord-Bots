import discord
import json
import time
import hmac
import os
from datetime import datetime
from requests import Request, Session, get

# Import config file
config = {}
config_path = os.path.dirname(os.path.abspath(__file__)) + '/config.json'
with open(config_path, 'r') as f:
    config = json.load(f)


def get_account_info(key, secret, subaccount_name=""):
    url = 'https://ftx.com/api/account'
    resp = send_signed_request(url, key, secret, subaccount_name).json()
    if resp['success']:
        return resp.json()['result']
    else:
        raise Exception(resp['error'])
    

def send_signed_request(url, key, secret, subaccount_name):
    ts = int(time.time() * 1000)
    request = Request('GET', url)
    prepared = request.prepare()
    signature_payload = f'{ts}{prepared.method}{prepared.path_url}'.encode()
    signature = hmac.new(secret.encode(), signature_payload, 'sha256').hexdigest()

    request.headers['FTX-KEY'] = key
    request.headers['FTX-SIGN'] = signature
    request.headers['FTX-TS'] = str(ts)
    if subaccount_name:
        request.headers['FTX-SUBACCOUNT'] = subaccount_name

    session = Session()
    resp = session.send(prepared)
    return resp

try:
    test = get_account_info(config['test_account']['key'], 
                            config['test_account']['secret'], 
                            config['test_account']['subaccount_name'])
    print(test)
except Exception as e:
    print('An error occured: {}'.format(e))
