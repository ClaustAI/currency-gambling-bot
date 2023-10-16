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


with open("currency.json") as f:
    currency_data = json.load(f)

def load_currency_data():
    try:
        with open("currency.json", "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def load_shop_data():
    try:
        with open("shop.json", "r") as file:
            shop_data = json.load(file)
            return shop_data
    except FileNotFoundError:
        return []

def load_user_items_data():
    try:
        with open("user_items.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
        
def save_currency_data(data):
    with open("currency.json", "w") as file:
        json.dump(data, file)

def format_currency(amount):
    suffixes = ["", "K", "M", "B", "T"]
    suffix_index = 0

    while amount >= 1000 and suffix_index < len(suffixes) - 1:
        amount /= 1000
        suffix_index += 1

    formatted_amount = f"{amount:.1f}{suffixes[suffix_index]}"
    return formatted_amount

def load_roles():
    try:
        with open("shoproles.json", "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


COOLDOWN_DURATION = 600


async def give_coins(ctx, user_id):
    if str(user_id) in currency_data:
        currency_data[str(user_id)]["balance"] += 4
    else:
        currency_data[str(user_id)] = {"balance": 4}
    with open("currency.json", "w") as f:
        json.dump(currency_data, f, indent=4)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    user_id = message.author.id
    await give_coins(message.channel, user_id)
    await bot.process_commands(message)
            
@bot.hybrid_command(name="earn", with_app_command=True, description="Earns remcoin")
async def earn(ctx):
    currency_data = load_currency_data()
    user_id = str(ctx.author.id)

    if user_id in currency_data:
        last_earn_time = currency_data[user_id]["last_earn_time"]
        current_time = time.time()

        if current_time - last_earn_time < COOLDOWN_DURATION:
            remaining_cooldown = int(COOLDOWN_DURATION - (current_time - last_earn_time))
            remaining_minutes = remaining_cooldown // 60
            await ctx.send(f"{ctx.author.mention}, you can earn <:remcoin:1160134332279701535>RemCash again in ` {remaining_minutes} minutes `")
            return

    amount = random.randint(500, 1500)

    if user_id in currency_data:
        currency_data[user_id]["last_earn_time"] = time.time()
        currency_data[user_id]["balance"] += amount
    else:
        currency_data[user_id] = {
            "last_earn_time": time.time(),
            "balance": amount
        }
    save_currency_data(currency_data)
    formatted_amount = format_currency(amount)
    if amount < 1000:
        await ctx.send(f"{ctx.author.mention}, you earned <:remcoin:1160134332279701535>{amount}")
    else:
        await ctx.send(f"{ctx.author.mention}, you earned <:remcoin:1160134332279701535>{formatted_amount}")
    
    
@bot.command(aliases=["bal", "bl"])
async def balance(ctx, member: discord.Member = None):
    currency_data = load_currency_data()
    user_id = str(member.id) if member else str(ctx.author.id)

    if user_id in currency_data:
        balance = currency_data[user_id]["balance"]
        formatted_amount = format_currency(balance)
        if balance < 1000:
            if member:
                await ctx.send(f"{member.mention}'s current balance is <:remcoin:1160134332279701535>{balance}")
            else:
                await ctx.send(f"{ctx.author.mention}, your current balance is <:remcoin:1160134332279701535>{balance}")
        else:
            if member:
                await ctx.send(f"{member.mention}'s current balance is <:remcoin:1160134332279701535>{formatted_amount}")
            else:
                await ctx.send(f"{ctx.author.mention}, your current balance is <:remcoin:1160134332279701535>{formatted_amount}")
    else:
        await ctx.send("User not found or has no coins.")


@bot.command()
async def top(ctx):
    currency_data = load_currency_data()
    sorted_users = sorted(currency_data.items(), key=lambda x: x[1]["balance"], reverse=True)
    top_users = sorted_users[:5]

    embed = discord.Embed(title="Rem Coin Leaderboard", color=discord.Color.red())

    for index, (user_id, user_data) in enumerate(top_users):
        member = ctx.guild.get_member(int(user_id))
        if member:
            username = member.display_name
            balance = user_data["balance"]
            formatted_amount = format_currency(balance)
            embed.add_field(name=f"{index+1}. {username}", value=f"<:remcoin:1160134332279701535>{formatted_amount}", inline=False)

    await ctx.send(embed=embed)


@bot.command()
async def give(ctx, member: discord.Member, amount: int):
    currency_data = load_currency_data()
    giving_user_id = str(ctx.author.id)
    receiving_user_id = str(member.id)

    if giving_user_id in currency_data and currency_data[giving_user_id]["balance"] >= amount:
        confirm_embed = discord.Embed(
            title="Give Coins Confirmation",
            description=f"Are you sure you want to give <:remcoin:1160134332279701535>{amount} to {member.mention}?",
            color=discord.Color.blue()
        )

        view = discord.ui.View()

        async def on_confirm(interaction: discord.Interaction):
            if str(interaction.user.id) != giving_user_id:
                await interaction.response.send_message(
                    content="Sorry, you are not authorized to confirm this transaction.", ephemeral=True
                )
                return

            currency_data[giving_user_id]["balance"] -= amount

            if receiving_user_id in currency_data:
                currency_data[receiving_user_id]["balance"] += amount
            else:
                currency_data[receiving_user_id] = {"balance": amount}

            save_currency_data(currency_data)

            await ctx.send(
                f"{ctx.author.mention} has given <:remcoin:1160134332279701535>{amount} to {member.mention}."
            )
            await confirm_message.delete()

        async def on_cancel(interaction: discord.Interaction):
            if str(interaction.user.id) != giving_user_id:
                await interaction.response.send_message(
                    content="Sorry, you are not authorized to cancel this transaction.", ephemeral=True
                )
                return

            await ctx.send(
                "Transaction canceled."
            )
            await confirm_message.delete()

        confirm_button = discord.ui.Button(label="Yes", style=discord.ButtonStyle.green)
        cancel_button = discord.ui.Button(label="No", style=discord.ButtonStyle.red)

        confirm_button.callback = on_confirm
        cancel_button.callback = on_cancel

        view.add_item(confirm_button)
        view.add_item(cancel_button)

        confirm_message = await ctx.send(embed=confirm_embed, view=view)
    else:
        await ctx.send(f"{ctx.author.mention}, you don't have enough rem cash to give.")

@bot.command()
@commands.has_role("I am alone")
async def spare(ctx, member: discord.Member, amount: int):
    currency_data = load_currency_data()
    giving_user_id = str(ctx.author.id)
    receiving_user_id = str(member.id)

    if giving_user_id in currency_data:
        confirm_embed = discord.Embed(
            title="Give Coins Confirmation",
            description=f"Are you sure you want to give <:remcoin:1160134332279701535>{amount} to {member.mention}?",
            color=discord.Color.blue()
        )

        view = discord.ui.View()

        async def on_confirm(interaction: discord.Interaction):
            if str(interaction.user.id) != giving_user_id:
                await interaction.response.send_message(
                    content="Sorry, you are not authorized to confirm this transaction.", ephemeral=True
                )
                return

            if receiving_user_id in currency_data:
                currency_data[receiving_user_id]["balance"] += amount
            else:
                currency_data[receiving_user_id] = {"balance": amount}

            save_currency_data(currency_data)

            await ctx.send(
                f"{ctx.author.mention} has given <:remcoin:1160134332279701535>{amount} to {member.mention}."
            )
            await confirm_message.delete()

        async def on_cancel(interaction: discord.Interaction):
            if str(interaction.user.id) != giving_user_id:
                await interaction.response.send_message(
                    content="Sorry, you are not authorized to cancel this transaction.", ephemeral=True
                )
                return

            await ctx.send(
                "Transaction canceled."
            )
            await confirm_message.delete()

        confirm_button = discord.ui.Button(label="Yes", style=discord.ButtonStyle.green)
        cancel_button = discord.ui.Button(label="No", style=discord.ButtonStyle.red)

        confirm_button.callback = on_confirm
        cancel_button.callback = on_cancel

        view.add_item(confirm_button)
        view.add_item(cancel_button)

        confirm_message = await ctx.send(embed=confirm_embed, view=view)
    else:
        await ctx.send(f"{ctx.author.mention}, you don't have enough rem cash to give.")


@bot.command(aliases=['cf'])
async def coinflip(ctx, amount: int):
    MAX_BID = 100000
    MIN_WIN_CHANCE = 0.4
    MAX_WIN_CHANCE = 0.6

    if amount <= 0:
        await ctx.send("Please enter a valid amount to bid.")
        return

    if amount > MAX_BID:
        await ctx.send(f"You cannot bid more than {format_currency(MAX_BID)}")
        return

    currency_data = load_currency_data()
    user_id = str(ctx.author.id)

    if user_id not in currency_data or currency_data[user_id]["balance"] < amount:
        await ctx.send("You don't have enough <:remcoin:1160134332279701535> to place that bid.")
        return

    user_balance = currency_data[user_id]["balance"]

    win_chances = min(MAX_WIN_CHANCE, max(MIN_WIN_CHANCE, amount / user_balance))

    flip_result = random.choices(["Heads", "Tails"], weights=[win_chances, 1 - win_chances], k=1)[0]
    formatted_amount = format_currency(amount)

    async def display_flip_animation():
        flip_message = await ctx.send(f"Flipping coin, bid amount: {formatted_amount}")
        for _ in range(3):
            await flip_message.edit(content=f"{flip_message.content} .")
            await asyncio.sleep(1)
        return flip_message

    flip_message = await display_flip_animation()

    if flip_result == "Heads":
        winnings = amount * 1
        currency_data[user_id]["balance"] += winnings
        save_currency_data(currency_data)
        formatted_winnings = format_currency(winnings)
        await flip_message.edit(content=f"The coin landed on **Heads**. You won {formatted_winnings}")
    else:
        currency_data[user_id]["balance"] -= amount
        save_currency_data(currency_data)
        formatted_loss = format_currency(amount)
        await flip_message.edit(content=f"The coin landed on **Tails**. You lost {formatted_loss}")


@bot.command()
@commands.has_permissions(administrator=True)
async def take(ctx, member: discord.Member, amount: int):
    currency_data = load_currency_data()
    user_id = str(member.id)

    if user_id not in currency_data or currency_data[user_id]["balance"] < amount:
        await ctx.send("The specified user does not have enough Remcash")
        return

    currency_data[user_id]["balance"] -= amount
    currency_data[str(ctx.author.id)]["balance"] += amount
    save_currency_data(currency_data)

    await ctx.send(f"Successfully taken <:remcoin:1160134332279701535>{amount} from {member.mention}")

quiz_count = {}
@bot.hybrid_command(name="quiz", with_app_command=True, description="anime quizes")
async def quiz(ctx):
    user_id = str(ctx.author.id)

    if user_id in quiz_count:
        if quiz_count[user_id] >= 10:
            await ctx.send("You have already taken 10 quizes to day!")
            return
    else:
        quiz_count[user_id] = 1

    response = requests.get("https://opentdb.com/api.php?amount=1&category=31&type=multiple")
    data = response.json()

    if data["response_code"] != 0:
        await ctx.send("Failed to fetch the quiz question.")
        return

    quiz_question = data["results"][0]
    question_text = unescape(quiz_question["question"])
    correct_answer = unescape(quiz_question["correct_answer"])
    options = [unescape(option) for option in quiz_question["incorrect_answers"]]
    options.append(correct_answer)
    random.shuffle(options)

    formatted_options = "\n".join(f"{i+1}. {option}" for i, option in enumerate(options))

    embed = discord.Embed(title="Anime Quiz", description=question_text, color=discord.Color.blue())
    embed.add_field(name="Options", value=formatted_options, inline=False)

    message = await ctx.send(embed=embed)

    number_reactions = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]

    for i in range(len(options)):
        await message.add_reaction(number_reactions[i])

    def check_answer(reaction, user):
        return user == ctx.author and reaction.message == message and str(reaction.emoji) in number_reactions
    try:
        reaction, _ = await bot.wait_for("reaction_add", check=check_answer, timeout=20.0)

        chosen_option = options[number_reactions.index(str(reaction.emoji))]

        if chosen_option == correct_answer:
            await ctx.send(f"Correct answer! You earned <:remcoin:1160134332279701535>2K, {ctx.author.mention}.")
            currency_data = load_currency_data()
            if user_id in currency_data:
                currency_data[user_id]["balance"] += 2000
            else:
                currency_data[user_id] = {"balance": 2000}
            save_currency_data(currency_data)
        else:
            await ctx.send(f"Wrong answer. The correct answer was: {correct_answer}")
    except asyncio.TimeoutError:
        await ctx.send("No answer received. The quiz has ended.")

    await message.delete()
    quiz_count[user_id] += 1

def load_shop_data():
    try:
        with open("shop.json", "r") as file:
            shop_data = json.load(file)
            return shop_data
    except FileNotFoundError:
        return []

shop_items = load_shop_data()
transactions = {}

@bot.hybrid_command(name="shop", with_app_command=True, description="shop")
async def shop(ctx):
    items_per_page = 5
    total_pages = (len(shop_items) + items_per_page - 1) // items_per_page

    page_number = 1

    async def on_button_click(interaction: discord.Interaction, increment):
        nonlocal page_number

        page_number += increment
        page_number = max(1, min(page_number, total_pages))

        start_index = (page_number - 1) * items_per_page
        end_index = min(start_index + items_per_page, len(shop_items))

        new_embed = create_shop_embed(start_index, end_index)
        current_page_button = view.children[1]
        current_page_button.label = f"Page {page_number}"
        previous_button.disabled = (page_number == 1)
        next_button.disabled = (page_number == total_pages)

        await interaction.message.edit(embed=new_embed, view=view)

    def create_shop_embed(start_index, end_index):
        embed = discord.Embed(title="Shop", description="Welcome to the shop!")
        for i in range(start_index, end_index):
            item = shop_items[i]
            embed.add_field(
                name=f"`{item['code']}` {item['name']}",
                value=f"Price: <:remcoin:1160134332279701535>{item['price']}",
                inline=False
            )
        return embed

    previous_button = discord.ui.Button(label="Back", style=discord.ButtonStyle.primary, emoji="⬅️")
    current_page_button = discord.ui.Button(label="Page 1", style=discord.ButtonStyle.secondary, disabled=True)
    next_button = discord.ui.Button(label="Forward", style=discord.ButtonStyle.primary, emoji="➡️")

    view = discord.ui.View()
    view.add_item(previous_button)
    view.add_item(current_page_button)
    view.add_item(next_button)

    previous_button.callback = lambda i: on_button_click(i, -1)
    next_button.callback = lambda i: on_button_click(i, 1)

    message = await ctx.send(embed=create_shop_embed(0, min(items_per_page, len(shop_items))), view=view)

    while True:
        try:
            interaction = await bot.wait_for("button_click", check=lambda i: i.user == ctx.author, timeout=120)
            await on_button_click(interaction, 0)
        except asyncio.TimeoutError:
            view.stop()
            break


@bot.command()
async def buy(ctx, item_code: str, *, role_name: str):
    print("Inside buy command")  

    currency_data = load_currency_data()
    shop_data = load_shop_data()
    user_items_data = load_user_items_data()

    user_id = str(ctx.author.id)

    if user_id not in currency_data:
        await ctx.send("You don't have enough currency to make a purchase.")
        return

    if item_code not in [item['code'] for item in shop_data]:
        await ctx.send("Invalid item code.")
        return

    item_to_buy = None
    for item in shop_data:
        if item['code'] == item_code:
            item_to_buy = item
            break

    if item_to_buy is None:
        await ctx.send("Item not found in the shop.")
        return

    item_price = item_to_buy['price']
    user_balance = currency_data[user_id]['balance']

    if user_balance < item_price:
        await ctx.send("You don't have enough currency to buy this item.")
        return

    print(f"Item code: {item_to_buy['code']}")

    if item_code == "1":
        roles_data = load_roles()
        if role_name in roles_data:
            role_id = int(roles_data[role_name])
            role = ctx.guild.get_role(role_id)
            if role:
                await ctx.author.add_roles(role)
            else:
                await ctx.send("Role not found on this server.")
        else:
            await ctx.send("Role not found in roles_data.")

    currency_data[user_id]['balance'] -= item_price
    if user_id not in user_items_data:
        user_items_data[user_id] = []

    user_items_data[user_id].append(item_to_buy)

    with open("currency.json", "w") as file:
        json.dump(currency_data, file, indent=4)

    with open("user_items.json", "w") as file:
        json.dump(user_items_data, file, indent=4)

    await ctx.send(f"You've successfully purchased {item_to_buy['name']} for {item_price} <:remcoin:1160134332279701535>.")



@bot.hybrid_command(name="item", with_app_command=True, description="check your items")
async def item(ctx):
    user_items_data = load_user_items_data()
    user_id = str(ctx.author.id)

    if user_id not in user_items_data:
        await ctx.send("You haven't purchased any items from the shop.")
        return

    user_items = user_items_data[user_id]
    
    embed = discord.Embed(title=f"{ctx.author.display_name}'s Items", description="Here are the items you've purchased:")
    
    for item in user_items:
        embed.add_field(name=item['name'], value=f"Code: {item['code']}\nPrice: <:remcoin:1160134332279701535>{item['price']}", inline=False)

    await ctx.send(embed=embed)


bot.run("")
