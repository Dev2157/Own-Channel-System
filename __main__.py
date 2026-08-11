import discord
from discord.ext import commands
from discord.ui import View, button

active_channels = {}
LOG_CHANNEL_ID = None  # Przechowuje ID kanału logów w pamięci

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

    async def send_log(self, guild: discord.Guild, message: str):
        """Pomocnicza funkcja do wysyłania logów na Discorda"""
        global LOG_CHANNEL_ID
        if LOG_CHANNEL_ID:
            log_chan = guild.get_channel(LOG_CHANNEL_ID)
            if log_chan:
                await log_chan.send(f"🛠️ **[J2C DEV LOG]** {message}")

    # Komenda do podłączenia podglądu logów na czacie Discorda
    @commands.command(name="j2c_logs")
    @commands.has_permissions(administrator=True)
    async def setup_logs(self, ctx: commands.Context):
        global LOG_CHANNEL_ID
        channel = await ctx.guild.create_text_channel(name="j2c-logi-dev")
        LOG_CHANNEL_ID = channel.id
        await ctx.send(f"✅ Utworzono kanał logów: {channel.mention}. Wszystkie zdarzenia bota będą tu wypisywane!")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        guild = member.guild

        # 1. Wykrywanie przejścia na jakikolwiek kanał głosowy
        if after.channel:
            await self.send_log(guild, f"Użytkownik `{member.name}` wszedł na kanał głosowy: **{after.channel.name}**")

            # Wykrywanie generatora (kanał musi mieć w nazwie ➕, Stwórz, J2C lub Join)
            if any(kw in after.channel.name for kw in ["➕", "Stwórz", "J2C", "Join"]):
                await self.send_log(guild, "Rozpoczynam tworzenie nowego pokoju...")

                category = after.channel.category
                overwrites = {
                    member: discord.PermissionOverwrite(
                        manage_channels=True, move_members=True, connect=True, view_channel=True
                    )
                }

                try:
                    # Tworzenie kanału
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
                    embed.set_footer(text=f"Właścinek: {member.display_name}")

                    view = VoiceControlPanel(owner_id=member.id)
                    await new_channel.send(embed=embed, view=view)
                    await self.send_log(guild, f"✅ Sukces! Utworzono kanał {new_channel.mention} i wysłano panel.")

                except discord.Forbidden:
                    await self.send_log(guild, "❌ **BŁĄD BRAKU UPRAWNIEŃ!** Bot nie posiada uprawnień do tworzenia kanałów lub przenoszenia osób.")
                except Exception as e:
                    await self.send_log(guild, f"❌ **BŁĄD:** {e}")

        # 2. Wyjście z kanału i czyszczenie
        if before.channel and before.channel.id in active_channels:
            if len(before.channel.members) == 0:
                try:
                    del active_channels[before.channel.id]
                    await before.channel.delete()
                    await self.send_log(guild, f"🗑️ Usunięto pusty kanał tymczasowy: **{before.channel.name}**")
                except Exception as e:
                    await self.send_log(guild, f"❌ Błąd podczas usuwania kanału: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(JoinToCreateCog(bot))
