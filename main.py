import sys
from pyrogram import Client
from config import API_ID, API_HASH, BOT_TOKEN

# Import all handlers so they register with the client
import handlers.commands
import handlers.video

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="merger_bot",
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            plugins=dict(root="handlers")
        )

    async def start(self):
        await super().start()
        print("Bot is online!")

    async def stop(self, *args):
        await super().stop()
        print("Bot stopped!")

if __name__ == "__main__":
    bot = Bot()
    bot.run()
