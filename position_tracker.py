import ftx_api
import discord
import json
import os
from datetime import datetime
from discord.ext import tasks, commands

# Global
ACCOUNT = {
    "name": "",
    "key": "",
    "secret": ""
}

# Import config file
config = {}
config_path = os.path.dirname(os.path.abspath(__file__)) + '/config.json'
with open(config_path, 'r') as f:
    config = json.load(f)


# Discord Bot
bot = commands.Bot(command_prefix='!')


def set_ftx_account(name, key, secret):
    global ACCOUNT
    ACCOUNT['name'] = name
    ACCOUNT['key'] = key
    ACCOUNT['secret'] = secret


def get_position_entry(market, entry_ts):
    fills = ftx_api.get_fills_history(ACCOUNT['key'], ACCOUNT['secret'], ACCOUNT['name'], market)

    if len(fills) > 0:
        full_size = 0
        average_price = 0
        total_fees = 0

        for fill in fills:
            fill_ts = int(datetime.strptime(fill['time'], '%Y-%m-%dT%H:%M:%S.%f%z').timestamp() * 1000)
            if fill_ts >= entry_ts:
                full_size += fill['price'] * fill['size']

        for fill in fills:
            fill_ts = int(datetime.strptime(fill['time'], '%Y-%m-%dT%H:%M:%S.%f%z').timestamp() * 1000)
            if fill_ts >= entry_ts:
                amount_paid = fill['size'] * fill['price']
                weight = amount_paid / full_size
                average_price += fill['price'] * weight
                if fill['feeCurrency'] == 'USD':
                    total_fees += fill['fee']
                else:
                    total_fees += fill['fee'] * fill['price']

        # TODO: find the issue with average price, maybe a miscalculation cuz it does not match the average calculted by FTX for the futures
        return {
            'average_price': average_price,
            'total_fees': total_fees
        }
    else:
        return "No position found"


def get_spot_position_entry(market, entry_time):
    entry_ts = int(datetime.strptime(entry_time, '%Y-%m-%dT%H:%M:%S').timestamp() * 1000)
    return get_position_entry(market, entry_ts)


def get_futures_position_entry(market, entry_time):
    entry_ts = int(datetime.strptime(entry_time, '%Y-%m-%dT%H:%M:%S').timestamp() * 1000)
    return get_position_entry(market, entry_ts)


def get_current_position(spot_market, future_market, entry_time):
    # Entry
    spot_entry = get_spot_position_entry(spot_market, entry_time)
    future_entry = get_futures_position_entry(future_market, entry_time)
    entry_spot_price = spot_entry['average_price']
    entry_futures_price = future_entry['average_price']

    # Spot
    spot_position = {}
    balances = ftx_api.get_balances(ACCOUNT['key'], ACCOUNT['secret'], ACCOUNT['name'])
    for balance in balances:
        if balance['coin'] + '/USD' == spot_market:
            spot_position = balance
            break
    current_spot_price = ftx_api.get_price(spot_market)

    # Futures
    future_position = {}
    positions = ftx_api.get_positions(ACCOUNT['key'], ACCOUNT['secret'], ACCOUNT['name'])
    for position in positions:
        if position['future'] == future_market:
            future_position = position
            break
    current_future_price = ftx_api.get_price(future_market)

    # Current position
    futures_pnl = (current_future_price - entry_futures_price) * future_position['netSize']
    spot_pnl = (current_spot_price - entry_spot_price) * spot_position['total']

    # Total pnl
    # TODO: the PNL doesnt seem to match the usd wallet balance on the website, investigate
    pnl = spot_pnl + futures_pnl

    # Position details
    position = {
        'average_spot_entry': entry_spot_price,
        'average_futures_entry': entry_futures_price,
        'entry_premium': (entry_futures_price / entry_spot_price - 1) * 100,
        'current_premium': (current_future_price / current_spot_price - 1) * 100,
        'unrealized_profit': ((entry_futures_price / entry_spot_price - 1) - (current_future_price / current_spot_price - 1)) * 100,
        'realized_profit': pnl / (entry_futures_price * future_position['size'] + entry_spot_price * spot_position['total']) * 100,
        'pnl': pnl,
        'fees_paid': spot_entry['total_fees'] + future_entry['total_fees']
    }
    return position


@bot.command(name='position')
async def get_position(ctx, futures_market, date=''):
    if ctx.channel.id == config['channel_ids']['ftx-arb-personal']:
        if futures_market == 'help':
            help_msg = 'Usage:\n `!position future-market entry_date` \n Example:\n`!position uni-0625 2021-05-13`'
            await ctx.channel.send(help_msg)
        else:
            coin = futures_market.split('-')[0]
            date = date + 'T00:00:00'
            position = get_current_position(coin + '/USD', futures_market, date)
            msg = '```{}```'.format(position)
            await ctx.channel.send(msg)


bot.run(config['bot_tokens']['ftx_arb_personal'])








