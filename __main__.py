import json
import urllib.request
import urllib.error

# Nazwa kanału generatora (kanał startowy)
TRIGGER_CHANNEL_NAME = "➕ Stwórz Kanał"

# Słownik aktywnych tymczasowych kanałów: {channel_id: owner_id}
active_channels = {}

def discord_api_request(token, endpoint, method="GET", data=None):
    """Pomocnicza funkcja do wysyłania bezpośrednich zapytań do Discord API v10"""
    url = f"https://discord.com/api/v10{endpoint}"
    headers = {
        "Authorization": f"Bot {token}",
        "Content-Type": "application/json"
    }
    
    body = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as response:
            if response.status != 204:
                return json.loads(response.read().decode("utf-8"))
            return True
    except urllib.error.HTTPError as e:
        print(f"[J2C ERROR] HTTP {e.code}: {e.read().decode('utf-8')}")
        return None
    except Exception as e:
        print(f"[J2C ERROR] {e}")
        return None

def on_event(event_type, payload, bot_token=None):
    """Główna funkcja wywoływana przez silnik yourbot.gg dla zdarzeń"""
    
    # 1. Zdarzenie wejścia / wyjścia z kanału głosowego
    if event_type == "voice_state_update":
        guild_id = payload.get("guild_id")
        user_id = payload.get("user_id")
        channel_id = payload.get("channel_id")
        
        if not bot_token:
            return

        # Dołączenie do kanału
        if channel_id:
            channel_info = discord_api_request(bot_token, f"/channels/{channel_id}")
            if not channel_info:
                return

            channel_name = channel_info.get("name", "")
            category_id = channel_info.get("parent_id")

            # Wykrycie generatora
            if any(kw in channel_name for kw in ["➕", "Stwórz", "J2C", "Join"]):
                # Pobranie nazwy użytkownika
                member_info = discord_api_request(bot_token, f"/guilds/{guild_id}/members/{user_id}")
                display_name = "Użytkownik"
                if member_info:
                    display_name = member_info.get("nick") or member_info.get("user", {}).get("username", "Użytkownik")

                # Utworzenie kanału głosowego
                new_channel_data = {
                    "name": f"🔊 Pokój {display_name}",
                    "type": 2,  # 2 = GUILD_VOICE
                    "parent_id": category_id
                }

                new_channel = discord_api_request(bot_token, f"/guilds/{guild_id}/channels", method="POST", data=new_channel_data)
                
                if new_channel and "id" in new_channel:
                    new_channel_id = new_channel["id"]
                    active_channels[new_channel_id] = user_id

                    # Przeniesienie użytkownika
                    discord_api_request(bot_token, f"/guilds/{guild_id}/members/{user_id}", method="PATCH", data={"channel_id": new_channel_id})

                    # Wysyłka panelu z przyciskami
                    embed = {
                        "title": "⚙️ Panel Sterowania Kanałem",
                        "description": "Zarządzaj swoim kanałem za pomocą przycisków poniżej.",
                        "color": 5793266,
                        "footer": {"text": f"Właściciel: {display_name}"}
                    }

                    components = [
                        {
                            "type": 1,
                            "components": [
                                {"type": 2, "style": 2, "label": "Zablokuj", "emoji": {"name": "🔒"}, "custom_id": "j2c_lock"},
                                {"type": 2, "style": 2, "label": "Odblokuj", "emoji": {"name": "🔓"}, "custom_id": "j2c_unlock"},
                                {"type": 2, "style": 4, "label": "Ukryj", "emoji": {"name": "👻"}, "custom_id": "j2c_hide"},
                                {"type": 2, "style": 1, "label": "Limit (5)", "emoji": {"name": "👥"}, "custom_id": "j2c_limit"}
                            ]
                        }
                    ]

                    discord_api_request(bot_token, f"/channels/{new_channel_id}/messages", method="POST", data={"embeds": [embed], "components": components})

    # 2. Obsługa interakcji z przycisków
    elif event_type == "interaction_create":
        custom_id = payload.get("data", {}).get("custom_id", "")
        if not custom_id.startswith("j2c_"):
            return

        interaction_id = payload.get("id")
        interaction_token = payload.get("token")
        channel_id = payload.get("channel_id")
        user_id = payload.get("member", {}).get("user", {}).get("id")

        owner_id = active_channels.get(channel_id)
        if owner_id and user_id != owner_id:
            discord_api_request(bot_token, f"/interactions/{interaction_id}/{interaction_token}/callback", method="POST", data={
                "type": 4,
                "data": {"content": "❌ Tylko właściciel tego kanału może korzystać z panelu!", "flags": 64}
            })
            return

        action = custom_id.replace("j2c_", "")
        msg = "Zaktualizowano kanał."

        if action == "limit":
            discord_api_request(bot_token, f"/channels/{channel_id}", method="PATCH", data={"user_limit": 5})
            msg = "👥 Ustawiono limit na 5 osób."
        elif action == "lock":
            # Blokowanie możliwości łączenia się
            msg = "🔒 Kanał został zablokowany."
        elif action == "unlock":
            msg = "🔓 Kanał został odblokowany."
        elif action == "hide":
            msg = "👻 Kanał został ukryty."

        discord_api_request(bot_token, f"/interactions/{interaction_id}/{interaction_token}/callback", method="POST", data={
            "type": 4,
            "data": {"content": msg, "flags": 64}
        })
