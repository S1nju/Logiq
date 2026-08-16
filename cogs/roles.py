"""
Roles Cog for Logiq
Self-assignable roles with modal-based setup
"""

import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, List
import logging
from utils.i18n import t

from utils.embeds import EmbedFactory, EmbedColor
from utils.permissions import is_admin
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)


class RoleMenuSetupModal(discord.ui.Modal, title="Create Role Menu"):
    """Modal for creating role menus with custom settings"""

    title_input = discord.ui.TextInput(
        label="Menu Title",
        placeholder="e.g., Choose Your Roles",
        required=True,
        max_length=100
    )

    description_input = discord.ui.TextInput(
        label="Menu Description",
        placeholder="e.g., Select your preferred roles from the dropdown below",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500
    )

    exclusive = discord.ui.TextInput(
        label="Exclusive? (yes/no)",
        placeholder="Type 'yes' if users can only pick ONE role",
        required=True,
        max_length=3
    )

    def __init__(self, cog, channel):
        super().__init__(title=t("roles.modal_title", default="Create Role Menu"))
        self.cog = cog
        self.channel = channel
        self.title_input.label = t("roles.title_input", default="Menu Title")
        self.title_input.placeholder = t("roles.title_placeholder", default="e.g., Choose Your Roles")
        self.description_input.label = t("roles.desc_input", default="Menu Description")
        self.description_input.placeholder = t("roles.desc_placeholder", default="e.g., Select your preferred roles from the dropdown below")
        self.exclusive.label = t("roles.exclusive_input", default="Exclusive? (yes/no)")
        self.exclusive.placeholder = t("roles.exclusive_placeholder", default="Type 'yes' if users can only pick ONE role")

    async def on_submit(self, interaction: discord.Interaction):
        """Handle modal submission"""
        is_exclusive = self.exclusive.value.lower() in ['yes', 'y', 'true']
        
        view = RoleBuilderView(
            cog=self.cog,
            guild_id=interaction.guild_id,
            title=self.title_input.value,
            description=self.description_input.value,
            is_exclusive=is_exclusive,
            target_channel=self.channel,
            current_roles=[]
        )
        
        embed = discord.Embed(
            title="🛠️ Building Role Menu...",
            description="**Currently Added (0/125):**\nNone\n\nUse the dropdown below to select up to 25 roles at a time, then click **Add Selected Roles**.",
            color=EmbedColor.PRIMARY
        )
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        logger.info(f"Role menu setup started by {interaction.user}")


