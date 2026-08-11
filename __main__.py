import discord
from discord import app_commands
from discord.ext import commands
from discord.ui import View, button

# Słownik do śledzenia aktywnych pokoi: {channel_id: owner_id}
active_channels = {}

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

    # Komenda rejestrująca Slash Commands
    @commands.command(name="sync_j2c")
    @commands.has_permissions(administrator=True)
    async def sync_j2c(self, ctx: commands.Context):
        await self.bot.tree.sync()
        await ctx.send("✅ Zsynchronizowano komendy slash!")

    @app_commands.command(name="setup_j2c", description="Stwarza kategroię i lobby do tworzenia kanałów")
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_j2c(self, interaction: discord.Interaction):
        guild = interaction.guild
        
        # Tworzenie nowej kategorii oraz kanału-generatora
        category = await guild.create_category(name="🔊 Kanały Prywatne")
        generator = await guild.create_voice_channel(name="➕ Stwórz Kanał", category=category)

        await interaction.response.send_message(
            f"✅ System aktywowany!\n"
            f"• Kategoria: **{category.name}**\n"
            f"• Kanał generatora: {generator.mention}", 
            ephemeral=True
        )

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # 1. Sprawdzanie czy użytkownik wszedł na kanał o nazwie "➕ Stwórz Kanał"
        if after.channel and after.channel.name == "➕ Stwórz Kanał":
            guild = member.guild
            category = after.channel.category

            overwrites = {
                member: discord.PermissionOverwrite(manage_channels=True, move_members=True, connect=True)
            }

            try:
                # Tworzenie nowego kanału
                new_channel = await guild.create_voice_channel(
                    name=f"🔊 Pokój {member.display_name}",
                    category=category,
                    overwrites=overwrites
                )

                active_channels[new_channel.id] = member.id
                await member.move_to(new_channel)

                embed = discord.Embed(
                    title="⚙️ Panel Sterowania Kanałem",
                    description="Zarządzaj swoim kanałem głosowym za pomocą przycisków poniżej.",
                    color=discord.Color.blurple()
                )
                embed.set_footer(text=f"Właściciel: {member.display_name}")

                view = VoiceControlPanel(owner_id=member.id)
                await new_channel.send(embed=embed, view=view)

            except Exception as e:
                print(f"[J2C ERROR] Błąd podczas tworzenia kanału: {e}")

        # 2. Usuwanie pustych pokoi tymczasowych
        if before.channel and before.channel.id in active_channels:
            if len(before.channel.members) == 0:
                del active_channels[before.channel.id]
                await before.channel.delete()


async def setup(bot: commands.Bot):
    await bot.add_cog(JoinToCreateCog(bot))
