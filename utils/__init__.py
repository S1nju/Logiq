"""Utilities package for Logiq"""

from .logger import setup_logger, BotLogger
from .i18n import I18nManager, i18n, t
from .converters import TimeConverter, MessageConverter, NumberConverter
from .constants import *

try:
    from .embeds import EmbedFactory, EmbedColor
    from .permissions import (
        is_admin, is_moderator, has_role,
        bot_has_permissions, is_guild_owner,
        PermissionChecker
    )
except ImportError:
    pass

__all__ = [
    'setup_logger',
    'BotLogger',
    'I18nManager',
    'i18n',
    't',
    'EmbedFactory',
    'EmbedColor',
    'is_admin',
    'is_moderator',
    'has_role',
    'bot_has_permissions',
    'is_guild_owner',
    'PermissionChecker',
    'TimeConverter',
    'MessageConverter',
    'NumberConverter'
]

