#! /home/rabbi/price_alerts_PTB/venv/bin/python3.8

import yfinance as yf
from database import ALERTS, delete_alert
from telegram import Bot
import asyncio
import logging
from database import TOKEN, PATH


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO, filename=f'{PATH}alerts.log'
)

monitor_symbols = ALERTS.distinct('symbol')


def get_prices(monitor_symbols=monitor_symbols):
    price_frame = yf.download(monitor_symbols, period='1d', interval='5m', group_by='column',
                              progress=False, rounding=True)
    price_frame = price_frame.loc[:,'Adj Close'].iloc[-1]
    if len(monitor_symbols) < 2:
        return {monitor_symbols[0]: price_frame}
    else:
        return price_frame.to_dict()


def check_alerts(current_prices):
    triggered = []
    for symbol in monitor_symbols:
        query = ALERTS.find({"$or": [{'symbol': symbol, 'up': True, 'price': {"$lt": current_prices[symbol]}},
                                         {'symbol': symbol, 'up': False, 'price': {"$gt": current_prices[symbol]}}
                                         ]})
        triggered.append([x for x in query])
    return [x[0] for x in triggered if x]


async def send_alerts(triggered):
    bot = Bot(TOKEN)
    for alert in triggered:
        await bot.send_message(chat_id=alert["user_id"], text=f'🔷 {alert["symbol"]} reached {alert["price"]}!')
        delete_alert(alert["_id"])


async def main():
    current_prices = get_prices(monitor_symbols)
    triggered = check_alerts(current_prices)
    await send_alerts(triggered)


if __name__ == "__main__":
    asyncio.run(main())
