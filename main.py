import discord
from discord.ext import commands
from collections import defaultdict
import json
import os
import time
from keep_alive import keep_alive
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import Json

# Connect to the PostgreSQL database
DATABASE_URL = os.getenv("DATABASE_URL")
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Create the table if it doesn't already exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS word_counts (
    user_id VARCHAR PRIMARY KEY,
    nigga_count INTEGER DEFAULT 0,
    nigger_count INTEGER DEFAULT 0
);
""")
conn.commit()

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
def get_counts(user_id):
    """Fetch word counts for a user from the database."""
    cursor.execute("SELECT nigga_count, nigger_count FROM word_counts WHERE user_id = %s;", (user_id,))
    result = cursor.fetchone()
    if result:
        return {"nigga": result[0], "nigger": result[1]}
    return {"nigga": 0, "nigger": 0}
    

# Cooldowns for counting words
count_cooldowns = {}


def update_counts(user_id, counts):
    """Update word counts for a user in the database."""
    cursor.execute("""
    INSERT INTO word_counts (user_id, nigga_count, nigger_count)
    VALUES (%s, %s, %s)
    ON CONFLICT (user_id) DO UPDATE
    SET nigga_count = word_counts.nigga_count + EXCLUDED.nigga_count,
        nigger_count = word_counts.nigger_count + EXCLUDED.nigger_count;
    """, (user_id, counts["nigga"], counts["nigger"]))
    conn.commit()


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
    if user_id in count_cooldowns and now - count_cooldowns[user_id] < COOLDOWN_TIME:
        await bot.process_commands(message)
        return

    # Words to track
    tracked_words = ['nigga', 'nigger']
    content = message.content.lower()
    word_found = any(word in content for word in tracked_words)

    if word_found:
        # Increment counts in the database
        counts = get_counts(user_id)
        for word in tracked_words:
            if word in content:
                counts[word] += 1
        update_counts(user_id, counts)
        count_cooldowns[user_id] = now

    await bot.process_commands(message)



@bot.command(aliases=["c"])
async def count(ctx, member: discord.Member = None):
    if member is None:
        user_id = str(ctx.author.id)
        counts = get_counts(user_id)
        await ctx.send(f"{ctx.author.mention}, you have said:\n"
                       f"**'nigga': {counts['nigga']} times**\n"
                       f"**'nigger': {counts['nigger']} times**")
    else:
        user_id = str(member.id)
        counts = get_counts(user_id)
        await ctx.send(f"{member.mention} has said:\n"
                       f"**'nigga': {counts['nigga']} times**\n"
                       f"**'nigger': {counts['nigger']} times**")


@bot.command()
async def leaderboard(ctx):
    """Display the leaderboard of top users."""
    cursor.execute("SELECT user_id, nigga_count, nigger_count FROM word_counts;")
    leaderboard = cursor.fetchall()
    leaderboard = sorted(leaderboard, key=lambda x: x[1] + x[2], reverse=True)

    message = "**Leaderboard:**\n"
    if not leaderboard:
        await ctx.send("No data available for the leaderboard.")
        return

    for rank, (user_id, nigga_count, nigger_count) in enumerate(leaderboard[:10], start=1):
        try:
            user = await bot.fetch_user(int(user_id))
            total = nigga_count + nigger_count
            message += f"{rank}. {user.name}: {total} total words ('nigga': {nigga_count}, 'nigger': {nigger_count})\n"
        except discord.NotFound:
            message += f"{rank}. [Unknown User]: Data not available.\n"

    await ctx.send(message)


@bot.event
async def on_close():
    cursor.close()
    conn.close()



# Run the bot
keep_alive()

bot.run(DISCORD_TOKEN)
