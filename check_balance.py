import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot
from aiogram.methods.get_my_star_balance import GetMyStarBalance


load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")


async def main():
    bot = Bot(token=BOT_TOKEN)

    try:
        balance = await bot(GetMyStarBalance())
        print(f"Stars: {balance.amount}")
        print(f"Nano: {balance.nanostar_amount}")
    except Exception as error:
        print(f"Ошибка: {error}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())