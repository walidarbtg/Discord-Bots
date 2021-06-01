import ftx_api
import discord
import json
import os
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


def set_ftx_account(name, key, secret):
    global ACCOUNT
    ACCOUNT['name'] = name
    ACCOUNT['key'] = key
    ACCOUNT['secret'] = secret


client = discord.Client()


@client.event
async def on_ready():
    await client.wait_until_ready()
    print('We have logged in as {0.user}'.format(client))
    guild = client.get_guild(client.guilds[0].id)
    update_balance.start(guild)


@client.event
async def on_message(message):
    global ACCOUNT
    if message.author == client.user:
        return

    if message.author.bot:
        return

    if message.content[0] == '!' or message.content[0] == '#' or message.content[0] == '.':
        return

    if message.channel.id == config['channel_ids']['ftx-arb-personal']:
        if message.content == 'help':
            msg = 'Set your api key:\n`key-mykey`\n`secret-mysecret`\n`name-subaccount name`'
            await message.channel.send(msg)
        else:
            data = message.content.split(' ')
            if data[0] == 'key':
                ACCOUNT['key'] = data[1]
            elif data[0] == 'secret':
                ACCOUNT['secret'] = data[1]
            elif data[0] == 'name':
                ACCOUNT['name'] = data[1]

            await message.channel.send('The {} have been set'.format(data[0]))


@tasks.loop(seconds=5)
async def update_balance(guild):
    account_value = ftx_api.get_account_usd_value(ACCOUNT['key'], ACCOUNT['secret'], ACCOUNT['name'])
    text = '${:,.2f}'.format(account_value)
    await guild.me.edit(nick=text)
    activity = discord.Activity(name=ACCOUNT['name'], type=discord.ActivityType.watching)
    await client.change_presence(status=discord.Status.online, activity=activity)

"""
@tasks.loop(seconds=5)
async def check_credentials(guild):
    if ACCOUNT['key'] == "" or ACCOUNT['secret'] == "" or ACCOUNT['name'] == "":
        pass
    else:
        update_balance.start(guild)
"""

set_ftx_account('Walid', config['ftx_accounts']['main']['key'], config['ftx_accounts']['main']['secret'])

client.run(config['bot_tokens']['balance_tracker_bot'])
