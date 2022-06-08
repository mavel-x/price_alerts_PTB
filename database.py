#! /home/rabbi/price_alerts_PTB/venv/bin/python3.8

import yfinance as yf
import pandas as pd
import pymongo
from bson.objectid import ObjectId
import json

PATH = '/home/rabbi/price_alerts_PTB/'
with open(f'{PATH}cred.json', 'r') as f:
    TOKEN = json.load(f)['TOKEN']

CLIENT = pymongo.MongoClient("mongodb://localhost:27017/")
DATABASE = CLIENT["prices"]
ALERTS = DATABASE["alerts"]
TOP_10 = DATABASE["top_10"]


def display_10():
    data_from_mongo = TOP_10.find()
    df = pd.DataFrame(data_from_mongo)
    print(df)
    df.drop('_id', axis=1, inplace=True)

    df.index += 1
    return df.to_markdown(tablefmt="plain", floatfmt=".2f").replace("|","\\|").replace("-","\\-").\
        replace(".","\\.").replace("+","\\+").replace("=","\\=")


def create_alert(user_id, full_name, username, symbol, target_price, current_price):
    target_price = float(target_price)
    current_price = float(current_price)
    return ALERTS.insert_one({"user_id": user_id, "full_name": full_name, "username": username,
                              'symbol': symbol.upper(), 'price': target_price,
                              'up': True if target_price > current_price else False})


def alerts_from_db(user_id):
    results = [res for res in ALERTS.find({"user_id": user_id})]
    return results


def duplicate_exists(user_id, symbol, price):
    return ALERTS.find_one({"$and": [{"user_id": user_id}, {"symbol": symbol}, {"price": price}]})


def delete_all(user_id):
    ALERTS.delete_many({'user_id': user_id})


def check_symbol(symbol):
    ticker = yf.Ticker(symbol)
    history = ticker.history(period="1d", interval="15m", rounding=True).loc[:,['Close', 'Volume']]
    if history.empty:
        return None
    price = history.iloc[-1]['Close']
    return {'symbol': symbol, 'price': price}


def delete_alert(alert_id):
    return ALERTS.delete_one({"_id": ObjectId(alert_id)})


def find_alert(alert_id):
    return ALERTS.find_one({"_id": ObjectId(alert_id)})


if __name__ == "__main__":
    print([x for x in ALERTS.find()])
