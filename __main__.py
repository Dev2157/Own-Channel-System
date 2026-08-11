import discord
from discord.ext import commands
from discord.ui import View, button

# ID Twojego kanału-generatora oraz kategorii dla nowych kanałów
GENERATOR_CHANNEL_ID = 123456789012345678  # Zamień na własne ID
CATEGORY_ID = 123456789012345678           # Zamień na własne ID

# Słownik przechowujący aktywne kanały: {channel_id: owner_id}
active_channels = {}


class VoiceControlPanel(View):
    def __init__(self, owner_id: int):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "❌ Tylko właściciel tego kanału może korzystać z panelu!", 
                ephemeral=True
            )
            return False
        return True

    @button(label="Zablokuj", style=discord.ButtonStyle.secondary, emoji="🔒", custom_id="j2c_lock")
    async def lock_channel(self, interaction: discord.Interaction, button_obj: discord.ui.Button):
        await interaction.channel.set_permissions(interaction.guild.default_role, connect=False)
        await interaction.response.send_message("🔒 Kanał został zablokowany.", ephemeral=True)

    @button(label="Odblokuj", style=discord.ButtonStyle.secondary, emoji="🔓", custom_id="j2c_unlock")
    async def unlock_channel(self, interaction: discord.Interaction, button_obj: discord.ui.Button):
        await interaction.channel.set_permissions(interaction.guild.default_role, connect=None)
        await interaction.response.send_message("🔓 Kanał został odblokowany.", ephemeral=True)

    @button(label="Ukryj", style=discord.ButtonStyle.danger, emoji="👻", custom_id="j2c_hide")
    async def hide_channel(self, interaction: discord.Interaction, button_obj: discord.ui.Button):
        await interaction.channel.set_permissions(interaction.guild.default_role, view_channel=False)
        await interaction.response.send_message("👻 Kanał został ukryty.", ephemeral=True)

    @button(label="Limit (5)", style=discord.ButtonStyle.primary, emoji="👥", custom_id="j2c_limit")
    async def set_limit(self, interaction: discord.Interaction, button_obj: discord.ui.Button):
        await interaction.channel.edit(user_limit=5)
        await interaction.response.send_message("👥 Ustawiono limit na 5 osób.", ephemeral=True)


class JoinToCreate(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # 1. Tworzenie nowego kanału po wejściu na generator
        if after.channel and after.channel.id == GENERATOR_CHANNEL_ID:
            guild = member.guild
            category = guild.get_channel(CATEGORY_ID)

            # Uprawnienia dla właściciela
            overwrites = {
                member: discord.PermissionOverwrite(manage_channels=True, move_members=True, connect=True)
            }

            # Tworzenie kanału głosowego
            new_channel = await guild.create_voice_channel(
                name=f"🔊 | Pokój {member.display_name}",
                category=category,
                overwrites=overwrites
            )

            active_channels[new_channel.id] = member.id
            await member.move_to(new_channel)

            # Budowa Embedu i Panelu
            embed = discord.Embed(
                title="⚙️ Panel Sterowania Kanałem",
                description="Użyj poniższych przycisków, aby dostosować swój kanał głosowy.",
                color=discord.Color.blurple()
            )
            embed.set_footer(text=f"Właściciel: {member.display_name}")

            view = VoiceControlPanel(owner_id=member.id)
            await new_channel.send(embed=embed, view=view)

        # 2. Usuwanie pustych kanałów tymczasowych
        if before.channel and before.channel.id in active_channels:
            if len(before.channel.members) == 0:
                del active_channels[before.channel.id]
                await before.channel.delete()


async def setup(bot: commands.Bot):
    await bot.add_cog(JoinToCreate(bot))
