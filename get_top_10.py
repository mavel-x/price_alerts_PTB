#! /bin/python3

import yfinance as yf
import pandas as pd
import sqlalchemy

from database import DATABASE, PATH
COLLECTION = DATABASE["top_10"]

TOP_TEN = ('AAPL', 'MSFT', 'GOOG', 'AMZN', 'TSLA', 'BRK-A', 'FB', 'JNJ', 'UNH', 'NVDA')
TOP_TEN_NAMES = {'AAPL': 'Apple Inc.', 'MSFT': 'Microsoft', 'GOOG': 'Alphabet Inc.',
                 'AMZN': 'Amazon.com', 'TSLA': 'Tesla, Inc.', 'BRK-A': 'Berkshire Hathaway',
                 'FB': 'Meta Platforms, Inc', 'JNJ': 'Johnson & Johnson', 'UNH': 'UnitedHealth Group',
                 'NVDA': 'NVIDIA Corporation'}

ENGINE = sqlalchemy.create_engine(f'sqlite:///{PATH}bot_stocks.db')


def today_to_db():
    today_frame = yf.download(TOP_TEN, period='2d', group_by='column', rounding=True)
    today_frame = today_frame.loc[:,'Adj Close']
    today_frame.reset_index(inplace=True)

    display_frame = pd.DataFrame([])
    for symbol in TOP_TEN:
        price = today_frame.loc[1:, symbol].values[0]
        prev_price = today_frame.loc[:1, symbol].values[0]
        change = round((price - prev_price) / price * 100, 2)
        sym_frame = pd.DataFrame([{'Symbol': symbol, 'Price': price,
                                   'Change': f"{change}%" if change <= 0 else f"+{change}%"}])
        display_frame = display_frame.append(sym_frame, ignore_index=True)

    display_frame.to_sql('stocks', ENGINE, if_exists='replace', index=False)


if __name__ == "__main__":
    today_to_db()
    df = pd.read_sql('stocks', ENGINE)
    print(df)




