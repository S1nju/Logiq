"""
Leveling Cog for Logiq
XP and leveling system with rank cards
"""

import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime
from typing import Optional
import logging
from utils.i18n import t
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

from utils.embeds import EmbedFactory, EmbedColor
from utils.constants import calculate_level_xp
from utils.permissions import is_admin
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class Leveling(commands.Cog):
    """Leveling system cog"""

    def __init__(self, bot: commands.Bot, db: DatabaseManager, config: dict):
        self.bot = bot
        self.db = db
        self.config = config
        self.module_config = config.get('modules', {}).get('leveling', {})
        self.xp_cooldown = {}
        self.voice_xp_loop.start()

    def cog_unload(self):
        """Cancel background tasks when cog unloads"""
        self.voice_xp_loop.cancel()

    @tasks.loop(seconds=60)
    async def voice_xp_loop(self):
        """Periodically award XP to members active in voice channels"""
        if not self.module_config.get('enabled', True):
            return

        voice_xp_rate = self.module_config.get('voice_xp_rate', 5)
        if voice_xp_rate <= 0:
            return

        for guild in self.bot.guilds:
            for channel in guild.voice_channels:
                # Skip AFK channel if configured
                if guild.afk_channel and channel.id == guild.afk_channel.id:
                    continue

                for member in channel.members:
                    if member.bot:
                        continue

                    user_data = await self.db.get_user(member.id, guild.id)
                    if not user_data:
                        user_data = await self.db.create_user(member.id, guild.id)

                    current_xp = user_data.get('xp', 0)
                    current_level = user_data.get('level', 0)
                    new_xp = current_xp + voice_xp_rate
                    next_level_xp = calculate_level_xp(current_level + 1)

                    if new_xp >= next_level_xp:
                        new_level = current_level + 1
                        await self.db.update_user(member.id, guild.id, {
                            'xp': new_xp,
                            'level': new_level
                        })
                        embed = EmbedFactory.level_up(member, new_level, new_xp)
                        level_up_channel_id = self.module_config.get('level_up_channel', 1537828641071693956)
                        log_channel = guild.get_channel(level_up_channel_id)
                        if log_channel:
                            await log_channel.send(member.mention, embed=embed)
                        logger.info(f"{member} leveled up to {new_level} via voice XP in {guild}")
                    else:
                        await self.db.update_user(member.id, guild.id, {'xp': new_xp})

    @voice_xp_loop.before_loop
    async def before_voice_xp_loop(self):
        """Wait until bot is ready before starting voice XP loop"""
        await self.bot.wait_until_ready()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Award XP for messages"""
        if not self.module_config.get('enabled', True):
            return

        if message.author.bot or not message.guild:
            return

        # Check cooldown
        user_key = f"{message.guild.id}_{message.author.id}"
        current_time = datetime.utcnow().timestamp()

        if user_key in self.xp_cooldown:
            if current_time - self.xp_cooldown[user_key] < self.module_config.get('xp_cooldown', 60):
                return

        self.xp_cooldown[user_key] = current_time

        # Get or create user
        user_data = await self.db.get_user(message.author.id, message.guild.id)
        if not user_data:
            user_data = await self.db.create_user(message.author.id, message.guild.id)

        # Calculate XP
        xp_gain = self.module_config.get('xp_per_message', 10)
        new_xp = user_data.get('xp', 0) + xp_gain
        current_level = user_data.get('level', 0)

        # Check for level up
        next_level_xp = calculate_level_xp(current_level + 1)

        if new_xp >= next_level_xp:
            new_level = current_level + 1
            await self.db.update_user(message.author.id, message.guild.id, {
                'xp': new_xp,
                'level': new_level
            })

            # Send level up message
            embed = EmbedFactory.level_up(message.author, new_level, new_xp)
            level_up_channel_id = self.module_config.get('level_up_channel', 1537828641071693956)
            channel = message.guild.get_channel(level_up_channel_id)
            
            if channel:
                await channel.send(message.author.mention, embed=embed)
            
            logger.info(f"{message.author} leveled up to {new_level} in {message.guild}")
        else:
            await self.db.update_user(message.author.id, message.guild.id, {'xp': new_xp})

    # NOTE: /rank and /leaderboard commands have been moved to games.py as PUBLIC commands

    @app_commands.command(name="setlevel", description="Set user's level (Admin)")
    @app_commands.describe(
        user="User to modify",
        level="New level"
    )
    @is_admin()
    async def set_level(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        level: int
    ):
        """Set user level"""
        if level < 0:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Invalid Level", "Level must be 0 or greater"),
                ephemeral=True
            )
            return

        xp = calculate_level_xp(level)

        await self.db.update_user(user.id, interaction.guild.id, {
            'level': level,
            'xp': xp
        })

        embed = EmbedFactory.success(
            "Level Set",
            f"Set {user.mention}'s level to **{level}** (XP: **{xp}**)"
        )
        await interaction.response.send_message(embed=embed)
        logger.info(f"{interaction.user} set {user}'s level to {level}")

    @app_commands.command(name="resetlevels", description="Reset all user levels to zero (Admin)")
    @app_commands.describe(guild_only="Reset levels only for this server (default: True)")
    @is_admin()
    async def reset_levels(self, interaction: discord.Interaction, guild_only: bool = True):
        """Reset all user levels to zero with confirmation UI"""
        target_guild_id = interaction.guild.id if guild_only else None
        db_ref = self.db

        class ResetConfirmView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=60)
                self.value = None

            @discord.ui.button(label="⚠️ Confirm Reset All Levels", style=discord.ButtonStyle.danger)
            async def confirm(self, inter: discord.Interaction, button: discord.ui.Button):
                if inter.user.id != interaction.user.id:
                    return await inter.response.send_message("❌ Only the command author can confirm.", ephemeral=True)

                await inter.response.defer(ephemeral=True)
                modified_count = await db_ref.reset_all_levels(target_guild_id)
                embed = EmbedFactory.success(
                    "Levels Reset",
                    f"Successfully reset **{modified_count}** user accounts to Level **0** and **0** XP."
                )
                for item in self.children:
                    item.disabled = True
                await inter.edit_original_response(embed=embed, view=self)
                logger.info(f"{inter.user} confirmed reset levels for guild_id={target_guild_id} ({modified_count} users updated)")

            @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
            async def cancel(self, inter: discord.Interaction, button: discord.ui.Button):
                if inter.user.id != interaction.user.id:
                    return await inter.response.send_message("❌ Only the command author can cancel.", ephemeral=True)

                for item in self.children:
                    item.disabled = True
                await inter.response.edit_message(content="❌ Level reset cancelled.", embed=None, view=self)

        confirm_embed = EmbedFactory.warning(
            "⚠️ Level Reset Warning",
            "This feature will reset all user levels and XP to **0**. This is a destructive action.\n\nAre you sure you want to proceed?"
        )
        view = ResetConfirmView()
        await interaction.response.send_message(embed=confirm_embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    """Setup function for cog loading"""
    await bot.add_cog(Leveling(bot, bot.db, bot.config))

