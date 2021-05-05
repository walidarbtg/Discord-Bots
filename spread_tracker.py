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

            price_resp = ftx_api.get_price(coin + '/usd')
            if price_resp['success']:
                coin_price = price_resp['result']['last']
            else:
                await ctx.channel.send(price_resp['error'])
                return

            futures_resp = ftx_api.get_price(market)
            if futures_resp['success']:
                futures_price = futures_resp['result']['last']
            else:
                await ctx.channel.send(futures_resp['error'])
                return

            spread = (futures_price-coin_price)/coin_price * 100
            await ctx.channel.send('Premium is {:.2f}%'.format(spread))

            expiry = arg_list[1]
            days_to_expiry = calculate_days_to_expiry(expiry[:2], expiry[2:])
            annualized = spread / days_to_expiry * 365
            await ctx.channel.send('Annualized is {:.2f}%'.format(annualized))


bot.run(config['spreads_bot']['token'])
