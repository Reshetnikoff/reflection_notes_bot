from telegram import Update
import os

import pandas as pd

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import logging

TOKEN = "947890754:AAEJhxrDyaQMT1tly5GuOFmHI_3gzZekl_0"

request_kwargs = {
                    'proxy_url': 'socks5h://127.0.0.1:9150/'
                }

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


class RefNotesNot():
    def __init__(self):
        self.users_file = "users.csv"
        self.data = None

        updater = Updater(token=TOKEN, request_kwargs=request_kwargs, use_context=True)
        dispatcher = updater.dispatcher

        write_handler = MessageHandler(Filters.update, self.write)
        dispatcher.add_handler(write_handler, group=0)

        start_handler = MessageHandler(Filters.update, self.start)
        dispatcher.add_handler(start_handler, group=2)

        updater.start_polling()

    def start(self, update, context):
        user = update.effective_chat

        if self.users_file in os.listdir("./"):
            users = pd.read_csv(self.users_file, sep='\t', header=None, index_col=None)
            users = users[0].values
        else:
            users = []
        if user.id not in users:
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"Welcome {user.first_name} {user.last_name}")
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"Your id is {user.id}")
            users.append(user.id)
            users = pd.DataFrame(users)
            users.to_csv(self.users_file, sep='\t', index=False, header=False)
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text="You have been registered yet!")


    def write(self, update, context):
        user = update.effective_chat
        if f"{user.id}.csv" in os.listdir("./data"):
           self.data = pd.read_csv(self.users_file, sep='\t', header=None, index_col=None)

        keyboard = [[
                        InlineKeyboardButton("Ideas", callback_data='1'),
                        InlineKeyboardButton("Notes", callback_data='2'),
                        InlineKeyboardButton("Cigarettes", callback_data='3'),
                        InlineKeyboardButton("Emotions", callback_data='3')
                     ]]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text('Please choose category:', reply_markup=reply_markup)


if __name__ == "__main__":
    bot = RefNotesNot()




