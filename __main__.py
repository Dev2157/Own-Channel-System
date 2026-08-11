import discord
from discord.ext import commands
from discord.ui import View, button

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
        print(" -> [DEV] Plugin JoinToCreate został pomyślnie załadowany do pamięci!")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        # Wypisujemy absolutnie każdy ruch na głosowych w konsoli DEV
        if after.channel:
            print(f"[DEV VOICE] {member.name} wszedł na: {after.channel.name}")

        # Wykrywanie wejścia na kanał generatora
        if after.channel and any(kw in after.channel.name for kw in ["➕", "Stwórz", "J2C", "Join"]):
            print(f"[DEV LOG] Wykryto wejście na generator przez: {member.name}")
            guild = member.guild
            category = after.channel.category

            overwrites = {
                member: discord.PermissionOverwrite(
                    manage_channels=True, move_members=True, connect=True, view_channel=True
                )
            }

            try:
                new_channel = await guild.create_voice_channel(
                    name=f"🔊 Pokój {member.display_name}",
                    category=category,
                    overwrites=overwrites
                )

                active_channels[new_channel.id] = member.id
                await member.move_to(new_channel)

                embed = discord.Embed(
                    title="⚙️ Panel Sterowania Kanałem (DEV)",
                    description="Pomyślnie utworzono Twój kanał tymczasowy.",
                    color=discord.Color.green()
                )
                embed.set_footer(text=f"Właściciel: {member.display_name}")

                view = VoiceControlPanel(owner_id=member.id)
                await new_channel.send(embed=embed, view=view)
                print("[DEV LOG] Sukces! Kanał i panel utworzone.")

            except Exception as e:
                print(f"[DEV BŁĄD] Wystąpił wyjątek podczas tworzenia kanału: {e}")

        # Czyszczenie kanałów
        if before.channel and before.channel.id in active_channels:
            if len(before.channel.members) == 0:
                try:
                    del active_channels[before.channel.id]
                    await before.channel.delete()
                    print(f"[DEV LOG] Usunięto pusty kanał: {before.channel.name}")
                except Exception as e:
                    print(f"[DEV BŁĄD] Nie udało się usunąć kanału: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(JoinToCreateCog(bot))
