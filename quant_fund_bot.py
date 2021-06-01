import ftx_api
import os
import json
import pandas as pd
from datetime import datetime
from discord.ext import commands, tasks

# Import config file
config = {}
config_path = os.path.dirname(os.path.abspath(__file__)) + '/config.json'
with open(config_path, 'r') as f:
    config = json.load(f)


bot = commands.Bot(command_prefix='.')


@bot.command(name='funding')
async def get_funding_returns(ctx, start_time='', end_time='', market=''):
    global config
    if ctx.channel.id == config['channel_ids']['quant_fund']:
        if start_time == 'help':
            help_msg = 'Usage example:\n `.funding start_time=2021-05-31 end_time=2021-06-01 market=BTC-PERP`'
            help_msg += '\nNote: arguments are optional'
            await ctx.channel.send(help_msg)
        else:
            try:
                if start_time:
                    start_time = start_time.split('=')[1]
                    start_time = int(datetime.strptime(start_time, '%Y-%m-%d').timestamp())
                if end_time:
                    end_time = end_time.split('=')[1]
                    end_time = int(datetime.strptime(end_time, '%Y-%m-%d').timestamp())
                if market:
                    market = market.split('=')[1]

                funding_payments = ftx_api.get_funding_payments(config['ftx_accounts']['main']['key'],
                                                                config['ftx_accounts']['main']['secret'],
                                                                'Quantfund', start_time, end_time, market)

                borrow_history = ftx_api.get_borrow_history(config['ftx_accounts']['main']['key'],
                                                            config['ftx_accounts']['main']['secret'],
                                                            'Quantfund', start_time, end_time)

                payments_received = 0
                for payment in funding_payments:
                    payments_received += payment['payment']

                borrow_cost = 0
                for borrow in borrow_history:
                    borrow_cost += borrow['cost']

                message = '```Funding Payments Received = ${:,.2f}' \
                          '\nBorrow Cost Paid = ${:,.2f}```'.format(0-payments_received, borrow_cost)

                await ctx.channel.send(message)
            except Exception as e:
                await ctx.channel.send(e)

bot.run(config['bot_tokens']['quant_fund_bot'])