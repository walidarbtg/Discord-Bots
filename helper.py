import json
import os
import sys
import traceback
import math
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from discord.ext import commands
from statsmodels.tsa.stattools import OLS, add_constant
from exchange.ftx.client import FtxClient

# Initialization
client = FtxClient()
bot = commands.Bot(command_prefix='!')

# Import config file
config = {}
config_path = os.path.dirname(os.path.abspath(__file__)) + '/config.json'
with open(config_path, 'r') as f:
    config = json.load(f)


@bot.command(name='beta')
async def get_beta(ctx, asset_a, asset_b="", period="", resolution_minutes=""):
    if ctx.channel.id == config['channel_ids']['commands_test']:
        if asset_a == 'help':
            help_msg = 'Usage:\n You want to check the beta between eth and btc based on last 10 days of 5min data \n Example:\n`!beta eth-perp btc-perp 30days 5min`'
            help_msg += '\nMethodology: Uses OLS Linear Regression. Tries both permutations and returns the mean of beta. \n`beta_mean = (beta_1 + 1/beta_2) / 2`'
            await ctx.channel.send(help_msg)
        else:
            period = int(period.replace('days', ''))
            resolution_minutes = int(resolution_minutes.replace('min', ''))
            # Check if period and resolution match (we have a limit of 5000 datapoints)
            max_period_allowed = int(5000 * resolution_minutes / 60 / 24)
            if period > max_period_allowed:
                msg = '`Maximum period allowed for this resolution is {} days`'.format(max_period_allowed)
                await ctx.channel.send(msg)
            else:
                try:
                    # Calculate start_time
                    start_date = datetime.today() - timedelta(days=period)
                    start_time_ts = int(start_date.timestamp())
                    end_time_ts = int(datetime.today().timestamp())

                    # Get price data
                    resolution_seconds = resolution_minutes * 60
                    data_a = pd.DataFrame(client.get_historical_data(asset_a, resolution_seconds, 5000, start_time_ts, end_time_ts))
                    data_b = pd.DataFrame(client.get_historical_data(asset_b, resolution_seconds, 5000, start_time_ts, end_time_ts))
                    data_a['startTime'] = data_a['startTime'].apply(lambda x: datetime.fromisoformat(x))
                    data_a_returns = data_a['close'].pct_change().dropna()
                    data_a_log_returns = (data_a_returns + 1).apply(lambda x: math.log(x))
                    data_b['startTime'] = data_b['startTime'].apply(lambda x: datetime.fromisoformat(x))
                    data_b_returns = data_b['close'].pct_change().dropna()
                    data_b_log_returns = (data_b_returns + 1).apply(lambda x: math.log(x))

                    # Calculate correlation
                    corr = data_a_log_returns.corr(data_b_log_returns, method='pearson')
                    msg = 'Correlation = `{:.2f}`\n'.format(corr)

                    # Calculate beta
                    model = OLS(data_a_log_returns, add_constant(data_b_log_returns))
                    reg = model.fit()
                    beta_1 = reg.params[1]
                    model2 = OLS(data_b_log_returns, add_constant(data_a_log_returns))
                    reg2 = model2.fit()
                    beta_2 = reg2.params[1]

                    beta = (beta_1 + 1/beta_2) / 2

                    if beta > 0:
                        msg += 'Beta = `{:.2f}` \nFor `$100` of `{}`, you need `${:.2f}` of `{}`'.format(beta, asset_a, 100*beta, asset_b)
                    else:
                        msg += 'Beta is negative, meaning the correlation is probably negative. Not an ideal candidate for a pair trade'
                    await ctx.channel.send(msg)
                except Exception as e:
                    err = traceback.format_exception(*sys.exc_info())[-1]
                    await ctx.channel.send(err)

bot.run(config['arb_helper_token'])
