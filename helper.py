import json
import os
import discord
import math
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from discord.ext import commands
from statsmodels.tsa.stattools import OLS, add_constant
from exchange.ftx.client import FtxClient
from sklearn.linear_model import Ridge

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
    period = int(period)
    resolution_minutes = int(resolution_minutes)
    if ctx.channel.id == config['channel_ids']['commands_test']:
        if asset_a == 'help':
            help_msg = 'Usage:\n `!beta asset_a asset_b period(in days) resolution(in min)` \n Example:\n`!beta eth-perp btc-perp 30 5`'
            await ctx.channel.send(help_msg)
        else:
            # Check if period and resolution match (we have a limit of 5000 datapoints)
            max_period_allowed = int(5000 * resolution_minutes / 60 / 24)
            if period > max_period_allowed:
                msg = '`Maximum period allowed for this resolution is {} days`'.format(max_period_allowed)
                await ctx.channel.send(msg)
            else:
                # Calculate start_time
                start_date = datetime.today() - timedelta(days=period)
                start_time_ts = int(start_date.timestamp())
                end_time_ts = int(datetime.today().timestamp())

                # Get price data
                resolution_seconds = resolution_minutes * 60
                data_a = pd.DataFrame(client.get_historical_data(asset_a, resolution_seconds, 5000, start_time_ts, end_time_ts))
                data_b = pd.DataFrame(client.get_historical_data(asset_b, resolution_seconds, 5000, start_time_ts, end_time_ts))
                data_a['startTime'] = data_a['startTime'].apply(lambda x: datetime.fromisoformat(x))
                data_a['log_price'] = data_a['close'].apply(lambda x: math.log(x))
                data_a['log_returns'] = data_a['log_price'].pct_change()
                data_b['startTime'] = data_b['startTime'].apply(lambda x: datetime.fromisoformat(x))
                data_b['log_price'] = data_b['close'].apply(lambda x: math.log(x))
                data_b['log_returns'] = data_b['log_price'].pct_change()

                # Calculate beta
                reg = OLS(data_a['log_returns'][1:], add_constant(data_b['log_returns'][1:])).fit()
                beta = reg.params[1]

                msg = '`Beta = {:.3f}`'.format(beta)
                await ctx.channel.send(msg)

bot.run(config['arb_helper_token'])
