"""
Embed utilities for Logiq
Creates consistent, themed embeds with i18n support
"""

import discord
from typing import Optional, List, Dict, Any
from datetime import datetime

from utils.i18n import t


class EmbedColor:
    """Color palette for embeds"""
    PRIMARY = 0x5865F2  # Discord Blurple
    SUCCESS = 0x57F287  # Green
    WARNING = 0xFEE75C  # Yellow
    ERROR = 0xED4245    # Red
    INFO = 0x5865F2     # Blue
    PREMIUM = 0xF47FFF  # Pink
    LEVELING = 0xFEE75C  # Gold
    ECONOMY = 0x57F287   # Green
    AI = 0x00D9FF        # Cyan


class EmbedFactory:
    """Factory for creating themed embeds"""

    @staticmethod
    def create(
        title: Optional[str] = None,
        description: Optional[str] = None,
        color: int = EmbedColor.PRIMARY,
        footer: Optional[str] = None,
        thumbnail: Optional[str] = None,
        image: Optional[str] = None,
        fields: Optional[List[Dict[str, Any]]] = None,
        timestamp: bool = True
    ) -> discord.Embed:
        """
        Create a custom embed with automatic i18n translation of strings

        Args:
            title: Embed title
            description: Embed description
            color: Embed color (hex)
            footer: Footer text
            thumbnail: Thumbnail URL
            image: Image URL
            fields: List of field dictionaries
            timestamp: Whether to add timestamp

        Returns:
            Configured Discord embed
        """
        translated_title = t(title) if isinstance(title, str) else title
        translated_desc = t(description) if isinstance(description, str) else description

        embed = discord.Embed(
            title=translated_title,
            description=translated_desc,
            color=color,
            timestamp=datetime.utcnow() if timestamp else None
        )

        if footer:
            embed.set_footer(text=t(footer) if isinstance(footer, str) else footer)

        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        if image:
            embed.set_image(url=image)

        if fields:
            for field in fields:
                name = field.get("name", "")
                val = field.get("value", "")
                embed.add_field(
                    name=t(name) if isinstance(name, str) else name,
                    value=t(val) if isinstance(val, str) else val,
                    inline=field.get("inline", True)
                )

        return embed

    @staticmethod
    def success(title: str, description: str) -> discord.Embed:
        """Create success embed"""
        t_title = t(title)
        t_desc = t(description)
        return EmbedFactory.create(
            title=f"✅ {t_title}",
            description=t_desc,
            color=EmbedColor.SUCCESS
        )

    @staticmethod
    def error(title: str, description: str) -> discord.Embed:
        """Create error embed"""
        t_title = t(title)
        t_desc = t(description)
        return EmbedFactory.create(
            title=f"❌ {t_title}",
            description=t_desc,
            color=EmbedColor.ERROR
        )

    @staticmethod
    def warning(title: str, description: str) -> discord.Embed:
        """Create warning embed"""
        t_title = t(title)
        t_desc = t(description)
        return EmbedFactory.create(
            title=f"⚠️ {t_title}",
            description=t_desc,
            color=EmbedColor.WARNING
        )

    @staticmethod
    def info(title: str, description: str) -> discord.Embed:
        """Create info embed"""
        t_title = t(title)
        t_desc = t(description)
        return EmbedFactory.create(
            title=f"ℹ️ {t_title}",
            description=t_desc,
            color=EmbedColor.INFO
        )


    @staticmethod
    def ai_response(message: str, model: str = "AI") -> discord.Embed:
        """Create AI response embed"""
        return EmbedFactory.create(
            title="🤖 AI Response",
            description=message,
            color=EmbedColor.AI,
            footer=f"Powered by {model}"
        )

    @staticmethod
    def level_up(user: discord.Member, new_level: int, xp: int) -> discord.Embed:
        """Create level up embed"""
        return EmbedFactory.create(
            title=t("leveling.level_up_title"),
            description=t("leveling.level_up_desc", user=user.mention, level=new_level),
            color=EmbedColor.LEVELING,
            thumbnail=user.display_avatar.url,
            fields=[
                {"name": t("leveling.level"), "value": str(new_level), "inline": True},
                {"name": t("leveling.xp"), "value": str(xp), "inline": True}
            ]
        )

    @staticmethod
    def rank_card(user: discord.Member, level: int, xp: int, rank: int, next_level_xp: int) -> discord.Embed:
        """Create rank card embed"""
        progress = (xp % next_level_xp) / next_level_xp * 100
        progress_bar = "█" * int(progress / 10) + "░" * (10 - int(progress / 10))

        return EmbedFactory.create(
            title=t("leveling.rank_title", user=user.display_name),
            color=EmbedColor.LEVELING,
            thumbnail=user.display_avatar.url,
            fields=[
                {"name": t("leveling.rank"), "value": f"#{rank}", "inline": True},
                {"name": t("leveling.level"), "value": str(level), "inline": True},
                {"name": t("leveling.xp"), "value": f"{xp % next_level_xp}/{next_level_xp}", "inline": True},
                {"name": t("leveling.progress"), "value": f"{progress_bar} {progress:.1f}%", "inline": False}
            ]
        )

    @staticmethod
    def economy_balance(user: discord.Member, balance: int, currency_symbol: str = "💎") -> discord.Embed:
        """Create balance embed"""
        return EmbedFactory.create(
            title=t("economy.balance_title", symbol=currency_symbol),
            description=t("economy.balance_desc", user=user.mention),
            color=EmbedColor.ECONOMY,
            thumbnail=user.display_avatar.url,
            fields=[
                {"name": t("economy.amount"), "value": f"{currency_symbol} {balance:,}", "inline": False}
            ]
        )

    @staticmethod
    def moderation_action(
        action: str,
        user: discord.Member,
        moderator: discord.Member,
        reason: str
    ) -> discord.Embed:
        """Create moderation action embed"""
        return EmbedFactory.create(
            title=t("moderation.action_title", action=action),
            description=t("moderation.action_desc", user=user.mention, action=action.lower()),
            color=EmbedColor.WARNING,
            fields=[
                {"name": t("moderation.target_user"), "value": f"{user.mention} ({user.id})", "inline": True},
                {"name": t("moderation.moderator"), "value": moderator.mention, "inline": True},
                {"name": t("moderation.reason"), "value": reason, "inline": False}
            ]
        )

    @staticmethod
    def verification_prompt() -> discord.Embed:
        """Create verification prompt embed"""
        return EmbedFactory.create(
            title=t("verification.prompt_title"),
            description=t("verification.prompt_desc"),
            color=EmbedColor.PRIMARY,
            footer=t("verification.prompt_footer")
        )

    @staticmethod
    def ticket_created(ticket_id: str, category: str) -> discord.Embed:
        """Create ticket created embed"""
        return EmbedFactory.create(
            title=t("tickets.created_title"),
            description=t("tickets.created_desc"),
            color=EmbedColor.SUCCESS,
            fields=[
                {"name": t("tickets.ticket_id"), "value": ticket_id, "inline": True},
                {"name": t("tickets.category"), "value": category, "inline": True}
            ]
        )

    @staticmethod
    def leaderboard(
        title: str,
        entries: List[Dict[str, Any]],
        field_name: str = "Rank",
        color: int = EmbedColor.LEVELING
    ) -> discord.Embed:
        """Create leaderboard embed"""
        description = ""
        for i, entry in enumerate(entries[:10], 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            description += f"{medal} <@{entry['user_id']}> - **{entry.get(field_name, 0):,}**\n"

        return EmbedFactory.create(
            title=f"🏆 {title}",
            description=description or t("common.none"),
            color=color
        )

