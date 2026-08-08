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

class ActionBackView(discord.ui.View):
    def __init__(self, action: str, author: discord.Member, target: discord.Member, label: str, back_desc_func):
        super().__init__(timeout=10.0)
        self.action = action
        self.author = author
        self.target = target
        self.message = None
        self.back_desc_func = back_desc_func
        
        btn_style = discord.ButtonStyle.danger if action == "slap" else discord.ButtonStyle.primary
        self.action_btn = discord.ui.Button(label=label, style=btn_style)
        self.action_btn.callback = self.button_callback
        self.add_item(self.action_btn)

    async def button_callback(self, interaction: discord.Interaction):
        if interaction.user != self.target:
            return await interaction.response.send_message("This button is not for you!", ephemeral=True)
            
        GIF_MAP = {
            "hug": (MEN_HUG_GIFS, "hug.gif"),
            "cuddle": (MEN_CUDDLE_GIFS, "cuddle.gif"),
            "slap": (MEN_SLAP_GIFS, "slap.gif")
        }
        
        gif_list, filename = GIF_MAP[self.action]
        gif_path = random.choice(gif_list)
        file = discord.File(gif_path, filename=filename)
        
        desc = self.back_desc_func(self.target, self.author)
        embed = discord.Embed(description=desc, color=EmbedColor.PRIMARY)
        embed.set_image(url=f"attachment://{filename}")
        
        for child in self.children:
            child.disabled = True
            
        try:
            if self.message:
                await self.message.edit(view=self)
            else:
                await interaction.message.edit(view=self)
        except discord.HTTPException:
            pass
            
        await interaction.response.send_message(file=file, embed=embed)

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self)
        except Exception:
            pass

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
        
        def get_desc(t, a): return f"**{t.display_name}** hugs **{a.display_name}** back! 🫂"
        view = ActionBackView("hug", interaction.user, member, "Hug Back 🫂", get_desc)
        await interaction.response.send_message(file=file, embed=embed, view=view)
        view.message = await interaction.original_response()

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
        
        def get_desc(t, a): return f"**{t.display_name}** cuddles **{a.display_name}** back! 🥰"
        view = ActionBackView("cuddle", interaction.user, member, "Cuddle Back 🥰", get_desc)
        await interaction.response.send_message(file=file, embed=embed, view=view)
        view.message = await interaction.original_response()

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
        
        def get_desc(t, a): return f"**{t.display_name}** slaps **{a.display_name}** back! 😠"
        view = ActionBackView("slap", interaction.user, member, "Slap Back 😠", get_desc)
        await interaction.response.send_message(file=file, embed=embed, view=view)
        view.message = await interaction.original_response()

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
                btn_label = "عناق متبادل 🫂"
                def get_desc(t, a): return f"**{t.display_name}** يبادلك العناق يا **{a.display_name}**! 🫂"
            elif action_type == "cuddle":
                gif_path = random.choice(MEN_CUDDLE_GIFS)
                file = discord.File(gif_path, filename="cuddle.gif")
                desc = f"**{message.author.display_name}** يبوس **{member.display_name}**! 🥰"
                attachment_name = "cuddle.gif"
                btn_label = "بوسة متبادلة 🥰"
                def get_desc(t, a): return f"**{t.display_name}** يبادلك البوسة يا **{a.display_name}**! 🥰"
            elif action_type == "slap":
                gif_path = random.choice(MEN_SLAP_GIFS)
                file = discord.File(gif_path, filename="slap.gif")
                desc = f"**{message.author.display_name}** يعطي كف لـ **{member.display_name}**! 😠"
                attachment_name = "slap.gif"
                btn_label = "كف متبادل 😠"
                def get_desc(t, a): return f"**{t.display_name}** يرد الكف لـ **{a.display_name}**! 😠"
                
            embed = discord.Embed(description=desc, color=EmbedColor.PRIMARY)
            embed.set_image(url=f"attachment://{attachment_name}")
            view = ActionBackView(action_type, message.author, member, btn_label, get_desc)
            view.message = await message.channel.send(file=file, embed=embed, view=view)

async def setup(bot: commands.Bot):
    """Setup function for cog loading"""
    await bot.add_cog(Fun(bot, bot.db, bot.config))