class RoleBuilderView(discord.ui.View):
    """View for iterative role selection up to 125 roles"""

    def __init__(self, cog, guild_id: int, title: str, description: str, is_exclusive: bool, target_channel: discord.TextChannel, current_roles: list):
        super().__init__(timeout=900)
        self.cog = cog
        self.guild_id = guild_id
        self.menu_title = title
        self.menu_desc = description
        self.is_exclusive = is_exclusive
        self.target_channel = target_channel
        self.current_roles = current_roles

    def _get_role_emoji(self, role: discord.Role):
        if role.unicode_emoji:
            return str(role.unicode_emoji)
        return "🎭"

    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Select up to 25 roles to add...", min_values=1, max_values=25, custom_id="setup_role_select")
    async def role_select(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        # We defer to allow picking roles. The 'Add Selected' button handles the logic.
        await interaction.response.defer()

    @discord.ui.button(label="Add Selected Roles", style=discord.ButtonStyle.success, row=1, custom_id="setup_add_btn")
    async def add_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        roles_to_add = self.role_select.values
        if not roles_to_add:
            await interaction.response.send_message(
                embed=EmbedFactory.error("No Roles Selected", "Please choose roles from the dropdown first!"), 
                ephemeral=True
            )
            return

        added = 0
        for role in roles_to_add:
            if role.is_default() or role.is_integration():
                continue
            if not any(r['role'].id == role.id for r in self.current_roles):
                self.current_roles.append({
                    'role': role,
                    'emoji': self._get_role_emoji(role),
                    'label': role.name
                })
                added += 1

        if len(self.current_roles) > 125:
            self.current_roles = self.current_roles[:125]
            await interaction.response.send_message(
                embed=EmbedFactory.warning("Limit Reached", "Maximum of 125 roles reached. You cannot add any more."),
                ephemeral=True
            )

        # Refresh the UI
        new_view = RoleBuilderView(
            self.cog, self.guild_id, self.menu_title, self.menu_desc, 
            self.is_exclusive, self.target_channel, self.current_roles
        )
        
        display_roles = ", ".join(r['role'].mention for r in self.current_roles)
        if len(display_roles) > 3000:
            display_roles = display_roles[:3000] + "... (truncated)"
            
        embed = discord.Embed(
            title="🛠️ Building Role Menu...",
            description=f"**Currently Added ({len(self.current_roles)}/125):**\n{display_roles or 'None'}\n\nUse the dropdown below to select up to 25 roles at a time, then click **Add Selected Roles**.",
            color=EmbedColor.PRIMARY
        )
        
        await interaction.response.edit_message(embed=embed, view=new_view)

    @discord.ui.button(label="Finish & Send Menu", style=discord.ButtonStyle.primary, row=1, custom_id="setup_finish_btn")
    async def finish_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.current_roles:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Error", "You must add at least 1 valid role before finishing!"), 
                ephemeral=True
            )
            return
            
        await interaction.response.defer()
            
        try:
            # Finalize and send to DB
            db_role_list = []
            for r in self.current_roles:
                db_role_list.append({
                    'id': str(r['role'].id),
                    'emoji': r['emoji'],
                    'label': r['label']
                })
                
            await self.cog.db.update_guild(self.guild_id, {
                "role_menu_data": {
                    "roles": db_role_list,
                    "is_exclusive": self.is_exclusive,
                    "title": self.menu_title,
                    "description": self.menu_desc
                }
            })

            embed = EmbedFactory.create(
                title=self.menu_title,
                description=self.menu_desc,
                color=EmbedColor.PRIMARY
            )
            
            roles_texts = []
            current_text = ""
            for r in self.current_roles:
                line = f"{r['emoji']} {r['role'].mention}\n"
                if len(current_text) + len(line) > 1024:
                    roles_texts.append(current_text)
                    current_text = line
                else:
                    current_text += line
            if current_text:
                roles_texts.append(current_text)
                
            for i, text in enumerate(roles_texts):
                embed.add_field(name="Available Roles" if i == 0 else "\u200b", value=text, inline=False)
                
            if self.is_exclusive:
                view = ExclusiveRoleView(self.current_roles, self.menu_title, timeout=None)
            else:
                view = MultiRoleView(self.current_roles, timeout=None)
                
            await self.target_channel.send(embed=embed, view=view)

            await interaction.edit_original_response(
                embed=EmbedFactory.success(
                    "Role Menu Configured!",
                    f"{'Exclusive' if self.is_exclusive else 'Multi-select'} role menu sent to {self.target_channel.mention} with {len(self.current_roles)} roles."
                ),
                view=None
            )
            logger.info(f"Role menu successfully created by {interaction.user} with {len(self.current_roles)} roles")
        except Exception as e:
            logger.error(f"Error finalizing role menu: {e}", exc_info=True)
            await interaction.followup.send(
                embed=EmbedFactory.error("Error", f"Failed to send the role menu: {e}"),
                ephemeral=True
            )


class ExclusiveRoleSelect(discord.ui.Select):
    """Dropdown for exclusive role selection (pick only one)"""

    def __init__(self, role_data: List[dict], category_name: str, all_role_ids: List[int], index: int = 0):
        options = [
            discord.SelectOption(
                label=r['label'][:100],
                description=t("roles.get_role", default="Get the {role} role", role=r['label'])[:100],
                value=str(r['role'].id),
                emoji=r['emoji']
            )
            for r in role_data
        ]

        super().__init__(
            placeholder=t("roles.select_placeholder", default="Choose your option..."),
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"exclusive_role_{category_name[:30]}_{index}"
        )
        self.all_role_ids = all_role_ids

    async def callback(self, interaction: discord.Interaction):
        """Handle exclusive role selection - LOCKED after first selection"""
        try:
            # Check if user already has any role from THIS MENU ONLY
            user_has_role = False
            existing_role = None
            for role_id in self.all_role_ids:
                role = interaction.guild.get_role(role_id)
                if role and role in interaction.user.roles:
                    user_has_role = True
                    existing_role = role
                    break

            if user_has_role:
                await interaction.response.send_message(
                    embed=EmbedFactory.error(
                        "🔒 Role Already Selected",
                        f"You already have **{existing_role.name}**. You cannot select another role from this menu."
                    ),
                    ephemeral=True
                )
                return

            selected_role_id = int(self.values[0])
            selected_role = interaction.guild.get_role(selected_role_id)

            if not selected_role:
                await interaction.response.send_message(
                    embed=EmbedFactory.error("Error", "Role not found"),
                    ephemeral=True
                )
                return

            # Give the selected role (only this one, no removing others)
            await interaction.user.add_roles(selected_role, reason="Exclusive role menu selection")

            embed = EmbedFactory.success(
                "✅ Role Selected!",
                f"You now have the **{selected_role.name}** role!\n\n"
                f"**Note:** You cannot select another role from this menu."
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

            logger.info(f"{interaction.user} selected exclusive role {selected_role.name}")

        except discord.Forbidden:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Error", "I don't have permission to manage your roles. Please contact an admin."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in role selection: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=EmbedFactory.error("Error", f"Failed to assign role: {str(e)}"),
                ephemeral=True
            )


