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

CRINGE_REPLIES = [
    "انا وحيد كالقمر... ومخيف كالذيب 🐺🚶‍♂️",
    "يا ليت المسافات تنطوي واشوفك قدامي الحين 🥺💔",
    "ممكن نتعرف؟ تري انا مو زي باقي العيال 🌹😎",
    "انتي القمر ولا القمر ماخذ نورك؟ 🌚✨",
    "انا ما ابكي... بس عيني دخل فيها تراب 😔🚭",
    "ليتني كنت دمعه تنولد بعينك واموت بخدك 💧🥀",
    "انا شخص غامض، محد يفهمني الا النت وقوقل 💻🖤",
    "تدرين وش الشي المشترك بيني وبين كريستيانو؟ كلنا اساطير بس انا اسطوره قلبك ⚽😏",
    "عيونك دوختني.. ممكن تعطيني باندول؟ 💊😵",
    "يا عينييي على اللي ينقط يا حلوك بس :07_bearplushieheart: ",
    "فديت هالتنقيطة وفديت راعيها، يا جعلني ما أنحرم منك.... :loveShy: ",
    "يا ناس على الزين اللي يطب علينا كذا فجأة.....:plz_no:",
    "يا حلوك ويا حلو هالتنقيط، فديت هالقلب :cat_cute_blush: ",
    "فديت قلبك يا شيخ:noplsno:  نورتنا ونوّرت المكان معك",
    "يا لبى هالعين وهالطلة وهالتنقيط بعد :periodsis: ",
    "ارحبببب يا أزين من ينقط، حي الله هالوجه :reaction_roles_9: ",
    "يا هلا باللي ينقط ويروح, تعال تعال وين رايح يا حلو؟ ",
    "يا زين من ينقط علينا,  نقط كل يوم تكفى لا تبخل:loveShy: ",
    "منور يا عسل:hh:  بس المرة الجاية لا تطول علينا:uwu: ",
    "أخيرًا طلع لك حس؟ هههههههه نورتنا يا بعدي :s_catuwu~1: ",
    "يا لبى اللي يمر علينا فجأة ويقلب الجو حلو :loveplead: ",
    "فديت هالوجه اللي يكفي عن ألف كلمة :emoji_45: ",
    "يا عيني عليك، تنقط وتخلّي الواحد يبتسم غصب 😭:emoji~6: ",
    "يا زينك ويا زين سوالفك، عاد لا تقطعها علينا :cat_cute_blush: ",
    "فديت من جانا على غفلة وخلّى للمكان طعم ثاني :emoji_53: ",
    "يا لبى قلبك، حتى تنقيطك له هيبة يا شيخ :loveShy: :emoji~5: ",
    "ارحب يا بعد حيي، نورت ولا هنت يا حلو :plz_no: ",
    "يا عسل لا تسويها مرة وحدة، نبيها عادة يومية :bochi_angry: ",
    "فديت هالتنقيطة اللي جت بوقتها وعدّلت المزاج :uwu: ",
    "يا ناس فديت الزين إذا قرر يطب علينا بدون موعد :uwu:  :emoji_50: ",
    "يا لبى هالطلة اللي تجي فجأة وتاخذ القلب معها",
    "يا حلو لا تنقط وتهج، اقعد لنا شوي توّنا قلنا يا هلا ...:s_catuwu~1: ",
    "فديت اللي إذا حضر حضر معه الزين كله :Event4: :copy_725F45E23D02495B898358B0D1E: ",
    "يا زين من ينقط ويخلّي المكان غير :Stars_nene: :emoji_80: ",
    "يا لبى هالوجه، وش هالزين اللي جاينا اليوم؟",
    "منور يا حلو، تنقيطتك تفتح النفس والله :loveShy: ",
    "فديت هالقلب اللي يذكرنا ويطب علينا بين فترة وفترة :emoji~4: ",
    "يا بعدهم، لا تغيب واجد ترى نتحسس :noplsno: ",
    "يا حلوك يا عسل، مرّاتك علينا غالية :emoji~5: ",
    "ارحب مليون، يا زين من جانا ونوّرنا :loveShy: ",
    "يا لبى اللي ينقط علينا، عسى ما ننحرم من هالطلة :emoji_50: ",
    "فديت الزين وفديت تنقيطه، عاد لا تقطعها تكفى 🤍:uwu:",
    "يا عيني على اللي ينقط يا حلوك :emoji_44: ",
    "فديت هالتنقيطه وصاحبها:emoji~4:",
    "يا ناس على الزين اللي يطب علينا فجأه:uwu: ",
    "يا حلوك ويا حلو تنقيطك :cute: :reaction_roles_9: ",
    "فديت قلبك يا شيخ نورتنا:__~17: ",
    "يا لبى هالعين وهالتنقيط  :uwu: ",
    "ارحببب يا اطلق من ينقط :emoji_51: ",
    "يا هلا باللي ينقط ويروح،  تعال تعال وين رايح :emoji_50: ",
    "يا زين من ينقط، نقط كل يوم تكفى:2730role: :minecraftheart: ",
    "منور يا عسل، لا تطول علينا المره الجايه:emoji_49: ",
    "اخيراً طلع لك صوت؟ هههههه نورتنا يا حلو:periodsis:"
]

HLA_REPLIES = [
    "هلا والله 👋",
    "ارحب ملايين ✨",
    "يا هلا ومسهلا 🌹",
    "هلا بالطش والرش 🌧️",
    "المهلي ما يولي يا عين اخوك 👑",
    "ياهلا بالزين كله 💖",
    "نورت المكان يالغالي 🌟",
    "هلا بك ياعيني ✌️"
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
        
        self.jokes = []
        try:
            with open("assets/jokes/humor.tsv", "r", encoding="utf-8") as f:
                next(f)  # skip header
                for line in f:
                    parts = line.strip("\n").split("\t")
                    if len(parts) >= 3 and parts[2].strip().lower() == "yes":
                        self.jokes.append(parts[1])
        except Exception as e:
            logger.error(f"Failed to load jokes dataset: {e}")

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
        
        if "نكتة" in content or "نكته" in content:
            if hasattr(self, "jokes") and self.jokes:
                joke = random.choice(self.jokes)
                await message.reply(joke)
            return

        if content == ".":
            cringe = random.choice(CRINGE_REPLIES)
            await message.reply(cringe)
            return

        if "هلا" in content.split() or content.startswith("هلا"):
            if random.random() < 0.6:
                reply = random.choice(HLA_REPLIES)
                await message.reply(reply)
                return

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
