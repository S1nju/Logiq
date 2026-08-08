"""
Moderation Cog for Logiq
Comprehensive moderation tools with AI-powered auto-moderation
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Optional
import logging
from utils.i18n import t
import asyncio

from utils.embeds import EmbedFactory, EmbedColor
from utils.permissions import is_moderator, PermissionChecker
from utils.converters import TimeConverter
from database.db_manager import DatabaseManager
from database.models import Warning

logger = logging.getLogger(__name__)


class Moderation(commands.Cog):
    """Moderation system cog"""

    def __init__(self, bot: commands.Bot, db: DatabaseManager, config: dict):
        self.bot = bot
        self.db = db
        self.config = config
        self.module_config = config.get('modules', {}).get('moderation', {})
        self.spam_tracker = {}  # Track spam
        self.toxicity_filter_enabled = self.module_config.get('auto_mod', {}).get('toxicity_filter', True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Auto-moderation on messages"""
        if not self.module_config.get('enabled', True):
            return

        if message.author.bot or not message.guild:
            return

        # --- Arabic Moderation Text Parser ---
        if message.content and message.mentions:
            guild_data = await self.db.get_guild(message.guild.id)
            if guild_data:
                aliases = guild_data.get('aliases', {})
                content_parts = message.content.strip().split()
                cmd_prefix = content_parts[0]
                target_member = message.mentions[0]
                
                # Check permissions physically
                can_moderate, _ = PermissionChecker.can_moderate(message.author, target_member)
                has_admin = message.author.guild_permissions.administrator
                
                if can_moderate or has_admin:
                    try:
                        if cmd_prefix == aliases.get('ban_add', 'باند'):
                            await target_member.ban(reason=f"Action invoked by {message.author}")
                            await message.channel.send(f"تم اعطاء باند لـ {target_member.mention}")
                                
                        elif cmd_prefix == aliases.get('ban_remove', 'ازالة'):
                            banned_users = [entry async for entry in message.guild.bans()]
                            ban_entry = discord.utils.get(banned_users, user__id=target_member.id)
                            if ban_entry:
                                await message.guild.unban(ban_entry.user)
                                await message.channel.send(f"تم إزالة الباند عن {target_member.mention}")
                                
                        elif cmd_prefix == aliases.get('voice_mute', 'ميوت'):
                            await target_member.edit(mute=True, reason=f"Voice muted by {message.author}")
                            await message.channel.send(f"تم اعطاء ميوت صوتي لـ {target_member.mention}")
                                
                        elif cmd_prefix == aliases.get('voice_unmute', 'فك'):
                            await target_member.edit(mute=False, reason=f"Voice unmuted by {message.author}")
                            await message.channel.send(f"تم فك الميوت الصوتي عن {target_member.mention}")
                                
                        elif cmd_prefix == aliases.get('chat_mute', 'اسكت'):
                            mute_role = discord.utils.get(message.guild.roles, name="Muted")
                            if not mute_role:
                                mute_role = await message.guild.create_role(name="Muted")
                                for ch in message.guild.text_channels:
                                    await ch.set_permissions(mute_role, send_messages=False)
                            await target_member.add_roles(mute_role, reason=f"Chat Mute by {message.author}")
                            await message.channel.send(f"تم اسكات {target_member.mention}")
                                
                        elif cmd_prefix == aliases.get('chat_unmute', 'تكلم'):
                            mute_role = discord.utils.get(message.guild.roles, name="Muted")
                            if mute_role and mute_role in target_member.roles:
                                await target_member.remove_roles(mute_role, reason=f"Chat Unmute by {message.author}")
                            await message.channel.send(f"تم فك الاسكات عن {target_member.mention}")
                                
                        elif cmd_prefix == aliases.get('media_block', 'صور'):
                            await message.channel.set_permissions(target_member, attach_files=False, embed_links=False)
                            await message.channel.send(f"تم منع {target_member.mention} من إرسال الصور")
                                
                        elif cmd_prefix == aliases.get('live_block', 'لايف'):
                            curr_voice = target_member.voice.channel if target_member.voice else None
                            if curr_voice:
                                await curr_voice.set_permissions(target_member, stream=False)
                                await message.channel.send(f"تم منع {target_member.mention} من البث المباشر (اللايف) في الروم الصوتي")
                            else:
                                await message.channel.send(f"يجب أن يكون {target_member.mention} في روم صوتي")
                    except discord.Forbidden:
                        await message.channel.send("❌ عذراً، لا أملك صلاحية كافية لتنفيذ هذا الإجراء على هذا العضو. تأكد من أن رتبتي أعلى من رتبته!")
                else:
                    # Provide feedback if they lack permissions but successfully matched an alias
                    valid_aliases = list(aliases.values()) if aliases else []
                    default_aliases = ['باند', 'ازالة', 'ميوت', 'فك', 'اسكت', 'تكلم', 'صور', 'لايف']
                    if cmd_prefix in valid_aliases or cmd_prefix in default_aliases:
                        await message.channel.send("❌ عذراً، ليس لديك الصلاحيات الكافية لتنفيذ هذا الأمر.")

        # Check spam
        if self.module_config.get('auto_mod', {}).get('spam_detection', True):
            await self._check_spam(message)

        # Check excessive mentions
        max_mentions = self.module_config.get('auto_mod', {}).get('max_mentions', 5)
        if len(message.mentions) > max_mentions:
            await message.delete()
            await message.channel.send(
                f"{message.author.mention} Please don't spam mentions!",
                delete_after=5
            )
            return

    async def _check_spam(self, message: discord.Message):
        """Check for spam messages"""
        user_id = message.author.id
        current_time = datetime.utcnow().timestamp()

        if user_id not in self.spam_tracker:
            self.spam_tracker[user_id] = []

        # Add message timestamp
        self.spam_tracker[user_id].append(current_time)

        # Remove old timestamps (older than 5 seconds)
        self.spam_tracker[user_id] = [
            ts for ts in self.spam_tracker[user_id]
            if current_time - ts < 5
        ]

        # Check if spam threshold exceeded
        if len(self.spam_tracker[user_id]) > 5:
            try:
                await message.author.timeout(timedelta(minutes=5), reason="Spam detected")
                await message.channel.send(
                    f"{message.author.mention} has been timed out for 5 minutes due to spam.",
                    delete_after=10
                )
                self.spam_tracker[user_id] = []
                logger.info(f"Auto-muted {message.author} for spam")
            except discord.Forbidden:
                pass

    @app_commands.command(name="warn", description="Warn a user")
    @app_commands.describe(
        user="User to warn",
        reason="Reason for warning"
    )
    @is_moderator()
    async def warn(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str
    ):
        """Warn a user"""
        can_moderate, error = PermissionChecker.can_moderate(interaction.user, user)
        if not can_moderate:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Cannot Warn", error),
                ephemeral=True
            )
            return

        # Create warning
        warning = Warning(
            moderator_id=interaction.user.id,
            reason=reason
        )

        # Get or create user
        user_data = await self.db.get_user(user.id, interaction.guild.id)
        if not user_data:
            user_data = await self.db.create_user(user.id, interaction.guild.id)

        # Add warning
        await self.db.add_warning(user.id, interaction.guild.id, warning.to_dict())

        # Get total warnings
        warnings = await self.db.get_warnings(user.id, interaction.guild.id)

        embed = EmbedFactory.moderation_action("Warning", user, interaction.user, reason)
        embed.add_field(name="Total Warnings", value=str(len(warnings)), inline=False)

        await interaction.response.send_message(embed=embed)

        # DM user
        try:
            dm_embed = EmbedFactory.warning(
                "You have been warned",
                f"**Server:** {interaction.guild.name}\n**Reason:** {reason}\n**Total Warnings:** {len(warnings)}"
            )
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            pass

        # Log
        await self._log_action(interaction.guild, embed)
        logger.info(f"{interaction.user} warned {user} in {interaction.guild}")

    @app_commands.command(name="warnings", description="View user warnings")
    @app_commands.describe(user="User to check")
    @is_moderator()
    async def warnings(self, interaction: discord.Interaction, user: discord.Member):
        """View user warnings"""
        warnings = await self.db.get_warnings(user.id, interaction.guild.id)

        if not warnings:
            await interaction.response.send_message(
                embed=EmbedFactory.info("No Warnings", f"{user.mention} has no warnings."),
                ephemeral=True
            )
            return

        description = ""
        for i, warning in enumerate(warnings, 1):
            moderator = interaction.guild.get_member(warning['moderator_id'])
            mod_name = moderator.mention if moderator else f"<@{warning['moderator_id']}>"
            timestamp = datetime.fromtimestamp(warning['timestamp']).strftime("%Y-%m-%d %H:%M")
            description += f"**{i}.** {warning['reason']}\n   *By {mod_name} on {timestamp}*\n\n"

        embed = EmbedFactory.create(
            title=f"⚠️ Warnings for {user.display_name}",
            description=description,
            color=EmbedColor.WARNING,
            thumbnail=user.display_avatar.url
        )
        embed.set_footer(text=f"Total warnings: {len(warnings)}")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="timeout", description="Timeout a user")
    @app_commands.describe(
        user="User to timeout",
        duration="Duration (e.g., 1h, 30m, 1d)",
        reason="Reason for timeout"
    )
    @is_moderator()
    async def timeout(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        duration: str,
        reason: str = "No reason provided"
    ):
        """Timeout a user"""
        can_moderate, error = PermissionChecker.can_moderate(interaction.user, user)
        if not can_moderate:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Cannot Timeout", error),
                ephemeral=True
            )
            return

        seconds = TimeConverter.parse(duration)
        if not seconds or seconds > 2419200:  # Max 28 days
            await interaction.response.send_message(
                embed=EmbedFactory.error("Invalid Duration", "Duration must be valid and less than 28 days"),
                ephemeral=True
            )
            return

        try:
            await user.timeout(timedelta(seconds=seconds), reason=reason)
            embed = EmbedFactory.moderation_action("Timeout", user, interaction.user, reason)
            embed.add_field(name="Duration", value=TimeConverter.format_seconds(seconds), inline=False)
            await interaction.response.send_message(embed=embed)

            # DM user
            try:
                dm_embed = EmbedFactory.warning(
                    "You have been timed out",
                    f"**Server:** {interaction.guild.name}\n**Duration:** {TimeConverter.format_seconds(seconds)}\n**Reason:** {reason}"
                )
                await user.send(embed=dm_embed)
            except discord.Forbidden:
                pass

            # Log
            await self._log_action(interaction.guild, embed)
            logger.info(f"{interaction.user} timed out {user} for {duration} in {interaction.guild}")

        except discord.Forbidden:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Error", "I don't have permission to timeout this user"),
                ephemeral=True
            )

    @app_commands.command(name="kick", description="Kick a user")
    @app_commands.describe(
        user="User to kick",
        reason="Reason for kick"
    )
    @is_moderator()
    async def kick(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = "No reason provided"
    ):
        """Kick a user"""
        can_moderate, error = PermissionChecker.can_moderate(interaction.user, user)
        if not can_moderate:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Cannot Kick", error),
                ephemeral=True
            )
            return

        try:
            # DM user before kicking
            try:
                dm_embed = EmbedFactory.warning(
                    "You have been kicked",
                    f"**Server:** {interaction.guild.name}\n**Reason:** {reason}"
                )
                await user.send(embed=dm_embed)
            except discord.Forbidden:
                pass

            await user.kick(reason=reason)
            embed = EmbedFactory.moderation_action("Kick", user, interaction.user, reason)
            await interaction.response.send_message(embed=embed)

            # Log
            await self._log_action(interaction.guild, embed)
            logger.info(f"{interaction.user} kicked {user} from {interaction.guild}")

        except discord.Forbidden:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Error", "I don't have permission to kick this user"),
                ephemeral=True
            )

    @app_commands.command(name="ban", description="Ban a user")
    @app_commands.describe(
        user="User to ban",
        reason="Reason for ban",
        delete_messages="Delete messages from last N days (0-7)"
    )
    @is_moderator()
    async def ban(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = "No reason provided",
        delete_messages: int = 0
    ):
        """Ban a user"""
        can_moderate, error = PermissionChecker.can_moderate(interaction.user, user)
        if not can_moderate:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Cannot Ban", error),
                ephemeral=True
            )
            return

        if delete_messages < 0 or delete_messages > 7:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Invalid Parameter", "delete_messages must be between 0-7"),
                ephemeral=True
            )
            return

        try:
            # DM user before banning
            try:
                dm_embed = EmbedFactory.error(
                    "You have been banned",
                    f"**Server:** {interaction.guild.name}\n**Reason:** {reason}"
                )
                await user.send(embed=dm_embed)
            except discord.Forbidden:
                pass

            await user.ban(reason=reason, delete_message_days=delete_messages)
            embed = EmbedFactory.moderation_action("Ban", user, interaction.user, reason)
            await interaction.response.send_message(embed=embed)

            # Log
            await self._log_action(interaction.guild, embed)
            logger.info(f"{interaction.user} banned {user} from {interaction.guild}")

        except discord.Forbidden:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Error", "I don't have permission to ban this user"),
                ephemeral=True
            )

    @app_commands.command(name="unban", description="Unban a user")
    @app_commands.describe(user_id="ID of user to unban")
    @is_moderator()
    async def unban(
        self,
        interaction: discord.Interaction,
        user_id: str
    ):
        """Unban a user"""
        try:
            user_id_int = int(user_id)
            user = await self.bot.fetch_user(user_id_int)
            await interaction.guild.unban(user)

            embed = EmbedFactory.success(
                "User Unbanned",
                f"{user.mention} ({user.id}) has been unbanned by {interaction.user.mention}"
            )
            await interaction.response.send_message(embed=embed)

            # Log
            await self._log_action(interaction.guild, embed)
            logger.info(f"{interaction.user} unbanned {user} in {interaction.guild}")

        except ValueError:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Invalid ID", "Please provide a valid user ID"),
                ephemeral=True
            )
        except discord.NotFound:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Not Found", "This user is not banned"),
                ephemeral=True
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Error", "I don't have permission to unban users"),
                ephemeral=True
            )

    @app_commands.command(name="clear", description="Clear messages in channel")
    @app_commands.describe(
        amount="Number of messages to delete (1-100)",
        user="Only delete messages from this user (optional)"
    )
    @is_moderator()
    async def clear(
        self,
        interaction: discord.Interaction,
        amount: int,
        user: Optional[discord.Member] = None
    ):
        """Clear messages from channel"""
        if amount < 1 or amount > 100:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Invalid Amount", "Amount must be between 1 and 100"),
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        try:
            def check(m):
                if user:
                    return m.author.id == user.id
                return True

            deleted = await interaction.channel.purge(limit=amount, check=check)
            
            target_text = f" from {user.mention}" if user else ""
            embed = EmbedFactory.success(
                "Messages Cleared",
                f"Deleted **{len(deleted)}** messages{target_text}"
            )
            await interaction.followup.send(embed=embed, ephemeral=True)

            # Log action
            log_embed = EmbedFactory.create(
                title="🗑️ Messages Cleared",
                description=f"**Channel:** {interaction.channel.mention}\n"
                           f"**Moderator:** {interaction.user.mention}\n"
                           f"**Amount:** {len(deleted)} messages{target_text}",
                color=EmbedColor.WARNING
            )
            await self._log_action(interaction.guild, log_embed)
            logger.info(f"{interaction.user} cleared {len(deleted)} messages in {interaction.channel}")

        except discord.Forbidden:
            await interaction.followup.send(
                embed=EmbedFactory.error("Error", "I don't have permission to delete messages"),
                ephemeral=True
            )

    @app_commands.command(name="slowmode", description="Set slowmode for channel")
    @app_commands.describe(seconds="Slowmode delay in seconds (0 to disable)")
    @is_moderator()
    async def slowmode(self, interaction: discord.Interaction, seconds: int):
        """Set slowmode for channel"""
        if seconds < 0 or seconds > 21600:  # Max 6 hours
            await interaction.response.send_message(
                embed=EmbedFactory.error("Invalid Duration", "Slowmode must be between 0 and 21600 seconds (6 hours)"),
                ephemeral=True
            )
            return

        try:
            await interaction.channel.edit(slowmode_delay=seconds)
            
            if seconds == 0:
                embed = EmbedFactory.success("Slowmode Disabled", "Slowmode has been disabled")
            else:
                embed = EmbedFactory.success(
                    "Slowmode Enabled",
                    f"Slowmode set to **{seconds}** seconds"
                )
            
            await interaction.response.send_message(embed=embed)

            # Log action
            log_embed = EmbedFactory.create(
                title="⏱️ Slowmode Updated",
                description=f"**Channel:** {interaction.channel.mention}\n"
                           f"**Moderator:** {interaction.user.mention}\n"
                           f"**Delay:** {seconds} seconds",
                color=EmbedColor.INFO
            )
            await self._log_action(interaction.guild, log_embed)
            logger.info(f"{interaction.user} set slowmode to {seconds}s in {interaction.channel}")

        except discord.Forbidden:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Error", "I don't have permission to edit this channel"),
                ephemeral=True
            )

    @app_commands.command(name="lock", description="Lock a channel")
    @app_commands.describe(channel="Channel to lock (optional, defaults to current)")
    @is_moderator()
    async def lock(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        """Lock a channel"""
        target_channel = channel or interaction.channel

        try:
            await target_channel.set_permissions(
                interaction.guild.default_role,
                send_messages=False
            )
            
            embed = EmbedFactory.success("🔒 Channel Locked", f"{target_channel.mention} has been locked")
            await interaction.response.send_message(embed=embed)

            # Log action
            log_embed = EmbedFactory.create(
                title="🔒 Channel Locked",
                description=f"**Channel:** {target_channel.mention}\n"
                           f"**Moderator:** {interaction.user.mention}",
                color=EmbedColor.WARNING
            )
            await self._log_action(interaction.guild, log_embed)
            logger.info(f"{interaction.user} locked {target_channel}")

        except discord.Forbidden:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Error", "I don't have permission to edit this channel"),
                ephemeral=True
            )

    @app_commands.command(name="unlock", description="Unlock a channel")
    @app_commands.describe(channel="Channel to unlock (optional, defaults to current)")
    @is_moderator()
    async def unlock(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        """Unlock a channel"""
        target_channel = channel or interaction.channel

        try:
            await target_channel.set_permissions(
                interaction.guild.default_role,
                send_messages=None
            )
            
            embed = EmbedFactory.success("🔓 Channel Unlocked", f"{target_channel.mention} has been unlocked")
            await interaction.response.send_message(embed=embed)

            # Log action
            log_embed = EmbedFactory.create(
                title="🔓 Channel Unlocked",
                description=f"**Channel:** {target_channel.mention}\n"
                           f"**Moderator:** {interaction.user.mention}",
                color=EmbedColor.SUCCESS
            )
            await self._log_action(interaction.guild, log_embed)
            logger.info(f"{interaction.user} unlocked {target_channel}")

        except discord.Forbidden:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Error", "I don't have permission to edit this channel"),
                ephemeral=True
            )

    @app_commands.command(name="nickname", description="Change a user's nickname")
    @app_commands.describe(
        user="User to change nickname",
        nickname="New nickname (leave empty to reset)"
    )
    @is_moderator()
    async def nickname(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        nickname: Optional[str] = None
    ):
        """Change user nickname"""
        can_moderate, error = PermissionChecker.can_moderate(interaction.user, user)
        if not can_moderate:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Cannot Change Nickname", error),
                ephemeral=True
            )
            return

        try:
            old_nick = user.display_name
            await user.edit(nick=nickname)
            
            if nickname:
                embed = EmbedFactory.success(
                    "Nickname Changed",
                    f"Changed {user.mention}'s nickname from **{old_nick}** to **{nickname}**"
                )
            else:
                embed = EmbedFactory.success(
                    "Nickname Reset",
                    f"Reset {user.mention}'s nickname"
                )
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"{interaction.user} changed {user}'s nickname to {nickname}")

        except discord.Forbidden:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Error", "I don't have permission to change this user's nickname"),
                ephemeral=True
            )

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """AutoRole assignment on join"""
        guild_data = await self.db.get_guild(member.guild.id)
        if guild_data:
            autorole_id = guild_data.get('autorole')
            if autorole_id:
                role = member.guild.get_role(autorole_id)
                if role:
                    try:
                        await member.add_roles(role, reason="AutoRole Configuration")
                    except discord.Forbidden:
                        pass

    @app_commands.command(name="set_alias", description="Configure custom Arabic prefix commands for actions")
    @app_commands.describe(
        action="The moderation action to rename (e.g. ban_add, voice_mute, chat_mute)",
        alias="The new Arabic text prefix (e.g. طرد)"
    )
    @is_moderator()
    async def set_alias(self, interaction: discord.Interaction, action: str, alias: str):
        """Set a dynamic alias for prefix moderation"""
        valid_actions = ['ban_add', 'ban_remove', 'voice_mute', 'voice_unmute', 'chat_mute', 'chat_unmute', 'media_block', 'live_block']
        if action not in valid_actions:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Invalid Action", f"Action must be one of: {', '.join(valid_actions)}"),
                ephemeral=True
            )
            return
            
        guild_data = await self.db.get_guild(interaction.guild.id)
        aliases = guild_data.get('aliases', {}) if guild_data else {}
        aliases[action] = alias
        
        await self.db.update_guild(interaction.guild.id, {"aliases": aliases})
        
        embed = EmbedFactory.success("Alias Updated", f"Successfully mapped **{action}** to **{alias}**")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="set_autorole", description="Configure the role automatically assigned to new members")
    @app_commands.describe(role="The role to assign")
    @is_moderator()
    async def set_autorole(self, interaction: discord.Interaction, role: discord.Role):
        """Set the autorole for the guild"""
        await self.db.update_guild(interaction.guild.id, {"autorole": role.id})
        embed = EmbedFactory.success("AutoRole Set", f"New members will now automatically receive the {role.mention} role.")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="role", description="Assign or remove a specific role from a user")
    @app_commands.describe(user="The user to modify", role="The role to assign/remove")
    @is_moderator()
    async def role_command(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        """Toggle a role on a user"""
        can_moderate, error = PermissionChecker.can_moderate(interaction.user, user)
        if not can_moderate:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Cannot modify roles", error),
                ephemeral=True
            )
            return
            
        try:
            if role in user.roles:
                await user.remove_roles(role, reason=f"Role removed by {interaction.user}")
                msg = f"Removed {role.mention} from {user.mention}"
            else:
                await user.add_roles(role, reason=f"Role added by {interaction.user}")
                msg = f"Added {role.mention} to {user.mention}"
                
            embed = EmbedFactory.success("Role Update", msg)
            await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Error", "I do not have permission to manage this role."),
                ephemeral=True
            )

    @app_commands.command(name="mute", description="Mute a user via the Muted role natively")
    @app_commands.describe(user="The user to mute")
    @is_moderator()
    async def mute(self, interaction: discord.Interaction, user: discord.Member):
        """Mute a user"""
        can_moderate, error = PermissionChecker.can_moderate(interaction.user, user)
        if not can_moderate:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Cannot Mute", error),
                ephemeral=True
            )
            return

        try:
            mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
            if not mute_role:
                mute_role = await interaction.guild.create_role(name="Muted")
                for ch in interaction.guild.text_channels:
                    await ch.set_permissions(mute_role, send_messages=False)
            
            await user.add_roles(mute_role, reason=f"Muted by {interaction.user}")
            embed = EmbedFactory.success("Muted", f"{user.mention} has been muted.")
            await interaction.response.send_message(embed=embed)
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Error", "I do not have permission to configure mute roles."),
                ephemeral=True
            )

    async def _log_action(self, guild: discord.Guild, embed: discord.Embed):
        """Log moderation action to log channel"""
        guild_config = await self.db.get_guild(guild.id)
        if not guild_config:
            return

        log_channel_id = guild_config.get('log_channel')
        if not log_channel_id:
            return

        log_channel = guild.get_channel(log_channel_id)
        if log_channel:
            try:
                await log_channel.send(embed=embed)
            except discord.Forbidden:
                logger.warning(f"Cannot send to log channel in {guild}")


async def setup(bot: commands.Bot):
    """Setup function for cog loading"""
    await bot.add_cog(Moderation(bot, bot.db, bot.config))
