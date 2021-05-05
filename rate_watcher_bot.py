import ftx_api
import discord
import os
import json
from discord.ext import tasks, commands

# Import config file
config = {}
config_path = os.path.dirname(os.path.abspath(__file__)) + '/config.json'
with open(config_path, 'r') as f:
    config = json.load(f)


client = discord.Client()

@client.event
async def on_ready():
    await client.wait_until_ready()
    print('We have logged in as {0.user}'.format(client))
    guild = client.get_guild(client.guilds[0].id)
    update_ticker.start(guild)
    activity = discord.Activity(name='Annualized Rate', type=discord.ActivityType.watching)
    await client.change_presence(status=discord.Status.online, activity=activity)

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')


@tasks.loop(minutes=30)
async def update_ticker(guild):
    rate = get_borrow_rate()
    annualized = rate * 24 * 365 * 100
    text = 'USD {:.2f}%'.format(annualized)
    await guild.me.edit(nick=text)


def get_borrow_rate():
    lending_rate = ftx_api.get_lending_rate('USD')
    account_info = ftx_api.get_account_info(config['ftx_accounts']['walid']['key'],
                                            config['ftx_accounts']['walid']['secret'],
                                            config['ftx_accounts']['walid']['subaccount_name'])
    taker_fee = account_info['takerFee']
    spot_margin_borrow_rate = min(500*taker_fee, 1)
    borrow_rate = lending_rate * (1+spot_margin_borrow_rate)
    return borrow_rate


client.run(config['borrow_rates_bot']['token'])

