import ftx_api
import discord
import json
import os
from discord.ext import tasks, commands


# Import config file
config = {}
config_path = os.path.dirname(os.path.abspath(__file__)) + '/config.json'
with open(config_path, 'r') as f:
    config = json.load(f)


def set_ftx_account_key(name, key, secret):
    global config
    if len(config.keys()) == 0:
        with open(config_path, 'r') as f:
            config = json.load(f)

    config['ftx_accounts'][name] = {
        "key": key,
        "secret": secret
    }

    with open(config_path, 'w') as f:
        json.dump(config, f)


client = discord.Client()

@client.event
async def on_ready():
    await client.wait_until_ready()
    print('We have logged in as {0.user}'.format(client))
    guild = client.get_guild(client.guilds[0].id)
    update_balance.start(guild)


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('$hello'):
        await message.channel.send('Hello!')


@tasks.loop(seconds=5)
async def update_balance(guild):
    account_value = ftx_api.get_account_usd_value(config['ftx_accounts']['walid']['key'],
                                                  config['ftx_accounts']['walid']['secret'],
                                                  config['ftx_accounts']['walid']['subaccount_name'])
    text = '${:,.2f}'.format(account_value)
    await guild.me.edit(nick=text)
    activity = discord.Activity(name=config['ftx_accounts']['walid']['subaccount_name'], type=discord.ActivityType.watching)
    await client.change_presence(status=discord.Status.online, activity=activity)


client.run(config['balance_tracker_bot']['token'])
