#! /home/rabbi/price_alerts_PTB/venv/bin/python3.8

import yfinance as yf
import pandas as pd

from database import DATABASE, PATH
TOP_10 = DATABASE["top_10"]

TOP_STOCKS = ('AAPL', 'MSFT', 'GOOG', 'AMZN', 'TSLA', 'BRK-A', 'FB', 'JNJ', 'UNH', 'NVDA')


def today_to_mongo():
    TOP_10.drop()

    today_frame = yf.download(TOP_STOCKS, period='2d', group_by='column', rounding=True)
    today_frame = today_frame.loc[:, 'Adj Close']
    today_frame.reset_index(inplace=True)

    display_frame = pd.DataFrame([])
    for symbol in TOP_STOCKS:
        price = today_frame.loc[1:, symbol].values[0]
        prev_price = today_frame.loc[:1, symbol].values[0]
        change = round((price - prev_price) / price * 100, 2)
        sym_frame = pd.DataFrame([{'Symbol': symbol, 'Price': price,
                                   'Change': f"{change}%" if change <= 0 else f"+{change}%"}])
        display_frame = display_frame.append(sym_frame, ignore_index=True)

    data_dict = display_frame.to_dict(orient='records')
    TOP_10.insert_many(data_dict)


if __name__ == "__main__":
    today_to_mongo()
    data_from_mongo = TOP_10.find()
    df = pd.DataFrame(data_from_mongo)
    df.drop('_id', axis=1, inplace=True)
    print(df)




