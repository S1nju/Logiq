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
    "https://klipy.com/gifs/bro-hug-bromance-love-1",
    "https://klipy.com/gifs/joey-friends-14",
    "https://klipy.com/gifs/guys-hugging-2",
    "https://klipy.com/gifs/robertmanion-ajholmes",
    "https://klipy.com/gifs/hugging-kiss-1"
]

MEN_CUDDLE_GIFS = [
    "https://klipy.com/gifs/anime-cuddle-43",
    "https://klipy.com/gifs/shark-sharks-2",
    "https://klipy.com/gifs/anime-cuddle-cuddle-anime",

]

MEN_SLAP_GIFS = [
    "https://klipy.com/gifs/slap-michael-bryce",
    "https://klipy.com/gifs/slap-slapping-231",
    "https://klipy.com/gifs/slap-bet-slap",
    "https://klipy.com/gifs/slap-face-slap-1",
    "https://klipy.com/gifs/slap-face-slap-on-face"
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
        await interaction.response.send_message(content=gif_url, embed=embed)

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
        await interaction.response.send_message(content=gif_url, embed=embed)

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
        await interaction.response.send_message(content=gif_url, embed=embed)

    @app_commands.command(name="هق", description="اعطِ شخصاً ما عناقاً دافئاً!")
    @app_commands.describe(member="الشخص الذي تريد معانقته")
    async def hug_arabic(self, interaction: discord.Interaction, member: discord.Member):
        if member == interaction.user:
            return await interaction.response.send_message("لا يمكنك معانقة نفسك، لكنني سأعانقك! 🫂", ephemeral=True)
            
        gif_url = random.choice(MEN_HUG_GIFS)
        
        embed = discord.Embed(
            description=f"**{interaction.user.display_name}** يعانق **{member.display_name}**! 🫂",
            color=EmbedColor.PRIMARY
        )
        await interaction.response.send_message(content=gif_url, embed=embed)

    @app_commands.command(name="بوسه", description="قم بتقبيل او معانقة شخص ما!")
    @app_commands.describe(member="الشخص الذي تريد تقبيله")
    async def cuddle_arabic(self, interaction: discord.Interaction, member: discord.Member):
        if member == interaction.user:
            return await interaction.response.send_message("لا يمكنك فعل ذلك لنفسك! 😅", ephemeral=True)
            
        gif_url = random.choice(MEN_CUDDLE_GIFS)
        
        embed = discord.Embed(
            description=f"**{interaction.user.display_name}** يبوس **{member.display_name}**! 🥰",
            color=EmbedColor.PRIMARY
        )
        await interaction.response.send_message(content=gif_url, embed=embed)

    @app_commands.command(name="كف", description="اضرب شخصاً ما كفاً على وجهه!")
    @app_commands.describe(member="الشخص الذي تريد أن تضربه")
    async def slap_arabic(self, interaction: discord.Interaction, member: discord.Member):
        if member == interaction.user:
            return await interaction.response.send_message("لماذا تريد ضرب نفسك؟ توقف عن ذلك!", ephemeral=True)
            
        gif_url = random.choice(MEN_SLAP_GIFS)
        
        embed = discord.Embed(
            description=f"**{interaction.user.display_name}** يعطي كف لـ **{member.display_name}**! 😠",
            color=EmbedColor.PRIMARY
        )
        await interaction.response.send_message(content=gif_url, embed=embed)

async def setup(bot: commands.Bot):
    """Setup function for cog loading"""
    await bot.add_cog(Fun(bot, bot.db, bot.config))