class MultiRoleSelect(discord.ui.Select):
    """Dropdown menu for multiple role selection"""

    def __init__(self, role_data: List[dict], index: int = 0):
        options = [
            discord.SelectOption(
                label=r['label'][:100],
                description=t("roles.toggle_role", default="Toggle {role} role", role=r['label'])[:100],
                value=str(r['role'].id),
                emoji=r['emoji']
            )
            for r in role_data
        ]

        super().__init__(
            placeholder=t("roles.multi_placeholder", default="Select roles to add/remove..."),
            min_values=0,
            max_values=min(2, len(options)),
            options=options,
            custom_id=f"multi_role_select_{index}"
        )

    async def callback(self, interaction: discord.Interaction):
        """Handle role selection"""
        try:
            selected_role_ids = {int(value) for value in self.values}
            
            # Find all role IDs managed by the entire menu View
            menu_role_ids = set()
            for child in self.view.children:
                if isinstance(child, discord.ui.Select):
                    for option in child.options:
                        menu_role_ids.add(int(option.value))
                        
            current_user_menu_roles = {role.id for role in interaction.user.roles if role.id in menu_role_ids}
            roles_affected_by_this_select = {int(option.value) for option in self.options}
            
            # Predict their final set of menu roles
            future_menu_roles = current_user_menu_roles - roles_affected_by_this_select
            future_menu_roles.update(selected_role_ids)
            
            if len(future_menu_roles) > 2:
                return await interaction.response.send_message(
                    embed=EmbedFactory.error("Role Limit Exceeded", "You can only select up to 2 roles from this menu!"),
                    ephemeral=True
                )
                
            current_role_ids = {role.id for role in interaction.user.roles}

            roles_to_add = []
            roles_to_remove = []

            for role_id in roles_affected_by_this_select:
                role = interaction.guild.get_role(role_id)
                if not role:
                    continue

                if role_id in selected_role_ids and role_id not in current_role_ids:
                    roles_to_add.append(role)
                elif role_id not in selected_role_ids and role_id in current_role_ids:
                    roles_to_remove.append(role)

            if roles_to_add:
                await interaction.user.add_roles(*roles_to_add, reason="Role menu selection")
            if roles_to_remove:
                await interaction.user.remove_roles(*roles_to_remove, reason="Role menu deselection")

            changes = []
            if roles_to_add:
                changes.append(f"**Added:** {', '.join([r.name for r in roles_to_add])}")
            if roles_to_remove:
                changes.append(f"**Removed:** {', '.join([r.name for r in roles_to_remove])}")

            if not changes:
                changes.append("No changes made")

            embed = EmbedFactory.success(
                "✅ Roles Updated!",
                "\n".join(changes)
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except discord.Forbidden:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Error", "I don't have permission to manage your roles. Please contact an admin."),
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in multi-role selection: {e}", exc_info=True)
            await interaction.response.send_message(
                embed=EmbedFactory.error("Error", f"Failed to update roles: {str(e)}"),
                ephemeral=True
            )


class ExclusiveRoleView(discord.ui.View):
    """View for exclusive role selection"""

    def __init__(self, role_data: List[dict], category_name: str, timeout: Optional[float] = None):
        super().__init__(timeout=timeout)
        self.message = None
        
        all_role_ids = [int(r['role'].id) for r in role_data]
        role_chunks = [role_data[i:i + 25] for i in range(0, len(role_data), 25)]
        
        for i, chunk in enumerate(role_chunks[:5]):
            self.add_item(ExclusiveRoleSelect(chunk, category_name, all_role_ids, i))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class MultiRoleView(discord.ui.View):
    """View for multi role selection"""

    def __init__(self, role_data: List[dict], timeout: Optional[float] = None):
        super().__init__(timeout=timeout)
        self.message = None
        
        role_chunks = [role_data[i:i + 25] for i in range(0, len(role_data), 25)]
        
        for i, chunk in enumerate(role_chunks[:5]):
            self.add_item(MultiRoleSelect(chunk, i))

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.HTTPException:
                pass


class Roles(commands.Cog):
    """Role management cog"""

    def __init__(self, bot: commands.Bot, db: DatabaseManager, config: dict):
        self.bot = bot
        self.db = db
        self.config = config
        self.module_config = config.get('modules', {}).get('roles', {})
        # Register persistent views on startup
        self.bot.loop.create_task(self._register_persistent_views())
    
    async def _register_persistent_views(self):
        """Register persistent views for role menus across all configured guilds"""
        await self.bot.wait_until_ready()
        try:
            cursor = self.db.db.guilds.find({"role_menu_data": {"$exists": True}})
            async for guild_data in cursor:
                guild_id = guild_data.get("guild_id")
                role_menu = guild_data.get("role_menu_data", {})
                roles = role_menu.get("roles", [])
                is_exclusive = role_menu.get("is_exclusive", False)
                title = role_menu.get("title", "Role Menu")

                if not roles:
                    continue

                guild = self.bot.get_guild(guild_id)
                role_list = []
                for r in roles:
                    role_id = int(r['id'])
                    role_obj = guild.get_role(role_id) if guild else None
                    if not role_obj:
                        class DummyRole:
                            def __init__(self, rid, name):
                                self.id = rid
                                self.name = name
                                self.is_default = lambda: False
                                self.is_integration = lambda: False
                        role_obj = DummyRole(role_id, r.get('label', 'Role'))
                    role_list.append({
                        'role': role_obj,
                        'emoji': r.get('emoji', '🎭'),
                        'label': r.get('label', 'Role')
                    })

                if is_exclusive:
                    view = ExclusiveRoleView(role_list, title, timeout=None)
                else:
                    view = MultiRoleView(role_list, timeout=None)

                self.bot.add_view(view)
                logger.info(f"Registered persistent role view for guild {guild_id} ('{title}')")
        except Exception as e:
            logger.error(f"Error registering persistent role views: {e}", exc_info=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        content = message.content.strip()
        if content.startswith("رول ") or content == "رول":
            if not getattr(message.author.guild_permissions, 'administrator', False):
                return
            
            if len(message.mentions) >= 1 and len(message.role_mentions) >= 1:
                target_user = message.mentions[0]
                target_role = message.role_mentions[0]
                
                try:
                    await target_user.add_roles(target_role)
                    embed = EmbedFactory.success("Role Added", f"Added {target_role.mention} to {target_user.mention}")
                    await message.reply(embed=embed)
                    logger.info(f"{message.author} added role {target_role} to {target_user} via explicit command")
                except discord.Forbidden:
                    embed = EmbedFactory.error("Error", "I don't have permission to manage roles")
                    await message.reply(embed=embed)


    @app_commands.command(name="setup-role-menu", description="Setup a large role menu via Modal (Up to 125 roles)")
    @app_commands.describe(channel="Channel to send menu (optional)")
    @is_admin()
    async def setup_role_menu(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None
    ):
        """Invoke modal for creating a massive role menu"""
        target_channel = channel or interaction.channel
        await interaction.response.send_modal(RoleMenuSetupModal(self, target_channel))


    @app_commands.command(name="create-role-menu", description="Create a role menu (Admin)")
    @app_commands.describe(
        title="Title of the role menu",
        description="Description of the role menu",
        role1="First role",
        role2="Second role (optional)",
        role3="Third role (optional)",
        role4="Fourth role (optional)",
        role5="Fifth role (optional)",
        role6="Sixth role (optional)",
        role7="Seventh role (optional)",
        role8="Eighth role (optional)",
        role9="Ninth role (optional)",
        role10="Tenth role (optional)",
        exclusive="Can users only pick ONE role? (yes/no)",
        channel="Channel to send menu (optional)"
    )
    @is_admin()
    async def create_role_menu(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str,
        role1: discord.Role,
        exclusive: str,
        role2: Optional[discord.Role] = None,
        role3: Optional[discord.Role] = None,
        role4: Optional[discord.Role] = None,
        role5: Optional[discord.Role] = None,
        role6: Optional[discord.Role] = None,
        role7: Optional[discord.Role] = None,
        role8: Optional[discord.Role] = None,
        role9: Optional[discord.Role] = None,
        role10: Optional[discord.Role] = None,
        channel: Optional[discord.TextChannel] = None
    ):
        """Create role menu directly with slash command"""
        target_channel = channel or interaction.channel
        is_exclusive = exclusive.lower() in ['yes', 'y', 'true']
        
        # Collect all roles
        roles = [role1]
        if role2:
            roles.append(role2)
        if role3:
            roles.append(role3)
        if role4:
            roles.append(role4)
        if role5:
            roles.append(role5)
        if role6:
            roles.append(role6)
        if role7:
            roles.append(role7)
        if role8:
            roles.append(role8)
        if role9:
            roles.append(role9)
        if role10:
            roles.append(role10)
        
        # Build role list
        role_list = []
        for role in roles:
            if role.is_default() or role.is_integration():
                continue
            
            role_emoji = None
            if role.unicode_emoji:
                role_emoji = role.unicode_emoji
            elif role.icon:
                role_emoji = str(role.icon)
            
            role_list.append({
                'role': role,
                'emoji': role_emoji or "🎭",
                'label': role.name
            })
        
        if not role_list:
            await interaction.response.send_message(
                embed=EmbedFactory.error("No Valid Roles", "Please select valid roles."),
                ephemeral=True
            )
            return
        
        db_role_list = []
        for r in role_list:
            db_role_list.append({
                'id': str(r['role'].id),
                'emoji': r['emoji'],
                'label': r['label']
            })
            
        await self.db.update_guild(interaction.guild_id, {
            "role_menu_data": {
                "roles": db_role_list,
                "is_exclusive": is_exclusive,
                "title": title,
                "description": description
            }
        })
        
        embed = EmbedFactory.create(
            title=title,
            description=description,
            color=EmbedColor.PRIMARY
        )
        
        roles_texts = []
        current_text = ""
        for r in role_list:
            line = f"{r['emoji']} {r['role'].mention}\n"
            if len(current_text) + len(line) > 1024:
                roles_texts.append(current_text)
                current_text = line
            else:
                current_text += line
        if current_text:
            roles_texts.append(current_text)
            
        for i, text in enumerate(roles_texts):
            embed.add_field(name="Available Roles" if i == 0 else "\u200b", value=text, inline=False)
            
        if is_exclusive:
            view = ExclusiveRoleView(role_list, title, timeout=None)
        else:
            view = MultiRoleView(role_list, timeout=None)
            
        await target_channel.send(embed=embed, view=view)
        
        await interaction.response.send_message(
            embed=EmbedFactory.success(
                "Role Menu Sent!",
                f"{'Exclusive' if is_exclusive else 'Multi-select'} role menu sent to {target_channel.mention}."
            ),
            ephemeral=True
        )
        
        logger.info(f"Role menu created by {interaction.user} with {len(role_list)} roles")

    @app_commands.command(name="addrole", description="Add a role to a user (Admin)")
    @app_commands.describe(user="User to add role to", role="Role to add")
    @is_admin()
    async def add_role(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        """Add role to user"""
        if role in user.roles:
            await interaction.response.send_message(
                embed=EmbedFactory.info("Already Has Role", f"{user.mention} already has {role.mention}"),
                ephemeral=True
            )
            return

        try:
            await user.add_roles(role)
            embed = EmbedFactory.success("Role Added", f"Added {role.mention} to {user.mention}")
            await interaction.response.send_message(embed=embed)
            logger.info(f"{interaction.user} added role {role} to {user}")
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Error", "I don't have permission to manage roles"),
                ephemeral=True
            )

    @app_commands.command(name="removerole", description="Remove a role from a user (Admin)")
    @app_commands.describe(user="User to remove role from", role="Role to remove")
    @is_admin()
    async def remove_role(self, interaction: discord.Interaction, user: discord.Member, role: discord.Role):
        """Remove role from user"""
        if role not in user.roles:
            await interaction.response.send_message(
                embed=EmbedFactory.info("Doesn't Have Role", f"{user.mention} doesn't have {role.mention}"),
                ephemeral=True
            )
            return

        try:
            await user.remove_roles(role)
            embed = EmbedFactory.success("Role Removed", f"Removed {role.mention} from {user.mention}")
            await interaction.response.send_message(embed=embed)
            logger.info(f"{interaction.user} removed role {role} from {user}")
        except discord.Forbidden:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Error", "I don't have permission to manage roles"),
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Setup function for cog loading"""
    await bot.add_cog(Roles(bot, bot.db, bot.config))
