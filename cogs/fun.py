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
    "assets/gifs/Nsd8B44i.gif",
    "assets/gifs/nQTI90lm.gif",
    "assets/gifs/ortTfVI6.gif",

]

MEN_CUDDLE_GIFS = [
    "assets/gifs/CFadSNIwNoleZ.gif",
    "assets/gifs/4xANsChqMOdmv.gif",
 

]

MEN_SLAP_GIFS = [
    "assets/gifs/5eFdSOUN.gif",
    "assets/gifs/Hdp9mqLE0Rstpi.gif",
    "assets/gifs/J7dNlRIcUYdgq.gif",
    "assets/gifs/T3Q5FcJ8QLClVE.gif",
    "assets/gifs/rpafuilN.gif"
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
            
        gif_path = random.choice(MEN_HUG_GIFS)
        file = discord.File(gif_path, filename="hug.gif")
        
        embed = discord.Embed(
            description=f"**{interaction.user.display_name}** hugs **{member.display_name}**! 🫂",
            color=EmbedColor.PRIMARY
        )
        embed.set_image(url="attachment://hug.gif")
        await interaction.response.send_message(file=file, embed=embed)

    @app_commands.command(name="cuddle", description="Cuddle up with someone!")
    @app_commands.describe(member="The person you want to cuddle")
    async def cuddle(self, interaction: discord.Interaction, member: discord.Member):
        if member == interaction.user:
            return await interaction.response.send_message("You can't really cuddle yourself like that! 😅", ephemeral=True)
            
        gif_path = random.choice(MEN_CUDDLE_GIFS)
        file = discord.File(gif_path, filename="cuddle.gif")
        
        embed = discord.Embed(
            description=f"**{interaction.user.display_name}** cuddles **{member.display_name}**! 🥰",
            color=EmbedColor.PRIMARY
        )
        embed.set_image(url="attachment://cuddle.gif")
        await interaction.response.send_message(file=file, embed=embed)

    @app_commands.command(name="slap", description="Slap someone across the face!")
    @app_commands.describe(member="The person you want to slap")
    async def slap(self, interaction: discord.Interaction, member: discord.Member):
        if member == interaction.user:
            return await interaction.response.send_message("Why would you want to slap yourself? Stop that!", ephemeral=True)
            
        gif_path = random.choice(MEN_SLAP_GIFS)
        file = discord.File(gif_path, filename="slap.gif")
        
        embed = discord.Embed(
            description=f"**{interaction.user.display_name}** slaps **{member.display_name}**! 😠",
            color=EmbedColor.PRIMARY
        )
        embed.set_image(url="attachment://slap.gif")
        await interaction.response.send_message(file=file, embed=embed)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        content = message.content.strip()
        
        action_type = None
        if content.startswith("هق"):
            action_type = "hug"
        elif content.startswith("بوسه"):
            action_type = "cuddle"
        elif content.startswith("كف"):
            action_type = "slap"
            
        if action_type and message.mentions:
            member = message.mentions[0]
            
            if member == message.author:
                if action_type == "hug":
                    await message.channel.send("لا يمكنك معانقة نفسك، لكنني سأعانقك! 🫂")
                elif action_type == "cuddle":
                    await message.channel.send("لا يمكنك فعل ذلك لنفسك! 😅")
                elif action_type == "slap":
                    await message.channel.send("لماذا تريد ضرب نفسك؟ توقف عن ذلك!")
                return
                
            if action_type == "hug":
                gif_path = random.choice(MEN_HUG_GIFS)
                file = discord.File(gif_path, filename="hug.gif")
                desc = f"**{message.author.display_name}** يعانق **{member.display_name}**! 🫂"
                attachment_name = "hug.gif"
            elif action_type == "cuddle":
                gif_path = random.choice(MEN_CUDDLE_GIFS)
                file = discord.File(gif_path, filename="cuddle.gif")
                desc = f"**{message.author.display_name}** يبوس **{member.display_name}**! 🥰"
                attachment_name = "cuddle.gif"
            elif action_type == "slap":
                gif_path = random.choice(MEN_SLAP_GIFS)
                file = discord.File(gif_path, filename="slap.gif")
                desc = f"**{message.author.display_name}** يعطي كف لـ **{member.display_name}**! 😠"
                attachment_name = "slap.gif"
                
            embed = discord.Embed(description=desc, color=EmbedColor.PRIMARY)
            embed.set_image(url=f"attachment://{attachment_name}")
            await message.channel.send(file=file, embed=embed)

async def setup(bot: commands.Bot):
    """Setup function for cog loading"""
    await bot.add_cog(Fun(bot, bot.db, bot.config))
