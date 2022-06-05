#! /bin/python3.8

import yfinance as yf
import pandas as pd
import pymongo
from bson.objectid import ObjectId
import json

PATH = ''
with open(f'{PATH}cred.json', 'r') as f:
    TOKEN = json.load(f)['TOKEN']

CLIENT = pymongo.MongoClient("mongodb://localhost:27017/")
DATABASE = CLIENT["test_users"]
COLLECTION = DATABASE["test_alerts"]


def display_10():
    frame = pd.read_sql('stocks', 'sqlite:///{PATH}bot_stocks.db')
    frame.index += 1
    return frame.to_markdown(tablefmt="plain", floatfmt=".2f").replace("|","\\|").replace("-","\\-").\
        replace(".","\\.").replace("+","\\+").replace("=","\\=")
    # optionally add 24 h graph


def create_alert(user_id, full_name, username, symbol, target_price, current_price):
    target_price = float(target_price)
    current_price = float(current_price)
    return COLLECTION.insert_one({"user_id": user_id, "full_name": full_name, "username": username,
                                  'symbol': symbol.upper(), 'price': target_price,
                                  'up': True if target_price > current_price else False})


def alerts_from_db(user_id):
    results = [res for res in COLLECTION.find({"user_id": user_id})]
    return results


def duplicate_exists(user_id, symbol, price):
    return COLLECTION.find_one({"$and": [{"user_id": user_id}, {"symbol": symbol}, {"price": price}]})


def delete_all(user_id):
    COLLECTION.delete_many({'user': user_id})


def check_symbol(symbol):
    ticker = yf.Ticker(symbol)
    history = ticker.history(period="1d", interval="15m", rounding=True).loc[:,['Close', 'Volume']]
    if history.empty:
        return None
    price = history.iloc[-1]['Close']
    return {'symbol': symbol, 'price': price}


def delete_alert(alert_id):
    return COLLECTION.delete_one({"_id": ObjectId(alert_id)})


def find_alert(alert_id):
    return COLLECTION.find_one({"_id": ObjectId(alert_id)})


if __name__ == "__main__":
    print([x for x in COLLECTION.find()])
