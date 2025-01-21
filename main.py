import discord
from discord.ext import commands
from collections import defaultdict
import json
import os
import time
from keep_alive import keep_alive
from dotenv import load_dotenv

load_dotenv()
token = os.getenv("DISCORD_TOKEN")
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
    """Load data from the JSON file or initialize if empty/invalid."""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as file:
                return json.load(file)
        except (json.JSONDecodeError, ValueError):
            print(
                f"Error: {DATA_FILE} is empty or corrupted. Reinitializing data."
            )
    return {}


# Load or initialize the word count data
user_word_count = load_data()

# Convert loaded data to defaultdict for easier usage
user_word_count = defaultdict(lambda: {
    'nigga': 0,
    'nigger': 0
}, user_word_count)

# Cooldowns for counting words
count_cooldowns = {}


def save_data():
    """Save user_word_count to a JSON file."""
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

    # Check for cooldown (only for word counting)
    if user_id in count_cooldowns and now - count_cooldowns[
            user_id] < COOLDOWN_TIME:
        await bot.process_commands(message)
        return

    # Words to track
    tracked_words = ['nigga', 'nigger']
    content = message.content.lower()
    word_found = any(word in content for word in tracked_words)

    if word_found:
        # Increment by 1 per word regardless of count in the message
        for word in tracked_words:
            if word in content:
                user_word_count[user_id][word] += 1
        count_cooldowns[user_id] = now
        save_data()  # Save data after each update

    await bot.process_commands(message)


@bot.command(aliases=["c"])
async def count(ctx, member: discord.Member = None):
    """Check the word count for the specified user or yourself if no user is mentioned."""
    if member is None:
        # Default to the message author if no member is mentioned
        user_id = str(ctx.author.id)
        counts = user_word_count[user_id]
        await ctx.send(f"{ctx.author.mention}, you have said:\n"
                       f"**'nigga': {counts['nigga']} times**\n"
                       f"**'nigger': {counts['nigger']} times**")
    else:
        # If a member is mentioned, show their count
        user_id = str(member.id)
        counts = user_word_count.get(user_id, {'nigga': 0, 'nigger': 0})
        await ctx.send(f"{member.mention} has said:\n"
                       f"**'nigga': {counts['nigga']} times**\n"
                       f"**'nigger': {counts['nigger']} times**")


@bot.command()
async def leaderboard(ctx):
    """Display the leaderboard of top users."""
    leaderboard = sorted(user_word_count.items(),
                         key=lambda x: sum(x[1].values()),
                         reverse=True)
    message = "**Leaderboard:**\n"

    if not leaderboard:
        await ctx.send("No data available for the leaderboard.")
        return

    for rank, (user_id, counts) in enumerate(leaderboard[:10], start=1):
        try:
            user = await bot.fetch_user(int(user_id))
            total = sum(counts.values())
            message += f"{rank}. {user.name}: {total} total words ('nigga': {counts['nigga']}, 'nigger': {counts['nigger']})\n"
        except discord.NotFound:
            message += f"{rank}. [Unknown User]: Data not available.\n"

    await ctx.send(message)


# Run the bot
keep_alive()

bot.run(token)
