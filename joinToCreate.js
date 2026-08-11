const { 
  ActionRowBuilder, 
  ButtonBuilder, 
  ButtonStyle, 
  EmbedBuilder, 
  ChannelType, 
  PermissionFlagsBits 
} = require('discord.js');

// Mapa przechowująca aktywne tymczasowe kanały: temporaryChannelId -> ownerUserId
const activeChannels = new Map();

// ID Kanału-Generatora (Po wejściu na ten kanał bot tworzy nowy)
const GENERATOR_CHANNEL_ID = 'TWÓJ_ID_KANAŁU_GENERATORA';
const CATEGORY_ID = 'TWÓJ_ID_KATEGORII_DLA_KANAŁÓW';

module.exports = {
  name: 'joinToCreate',

  init(client) {
    // 1. Zdarzenie do obsługi wchodzenia/wychodzenia z kanałów
    client.on('voiceStateUpdate', async (oldState, newState) => {
      // Użytkownik wszedł na kanał generatora
      if (newState.channelId === GENERATOR_CHANNEL_ID) {
        await createVoiceChannel(newState.member);
      }

      // Czyszczenie pustych kanałów tymczasowych
      if (oldState.channelId && activeChannels.has(oldState.channelId)) {
        const voiceChannel = oldState.guild.channels.cache.get(oldState.channelId);
        if (voiceChannel && voiceChannel.members.size === 0) {
          activeChannels.delete(voiceChannel.id);
          await voiceChannel.delete().catch(() => {});
        }
      }
    });

    // 2. Obsługa przycisków z panelu sterowania
    client.on('interactionCreate', async (interaction) => {
      if (!interaction.isButton()) return;
      if (!interaction.customId.startsWith('j2c_')) return;

      const channel = interaction.member.voice.channel;
      if (!channel || !activeChannels.has(channel.id)) {
        return interaction.reply({ content: '❌ Musisz znajdować się na swoim kanale tymczasowym!', ephemeral: true });
      }

      const ownerId = activeChannels.get(channel.id);
      if (interaction.user.id !== ownerId) {
        return interaction.reply({ content: '❌ Tylko właściciel kanału może używać tego panelu!', ephemeral: true });
      }

      await handlePanelAction(interaction, channel);
    });
  }
};

// Tworzenie nowego kanału głosowego i wysyłanie panelu
async function createVoiceChannel(member) {
  const guild = member.guild;

  const newChannel = await guild.channels.create({
    name: `🔊 | Pokój ${member.displayName}`,
    type: ChannelType.GuildVoice,
    parent: CATEGORY_ID,
    permissionOverwrites: [
      {
        id: member.id,
        allow: [PermissionFlagsBits.ManageChannels, PermissionFlagsBits.MoveMembers, PermissionFlagsBits.Connect],
      },
    ],
  });

  // Przepięcie użytkownika do nowego kanału
  await member.voice.setChannel(newChannel);
  activeChannels.set(newChannel.id, member.id);

  // Budowa Panelu Sterowania (Component Message)
  const embed = new EmbedBuilder()
    .setTitle('⚙️ Panel Sterowania Kanałem')
    .setDescription('Użyj poniższych przycisków, aby dostosować swój kanał głosowy.')
    .setColor('#5865F2')
    .setFooter({ text: `Właściciel: ${member.user.tag}` });

  const row = new ActionRowBuilder().addComponents(
    new ButtonBuilder().setCustomId('j2c_lock').setLabel('Zablokuj').setEmoji('🔒').setStyle(ButtonStyle.Secondary),
    new ButtonBuilder().setCustomId('j2c_unlock').setLabel('Odblokuj').setEmoji('🔓').setStyle(ButtonStyle.Secondary),
    new ButtonBuilder().setCustomId('j2c_hide').setLabel('Ukryj').setEmoji('👻').setStyle(ButtonStyle.Danger),
    new ButtonBuilder().setCustomId('j2c_limit').setLabel('Limit (5)').setEmoji('👥').setStyle(ButtonStyle.Primary)
  );

  // Wysyłanie panelu na czat głosowy kanału
  await newChannel.send({ embeds: [embed], components: [row] });
}

// Logic przycisków
async function handlePanelAction(interaction, channel) {
  const action = interaction.customId.replace('j2c_', '');

  switch (action) {
    case 'lock':
      await channel.permissionOverwrites.edit(channel.guild.roles.everyone, { Connect: false });
      await interaction.reply({ content: '🔒 Kanał został zablokowany.', ephemeral: true });
      break;

    case 'unlock':
      await channel.permissionOverwrites.edit(channel.guild.roles.everyone, { Connect: null });
      await interaction.reply({ content: '🔓 Kanał został odblokowany.', ephemeral: true });
      break;

    case 'hide':
      await channel.permissionOverwrites.edit(channel.guild.roles.everyone, { ViewChannel: false });
      await interaction.reply({ content: '👻 Kanał został ukryty.', ephemeral: true });
      break;

    case 'limit':
      await channel.setUserLimit(5);
      await interaction.reply({ content: '👥 Ustawiono limit na 5 osób.', ephemeral: true });
      break;
  }
}
