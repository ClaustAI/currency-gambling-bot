import discord
import asyncio
import random
import os
import io
import json
import time
import requests
import string
import re
from html import unescape
from discord.ext import commands
from datetime import datetime, timedelta
from discord.ui import Button, View
from discord import app_commands
from typing import Union
from PIL import Image, ImageDraw, ImageFont
import aiohttp

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix=["?", "!"], intents=intents, case_insensitive=True)


@bot.event
async def on_ready():
    print('We have logged in as {0.user}\n'.format(bot))
    print(f'Bot ID {bot.user.id}')
    print(f'Discord version {discord.__version__}')
    print('Serving in servers: ')
    for guild in bot.guilds:
        print(f'- {guild.name}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

def load_shop_data():
    try:
        with open("shop.json", "r") as file:
            shop_data = json.load(file)
            return shop_data
    except FileNotFoundError:
        return []

class Select(discord.ui.Select):
    def __init__(self, guild):
        super().__init__(placeholder="Select a role", max_values=1, min_values=1, options=[])
        self.guild = guild   
        self.load_options()  

    def load_options(self):
        shop_data = load_shop_data()
        options = []
        for role_name, role_id in shop_data.items():
            role = discord.utils.get(self.guild.roles, id=role_id)
            if role:
                options.append(discord.SelectOption(label=role_name, value=str(role_id)))
        if options:
            self.options = options

    async def callback(self, interaction: discord.Interaction):
        selected_role_id = self.values[0]
        selected_role = discord.utils.get(self.guild.roles, id=int(selected_role_id))
        if selected_role:
            try:
                await interaction.user.add_roles(selected_role)
                await interaction.response.send_message(f"Successfully gave you the role: {selected_role.mention}", ephemeral=True)
            except discord.Forbidden:
                await interaction.response.send_message("I do not have permission to assign roles.", ephemeral=True)
        else:
            await interaction.response.send_message("The selected role does not exist.", ephemeral=True)

class SelectView(discord.ui.View):
    def __init__(self, *, timeout=180, guild):
        super().__init__(timeout=timeout)
        self.add_item(Select(guild=guild)) 

@bot.command()
async def menu(ctx):
    await ctx.send("Menus!", view=SelectView(timeout=180, guild=ctx.guild))


@bot.command()
async def ping(ctx):
    await ctx.reply("pong")



bot.run("")