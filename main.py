#! /bin/python3

import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ForceReply
from telegram.ext import (CallbackQueryHandler, CallbackContext,
                          Application, CommandHandler, ConversationHandler, MessageHandler,
                          filters)
import re
import database

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO, filename=f'{database.PATH}stock_bot_main.log'
)

TYPING_SYMBOL, TYPING_PRICE = range(2)


async def start(update: Update, context: CallbackContext) -> None:
    msg = f"Create alerts for any ticker from Yahoo Finance by sending me " \
          f"the desired ticker symbol\.\n" \
          f"If you don't know the right symbol for the ticker, you may find it " \
          f"at https://finance\.yahoo\.com/\n" \
          f"This bot was created with python\-telegram\-bot and yfinance\.\n" \
          f"Here are the top 10 stocks by market cap to get you started\.\n\n" \
          f"`{database.display_10()}`\n\n"

    keyboard = [
        [InlineKeyboardButton("Create an alert", callback_data="create")],
        [InlineKeyboardButton("Browse your alerts", callback_data="browse")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if 'BACK_TO_START' in context.user_data:
        if context.user_data['BACK_TO_START'] is True:
            await update.callback_query.edit_message_text(text=msg, reply_markup=reply_markup,
                                                          parse_mode='MarkdownV2', disable_web_page_preview=True)
            context.user_data['BACK_TO_START'] = False
            return
    await update.message.reply_text(text=msg, reply_markup=reply_markup,
                                    parse_mode='MarkdownV2', disable_web_page_preview=True)


async def button(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if query.data == 'create':
        await create_alert(update, context)

    elif query.data == 'browse':
        await fetch_alerts(update, context)

    elif query.data == 'select_alert_to_delete':
        await select_alert_to_delete(update, context)

    elif 'delete_index ' in query.data:
        await delete_confirmation(update, context)

    elif 'confirmed_delete ' in query.data:
        await confirmed_delete_one(update, context)

    elif query.data == 'delete_all':
        await delete_all(update, context)

    elif query.data == 'confirmed_delete_all':
        await confirmed_delete_all(update, context)

    elif query.data == 'back_to_browse':
        context.user_data['BACK_TO_BROWSE'] = True
        await fetch_alerts(update, context)

    elif query.data == 'back_to_start':
        context.user_data['BACK_TO_START'] = True
        await start(update, context)


async def create_alert(update: Update, context: CallbackContext):
    msg = f"To create an alert, just send me the ticker symbol you want to be alerted about (up to 6 characters)."
    await update.effective_chat.send_message(text=msg)
    return TYPING_SYMBOL


async def price_prompt(update: Update, context: CallbackContext):
    symbol = update.message.text.upper()

    if 'alerts' in context.user_data:
        if len(context.user_data['alerts']) > 14:
            await update.message.reply_text(text="You've reached the limit of active alerts for the free tier. "
                                                 "To create a new alert, please delete some of the alerts you "
                                                 "currently have.")
            return TYPING_SYMBOL

    check = database.check_symbol(symbol)
    if check is None:
        await update.message.reply_text(text="I couldn't find this symbol on Yahoo. Please try again. "
                                             "If you're having trouble, check the correct symbol on "
                                             "https://finance.yahoo.com/", disable_web_page_preview=True)
        return TYPING_SYMBOL

    context.user_data['symbol'] = symbol
    context.user_data['current_price'] = check['price']
    message = await update.message.reply_text(text=f"You've selected {symbol} (current price {check['price']}). "
                                                   f"Please enter the price for the alert or use the command "
                                                   f"/cancel.", reply_markup=ForceReply())
    await update.effective_chat.pin_message(message.message_id)
    return TYPING_PRICE


async def alert_to_db(update: Update, context: CallbackContext):
    price = update.message.text
    if not re.fullmatch('^[0-9]{1,6}.?[0-9]{0,2}$', price):
        msg = "It seems you have not entered the price correctly. " \
              "Please enter the price as a number with up to 2 decimals or " \
              "use the command /cancel."
        await update.message.reply_text(text=msg)
        return TYPING_PRICE

    price = float(price)
    context.user_data['price'] = price
    symbol = context.user_data['symbol']
    user = update.effective_user

    if not database.duplicate_exists(user.id, symbol, price):
        database.create_alert(user.id, user.full_name, user.username, symbol, price,
                              context.user_data['current_price'])

        msg = f'Alert created: {symbol} at {price}'

        keyboard = [[InlineKeyboardButton('Thanks!', callback_data='back_to_browse')]]

    else:
        msg = f'Alert for {symbol} at {price} already exists.'
        keyboard = [[InlineKeyboardButton('What?! Show me!', callback_data='back_to_browse')]]

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.effective_user.unpin_all_messages()
    await update.message.reply_text(text=msg, reply_markup=reply_markup)
    return ConversationHandler.END


async def cancel(update: Update, context: CallbackContext):
    await update.effective_user.unpin_all_messages()
    await update.message.reply_text(text='Okay, no alert was created.')
    return ConversationHandler.END


async def alerts_to_msg(alerts):
    msg = '\n'
    if isinstance(alerts, list):
        for i, alert in enumerate(alerts, start=1):
            msg += f'\n{i}. {alert["symbol"]} at {alert["price"]}'
    else:
        msg += f'\n{alerts["symbol"]} at {alerts["price"]}'
    msg += '\n\n'

    return msg


async def fetch_alerts(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    alerts = database.alerts_from_db(update.effective_user.id)
    context.user_data['alerts'] = alerts

    msg = 'You have the following alerts:'
    msg += await alerts_to_msg(alerts)

    keyboard = [[InlineKeyboardButton('Create a new alert', callback_data='create')],
                [InlineKeyboardButton('Delete one...', callback_data='select_alert_to_delete')],
                [InlineKeyboardButton('Delete all!', callback_data='delete_all')]]

    if not alerts:
        msg = "You don't have any active alerts."
        keyboard = [keyboard[0]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if 'BACK_TO_BROWSE' in context.user_data:
        if context.user_data['BACK_TO_BROWSE'] is True:
            await update.callback_query.edit_message_text(text=msg, reply_markup=reply_markup)
            context.user_data['BACK_TO_BROWSE'] = False
            return

    await query.message.reply_text(text=msg, reply_markup=reply_markup)


async def select_alert_to_delete(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    if 'alerts' not in context.user_data:
        context.user_data['alerts'] = database.alerts_from_db(update.effective_user.id)

    alerts = context.user_data['alerts']
    msg = 'Which one would you like to delete?'
    msg += await alerts_to_msg(alerts)

    buttons = [InlineKeyboardButton('- ' + str(i + 1) + ' -',
                                 callback_data=f"delete_index {str(i)}") for i, alert in enumerate(alerts)]
    rows = list()
    chunk_size = 4
    for i in range(0, len(buttons), chunk_size):
        rows.append(buttons[i:i+chunk_size])
    if len(rows[-1]) < 4:
        rows[-1].append(InlineKeyboardButton('Back', callback_data='back_to_browse'))
    else:
        rows.append([InlineKeyboardButton('Back', callback_data='back_to_browse')])

    keyboard = rows
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(msg, reply_markup=reply_markup)


async def delete_confirmation(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    alert_to_delete = int(query.data.split(" ")[1])

    keyboard = [[
        InlineKeyboardButton('Yes, delete it.', callback_data=f'confirmed_delete {alert_to_delete}')
    ], [
        InlineKeyboardButton('No, go back.', callback_data='back_to_browse')
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if 'alerts' not in context.user_data:
        context.user_data['alerts'] = database.alerts_from_db(update.effective_user.id)

    alert_for_msg = await alerts_to_msg(context.user_data["alerts"][alert_to_delete])
    msg = f'Delete alert?' \
          f'{alert_for_msg}' \

    await query.edit_message_text(msg, reply_markup=reply_markup)


async def confirmed_delete_one(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    alert_to_delete = int(query.data.split(" ")[1])

    database.delete_alert(context.user_data['alerts'][alert_to_delete]["_id"])

    msg = 'Alert deleted.'
    keyboard = [[InlineKeyboardButton('Thanks!', callback_data='back_to_browse')]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(msg, reply_markup=reply_markup)


async def delete_all(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    if 'alerts' not in context.user_data:
        context.user_data['alerts'] = database.alerts_from_db(update.effective_user.id)
    alerts = context.user_data['alerts']
    msg = 'Delete all your alerts?'
    msg += await alerts_to_msg(alerts)

    keyboard = [[InlineKeyboardButton('Yes, delete all my alerts.', callback_data='confirmed_delete_all')],
                [InlineKeyboardButton('No, go back!', callback_data='back_to_browse')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(msg, reply_markup=reply_markup)


async def confirmed_delete_all(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()

    database.delete_all(update.effective_user.id)
    msg = 'All alerts have been deleted.'
    keyboard = [[InlineKeyboardButton('Thanks!', callback_data='back_to_start')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(msg, reply_markup=reply_markup)


async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Press /start to use this bot or send me the symbol for the ticker "
                                    "you would like to get alerted about (up to 6 characters).")


def main() -> None:
    application = Application.builder().token(database.TOKEN).build()

    create_alert_handler = ConversationHandler(
        entry_points=[CommandHandler("create", create_alert),
                      MessageHandler(filters.TEXT & filters.Regex('^[a-zA-Z.-]{1,6}$'), callback=price_prompt)],
        states={
            TYPING_SYMBOL: [
                MessageHandler(filters.TEXT & filters.Regex('^[a-zA-Z.-]{1,6}$'), callback=price_prompt)
            ],
            TYPING_PRICE: [
                MessageHandler(filters.TEXT & (~ filters.COMMAND), callback=alert_to_db)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel), ]
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(create_alert_handler)
    application.add_handler(MessageHandler(filters.TEXT & (~ filters.Regex('^[a-zA-Z.-]{1,6}$')), create_alert))

    application.run_polling()


if __name__ == "__main__":
    main()
