import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, button

# Słowniki przechowujące konfigurację serwerów i aktywne pokoje
guild_configs = {}  # {guild_id: {"generator_id": int, "category_id": int}}
active_channels = {}  # {channel_id: owner_id}

class VoiceControlPanel(View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message("❌ Tylko właściciel tego kanału może korzystać z panelu!", ephemeral=True)
            return False
        return True

    @button(label="Zablokuj", style=discord.ButtonStyle.secondary, emoji="🔒", custom_id="j2c_lock")
    async def lock_channel(self, interaction: discord.Interaction, button_obj: discord.ui.Button):
        await interaction.channel.set_permissions(interaction.guild.default_role, connect=False)
        await interaction.response.send_message("🔒 Zablokowano kanał.", ephemeral=True)

    @button(label="Odblokuj", style=discord.ButtonStyle.secondary, emoji="🔓", custom_id="j2c_unlock")
    async def unlock_channel(self, interaction: discord.Interaction, button_obj: discord.ui.Button):
        await interaction.channel.set_permissions(interaction.guild.default_role, connect=None)
        await interaction.response.send_message("🔓 Odblokowano kanał.", ephemeral=True)

    @button(label="Ukryj", style=discord.ButtonStyle.danger, emoji="👻", custom_id="j2c_hide")
    async def hide_channel(self, interaction: discord.Interaction, button_obj: discord.ui.Button):
        await interaction.channel.set_permissions(interaction.guild.default_role, view_channel=False)
        await interaction.response.send_message("👻 Ukryto kanał.", ephemeral=True)

    @button(label="Limit (5)", style=discord.ButtonStyle.primary, emoji="👥", custom_id="j2c_limit")
    async def set_limit(self, interaction: discord.Interaction, button_obj: discord.ui.Button):
        await interaction.channel.edit(user_limit=5)
        await interaction.response.send_message("👥 Ustawiono limit na 5 osób.", ephemeral=True)

class JoinToCreateCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setup_j2c", description="Konfiguruje system Join to Create na serwerze.")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_j2c(self, interaction: discord.Interaction):
        guild = interaction.guild
        
        # 1. Tworzenie kategorii i generatora
        category = await guild.create_category(name="🔊 Kanały Prywatne")
        generator = await guild.create_voice_channel(name="➕ Stwórz Kanał", category=category)

        guild_configs[guild.id] = {
            "generator_id": generator.id,
            "category_id": category.id
        }

        await interaction.response.send_message(f"✅ System skonfigurowany! Kanał generatora: {generator.mention}", ephemeral=True)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        guild_id = member.guild.id
        config = guild_configs.get(guild_id)

        # Dołączenie do generatora
        if config and after.channel and after.channel.id == config["generator_id"]:
            guild = member.guild
            category = guild.get_channel(config["category_id"])

            overwrites = {
                member: discord.PermissionOverwrite(manage_channels=True, move_members=True, connect=True)
            }

            new_channel = await guild.create_voice_channel(
                name=f"🔊 Pokój {member.display_name}",
                category=category,
                overwrites=overwrites
            )

            active_channels[new_channel.id] = member.id
            await member.move_to(new_channel)

            embed = discord.Embed(
                title="⚙️ Panel Sterowania Kanałem",
                description="Zarządzaj swoim kanałem za pomocą przycisków poniżej.",
                color=discord.Color.blurple()
            )
            embed.set_footer(text=f"Właściciel: {member.display_name}")

            view = VoiceControlPanel(owner_id=member.id)
            await new_channel.send(embed=embed, view=view)

        # Opuszczenie i czyszczenie pustych pokoi
        if before.channel and before.channel.id in active_channels:
            if len(before.channel.members) == 0:
                del active_channels[before.channel.id]
                await before.channel.delete()

async def setup(bot: commands.Bot):
    await bot.add_cog(JoinToCreateCog(bot))
