import os
import time

import pandas as pd
import numpy as np

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler, \
                            MessageHandler, Filters
import logging

TOKEN = "947890754:AAEJhxrDyaQMT1tly5GuOFmHI_3gzZekl_0"
MIN = 60
HOURS = 24
SEC = 60

request_kwargs = {
                    'proxy_url': 'socks5h://127.0.0.1:9150/'
                }

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

conv_states = {
    "CHOOSING": 1,
    "TYPING": 2,
    "EDIT": 3
}

class RefNotesNot():
    def __init__(self):
        self.users_file = "users.csv"
        self.data = "./data"
        self.bot = None

        self.button_reply = dict()
        self.save_text = dict()
        self.subcat = dict()

        updater = Updater(token=TOKEN, request_kwargs=request_kwargs, use_context=True)
        dispatcher = updater.dispatcher

        self.bot = dispatcher.bot

        start_handler = CommandHandler(command="start",
                                       filters=Filters.update,
                                       callback=self.start)

        write_reflection_handler = ConversationHandler(
            entry_points=[CommandHandler("write_reflection", self.write_reflection)],

            states={
                conv_states["CHOOSING"]: [CallbackQueryHandler(self.write_your_choose)],
                conv_states["TYPING"]: [MessageHandler(Filters.all, self.process_reflection_reply)],
                conv_states["EDIT"]: [CallbackQueryHandler(self.edit_ref)]
            },

            fallbacks=[CommandHandler('cancel', self.cancel)]

        )

        write_tasks_handler = ConversationHandler(
            entry_points=[CommandHandler("write_tasks", self.write_tasks)],

            states={
                conv_states["TYPING"]: [MessageHandler(Filters.all, self.process_tasks_reply)],
                conv_states["EDIT"]: [CallbackQueryHandler(self.edit_tasks)]
            },

            fallbacks=[CommandHandler('cancel', self.cancel)]

        )

        load_tasks_handler = ConversationHandler(
            entry_points=[CommandHandler("load_tasks", self.load_data)],

            states={
                conv_states["TYPING"]: [MessageHandler(Filters.all,
                                                       lambda x, y: self.process_load_data(x, y, category='tasks'))],
            },

            fallbacks=[CommandHandler('cancel', self.cancel)]

        )

        load_ref_handler = ConversationHandler(
            entry_points=[CommandHandler("load_reflection", self.load_data)],

            states={
                conv_states["TYPING"]: [MessageHandler(Filters.all,
                                                       lambda x, y: self.process_load_data(x, y,category='reflection'))],
            },

            fallbacks=[CommandHandler('cancel', self.cancel)]

        )

        dispatcher.add_handler(start_handler, group=0)
        dispatcher.add_handler(write_tasks_handler, group=0)
        dispatcher.add_handler(load_tasks_handler, group=0)
        dispatcher.add_handler(load_ref_handler, group=0)
        dispatcher.add_handler(write_reflection_handler, group=1)

        updater.start_polling()

    def load_data(self, update, context):
        chat_id = update.effective_chat.id
        self.bot.send_message(chat_id=chat_id,
                              text='Ok, how many days do you want upload?. If you want to cancel type /cancel')
        return conv_states["TYPING"]

    def process_load_data(self, update, context, category):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        self.save_text[user_id] = update.message.text

        if not (self.save_text[user_id].isdigit()):
            self.bot.send_message(chat_id=chat_id,
                                  text='It is not number. Please try again!')
            return conv_states["TYPING"]
        else:
            data = pd.read_csv(f"{self.data}/{user_id}.csv", sep='\t', header=0, index_col=0)
            data = data.astype({"date": np.int32})
            data = data[data["cat"] == category]
            last_time = int(time.time()) - int(self.save_text[user_id]) * MIN * HOURS * SEC
            data = data[data['date'] > last_time]
            data.to_csv(f"{self.data}/{user_id}_temp.csv", sep='\t', header=True, index=True)

            f = open(f"{self.data}/{user_id}_temp.csv", 'rb')
            self.bot.send_document(chat_id=chat_id, document=f)
            f.close()

            return ConversationHandler.END

    def start(self, update, context):
        user = update.effective_user

        if self.users_file in os.listdir("./"):
            users = pd.read_csv(self.users_file, sep='\t', header=None, index_col=None)
            users = users[0].values
        else:
            users = []
        if user.id not in users:
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"Welcome {user.first_name} {user.last_name}")
            users.append(user.id)
            users = pd.DataFrame(users)
            data = pd.DataFrame(columns=["date", "cat", "subcat", "text"])
            users.to_csv(self.users_file, sep='\t', index=False, header=False)
            data.to_csv(f"{self.data}/{user.id}.csv", sep='\t', header=True, index=True)
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text="You have been registered yet!")

    def write_tasks(self, update, context):
        chat_id = update.effective_chat.id
        self.bot.send_message(chat_id=chat_id, text='Start write reflection. If you want to cancel type /cancel')
        self.bot.send_message(chat_id=chat_id, text='Could you task type in format: \n1) Task #1\n2) Task  #2\n3)...')

        return conv_states["TYPING"]

    def process_tasks_reply(self, update, context):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        self.save_text[user_id] = update.message.text

        chat_id = update.effective_chat.id
        self.bot.send_message(chat_id=chat_id, text=f'You note is:\n{self.save_text[user_id]}')

        keyboard = [[
            InlineKeyboardButton("Yes", callback_data='1'),
            InlineKeyboardButton("No", callback_data='2')
        ]]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text('Do you want to edit?', reply_markup=reply_markup)

        return conv_states["EDIT"]

    def edit_tasks(self, update, text):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        print(update.callback_query.data)
        if update.callback_query.data == '1':
            self.bot.send_message(chat_id=chat_id, text=f"Ok, you could typing:")
            return conv_states["TYPING"]
        else:
            data = pd.read_csv(f"{self.data}/{user_id}.csv", sep='\t', header=0, index_col=0)
            date = int(time.time())
            data = data.append({"date": date, "cat": "tasks", "subcat": "None", "text": self.save_text[user_id]},
                                ignore_index=True)

            data.to_csv(f"{self.data}/{user_id}.csv", sep='\t', header=True, index=True)

            self.bot.send_message(chat_id=chat_id, text=f"Good! Your tasks is saved")

            return ConversationHandler.END


    def write_reflection(self, update, context):
        chat_id = update.effective_chat.id
        self.bot.send_message(chat_id=chat_id, text='Start write reflection. If you want to cancel type /cancel')

        keyboard = [[
                        InlineKeyboardButton("Ideas", callback_data='Ideas'),
                        InlineKeyboardButton("Notes", callback_data='Notes'),
                        InlineKeyboardButton("Emotions", callback_data='Emotions')
                     ]]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text('Please choose category:', reply_markup=reply_markup)

        return conv_states["CHOOSING"]

    def write_your_choose(self, update, context):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        self.subcat[user_id] = update.callback_query.data

        self.bot.send_message(chat_id=chat_id, text=f"Type your notes:")

        return conv_states["TYPING"]

    def process_reflection_reply(self, update, context):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        self.save_text[user_id] = update.message.text

        self.bot.send_message(chat_id=chat_id, text=f'You note is:\n{self.save_text[user_id]}')

        keyboard = [[
            InlineKeyboardButton("Yes", callback_data='1'),
            InlineKeyboardButton("No", callback_data='2')
        ]]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text('Do you want to edit?', reply_markup=reply_markup)

        return conv_states["EDIT"]


    def edit_ref(self, update, context):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id

        if update.callback_query.data == '1':
            self.bot.send_message(chat_id=chat_id, text=f"Ok, you could typing:")
            return conv_states["TYPING"]
        else:
            data = pd.read_csv(f"{self.data}/{user_id}.csv", sep='\t', header=0, index_col=0)
            date = int(time.time())
            data = data.append({"date": date, "cat": "reflection", "subcat": self.subcat[user_id],
                                "text": self.save_text[user_id]}, ignore_index=True)

            data.to_csv(f"{self.data}/{user_id}.csv", sep='\t', header=True, index=True)

            self.bot.send_message(chat_id=chat_id, text=f"Good! Your tasks is saved")

            return ConversationHandler.END

    def cancel(self, update, context):
        chat_id = update.effective_chat.id

        self.bot.send_message(chat_id=chat_id, text='You cancel typing!')

        return ConversationHandler.END


if __name__ == "__main__":
    bot = RefNotesNot()


