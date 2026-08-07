"""
Admin Cog for Logiq
Administrative commands and bot management
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
import logging
import sys

from utils.embeds import EmbedFactory, EmbedColor
from utils.permissions import is_admin
from database.db_manager import DatabaseManager
from utils.i18n import i18n, t

logger = logging.getLogger(__name__)


class Admin(commands.Cog):
    """Admin and management cog"""

    def __init__(self, bot: commands.Bot, db: DatabaseManager, config: dict):
        self.bot = bot
        self.db = db
        self.config = config

    @app_commands.command(name="setlanguage", description="Change bot language setting (Admin)")
    @app_commands.describe(language="Select language (en for English, ar for Arabic)")
    @app_commands.choices(language=[
        app_commands.Choice(name="English (English)", value="en"),
        app_commands.Choice(name="العربية (Arabic)", value="ar")
    ])
    @is_admin()
    async def set_language(self, interaction: discord.Interaction, language: app_commands.Choice[str]):
        """Set bot language state (Slash Command)"""
        lang_code = language.value
        await self._perform_set_language(interaction.response.send_message, lang_code, ephemeral=True)

    @commands.command(name="setlanguage", aliases=["lang", "setlang"])
    @commands.has_permissions(administrator=True)
    async def set_language_prefix(self, ctx: commands.Context, lang_code: str):
        """Set bot language state (Prefix Command: !setlanguage en|ar)"""
        await self._perform_set_language(ctx.send, lang_code.lower())

    async def _perform_set_language(self, send_func, lang_code: str, ephemeral: bool = False):
        success = i18n.set_language(lang_code)
        if success:
            lang_name = i18n.get_language_name(lang_code)
            embed = EmbedFactory.success(
                t("language.set_success_title", lang=lang_code),
                t("language.set_success", lang=lang_code, lang_name=lang_name, lang_code=lang_code)
            )
            await send_func(embed=embed, ephemeral=ephemeral) if ephemeral else await send_func(embed=embed)
        else:
            embed = EmbedFactory.error(
                t("common.error"),
                t("language.invalid")
            )
            await send_func(embed=embed, ephemeral=ephemeral) if ephemeral else await send_func(embed=embed)



    @app_commands.command(name="reload", description="Reload a cog")
    @app_commands.describe(cog="Name of the cog to reload")
    @is_admin()
    async def reload(self, interaction: discord.Interaction, cog: str):
        """Reload a cog"""
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
            embed = EmbedFactory.success(
                t("admin.reload_success_title"),
                t("admin.reload_success", cog=cog)
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            logger.info(f"{interaction.user} reloaded cog {cog}")
        except commands.ExtensionNotLoaded:
            await interaction.response.send_message(
                embed=EmbedFactory.error(t("common.error"), t("admin.reload_not_loaded", cog=cog)),
                ephemeral=True
            )
        except commands.ExtensionNotFound:
            await interaction.response.send_message(
                embed=EmbedFactory.error(t("common.error"), t("admin.reload_not_found", cog=cog)),
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                embed=EmbedFactory.error(t("common.error"), t("admin.reload_failed", error=str(e))),
                ephemeral=True
            )
            logger.error(f"Error reloading cog {cog}: {e}", exc_info=True)

    @app_commands.command(name="sync", description="Sync slash commands")
    @is_admin()
    async def sync(self, interaction: discord.Interaction):
        """Sync command tree (Slash Command)"""
        await interaction.response.defer(ephemeral=True)
        try:
            synced = await self.bot.tree.sync()
            embed = EmbedFactory.success(
                t("admin.sync_success_title"),
                t("admin.sync_success", count=len(synced))
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            logger.info(f"{interaction.user} synced commands")
        except Exception as e:
            await interaction.followup.send(
                embed=EmbedFactory.error(t("common.error"), t("admin.sync_failed", error=str(e))),
                ephemeral=True
            )
            logger.error(f"Error syncing commands: {e}", exc_info=True)

    @commands.command(name="sync")
    @commands.has_permissions(administrator=True)
    async def sync_prefix(self, ctx: commands.Context):
        """Sync command tree (Prefix Command: !sync)"""
        try:
            synced = await self.bot.tree.sync()
            embed = EmbedFactory.success(
                t("admin.sync_success_title"),
                t("admin.sync_success", count=len(synced))
            )
            await ctx.send(embed=embed)
            logger.info(f"{ctx.author} synced commands via prefix command")
        except Exception as e:
            await ctx.send(embed=EmbedFactory.error(t("common.error"), t("admin.sync_failed", error=str(e))))
            logger.error(f"Error syncing commands via prefix command: {e}", exc_info=True)

    @app_commands.command(name="modules", description="View and toggle modules")
    @is_admin()
    async def modules(self, interaction: discord.Interaction):
        """View module status"""
        modules = self.config.get('modules', {})

        description = ""
        for module_name, module_config in modules.items():
            enabled = module_config.get('enabled', True)
            status = "🟢 Enabled" if enabled else "🔴 Disabled"
            description += f"**{module_name.title()}**: {status}\n"

        embed = EmbedFactory.create(
            title=t("admin.modules_title"),
            description=description or t("admin.modules_empty"),
            color=EmbedColor.INFO
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="botinfo", description="View bot information")
    async def botinfo(self, interaction: discord.Interaction):
        """Display bot information"""
        # Calculate uptime
        uptime = discord.utils.utcnow() - self.bot.start_time if hasattr(self.bot, 'start_time') else None
        uptime_str = str(uptime).split('.')[0] if uptime else t("common.unknown")

        # Get stats
        total_guilds = len(self.bot.guilds)
        total_users = sum(g.member_count for g in self.bot.guilds)
        total_channels = sum(len(g.channels) for g in self.bot.guilds)

        embed = EmbedFactory.create(
            title=t("admin.botinfo_title"),
            color=EmbedColor.PRIMARY,
            thumbnail=self.bot.user.display_avatar.url if self.bot.user else None,
            fields=[
                {"name": t("utility.serverstats_title", name="Servers"), "value": str(total_guilds), "inline": True},
                {"name": t("utility.total_members"), "value": f"{total_users:,}", "inline": True},
                {"name": t("utility.text_channels"), "value": str(total_channels), "inline": True},
                {"name": t("phrases.Uptime"), "value": uptime_str, "inline": True},
                {"name": t("phrases.Python Version"), "value": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}", "inline": True},
                {"name": t("phrases.Discord.py"), "value": discord.__version__, "inline": True},
                {"name": t("phrases.Database"), "value": "MongoDB (Motor)", "inline": True},
                {"name": t("phrases.Latency"), "value": f"{round(self.bot.latency * 1000)}ms", "inline": True}
            ]
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="setlogchannel", description="Set the log channel")
    @app_commands.describe(channel="Channel for moderation logs")
    @is_admin()
    async def set_log_channel(self, interaction: discord.Interaction, channel: discord.TextChannel):
        """Set log channel"""
        guild_config = await self.db.get_guild(interaction.guild.id)
        if not guild_config:
            guild_config = await self.db.create_guild(interaction.guild.id)

        await self.db.update_guild(interaction.guild.id, {'log_channel': channel.id})

        embed = EmbedFactory.success(
            t("admin.setlogchannel_success_title"),
            t("admin.setlogchannel_success", channel=channel.mention)
        )
        await interaction.response.send_message(embed=embed)
        logger.info(f"Log channel set to {channel} in {interaction.guild}")

    @app_commands.command(name="config", description="View server configuration")
    @is_admin()
    async def config(self, interaction: discord.Interaction):
        """View server configuration"""
        guild_config = await self.db.get_guild(interaction.guild.id)

        if not guild_config:
            await interaction.response.send_message(
                embed=EmbedFactory.info(t("phrases.No Configuration"), t("admin.config_none")),
                ephemeral=True
            )
            return

        not_set = t("common.not_set")
        log_channel = f"<#{guild_config.get('log_channel')}>" if guild_config.get('log_channel') else not_set
        welcome_channel = f"<#{guild_config.get('welcome_channel')}>" if guild_config.get('welcome_channel') else not_set
        verified_role = f"<@&{guild_config.get('verified_role')}>" if guild_config.get('verified_role') else not_set

        embed = EmbedFactory.create(
            title=t("admin.config_title"),
            color=EmbedColor.INFO,
            fields=[
                {"name": t("phrases.Log Channel"), "value": log_channel, "inline": False},
                {"name": t("phrases.Welcome Channel"), "value": welcome_channel, "inline": False},
                {"name": t("phrases.Verified Role"), "value": verified_role, "inline": False},
                {"name": t("phrases.Verification Type"), "value": guild_config.get('verification_type', 'button'), "inline": True}
            ]
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="purge", description="Delete messages in bulk")
    @app_commands.describe(amount="Number of messages to delete (1-100)")
    @is_admin()
    async def purge(self, interaction: discord.Interaction, amount: int):
        """Purge messages"""
        if amount < 1 or amount > 100:
            await interaction.response.send_message(
                embed=EmbedFactory.error(t("common.invalid_amount"), t("admin.purge_invalid")),
                ephemeral=True
            )
            return

        try:
            deleted = await interaction.channel.purge(limit=amount)
            embed = EmbedFactory.success(
                t("admin.purge_success_title"),
                t("admin.purge_success", count=len(deleted))
            )
            await interaction.response.send_message(embed=embed, ephemeral=True, delete_after=5)
            logger.info(f"{interaction.user} purged {len(deleted)} messages in {interaction.channel}")
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=EmbedFactory.error(t("common.error"), t("admin.purge_no_permission")),
                ephemeral=True
            )



async def setup(bot: commands.Bot):
    """Setup function for cog loading"""
    await bot.add_cog(Admin(bot, bot.db, bot.config))
