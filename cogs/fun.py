"""
Fun Cog for Logiq
Handles fun roleplay commands like hug, cuddle, and slap.
Features ONLY men in the GIFs as requested.
"""
import discord
from discord import app_commands
from discord.ext import commands
import random
import logging

from utils.embeds import EmbedFactory, EmbedColor

logger = logging.getLogger(__name__)

# Hardcoded GIF lists to guarantee ONLY men are featured
MEN_HUG_GIFS = [
    "https://media.tenor.com/z4bYsm9-FQQAAAAC/anime-hug.gif",
    "https://media.tenor.com/y_7gY8Kk70wAAAAC/free-mako.gif",
    "https://media.tenor.com/V7B-x2v8hT8AAAAC/hug-anime.gif",
    "https://media.tenor.com/Fq5B_q0NqTMAAAAC/anime-hug.gif",
    "https://media.tenor.com/RMBjhwf1MtcAAAAC/anime-hug.gif"
]

MEN_CUDDLE_GIFS = [
    "https://media.tenor.com/2cZBvtb7J3wAAAAC/anime-sleep.gif",
    "https://media.tenor.com/PZ8rRkXpE2kAAAAC/sleep-anime.gif",
    "https://media.tenor.com/zD11I_C0VjMAAAAC/anime-snuggle.gif",
    "https://media.tenor.com/lOlsO4Qy_QYAAAAC/anime-cuddle.gif"
]

MEN_SLAP_GIFS = [
    "https://media.tenor.com/WvM5aO4pPCEAAAAC/anime-slap.gif",
    "https://media.tenor.com/E3OwKqIV72oAAAAC/anime-slap.gif",
    "https://media.tenor.com/PeJyXelnMi0AAAAC/sao-sword-art-online.gif",
    "https://media.tenor.com/D_iN7wQ4Q14AAAAC/mushoku-tensei-slap.gif"
]

class Fun(commands.Cog):
    """Fun Roleplay Commands"""

    def __init__(self, bot: commands.Bot, db, config: dict):
        self.bot = bot
        self.db = db
        self.config = config

    @app_commands.command(name="hug", description="Give someone a warm hug!")
    @app_commands.describe(member="The person you want to hug")
    async def hug(self, interaction: discord.Interaction, member: discord.Member):
        if member == interaction.user:
            return await interaction.response.send_message("You can't hug yourself, but I'll hug you! 🫂", ephemeral=True)
            
        gif_url = random.choice(MEN_HUG_GIFS)
        
        embed = discord.Embed(
            description=f"**{interaction.user.display_name}** hugs **{member.display_name}**! 🫂",
            color=EmbedColor.PRIMARY
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="cuddle", description="Cuddle up with someone!")
    @app_commands.describe(member="The person you want to cuddle")
    async def cuddle(self, interaction: discord.Interaction, member: discord.Member):
        if member == interaction.user:
            return await interaction.response.send_message("You can't really cuddle yourself like that! 😅", ephemeral=True)
            
        gif_url = random.choice(MEN_CUDDLE_GIFS)
        
        embed = discord.Embed(
            description=f"**{interaction.user.display_name}** cuddles **{member.display_name}**! 🥰",
            color=EmbedColor.PRIMARY
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="slap", description="Slap someone across the face!")
    @app_commands.describe(member="The person you want to slap")
    async def slap(self, interaction: discord.Interaction, member: discord.Member):
        if member == interaction.user:
            return await interaction.response.send_message("Why would you want to slap yourself? Stop that!", ephemeral=True)
            
        gif_url = random.choice(MEN_SLAP_GIFS)
        
        embed = discord.Embed(
            description=f"**{interaction.user.display_name}** slaps **{member.display_name}**! 😠",
            color=EmbedColor.PRIMARY
        )
        embed.set_image(url=gif_url)
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    """Setup function for cog loading"""
    await bot.add_cog(Fun(bot, bot.db, bot.config))
