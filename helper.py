import json
import os
import sys
import traceback
import math
import pandas as pd
import binance_api
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


@bot.command(name='binance_funding_arb')
async def get_binance_funding_arb(ctx):
    if ctx.channel.id == config['channel_ids']['commands_test']:
        API = config['binance_api']

        margin_data_df = pd.DataFrame(binance_api.get_isolated_margin_data(API)).set_index('symbol')
        mark_prices_df = pd.DataFrame(binance_api.get_mark_prices(API)).set_index('symbol')
        funding_rates_df = mark_prices_df['lastFundingRate'].apply(lambda x: float(x))
        negative_funding_rates = funding_rates_df[funding_rates_df < 0]

        rate_differences = {}
        vip_level = None
        spot_taker_fee = 0.001
        future_maker_fee = 0.0002
        max_trading_cost = 2 * spot_taker_fee + 2 * future_maker_fee
        for symbol in negative_funding_rates.index:
            if symbol in margin_data_df.index:
                if not vip_level:
                    vip_level = margin_data_df.loc[symbol]['vipLevel']
                max_leverage = margin_data_df.loc[symbol]['leverage'] 
                margin_data = margin_data_df.loc[symbol]['data']
                daily_borrow_rate = float(margin_data[0]['dailyInterest'])
                borrow_limit = float(margin_data[0]['borrowLimit'])

                hourly_borrow_rate = daily_borrow_rate / 24

                # rate arb for a single funding payment
                rate_diff = abs(negative_funding_rates.loc[symbol]) - hourly_borrow_rate

                if rate_diff > max_trading_cost:
                    rate_diff = rate_diff - max_trading_cost

                    max_dollar_size = borrow_limit * float(mark_prices_df.loc[symbol]['markPrice'])

                    rate_differences[symbol] = {
                        'arb_profit': rate_diff*100,
                        'max_borrow_in_dollars': int(max_dollar_size)
                    }

        rate_diffs_df = pd.DataFrame(rate_differences).T
        top_arbs = rate_diffs_df.sort_values(['arb_profit'], ascending=False)

        top_arbs['arb_profit'] = top_arbs['arb_profit'].apply(lambda x: '{:.2f} %'.format(x))
        top_arbs['max_borrow_in_dollars'] = top_arbs['max_borrow_in_dollars'].apply(lambda x: '$'.format(x))

        await ctx.channel.send('``{}``'.format(str(top_arbs)))
        

bot.run(config['arb_helper_token'])
