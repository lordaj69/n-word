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
COOLDOWN_TIME = 12


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


def update_counts(user_id, word, count):
    """Increment word count for a specific user in the database."""
    cursor.execute(f"""
    INSERT INTO word_counts (user_id, {word}_count)
    VALUES (%s, %s)
    ON CONFLICT (user_id) DO UPDATE
    SET {word}_count = word_counts.{word}_count + EXCLUDED.{word}_count;
    """, (user_id, count))
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
        for word in tracked_words:
            if word in content:
                update_counts(user_id, word, 1)  # Increment count by 1 for each word found
        count_cooldowns[user_id] = now

    await bot.process_commands(message)




@bot.command(aliases=["c"])
async def count(ctx, member: discord.Member = None):
    """Check the word count for the specified user or yourself if no user is mentioned."""
    if member is None:
        # Default to the message author if no member is mentioned
        member = ctx.author

    user_id = str(member.id)
    cursor.execute("""
    SELECT nigga_count, nigger_count FROM word_counts WHERE user_id = %s;
    """, (user_id,))
    result = cursor.fetchone()

    counts = {'nigga': 0, 'nigger': 0}
    if result:
        counts['nigga'], counts['nigger'] = result

    total_count = counts['nigga'] + counts['nigger']

    embed = discord.Embed(
        title=f"{member.name}'s Word Count Stats",
        color=discord.Color.blurple(),
        description=f"**Here's the word usage count for {member.mention} :**"
    )
    embed.set_thumbnail(url=member.avatar.url)
    embed.add_field(name="'Nigga'", value=f"**{counts['nigga']}**", inline=True)
    embed.add_field(name="'Nigger'", value=f"**{counts['nigger']}**", inline=True)
    embed.add_field(name="Total Count", value=f"**{total_count}**", inline=False)
    embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar.url)
    
    await ctx.send(embed=embed)



@bot.command()
async def leaderboard(ctx):
    """Display the leaderboard of top users."""
    cursor.execute("""
    SELECT user_id, nigga_count, nigger_count
    FROM word_counts
    ORDER BY (nigga_count + nigger_count) DESC
    LIMIT 10;
    """)
    leaderboard = cursor.fetchall()

    if not leaderboard:
        await ctx.send("No data available for the leaderboard.")
        return

    embed = discord.Embed(
        title="📊 Leaderboard",
        color=discord.Color.gold(),
        description="Here are the top 10 users based on their word counts:"
    )

    for rank, (user_id, nigga_count, nigger_count) in enumerate(leaderboard, start=1):
        total_count = nigga_count + nigger_count
        try:
            user = await bot.fetch_user(int(user_id))
            embed.add_field(
                name=f"#{rank} - {user.name}",
                value=(
                    f"**Total Words:** {total_count}\n"
                    f"'Nigga': {nigga_count}, 'Nigger': {nigger_count}"
                ),
                inline=False
            )
        except discord.NotFound:
            embed.add_field(
                name=f"#{rank} - Unknown User",
                value=(
                    f"**Total Words:** {total_count}\n"
                    f"'Nigga': {nigga_count}, 'Nigger': {nigger_count}"
                ),
                inline=False
            )

    embed.set_footer(text=f"Requested by {ctx.author.name}", icon_url=ctx.author.avatar.url)
    await ctx.send(embed=embed)



@bot.event
async def on_close():
    cursor.close()
    conn.close()



# Run the bot
keep_alive()

bot.run(DISCORD_TOKEN)
