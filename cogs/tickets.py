"""
Tickets Cog for Logiq
Support ticket system with ownership claiming, access control, and staff scoring.
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, List
import logging
import asyncio
import time

from utils.embeds import EmbedFactory, EmbedColor
from utils.permissions import is_admin
from utils.i18n import t
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class TicketCreateView(discord.ui.View):
    """Persistent view for creating tickets"""

    def __init__(self, cog: 'Tickets'):
        super().__init__(timeout=None)
        self.cog = cog
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == "create_ticket":
                item.label = t("tickets.create_button", default="Create Ticket")

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.green, custom_id="create_ticket", emoji="🎫")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle ticket creation"""
        await self.cog.create_ticket_for_user(interaction)


class TicketAddUserSelect(discord.ui.UserSelect):
    """User select menu for granting access to ticket"""

    def __init__(self, cog: 'Tickets'):
        super().__init__(
            placeholder=t("tickets.add_user_placeholder", default="Select a user to add to this ticket..."),
            min_values=1,
            max_values=1,
            custom_id="ticket_add_user_select"
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        selected_user = self.values[0]
        if isinstance(selected_user, discord.User):
            selected_user = interaction.guild.get_member(selected_user.id) or selected_user

        if not isinstance(selected_user, discord.Member):
            await interaction.response.send_message(
                embed=EmbedFactory.error("Error", "Selected user is not a member of this server."),
                ephemeral=True
            )
            return

        # Grant read & send permissions
        channel = interaction.channel
        await channel.set_permissions(selected_user, read_messages=True, send_messages=True)

        embed = EmbedFactory.success(
            t("tickets.user_added_title", default="👤 User Added"),
            t("tickets.user_added_desc", default="{user} has been granted access to this ticket by {author}.",
              user=selected_user.mention, author=interaction.user.mention)
        )
        await interaction.response.send_message(embed=embed)


class TicketRemoveUserSelect(discord.ui.UserSelect):
    """User select menu for revoking access from ticket"""

    def __init__(self, cog: 'Tickets'):
        super().__init__(
            placeholder=t("tickets.remove_user_placeholder", default="Select a user to remove from this ticket..."),
            min_values=1,
            max_values=1,
            custom_id="ticket_remove_user_select"
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        selected_user = self.values[0]
        if isinstance(selected_user, discord.User):
            selected_user = interaction.guild.get_member(selected_user.id) or selected_user

        if not isinstance(selected_user, discord.Member):
            await interaction.response.send_message(
                embed=EmbedFactory.error("Error", "Selected user is not a member of this server."),
                ephemeral=True
            )
            return

        channel = interaction.channel
        # Remove custom overwrites for user
        await channel.set_permissions(selected_user, overwrite=None)

        embed = EmbedFactory.warning(
            t("tickets.user_removed_title", default="🚫 User Removed"),
            t("tickets.user_removed_desc", default="{user}'s access to this ticket was revoked by {author}.",
              user=selected_user.mention, author=interaction.user.mention)
        )
        await interaction.response.send_message(embed=embed)


class TicketAddUserView(discord.ui.View):
    """View containing the user select for adding a user"""
    def __init__(self, cog: 'Tickets'):
        super().__init__(timeout=60)
        self.add_item(TicketAddUserSelect(cog))


class TicketRemoveUserView(discord.ui.View):
    """View containing the user select for removing a user"""
    def __init__(self, cog: 'Tickets'):
        super().__init__(timeout=60)
        self.add_item(TicketRemoveUserSelect(cog))


class TicketControlView(discord.ui.View):
    """Persistent view for ticket controls (Claim, Add Access, Remove Access, Close)"""

    def __init__(self, cog: 'Tickets'):
        super().__init__(timeout=None)
        self.cog = cog
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                if item.custom_id == "claim_ticket_btn":
                    item.label = t("tickets.claim_button", default="Take Ownership")
                elif item.custom_id == "add_access_btn":
                    item.label = t("tickets.add_access_button", default="Add User")
                elif item.custom_id == "remove_access_btn":
                    item.label = t("tickets.remove_access_button", default="Remove User")
                elif item.custom_id == "close_ticket_btn":
                    item.label = t("tickets.close_button", default="Close Ticket")

    @discord.ui.button(label="Take Ownership", style=discord.ButtonStyle.primary, custom_id="claim_ticket_btn", emoji="🙋")
    async def claim_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle taking ownership of ticket"""
        await self.cog.claim_ticket_for_user(interaction)

    @discord.ui.button(label="Add User", style=discord.ButtonStyle.secondary, custom_id="add_access_btn", emoji="👤")
    async def add_access_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle adding a user to ticket"""
        if not await self.cog.can_manage_ticket(interaction):
            await interaction.response.send_message(
                embed=EmbedFactory.error("No Permission", "Only ticket owners or staff can modify ticket access."),
                ephemeral=True
            )
            return

        view = TicketAddUserView(self.cog)
        await interaction.response.send_message(
            content=t("tickets.select_user_to_add", default="Select a user to grant access:"),
            view=view,
            ephemeral=True
        )

    @discord.ui.button(label="Remove User", style=discord.ButtonStyle.secondary, custom_id="remove_access_btn", emoji="🚫")
    async def remove_access_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle removing a user from ticket"""
        if not await self.cog.can_manage_ticket(interaction):
            await interaction.response.send_message(
                embed=EmbedFactory.error("No Permission", "Only ticket owners or staff can modify ticket access."),
                ephemeral=True
            )
            return

        view = TicketRemoveUserView(self.cog)
        await interaction.response.send_message(
            content=t("tickets.select_user_to_remove", default="Select a user to revoke access:"),
            view=view,
            ephemeral=True
        )

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger, custom_id="close_ticket_btn", emoji="🔒")
    async def close_ticket_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Handle ticket closing via button"""
        await self.cog.close_ticket_for_user(interaction, "Closed by user")


class Tickets(commands.Cog):
    """Support ticket system cog"""

    def __init__(self, bot: commands.Bot, db: DatabaseManager, config: dict):
        self.bot = bot
        self.db = db
        self.config = config
        self.module_config = config.get('modules', {}).get('tickets', {})
        # Rate limiting dict for ticket message activity score: (guild_id, user_id, channel_id) -> last_time
        self.message_cooldowns = {}

    async def cog_load(self):
        """Register persistent views when cog is loaded so buttons work across bot restarts"""
        self.bot.add_view(TicketCreateView(self))
        self.bot.add_view(TicketControlView(self))
        logger.info("Registered persistent TicketCreateView and TicketControlView")

    async def is_eligible_for_scoring(self, member: discord.Member, guild_config: dict) -> bool:
        """Check if a member has a role eligible for ticket scoring/staff permissions (Owner, Admin, Support Role, Score Roles, View Roles)"""
        if member.id == member.guild.owner_id or member.guild_permissions.administrator:
            return True

        support_role_id = guild_config.get('support_role')
        if support_role_id and any(r.id == support_role_id for r in member.roles):
            return True

        score_roles = guild_config.get('ticket_score_roles', [])
        if any(r.id in score_roles for r in member.roles):
            return True

        view_roles = guild_config.get('ticket_view_roles', [])
        if any(r.id in view_roles for r in member.roles):
            return True

        return False

    async def can_manage_ticket(self, interaction: discord.Interaction) -> bool:
        """Check if user is staff or ticket owner/claimer"""
        guild_config = await self.db.get_guild(interaction.guild.id) or {}
        if await self.is_eligible_for_scoring(interaction.user, guild_config):
            return True

        # Check if user created or claimed the ticket
        ticket = await self.db.get_ticket_by_channel(interaction.channel.id)
        if ticket and (ticket.get('user_id') == interaction.user.id or ticket.get('claimed_by') == interaction.user.id):
            return True

        return False

    async def is_ticket_channel(self, channel: discord.abc.GuildChannel) -> bool:
        """Check if channel is a ticket channel"""
        if not isinstance(channel, discord.TextChannel):
            return False
        if channel.name.startswith("🎫") or channel.name.startswith("ticket-"):
            return True
        ticket = await self.db.get_ticket_by_channel(channel.id)
        return ticket is not None

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Award score points to staff for message activity in ticket channels"""
        if message.author.bot or not message.guild or not isinstance(message.channel, discord.TextChannel):
            return

        if not await self.is_ticket_channel(message.channel):
            return

        guild_config = await self.db.get_guild(message.guild.id)
        if not guild_config:
            return

        # Verify member is eligible staff/score role
        member = message.guild.get_member(message.author.id)
        if not member or not await self.is_eligible_for_scoring(member, guild_config):
            return

        # Check rate limit (1 score point per 30 seconds per user in a ticket channel)
        key = (message.guild.id, message.author.id, message.channel.id)
        now = time.time()
        last_time = self.message_cooldowns.get(key, 0)
        if now - last_time < 30:
            return

        self.message_cooldowns[key] = now
        await self.db.add_ticket_score(message.author.id, message.guild.id, points=1, action="message")

    async def create_ticket_for_user(self, interaction: discord.Interaction):
        """Create a ticket for a user"""
        guild_config = await self.db.get_guild(interaction.guild.id)
        if not guild_config:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Not Configured", "Ticket system not configured"),
                ephemeral=True
            )
            return

        ticket_category_id = guild_config.get('ticket_category')
        if not ticket_category_id:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Not Configured", "Ticket category not set up"),
                ephemeral=True
            )
            return

        category = interaction.guild.get_channel(ticket_category_id)
        if not category or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message(
                embed=EmbedFactory.error("Error", "Ticket category not found"),
                ephemeral=True
            )
            return

        # Check if user already has an open ticket in database or channel
        existing_ticket = await self.db.db.tickets.find_one({
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id,
            "status": {"$ne": "closed"}
        })

        if existing_ticket:
            existing_channel = interaction.guild.get_channel(existing_ticket.get('channel_id'))
            if existing_channel:
                await interaction.response.send_message(
                    embed=EmbedFactory.warning(
                        "Ticket Exists",
                        f"You already have an open ticket: {existing_channel.mention}"
                    ),
                    ephemeral=True
                )
                return

        try:
            # Create ticket channel overwrites
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            # Add support role if configured
            support_role_id = guild_config.get('support_role')
            if support_role_id:
                support_role = interaction.guild.get_role(support_role_id)
                if support_role:
                    overwrites[support_role] = discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True
                    )

            # Add custom view roles
            view_roles = guild_config.get('ticket_view_roles', [])
            for r_id in view_roles:
                v_role = interaction.guild.get_role(r_id)
                if v_role:
                    overwrites[v_role] = discord.PermissionOverwrite(
                        read_messages=True,
                        send_messages=True
                    )

            # Get sequential ticket number (starting from 631)
            ticket_number = await self.db.get_next_ticket_number(interaction.guild.id)
            channel_name = f"🎫・{ticket_number}"

            channel = await category.create_text_channel(
                name=channel_name,
                overwrites=overwrites
            )

            # Create ticket in database
            ticket_data = {
                "guild_id": interaction.guild.id,
                "user_id": interaction.user.id,
                "channel_id": channel.id,
                "category": "General Support",
                "status": "open",
                "claimed_by": None,
                "number": ticket_number
            }
            ticket_id = await self.db.create_ticket(ticket_data)

            # Send welcome message with control buttons
            embed = EmbedFactory.create(
                title=t("tickets.ticket_title", default="🎫 Support Ticket"),
                description=t("tickets.ticket_welcome",
                              default="Hello {user}!\n\nThank you for creating a support ticket. Please describe your issue and a staff member will assist you shortly.\n\n**Ticket ID:** {ticket_id}",
                              user=interaction.user.mention, ticket_id=ticket_number),
                color=EmbedColor.SUCCESS
            )

            # Add ticket control view buttons
            control_view = TicketControlView(self)
            await channel.send(embed=embed, view=control_view)

            # Log ticket creation to ticket log channel
            ticket_log_channel_id = guild_config.get('ticket_log_channel')
            if ticket_log_channel_id:
                log_channel = interaction.guild.get_channel(ticket_log_channel_id)
                if log_channel:
                    log_embed = EmbedFactory.create(
                        title="🎫 New Ticket Created",
                        description=f"**Ticket:** {channel.mention}\n"
                                   f"**Created by:** {interaction.user.mention}\n"
                                   f"**Ticket ID:** {ticket_number}\n"
                                   f"**Status:** Open",
                        color=EmbedColor.SUCCESS
                    )
                    await log_channel.send(embed=log_embed)

            await interaction.response.send_message(
                embed=EmbedFactory.success(
                    "Ticket Created",
                    f"Your ticket has been created: {channel.mention}"
                ),
                ephemeral=True
            )

            logger.info(f"Ticket created for {interaction.user} in {interaction.guild} ({channel_name})")

        except discord.Forbidden:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Error", "I don't have permission to create channels"),
                ephemeral=True
            )

    async def claim_ticket_for_user(self, interaction: discord.Interaction):
        """Allow an eligible staff member to take ownership of a ticket channel"""
        if not await self.is_ticket_channel(interaction.channel):
            await interaction.response.send_message(
                embed=EmbedFactory.error("Not a Ticket", "This button can only be used in ticket channels"),
                ephemeral=True
            )
            return

        guild_config = await self.db.get_guild(interaction.guild.id) or {}
        if not await self.is_eligible_for_scoring(interaction.user, guild_config):
            await interaction.response.send_message(
                embed=EmbedFactory.error("No Permission", "Only staff members with authorized roles can claim tickets."),
                ephemeral=True
            )
            return

        ticket = await self.db.get_ticket_by_channel(interaction.channel.id)
        if ticket and ticket.get('claimed_by'):
            claimed_by_id = ticket.get('claimed_by')
            if claimed_by_id == interaction.user.id:
                await interaction.response.send_message(
                    embed=EmbedFactory.warning("Already Owner", "You already own this ticket!"),
                    ephemeral=True
                )
                return
            else:
                claimed_member = interaction.guild.get_member(claimed_by_id)
                owner_name = claimed_member.mention if claimed_member else f"<@{claimed_by_id}>"
                await interaction.response.send_message(
                    embed=EmbedFactory.warning(
                        "Ticket Claimed",
                        f"This ticket is already claimed by {owner_name}."
                    ),
                    ephemeral=True
                )
                return

        # Update database record
        await self.db.claim_ticket(interaction.channel.id, interaction.user.id)

        # Update channel permissions: give claimer explicit write & manage permissions
        await interaction.channel.set_permissions(
            interaction.user,
            read_messages=True,
            send_messages=True,
            manage_messages=True
        )

        # Revoke access for support role and view roles so only claimer, creator, and explicitly added users can see it
        support_role_id = guild_config.get('support_role')
        if support_role_id:
            support_role = interaction.guild.get_role(support_role_id)
            if support_role:
                await interaction.channel.set_permissions(support_role, overwrite=None)

        view_roles = guild_config.get('ticket_view_roles', [])
        for r_id in view_roles:
            v_role = interaction.guild.get_role(r_id)
            if v_role:
                await interaction.channel.set_permissions(v_role, overwrite=None)

        # Update channel topic
        try:
            await interaction.channel.edit(topic=f"📌 Ticket Owner: {interaction.user.display_name} ({interaction.user.id})")
        except Exception as e:
            logger.warning(f"Could not update channel topic: {e}")

        # Award score points (+10 points for claiming a ticket)
        await self.db.add_ticket_score(interaction.user.id, interaction.guild.id, points=10, action="claim")

        embed = EmbedFactory.success(
            t("tickets.claimed_title", default="🙋 Ownership Claimed"),
            t("tickets.claimed_desc", default="{user} has taken ownership of this ticket!\n⭐ **+10 Score Points** awarded.",
              user=interaction.user.mention)
        )
        await interaction.response.send_message(embed=embed)
        logger.info(f"Ticket {interaction.channel.name} claimed by {interaction.user}")

    async def close_ticket_for_user(self, interaction: discord.Interaction, reason: str = "Resolved"):
        """Close a ticket (called from button or command)"""
        if not await self.is_ticket_channel(interaction.channel):
            await interaction.response.send_message(
                embed=EmbedFactory.error("Not a Ticket", "This can only be used in ticket channels"),
                ephemeral=True
            )
            return

        guild_config = await self.db.get_guild(interaction.guild.id) or {}
        if not await self.can_manage_ticket(interaction):
            await interaction.response.send_message(
                embed=EmbedFactory.error("No Permission", "Only the ticket owner or staff can close this ticket"),
                ephemeral=True
            )
            return

        ticket_channel_id = interaction.channel.id

        # If closer is staff, award score points (+5 for closing/resolving ticket)
        if await self.is_eligible_for_scoring(interaction.user, guild_config):
            await self.db.add_ticket_score(interaction.user.id, interaction.guild.id, points=5, action="close")

        # Log ticket closure to ticket log channel
        ticket_log_channel_id = guild_config.get('ticket_log_channel')
        if ticket_log_channel_id:
            log_channel = interaction.guild.get_channel(ticket_log_channel_id)
            if log_channel:
                log_embed = EmbedFactory.create(
                    title="🔒 Ticket Closed",
                    description=f"**Ticket:** {interaction.channel.name}\n"
                               f"**Closed by:** {interaction.user.mention}\n"
                               f"**Reason:** {reason}\n"
                               f"**Status:** Closed",
                    color=EmbedColor.WARNING
                )
                await log_channel.send(embed=log_embed)

        embed = EmbedFactory.warning(
            "🔒 Ticket Closing",
            f"This ticket is being closed by {interaction.user.mention}.\n\n**Reason:** {reason}\n\n"
            f"Channel will be deleted in 5 seconds..."
        )
        await interaction.response.send_message(embed=embed)

        logger.info(f"Ticket {interaction.channel.name} closed by {interaction.user}")

        try:
            await self.db.db.tickets.update_one(
                {"channel_id": ticket_channel_id},
                {"$set": {"status": "closed", "closed_by": interaction.user.id, "close_reason": reason}}
            )
        except Exception as e:
            logger.error(f"Error updating ticket in database: {e}")

        await asyncio.sleep(5)

        try:
            await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")
            logger.info(f"Deleted ticket channel: {interaction.channel.name}")
        except discord.Forbidden:
            logger.error(f"No permission to delete ticket channel: {interaction.channel.name}")
        except Exception as e:
            logger.error(f"Error deleting ticket channel: {e}")

    @app_commands.command(name="ticket-setup", description="Setup ticket system (Admin)")
    @app_commands.describe(
        category="Category for ticket channels",
        log_channel="Channel for ticket logs",
        support_role="Role to ping for new tickets (optional)"
    )
    @is_admin()
    async def ticket_setup(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel,
        log_channel: discord.TextChannel,
        support_role: Optional[discord.Role] = None
    ):
        """Setup ticket system (ADMIN ONLY)"""
        guild_config = await self.db.get_guild(interaction.guild.id)
        if not guild_config:
            guild_config = await self.db.create_guild(interaction.guild.id)

        update_data = {
            'ticket_category': category.id,
            'ticket_log_channel': log_channel.id
        }
        if support_role:
            update_data['support_role'] = support_role.id

        await self.db.update_guild(interaction.guild.id, update_data)

        embed = EmbedFactory.success(
            "✅ Ticket System Setup",
            f"**Category:** {category.mention}\n"
            f"**Log Channel:** {log_channel.mention}\n" +
            (f"**Support Role:** {support_role.mention}" if support_role else "")
        )
        await interaction.response.send_message(embed=embed)
        logger.info(f"Ticket system setup in {interaction.guild}")

    @app_commands.command(name="ticket-panel", description="Send ticket creation panel with optional custom embed (Admin)")
    @app_commands.describe(
        title="Custom title for the ticket panel embed (optional)",
        description="Custom description for the panel embed (use \\n for line breaks) (optional)",
        image_url="Custom banner image URL for the panel embed (optional)",
        thumbnail_url="Custom thumbnail image URL for the panel embed (optional)"
    )
    @is_admin()
    async def ticket_panel(
        self,
        interaction: discord.Interaction,
        title: Optional[str] = None,
        description: Optional[str] = None,
        image_url: Optional[str] = None,
        thumbnail_url: Optional[str] = None
    ):
        """Send persistent ticket panel (ADMIN ONLY)"""
        panel_title = title if title else t("tickets.panel_title", default="🎫 Support Tickets")
        panel_desc = (description.replace("\\n", "\n") if description else
                      t("tickets.panel_desc", default="Need help? Click the button below to create a support ticket!\n\nA private channel will be created where you can discuss your issue with staff."))

        embed = EmbedFactory.create(
            title=panel_title,
            description=panel_desc,
            color=EmbedColor.PRIMARY
        )

        if image_url:
            embed.set_image(url=image_url)
        if thumbnail_url:
            embed.set_thumbnail(url=thumbnail_url)

        view = TicketCreateView(self)
        await interaction.channel.send(embed=embed, view=view)

        await interaction.response.send_message(
            embed=EmbedFactory.success("Panel Sent", "Ticket panel created with persistent button!"),
            ephemeral=True
        )

    @app_commands.command(name="close-ticket", description="Close a ticket (Admin/Staff)")
    @app_commands.describe(reason="Reason for closing")
    async def close_ticket(self, interaction: discord.Interaction, reason: Optional[str] = "Resolved"):
        """Close a ticket (ADMIN/STAFF ONLY)"""
        await self.close_ticket_for_user(interaction, reason)

    @app_commands.command(name="ticket-leaderboard", description="View staff ticket score leaderboard")
    async def ticket_leaderboard(self, interaction: discord.Interaction):
        """View staff ticket score leaderboard"""
        leaderboard_data = await self.db.get_ticket_leaderboard(interaction.guild.id, limit=10)
        if not leaderboard_data:
            await interaction.response.send_message(
                embed=EmbedFactory.info("Leaderboard Empty", "No ticket score stats recorded yet."),
                ephemeral=True
            )
            return

        lines = []
        for idx, user_data in enumerate(leaderboard_data, 1):
            user_id = user_data.get("user_id")
            score = user_data.get("ticket_score", 0)
            claimed = user_data.get("tickets_claimed", 0)
            messages = user_data.get("ticket_messages", 0)
            member = interaction.guild.get_member(user_id)
            user_str = member.mention if member else f"<@{user_id}>"

            medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else f"#{idx}"
            lines.append(f"{medal} {user_str} — **{score} pts** ({claimed} claimed, {messages} msgs)")

        embed = EmbedFactory.create(
            title=t("tickets.leaderboard_title", default="🏆 Staff Ticket Leaderboard"),
            description="\n".join(lines),
            color=EmbedColor.PRIMARY
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ticket-score", description="View staff ticket score and statistics")
    @app_commands.describe(user="Staff user to check stats for (optional)")
    async def ticket_score(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        """View staff member's ticket score & stats"""
        target_user = user or interaction.user
        stats = await self.db.get_ticket_score(target_user.id, interaction.guild.id)

        embed = EmbedFactory.create(
            title=f"📊 Ticket Stats — {target_user.display_name}",
            description=f"**Total Score Points:** `{stats.get('ticket_score', 0)}`\n"
                        f"**Tickets Claimed:** `{stats.get('tickets_claimed', 0)}`\n"
                        f"**Tickets Closed:** `{stats.get('tickets_closed', 0)}`\n"
                        f"**Ticket Messages:** `{stats.get('ticket_messages', 0)}`",
            color=EmbedColor.INFO
        )
        embed.set_thumbnail(url=target_user.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ticket-scoreroles", description="Manage roles eligible for ticket scoring (Admin)")
    @app_commands.describe(
        action="Add or remove score role",
        role="Role to manage"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Add Role", value="add"),
        app_commands.Choice(name="Remove Role", value="remove"),
        app_commands.Choice(name="List Roles", value="list")
    ])
    @is_admin()
    async def ticket_scoreroles(
        self,
        interaction: discord.Interaction,
        action: str,
        role: Optional[discord.Role] = None
    ):
        """Configure roles eligible for ticket scoring (ADMIN ONLY)"""
        guild_config = await self.db.get_guild(interaction.guild.id)
        if not guild_config:
            guild_config = await self.db.create_guild(interaction.guild.id)

        score_roles = guild_config.get('ticket_score_roles', [])

        if action == "list":
            if not score_roles:
                await interaction.response.send_message(
                    embed=EmbedFactory.info("Score Roles", "No specific ticket score roles configured. Defaulting to admins and support role."),
                    ephemeral=True
                )
                return
            role_mentions = [interaction.guild.get_role(r_id).mention for r_id in score_roles if interaction.guild.get_role(r_id)]
            embed = EmbedFactory.create(
                title="⚙️ Ticket Score Roles",
                description="\n".join(role_mentions) if role_mentions else "None active",
                color=EmbedColor.INFO
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if not role:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Missing Role", "Please select a role to add or remove."),
                ephemeral=True
            )
            return

        if action == "add":
            if role.id in score_roles:
                await interaction.response.send_message(
                    embed=EmbedFactory.warning("Already Added", f"{role.mention} is already in the score roles list."),
                    ephemeral=True
                )
                return
            score_roles.append(role.id)
            await self.db.update_guild(interaction.guild.id, {"ticket_score_roles": score_roles})
            await interaction.response.send_message(
                embed=EmbedFactory.success("Role Added", f"Added {role.mention} to ticket score roles."),
                ephemeral=True
            )

        elif action == "remove":
            if role.id not in score_roles:
                await interaction.response.send_message(
                    embed=EmbedFactory.warning("Not Found", f"{role.mention} is not in the score roles list."),
                    ephemeral=True
                )
                return
            score_roles.remove(role.id)
            await self.db.update_guild(interaction.guild.id, {"ticket_score_roles": score_roles})
            await interaction.response.send_message(
                embed=EmbedFactory.success("Role Removed", f"Removed {role.mention} from ticket score roles."),
                ephemeral=True
            )

    @app_commands.command(name="ticket-viewroles", description="Manage roles who can view unclaimed tickets (Admin)")
    @app_commands.describe(
        action="Add or remove view role",
        role="Role to manage"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Add Role", value="add"),
        app_commands.Choice(name="Remove Role", value="remove"),
        app_commands.Choice(name="List Roles", value="list")
    ])
    @is_admin()
    async def ticket_viewroles(
        self,
        interaction: discord.Interaction,
        action: str,
        role: Optional[discord.Role] = None
    ):
        """Configure roles eligible to see unclaimed tickets (ADMIN ONLY)"""
        guild_config = await self.db.get_guild(interaction.guild.id)
        if not guild_config:
            guild_config = await self.db.create_guild(interaction.guild.id)

        view_roles = guild_config.get('ticket_view_roles', [])

        if action == "list":
            if not view_roles:
                await interaction.response.send_message(
                    embed=EmbedFactory.info("View Roles", "No specific ticket view roles configured. Defaulting to admins and support role."),
                    ephemeral=True
                )
                return
            role_mentions = [interaction.guild.get_role(r_id).mention for r_id in view_roles if interaction.guild.get_role(r_id)]
            embed = EmbedFactory.create(
                title="👁️ Ticket View Roles",
                description="\n".join(role_mentions) if role_mentions else "None active",
                color=EmbedColor.INFO
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if not role:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Missing Role", "Please select a role to add or remove."),
                ephemeral=True
            )
            return

        if action == "add":
            if role.id in view_roles:
                await interaction.response.send_message(
                    embed=EmbedFactory.warning("Already Added", f"{role.mention} is already in the view roles list."),
                    ephemeral=True
                )
                return
            view_roles.append(role.id)
            await self.db.update_guild(interaction.guild.id, {"ticket_view_roles": view_roles})
            await interaction.response.send_message(
                embed=EmbedFactory.success("Role Added", f"Added {role.mention} to ticket view roles."),
                ephemeral=True
            )

        elif action == "remove":
            if role.id not in view_roles:
                await interaction.response.send_message(
                    embed=EmbedFactory.warning("Not Found", f"{role.mention} is not in the view roles list."),
                    ephemeral=True
                )
                return
            view_roles.remove(role.id)
            await self.db.update_guild(interaction.guild.id, {"ticket_view_roles": view_roles})
            await interaction.response.send_message(
                embed=EmbedFactory.success("Role Removed", f"Removed {role.mention} from ticket view roles."),
                ephemeral=True
            )

    @app_commands.command(name="tickets", description="View all active tickets (Admin)")
    @is_admin()
    async def view_tickets(self, interaction: discord.Interaction):
        """View all active tickets (ADMIN ONLY)"""
        guild_config = await self.db.get_guild(interaction.guild.id)
        if not guild_config:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Not Configured", "Ticket system not configured"),
                ephemeral=True
            )
            return

        ticket_category_id = guild_config.get('ticket_category')
        if not ticket_category_id:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Not Configured", "Ticket category not set up"),
                ephemeral=True
            )
            return

        category = interaction.guild.get_channel(ticket_category_id)
        if not category or not isinstance(category, discord.CategoryChannel):
            await interaction.response.send_message(
                embed=EmbedFactory.error("Error", "Ticket category not found"),
                ephemeral=True
            )
            return

        ticket_channels = [ch for ch in category.channels if ch.name.startswith("ticket-")]

        if not ticket_channels:
            await interaction.response.send_message(
                embed=EmbedFactory.info("No Active Tickets", "There are currently no active tickets"),
                ephemeral=True
            )
            return

        description = ""
        for channel in ticket_channels[:25]:
            ticket_owner = channel.name.replace("ticket-", "")
            description += f"🎫 {channel.mention} - **{ticket_owner}**\n"

        embed = EmbedFactory.create(
            title=f"🎫 Active Tickets ({len(ticket_channels)})",
            description=description,
            color=EmbedColor.INFO
        )

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Setup function for cog loading"""
    await bot.add_cog(Tickets(bot, bot.db, bot.config))

