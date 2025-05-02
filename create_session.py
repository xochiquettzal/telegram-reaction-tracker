import os
import asyncio
from telethon import TelegramClient
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API kimlik bilgilerini al
API_ID = os.getenv('API_ID')
API_HASH = os.getenv('API_HASH')
PHONE_NUMBER = os.getenv('PHONE_NUMBER')

# Oturum adı
SESSION_NAME = 'session'

async def main():
    # Initialize and start Telegram client
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start(phone=PHONE_NUMBER)
    
    # Kullanıcının giriş yapıp yapmadığını kontrol et
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"Login successful: {me.first_name} (@{me.username})")
        print(f"session.session file created.")
    else:
        print("Login failed.")
    
    # İstemciyi kapat
    await client.disconnect()

if __name__ == "__main__":
    # asyncio loop'u çalıştır
    asyncio.run(main()) 