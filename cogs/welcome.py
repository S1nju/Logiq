"""
Welcome Cog for Logiq
Handles customizable rich welcome messages and embeds.
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import json
from utils.i18n import t

from utils.embeds import EmbedFactory, EmbedColor
from utils.permissions import is_admin
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class WelcomeSetupModal(discord.ui.Modal, title="Configure Welcome System"):
    """Modal for creating/updating a rich welcome configuration"""
    
    message_input = discord.ui.TextInput(
        label="Message Content (Outside Embed)",
        placeholder="Type {user} to mention, {server} for name, etc...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500
    )

    embed_title = discord.ui.TextInput(
        label="Embed Title",
        placeholder="e.g. 👋 Welcome to {server}!",
        required=False,
        max_length=200
    )

    embed_desc = discord.ui.TextInput(
        label="Embed Description",
        placeholder="e.g. We're so glad you're here, {user}!",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=1000
    )

    embed_image = discord.ui.TextInput(
        label="Embed Image URL",
        placeholder="http://example.com/image.png (Optional)",
        required=False,
        max_length=300
    )

    def __init__(self, cog, channel: discord.TextChannel):
        super().__init__(title=t("welcome.modal_title", default="Configure Welcome System"))
        self.cog = cog
        self.channel = channel
        self.message_input.label = t("welcome.message_input", default="Message Content (Outside Embed)")
        self.embed_title.label = t("welcome.embed_title", default="Embed Title (optional)")
        self.embed_desc.label = t("welcome.embed_desc", default="Embed Description")
        self.embed_image.label = t("welcome.embed_image", default="Embed Image URL")

    async def on_submit(self, interaction: discord.Interaction):
        # Update db
        guild_id = interaction.guild.id
        guild_config = await self.cog.db.get_guild(guild_id)
        if not guild_config:
            guild_config = await self.cog.db.create_guild(guild_id)
            
        welcome_config = {
            "channel_id": self.channel.id,
            "message": self.message_input.value,
            "title": self.embed_title.value,
            "description": self.embed_desc.value,
            "image_url": self.embed_image.value
        }
        
        await self.cog.db.update_guild(guild_id, {"welcome_config": welcome_config})
        
        await interaction.response.send_message(
            embed=EmbedFactory.success(
                t("welcome.success_title", default="Welcome Configured!"),
                t("welcome.success_desc", default=f"Welcome messages will now be sent to {self.channel.mention} with your new design.")
            ),
            ephemeral=True
        )

class Welcome(commands.Cog):
    """Rich Welcome Message cog"""

    def __init__(self, bot: commands.Bot, db: DatabaseManager, config: dict):
        self.bot = bot
        self.db = db
        self.config = config
        self.module_config = config.get('modules', {}).get('welcome', {'enabled': True})

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not self.module_config.get('enabled', True):
            return

        guild_config = await self.db.get_guild(member.guild.id)
        if not guild_config:
            return

        welcome_config = guild_config.get('welcome_config')
        if not welcome_config:
            # Check legacy config for backward compatibility
            legacy_channel_id = guild_config.get('welcome_channel')
            if legacy_channel_id:
                legacy_msg = guild_config.get('welcome_message', "Welcome to **{server}**! 👋\\n\\nPlease verify yourself.")
                welcome_config = {
                    "channel_id": legacy_channel_id,
                    "message": "{user}",
                    "title": "👋 Welcome to {server}!",
                    "description": legacy_msg,
                    "image_url": ""
                }
            else:
                return

        channel_id = welcome_config.get('channel_id')
        if not channel_id:
            return
            
        channel = member.guild.get_channel(channel_id)
        if not channel:
            return

        def process_text(text):
            if not text:
                return text
            res = text.replace('{user}', member.mention)
            res = res.replace('{username}', member.display_name)
            res = res.replace('{server}', member.guild.name)
            res = res.replace('{member_count}', str(member.guild.member_count))
            return res

        msg_content = process_text(welcome_config.get('message', ''))
        title = process_text(welcome_config.get('title', 'Welcome!'))
        desc = process_text(welcome_config.get('description', ''))
        img_url = welcome_config.get('image_url', '')

        embed = EmbedFactory.create(title=title, description=desc, color=EmbedColor.PRIMARY)
        follow_up_embed = EmbedFactory.create(title="", description="", color=EmbedColor.PRIMARY, image="https://cdn.discordapp.com/attachments/1532825623435804692/1535620592680570930/LINE.gif?ex=6a786d9f&is=6a771c1f&hm=10f9a21b6fd1480a0f7b26009cc7409f28a11c48b8868e929b0421271efc89db&")
        
        if img_url and img_url.startswith('http'):
            try:
                # Appending timestamp prevents client side cache from stalling if url changes sometimes, but here we just pass url
                embed.set_image(url=img_url)
            except Exception:
                pass

        try:
            if msg_content or desc or title or img_url:
                await channel.send(content=msg_content if msg_content else None, embed=embed if (title or desc or img_url) else None)
                await channel.send(embed=follow_up_embed)
            logger.info(f"Sent rich welcome message for {member} in {channel}")
        except discord.Forbidden:
            logger.warning(f"No permission to send welcome in {channel}")

    @app_commands.command(name="setup-welcome", description="Configure rich welcome messages (Admin)")
    @app_commands.describe(channel="The channel for welcome messages")
    @is_admin()
    async def configure_welcome(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Configure Welcome Message"""
        modal = WelcomeSetupModal(self, channel)
        await interaction.response.send_modal(modal)

async def setup(bot: commands.Bot):
    """Setup function for cog loading"""
    await bot.add_cog(Welcome(bot, bot.db, bot.config))
