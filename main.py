import discord
from discord.ext import commands
from collections import defaultdict
import json
import os
import time
from keep_alive import keep_alive
from dotenv import load_dotenv

load_dotenv()
DISCORD_TOKEN = os.getenv("TOKEN")
if not DISCORD_TOKEN:
    raise ValueError("No token found. Make sure the TOKEN environment variable is set.")

# Intents and Bot setup
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

# File for persistent storage
DATA_FILE = "word_count_data.json"

# Configurable cooldown time (in seconds)
COOLDOWN_TIME = 1


# Function to load JSON data safely
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as file:
                return json.load(file)
        except (json.JSONDecodeError, ValueError):
            print(f"Error: {DATA_FILE} is empty or corrupted. Reinitializing data.")
    return {}


# Load or initialize the word count data
user_word_count = load_data()
user_word_count = defaultdict(lambda: {"nigga": 0, "nigger": 0}, user_word_count)

# Cooldowns for counting words
count_cooldowns = {}


def save_data():
    with open(DATA_FILE, "w") as file:
        json.dump(user_word_count, file)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = str(message.author.id)
    now = time.time()

    # Check for cooldown
    if user_id in count_cooldowns and now - count_cooldowns[user_id] < COOLDOWN_TIME:
        await bot.process_commands(message)
        return

    # Words to track
    tracked_words = ["nigga", "nigger"]
    content = message.content.lower()
    word_found = any(word in content for word in tracked_words)

    if word_found:
        for word in tracked_words:
            if word in content:
                user_word_count[user_id][word] += 1
        count_cooldowns[user_id] = now
        save_data()

    await bot.process_commands(message)


@bot.command(aliases=["c"])
async def count(ctx, member: discord.Member = None):
    """Check the word count for the specified user or yourself if no user is mentioned."""
    member = member or ctx.author
    user_id = str(member.id)
    counts = user_word_count.get(user_id, {"nigga": 0, "nigger": 0})
    total_count = sum(counts.values())

    embed = discord.Embed(
        title="Word Usage Count",
        color=discord.Color.blue(),
        description=f"Here's the word usage count for {member.mention}:"
    )
    embed.set_thumbnail(url=member.avatar.url)
    embed.add_field(name="Total Words", value=f"{total_count}", inline=False)
    embed.add_field(name="'nigga'", value=f"{counts['nigga']}", inline=True)
    embed.add_field(name="'nigger'", value=f"{counts['nigger']}", inline=True)
    embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar.url)

    await ctx.send(embed=embed)


@bot.command()
async def leaderboard(ctx):
    """Display the leaderboard of top users."""
    leaderboard = sorted(
        user_word_count.items(), key=lambda x: sum(x[1].values()), reverse=True
    )
    embed = discord.Embed(
        title="Leaderboard",
        color=discord.Color.gold(),
        description="Top users based on word usage:"
    )

    if not leaderboard:
        embed.description = "No data available for the leaderboard."
        await ctx.send(embed=embed)
        return

    for rank, (user_id, counts) in enumerate(leaderboard[:10], start=1):
        try:
            user = await bot.fetch_user(int(user_id))
            total = sum(counts.values())
            embed.add_field(
                name=f"{rank}. {user.name}",
                value=f"**Total**: {total} | **'nigga'**: {counts['nigga']} | **'nigger'**: {counts['nigger']}",
                inline=False
            )
        except discord.NotFound:
            embed.add_field(
                name=f"{rank}. Unknown User",
                value="User data not available.",
                inline=False
            )

    embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)


# Run the bot
keep_alive()

bot.run(DISCORD_TOKEN)
