import ftx_api
import json
import os
import discord
from datetime import datetime
from discord.ext import commands


# Import config file
config = {}
config_path = os.path.dirname(os.path.abspath(__file__)) + '/config.json'
with open(config_path, 'r') as f:
    config = json.load(f)


bot = commands.Bot(command_prefix='!')


def calculate_days_to_expiry(month, day):
    today = datetime.today()

    if int(month) < today.month:
        year = today.year + 1
    else:
        year = today.year

    expiry = datetime(year, int(month), int(day))
    dtt = expiry - today

    return dtt.days


@bot.command(name='spread')
async def get_spread(ctx, arg):
    if ctx.channel.id == config['channel_ids']['commands']:
        if arg == 'help':
            help_msg = 'Usage example:\n `!spread sushi-0625`'
            await ctx.channel.send(help_msg)
        else:
            arg_list = arg.split('-')
            coin = arg_list[0]
            market = arg
            coin_price = 0
            futures_price = 0

            try:
                coin_price = ftx_api.get_price(coin + '/usd')
            except Exception as e:
                await ctx.channel.send(e)
                return

            try:
                futures_price = ftx_api.get_price(market)
            except Exception as e:
                await ctx.channel.send(e)
                return

            spread = (futures_price-coin_price)/coin_price * 100
            await ctx.channel.send('Premium is {:.2f}%'.format(spread))

            expiry = arg_list[1]
            days_to_expiry = calculate_days_to_expiry(expiry[:2], expiry[2:])
            annualized = spread / days_to_expiry * 365
            await ctx.channel.send('Annualized is {:.2f}%'.format(annualized))


def get_slippage(market, side, order_size_usd):
    last_price = ftx_api.get_price(market)
    orderbook = ftx_api.get_orderbook(market)
    average_price = 0
    remaining_size = order_size_usd

    if side == 'buy':
        for ask in orderbook['asks']:
            price = ask[0]
            size = ask[1]
            if remaining_size > (price * size):
                average_price += price * size / order_size_usd * price
                remaining_size -= price * size
            else:
                size = remaining_size / price
                average_price += price * size / order_size_usd * price
                break
    elif side == 'sell':
        for bid in orderbook['bids']:
            price = bid[0]
            size = bid[1]
            if remaining_size > (price * size):
                average_price += price * size / order_size_usd * price
                remaining_size -= price * size
            else:
                size = remaining_size / price
                average_price += price * size / order_size_usd * price
                break

    slippage = (last_price / average_price - 1) * 100
    return abs(slippage)


@bot.command(name='slippage')
async def get_trade_slippage(ctx, market, side='', size=''):
    await ctx.me.edit(nick='Helper')
    if ctx.channel.id == config['channel_ids']['commands']:
        if market == 'help':
            help_msg = 'Usage:\n `!slippage market side size` \n Example:\n`!slippage uni-0625 buy 25000`'
            await ctx.channel.send(help_msg)
        else:
            slippage = get_slippage(market, side, float(size))
            msg = '`Slippage = {:.2f}%`'.format(slippage)
            await ctx.channel.send(msg)


bot.run(config['bot_tokens']['spreads_bot'])
