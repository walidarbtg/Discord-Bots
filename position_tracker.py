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
bot = commands.Bot(command_prefix='#')


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


def calculate_days_to_expiry(month, day):
    today = datetime.today()

    if int(month) < today.month:
        year = today.year + 1
    else:
        year = today.year

    expiry = datetime(year, int(month), int(day))
    dtt = expiry - today

    return dtt.days


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

    # Total size
    total_size = current_future_price * future_position['size'] + current_spot_price * spot_position['total']

    # Premium
    entry_premium = (entry_futures_price / entry_spot_price - 1) * 100
    current_premium = (current_future_price / current_spot_price - 1) * 100

    expiry = future_market.split('-')[1]
    days_to_expiry = calculate_days_to_expiry(expiry[:2], expiry[2:])

    entry_date = datetime.strptime(entry_time, '%Y-%m-%dT%H:%M:%S')
    today = datetime.now()
    entry_to_now = (today - entry_date).days

    entry_premium_annualized = entry_premium / (days_to_expiry + entry_to_now) * 365
    current_premium_annualized = current_premium / days_to_expiry * 365

    # Position details
    position = {
        'average_spot_entry': '${:,.2f}'.format(entry_spot_price),
        'average_futures_entry': '${:,.2f}'.format(entry_futures_price),
        'total_size': '${:,.2f}'.format(total_size),
        'entry_premium': '{:.2f}%'.format(entry_premium),
        'entry_premium_annualized': '{:.2f}%'.format(entry_premium_annualized),
        'current_premium': '{:.2f}%'.format(current_premium),
        'current_premium_annualized': '{:.2f}%'.format(current_premium_annualized),
        'pnl': '${:,.2f}'.format(pnl),
        'fees_paid': '${:.2f}'.format(spot_entry['total_fees'] + future_entry['total_fees'])
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
            msg = '```Average Spot Entry: {}\n' \
                  'Average Futures Entry: {}\n' \
                  'Total Position Size: {}\n' \
                  'Premium at entry: {}\n' \
                  'Annualized premium at entry: {}\n' \
                  'Current premium: {}\n' \
                  'Current annualized premium: {}\n' \
                  'PNL: {}\n' \
                  'Fees paid: {}```\n'.format(position['average_spot_entry'], position['average_futures_entry'],
                                              position['total_size'], position['entry_premium'],
                                              position['entry_premium_annualized'], position['current_premium'],
                                              position['current_premium_annualized'], position['pnl'],
                                              position['fees_paid'])
            await ctx.channel.send(msg)


set_ftx_account('Walid', config['ftx_accounts']['main']['key'], config['ftx_accounts']['main']['secret'])

bot.run(config['bot_tokens']['ftx_arb_personal'])








