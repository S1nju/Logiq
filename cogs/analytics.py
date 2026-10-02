"""
Analytics Cog for Logiq
Server analytics and statistics tracking
"""

import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from typing import Optional
import logging
from utils.i18n import t

from utils.embeds import EmbedFactory, EmbedColor
from utils.permissions import is_admin
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class Analytics(commands.Cog):
    """Analytics and statistics cog"""

    def __init__(self, bot: commands.Bot, db: DatabaseManager, config: dict):
        self.bot = bot
        self.db = db
        self.config = config
        self.module_config = config.get('modules', {}).get('analytics', {})

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """Track message events"""
        if not self.module_config.get('enabled', True):
            return

        if message.author.bot or not message.guild:
            return

        await self.db.log_event('message', {
            'guild_id': message.guild.id,
            'user_id': message.author.id,
            'channel_id': message.channel.id
        })

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Track member joins"""
        if not self.module_config.get('enabled', True):
            return

        await self.db.log_event('member_join', {
            'guild_id': member.guild.id,
            'user_id': member.id
        })

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """Track member leaves"""
        if not self.module_config.get('enabled', True):
            return

        await self.db.log_event('member_leave', {
            'guild_id': member.guild.id,
            'user_id': member.id
        })

    @app_commands.command(name="analytics", description="View server analytics")
    @app_commands.describe(days="Number of days to analyze (default: 7)")
    @is_admin()
    async def analytics(self, interaction: discord.Interaction, days: int = 7):
        """View server analytics"""
        if days < 1 or days > 365:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Invalid Range", "Days must be between 1 and 365"),
                ephemeral=True
            )
            return

        await interaction.response.defer()

        # Calculate time range
        end_time = datetime.utcnow().timestamp()
        start_time = (datetime.utcnow() - timedelta(days=days)).timestamp()

        # Get analytics data
        messages = await self.db.get_analytics(
            interaction.guild.id,
            event_type='message',
            start_time=start_time,
            end_time=end_time
        )

        joins = await self.db.get_analytics(
            interaction.guild.id,
            event_type='member_join',
            start_time=start_time,
            end_time=end_time
        )

        leaves = await self.db.get_analytics(
            interaction.guild.id,
            event_type='member_leave',
            start_time=start_time,
            end_time=end_time
        )

        # Calculate stats
        total_messages = len(messages)
        total_joins = len(joins)
        total_leaves = len(leaves)
        net_growth = total_joins - total_leaves

        # Most active users
        user_message_counts = {}
        for msg in messages:
            user_id = msg.get('user_id')
            user_message_counts[user_id] = user_message_counts.get(user_id, 0) + 1

        top_users = sorted(user_message_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        top_users_text = "\n".join([
            f"{i + 1}. <@{user_id}>: {count} messages"
            for i, (user_id, count) in enumerate(top_users)
        ]) if top_users else "No data"

        embed = EmbedFactory.create(
            title=f"📊 Server Analytics - Last {days} Days",
            color=EmbedColor.INFO,
            fields=[
                {"name": "💬 Total Messages", "value": str(total_messages), "inline": True},
                {"name": "👋 Members Joined", "value": str(total_joins), "inline": True},
                {"name": "🚪 Members Left", "value": str(total_leaves), "inline": True},
                {"name": "📈 Net Growth", "value": str(net_growth), "inline": True},
                {"name": "📅 Period", "value": f"{days} days", "inline": True},
                {"name": "⏰ Generated", "value": datetime.utcnow().strftime("%Y-%m-%d %H:%M"), "inline": True},
                {"name": "🏆 Most Active Users", "value": top_users_text, "inline": False}
            ]
        )

        await interaction.followup.send(embed=embed)
        logger.info(f"Analytics generated for {interaction.guild}")

    @app_commands.command(name="activity", description="View recent server activity")
    @is_admin()
    async def activity(self, interaction: discord.Interaction):
        """View recent activity"""
        # Get last 24 hours of activity
        end_time = datetime.utcnow().timestamp()
        start_time = (datetime.utcnow() - timedelta(hours=24)).timestamp()

        events = await self.db.get_analytics(
            interaction.guild.id,
            start_time=start_time,
            end_time=end_time
        )

        if not events:
            await interaction.response.send_message(
                embed=EmbedFactory.info("No Activity", "No recent activity data available"),
                ephemeral=True
            )
            return

        # Group by hour
        hourly_activity = {}
        for event in events:
            hour = datetime.fromtimestamp(event['timestamp']).strftime("%Y-%m-%d %H:00")
            hourly_activity[hour] = hourly_activity.get(hour, 0) + 1

        # Create activity chart (text-based)
        chart_text = ""
        for hour, count in sorted(hourly_activity.items())[-12:]:  # Last 12 hours
            bar = "█" * min(count // 10, 20)
            chart_text += f"{hour}: {bar} ({count})\n"

        embed = EmbedFactory.create(
            title="📈 Server Activity (Last 24 Hours)",
            description=f"```\n{chart_text}\n```",
            color=EmbedColor.INFO
        )
        embed.set_footer(text=f"Total events: {len(events)}")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="active_user_information", description="عرض معلومات ونشاط العضو (نقاط التذاكر، وقت الفويس، والرسائل)")
    @app_commands.describe(
        member="العضو المراد استعراض بياناته (اختياري)",
        period="الفترة الزمنية (days = 24h, week = 7d, month = 30d, all = الكل)"
    )
    @app_commands.choices(period=[
        app_commands.Choice(name="اليوم (24 ساعة)", value="days"),
        app_commands.Choice(name="الأسبوع (7 أيام)", value="week"),
        app_commands.Choice(name="الشهر (30 يوم)", value="month"),
        app_commands.Choice(name="كل الأوقات (All Time)", value="all")
    ])
    async def active_user_information_slash(
        self,
        interaction: discord.Interaction,
        member: Optional[discord.Member] = None,
        period: str = "week"
    ):
        """Slash command for active user information"""
        target_member = member or interaction.user
        await interaction.response.defer()
        embed = await self._generate_active_user_embed(interaction.guild, target_member, period)
        await interaction.followup.send(embed=embed)

    @commands.command(name="active_user_information", aliases=["نشاط_العضو", "معلومات_النشاط", "activeuserinfo"])
    async def active_user_information_prefix(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None,
        period: str = "week"
    ):
        """Prefix command for active user information"""
        target_member = member or ctx.author
        if period not in ["days", "week", "month", "all"]:
            period = "week"
        embed = await self._generate_active_user_embed(ctx.guild, target_member, period)
        await ctx.send(embed=embed)

    async def _generate_active_user_embed(self, guild: discord.Guild, member: discord.Member, period: str) -> discord.Embed:
        """Helper to generate active user information embed"""
        import time
        now = time.time()
        
        if period == "days":
            start_time = now - (24 * 3600)
            period_name = "⏱️ اليوم (24 ساعة)"
        elif period == "week":
            start_time = now - (7 * 24 * 3600)
            period_name = "📅 الأسبوع (7 أيام)"
        elif period == "month":
            start_time = now - (30 * 24 * 3600)
            period_name = "🗓️ الشهر (30 يوم)"
        else:
            start_time = 0
            period_name = "♾️ كل الأوقات (All Time)"

        events = await self.db.get_user_analytics(guild.id, member.id, start_time=start_time)

        msg_count = 0
        vc_seconds = 0
        ticket_points = 0
        ticket_claims = 0
        ticket_closes = 0
        ticket_msgs = 0

        for ev in events:
            ev_type = ev.get('type')
            if ev_type == 'message':
                msg_count += 1
            elif ev_type == 'voice_time':
                vc_seconds += ev.get('duration_seconds', 60)
            elif ev_type == 'ticket_point':
                action = ev.get('action')
                pts = ev.get('points', 0)
                ticket_points += pts
                if action == 'claim':
                    ticket_claims += 1
                elif action == 'close':
                    ticket_closes += 1
                elif action == 'message':
                    ticket_msgs += 1

        # Fallback for all time or overall user record if analytics events are recent
        if period == "all":
            user_ticket_stats = await self.db.get_ticket_score(member.id, guild.id)
            if user_ticket_stats.get('ticket_score', 0) > ticket_points:
                ticket_points = user_ticket_stats.get('ticket_score', 0)
                ticket_claims = max(ticket_claims, user_ticket_stats.get('tickets_claimed', 0))
                ticket_closes = max(ticket_closes, user_ticket_stats.get('tickets_closed', 0))
                ticket_msgs = max(ticket_msgs, user_ticket_stats.get('ticket_messages', 0))

        hours = int(vc_seconds // 3600)
        minutes = int((vc_seconds % 3600) // 60)
        secs = int(vc_seconds % 60)
        
        if hours > 0:
            vc_str = f"**{hours}** ساعة و **{minutes}** دقيقة"
        elif minutes > 0:
            vc_str = f"**{minutes}** دقيقة و **{secs}** ثانية"
        else:
            vc_str = f"**{secs}** ثانية"

        embed = EmbedFactory.create(
            title=f"👤 معلومات ونشاط العضو | {member.display_name}",
            color=EmbedColor.PRIMARY,
            fields=[
                {"name": "⏳ الفترة المحدد", "value": period_name, "inline": False},
                {"name": "🎫 نقاط التذاكر", "value": f"**{ticket_points}** نقطة", "inline": True},
                {"name": "📥 التذاكر المستلمة (Claim)", "value": f"**{ticket_claims}** تذكرة", "inline": True},
                {"name": "🔒 التذاكر المغلقة (Close)", "value": f"**{ticket_closes}** تذكرة", "inline": True},
                {"name": "🔊 الوقت في الرومات الصوتية (VC)", "value": vc_str, "inline": False},
                {"name": "💬 إجمالي الرسائل المرسلة", "value": f"**{msg_count}** رسالة", "inline": True},
                {"name": "✉️ رسائل التذاكر", "value": f"**{ticket_msgs}** رسالة", "inline": True},
            ]
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Requested by {interaction.user.display_name if hasattr(interaction, 'user') else 'User'}", icon_url=member.display_avatar.url)
        return embed


async def setup(bot: commands.Bot):
    """Setup function for cog loading"""
    await bot.add_cog(Analytics(bot, bot.db, bot.config))
