"""
Music Cog for Logiq
Music player powered by Wavelink (Lavalink)
"""

import discord
from discord import app_commands
from discord.ext import commands
import logging
import wavelink
from utils.i18n import t
from utils.embeds import EmbedFactory, EmbedColor
from utils.permissions import is_admin
from database.db_manager import DatabaseManager

logger = logging.getLogger(__name__)

class MusicControlView(discord.ui.View):
    """Music player controls"""
    
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="⏸️ Pause", style=discord.ButtonStyle.primary, custom_id="music_pause")
    async def pause_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Pause/Resume music"""
        player: wavelink.Player = interaction.guild.voice_client
        if not player:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Not Playing", "No music is playing"),
                ephemeral=True
            )
            return
            
        if player.paused:
            await player.pause(False)
            button.label = t("music.pause", default="⏸️ Pause")
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(
                embed=EmbedFactory.info("Resumed", "Music resumed"),
                ephemeral=True
            )
        else:
            await player.pause(True)
            button.label = t("music.resume", default="▶️ Resume")
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(
                embed=EmbedFactory.info("Paused", "Music paused"),
                ephemeral=True
            )
            
    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.secondary, custom_id="music_skip")
    async def skip_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Skip current track"""
        player: wavelink.Player = interaction.guild.voice_client
        if not player:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Not Playing", "No music is playing"),
                ephemeral=True
            )
            return
            
        await player.skip(force=True)
        await interaction.response.send_message(
            embed=EmbedFactory.success("Skipped", "Skipped current track"),
            ephemeral=True
        )
            
    @discord.ui.button(label="⏹️ Stop", style=discord.ButtonStyle.danger, custom_id="music_stop")
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Stop music and disconnect"""
        player: wavelink.Player = interaction.guild.voice_client
        if not player:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Not Playing", "No music is playing"),
                ephemeral=True
            )
            return
            
        await player.disconnect()
        await interaction.response.send_message(
            embed=EmbedFactory.success("Stopped", "Music stopped and disconnected"),
            ephemeral=True
        )


class Music(commands.Cog):
    """Music player cog powered by Wavelink"""

    def __init__(self, bot: commands.Bot, db: DatabaseManager, config: dict):
        self.bot = bot
        self.db = db
        self.config = config
        self.module_config = config.get('modules', {}).get('music', {})

    async def cog_load(self):
        """Called when the cog is loaded."""
        nodes = [wavelink.Node(uri="http://127.0.0.1:2333", password="youshallnotpass")]
        try:
            await wavelink.Pool.connect(nodes=nodes, client=self.bot, cache_capacity=100)
            logger.info("Successfully connected to Wavelink Node.")
        except Exception as e:
            logger.error(f"Failed to connect to Wavelink node: {e}")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        """Event fired when a track ends."""
        if not payload.player:
            return
        # Wavelink 3.x AutoPlay handles queue progression, but if we don't use AutoPlay,
        # we can just play the next track manually if it exists.
        if not payload.player.queue.is_empty:
            next_track = payload.player.queue.get()
            await payload.player.play(next_track)

    @app_commands.command(name="play", description="Play music from YouTube, Spotify, SoundCloud, or Links")
    @app_commands.describe(query="Song name or URL")
    async def play(self, interaction: discord.Interaction, query: str):
        """Play music"""
        await interaction.response.defer()
        
        if not interaction.user.voice:
            await interaction.followup.send(
                embed=EmbedFactory.error("Not in Voice", "You must be in a voice channel to use this command"),
                ephemeral=True
            )
            return

        player: wavelink.Player = interaction.guild.voice_client
        
        if not player:
            try:
                player = await interaction.user.voice.channel.connect(cls=wavelink.Player)
            except Exception as e:
                await interaction.followup.send(
                    embed=EmbedFactory.error("Connection Failed", f"Could not join voice channel: {str(e)}"),
                    ephemeral=True
                )
                return

        try:
            # Wavelink handles YouTube, Spotify, Soundcloud automatically
            tracks: wavelink.Search = await wavelink.Playable.search(query)
            if not tracks:
                await interaction.followup.send(
                    embed=EmbedFactory.error("Not Found", "No songs were found matching your query."),
                    ephemeral=True
                )
                return

            # If it's a playlist, add all tracks
            if isinstance(tracks, wavelink.Playlist):
                added = len(tracks.tracks)
                for track in tracks.tracks:
                    player.queue.put(track)
                embed = EmbedFactory.success(
                    "Playlist Added",
                    f"**Added {added} tracks from:** {tracks.name}\n"
                    f"**Requested by:** {interaction.user.mention}"
                )
            else:
                track = tracks[0]
                player.queue.put(track)
                embed = EmbedFactory.success(
                    "Added to Queue",
                    f"**Track:** {track.title}\n"
                    f"**Artist:** {track.author}\n"
                    f"**Requested by:** {interaction.user.mention}\n"
                    f"**Position in queue:** {player.queue.count}"
                )
            
            await interaction.followup.send(embed=embed, view=MusicControlView())
            
            # Start playback if not already playing
            if not player.playing:
                await player.play(player.queue.get())
                
            logger.info(f"Added to queue by {interaction.user}: {query}")
            
        except Exception as e:
            logger.error(f"Error playing track: {e}")
            await interaction.followup.send(
                embed=EmbedFactory.error("Error", f"Failed to play the track: {e}"),
                ephemeral=True
            )

    @app_commands.command(name="join", description="Join your voice channel")
    async def join(self, interaction: discord.Interaction):
        """Join voice channel"""
        await interaction.response.defer()
        if not interaction.user.voice:
            await interaction.followup.send(
                embed=EmbedFactory.error("Not in Voice", "You must be in a voice channel"),
                ephemeral=True
            )
            return

        channel = interaction.user.voice.channel
        player: wavelink.Player = interaction.guild.voice_client
        
        try:
            if player:
                await player.move_to(channel)
            else:
                await channel.connect(cls=wavelink.Player)
                
            embed = EmbedFactory.success("Joined", f"Joined {channel.mention}")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(
                embed=EmbedFactory.error("Connection Failed", f"An error occurred: {e}"),
                ephemeral=True
            )

    @app_commands.command(name="leave", description="Leave voice channel")
    async def leave(self, interaction: discord.Interaction):
        """Leave voice channel"""
        await interaction.response.defer()
        player: wavelink.Player = interaction.guild.voice_client
        if not player:
            await interaction.followup.send(
                embed=EmbedFactory.error("Not Connected", "I'm not in a voice channel"),
                ephemeral=True
            )
            return

        await player.disconnect()
        embed = EmbedFactory.success("Disconnected", "Left voice channel")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="queue", description="View music queue")
    async def view_queue(self, interaction: discord.Interaction):
        """View music queue"""
        player: wavelink.Player = interaction.guild.voice_client
        
        if not player or (not player.playing and player.queue.is_empty):
            await interaction.response.send_message(
                embed=EmbedFactory.info("Empty Queue", "The music queue is empty"),
                ephemeral=True
            )
            return

        description = ""
        if player.current:
            description += f"**Now Playing:**\n{player.current.title} - {player.current.author}\n\n"

        if not player.queue.is_empty:
            description += "**Up Next:**\n"
            for i, track in enumerate(player.queue[:10], 1):
                description += f"{i}. {track.title} - {track.author}\n"

        embed = EmbedFactory.create(
            title="🎵 Music Queue",
            description=description,
            color=EmbedColor.INFO
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="skip", description="Skip current track")
    async def skip(self, interaction: discord.Interaction):
        """Skip current track"""
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.playing:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Not Playing", "No music is playing"),
                ephemeral=True
            )
            return

        await player.skip(force=True)
        embed = EmbedFactory.success("Skipped", "Skipped current track")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pause", description="Pause music")
    async def pause(self, interaction: discord.Interaction):
        """Pause music"""
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.playing:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Not Playing", "No music is playing"),
                ephemeral=True
            )
            return

        if not player.paused:
            await player.pause(True)
            embed = EmbedFactory.success("Paused", "Music paused")
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Already Paused", "Music is already paused"),
                ephemeral=True
            )

    @app_commands.command(name="resume", description="Resume music")
    async def resume(self, interaction: discord.Interaction):
        """Resume music"""
        player: wavelink.Player = interaction.guild.voice_client
        if not player:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Not Playing", "I am not in a voice channel"),
                ephemeral=True
            )
            return

        if player.paused:
            await player.pause(False)
            embed = EmbedFactory.success("Resumed", "Music resumed")
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Not Paused", "Music is not paused"),
                ephemeral=True
            )

    @app_commands.command(name="volume", description="Set volume (Admin)")
    @app_commands.describe(volume="Volume level (0-100)")
    @is_admin()
    async def volume(self, interaction: discord.Interaction, volume: int):
        """Set volume"""
        if volume < 0 or volume > 100:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Invalid Volume", "Volume must be between 0 and 100"),
                ephemeral=True
            )
            return

        player: wavelink.Player = interaction.guild.voice_client
        if not player:
            await interaction.response.send_message(
                embed=EmbedFactory.error("Not Playing", "I am not in a voice channel"),
                ephemeral=True
            )
            return

        await player.set_volume(volume)
        embed = EmbedFactory.success("Volume", f"Volume set to {volume}%")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="nowplaying", description="Show currently playing track")
    async def nowplaying(self, interaction: discord.Interaction):
        """Show currently playing track"""
        player: wavelink.Player = interaction.guild.voice_client
        if not player or not player.current:
            await interaction.response.send_message(
                embed=EmbedFactory.info("Nothing Playing", "No music is currently playing"),
                ephemeral=True
            )
            return

        embed = EmbedFactory.create(
            title="🎵 Now Playing",
            description=f"**{player.current.title}** by {player.current.author}",
            color=EmbedColor.INFO
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    """Setup function for cog loading"""
    await bot.add_cog(Music(bot, bot.db, bot.config))
