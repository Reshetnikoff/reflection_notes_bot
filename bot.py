import os
import time

import pandas as pd
import numpy as np

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, ConversationHandler, \
    MessageHandler, Filters
import logging

import config

# params for config
TOKEN = config.config["TOKEN"]

request_kwargs = {
    'proxy_url': f'socks5h://{config.config["ADRESS"]}:{config.config["PORT"]}/',

    'urllib3_proxy_kwargs': {
        'username': config.config["username"],
        'password': config.config["password"],
        }
}

# CONSTANT
MIN = 60
HOURS = 24
SEC = 60

conv_states = {
    "CHOOSING": 1,
    "TYPING": 2,
    "EDIT": 3,
    "EXIST_TASKS": 4,
    "CHOOSING_ANSWER": 5,
    "EDIT_EXIST_TASKS": 6,
    "TYPING_TWO": 7
}

# Logging (need to config)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


class RefNotesNot():
    def __init__(self):
        self.users_file = "users.csv"
        self.data_file = "./data"

        self.edit = False

        self.button_reply = dict()
        self.save_text = dict()
        self.subcat = dict()

        self.time_for_tasks = None
        self.time_for_results = None

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
                conv_states["TYPING"]: [MessageHandler(Filters.text, self.process_tasks_reply)],
                conv_states["EDIT"]: [CallbackQueryHandler(self.edit_tasks)],
                conv_states["EDIT_EXIST_TASKS"]: [CallbackQueryHandler(self.edit_exist_tasks)]
            },

            fallbacks=[CommandHandler('cancel', self.cancel)]

        )

        load_tasks_handler = ConversationHandler(
            entry_points=[CommandHandler("load_tasks", self.load_table)],

            states={
                conv_states["TYPING"]: [MessageHandler(Filters.text,
                                                       lambda x, y: self.process_load_table(x, y, category='tasks'))],
            },

            fallbacks=[CommandHandler('cancel', self.cancel)]

        )

        load_ref_handler = ConversationHandler(
            entry_points=[CommandHandler("load_reflection", self.load_table)],

            states={
                conv_states["TYPING"]: [MessageHandler(Filters.all,
                                                       lambda x, y: self.process_load_table(x, y,
                                                                                            category='reflection'))],
            },

            fallbacks=[CommandHandler('cancel', self.cancel)]

        )

        load_res_handler = ConversationHandler(
            entry_points=[CommandHandler("load_results", self.load_table)],

            states={
                conv_states["TYPING"]: [MessageHandler(Filters.all,
                                                       lambda x, y: self.process_load_table(x, y,
                                                                                            category='results'))],
            },

            fallbacks=[CommandHandler('cancel', self.cancel)]

        )

        write_results_handler = ConversationHandler(
            entry_points=[CommandHandler("write_results", self.write_results)],

            states={
                conv_states["EDIT"]: [CallbackQueryHandler(self.edit_results)],
                conv_states["TYPING"]: [MessageHandler(Filters.text, self.typing_result)],
                conv_states["CHOOSING"]: [CallbackQueryHandler(self.choose_results)],
                conv_states["EXIST_TASKS"]: [CallbackQueryHandler(self.answer_to_edit_results)]
            },

            fallbacks=[CommandHandler('cancel', self.cancel)]

        )

        dispatcher.add_handler(start_handler, group=0)
        dispatcher.add_handler(write_tasks_handler, group=0)
        dispatcher.add_handler(load_tasks_handler, group=0)
        dispatcher.add_handler(load_ref_handler, group=0)
        dispatcher.add_handler(write_reflection_handler, group=1)
        dispatcher.add_handler(write_results_handler, group=1)
        dispatcher.add_handler(load_res_handler, group=1)

        updater.start_polling()

    def start(self, update, context):
        chat_id, user_id = self.get_id(update)

        if self.users_file in os.listdir("./"):
            users = pd.read_csv(self.users_file, sep='\t', header=0, index_col=None)
        else:
            users = pd.DataFrame(columns=['users'])

        if user_id not in users:
            user = update.effective_user
            context.bot.send_message(chat_id=update.effective_chat.id,
                                     text=f"Welcome {user.first_name} {user.last_name}")
            users = users.append({"users" : user_id}, ignore_index=True)
            data = pd.DataFrame(columns=["date", "cat", "subcat", "text"])
            users.to_csv(self.users_file, sep='\t', index=False, header=True)
            data.to_csv(f"{self.data_file}/{user_id}.csv", sep='\t', header=True, index=True)
        else:
            print(user_id)
            context.bot.send_message(chat_id=chat_id, text="You have been registered yet!")

    '''
        Function for manipulate dates
    '''

    def load_data(self, update):
        chat_id, user_id = self.get_id(update)

        data = pd.read_csv(f"{self.data_file}/{user_id}.csv", sep='\t', header=0, index_col=0)
        data = data.astype({"date": np.int32})
        return data

    def save_data(self, data, update):
        chat_id, user_id = self.get_id(update)

        data.to_csv(f"{self.data_file}/{user_id}.csv", sep='\t', header=True, index=True)

    def save_temp_data(self, data, update):
        chat_id, user_id = self.get_id(update)

        data.to_csv(f"{self.data_file}/{user_id}_temp.csv", sep='\t', header=True, index=True)

    def append_data(self, data, text, cat, subcat):
        date = int(time.time())
        data = data.append({"date": date, "cat": cat, "subcat": subcat, "text": text},
                           ignore_index=True)
        return data

    def get_last_note(self, data, cat):
        if len(data[data['cat'] == cat]) == 0:
            return []
        else:
            return data[data['cat'] == cat].iloc[-1]

    def send_temp_file(self, update):
        chat_id, user_id = self.get_id(update)
        
        f = open(f"{self.data_file}/{user_id}_temp.csv", 'rb')
        self.bot.send_document(chat_id=chat_id, document=f)
        f.close()

    '''
        /write_results function
    '''

    def write_results(self, update, context):
        chat_id, user_id = self.get_id(update)

        data = self.load_data(update)

        if len(data[data['cat'] == 'tasks']) == 0:
            self.bot.send_message(chat_id=chat_id,
                                  text='You have not written anything in your data!')
            return ConversationHandler.END
        else:
            last_tasks = self.get_last_note(data, 'tasks')
            last_result = self.get_last_note(data, 'results')
            text = last_tasks["text"]
            date = time.ctime(last_tasks['date'])
            if len(last_result) > 0:
                last_results = self.get_last_note(data, 'results')
                last_results_index = data[data["cat"] == 'tasks'].index[-1]
                if int(last_results['subcat']) == last_results_index:
                    self.bot.send_message(chat_id=chat_id, text=f"You already write results")
                    reply_markup = self.yes_no_buttom()
                    update.message.reply_text('Do you want to edit it?', reply_markup=reply_markup)
                    return conv_states["EXIST_TASKS"]

            self.bot.send_message(chat_id=chat_id,
                                  text=f'Your last list of tasks:\n{text}\n{date}')
            reply_markup = self.yes_no_buttom()

            update.message.reply_text('Do you want to report result?', reply_markup=reply_markup)

            return conv_states['CHOOSING']

    def answer_to_edit_results(self, update, context):
        chat_id, user_id = self.get_id(update)

        if update.callback_query.data == '1':
            self.bot.send_message(chat_id=chat_id, text=f"Ok, now you can typing")
            self.edit = True
            return conv_states["TYPING"]
        else:

            self.bot.send_message(chat_id=chat_id, text=f"Ok, note isn't changed")

            return ConversationHandler.END

    def choose_results(self, update, context):
        chat_id, user_id = self.get_id(update)

        if update.callback_query.data == '1':
            self.bot.send_message(chat_id=chat_id, text=f"Ok, now you can typing")
            self.bot.send_message(chat_id=chat_id, text=f"Please, do it in format like you wrote tasks")
            return conv_states["TYPING"]
        else:
            self.bot.send_message(chat_id=chat_id, text=f"Ok, cancel of operation")
            return ConversationHandler.END

    def typing_result(self, update, context):
        chat_id, user_id = self.get_id(update)

        self.save_text[user_id] = update.message.text

        data = self.load_data(update)

        last_tasks = self.get_last_note(data, 'tasks')
        text = last_tasks["text"]

        if len(text.split("\n")) == len(self.save_text[user_id].split("\n")):
            reply_markup = self.yes_no_buttom()

            update.message.reply_text('Do you want to edit?', reply_markup=reply_markup)
            return conv_states['EDIT']
        else:
            self.bot.send_message(chat_id=chat_id,
                                  text=f"Number of result is not equal number of tasks!\nDo it again:")
            return conv_states["TYPING"]

    def edit_results(self, update, context):
        chat_id, user_id = self.get_id(update)

        if update.callback_query.data == '1':
            self.bot.send_message(chat_id=chat_id, text=f"Ok, now you can typing")
            return conv_states["TYPING"]
        else:
            data = self.load_data(update)
            last_tasks_index = data[data["cat"] == 'tasks'].index[-1]
            last_results_index = data[data["cat"] == 'tasks'].index[-1]
            if self.edit == True:
                data = data[data.index != last_results_index]
                self.edit = False

            data = self.append_data(data=data, cat="results", subcat=last_tasks_index,
                                    text=self.save_text[user_id])

            self.save_data(data, update)

            self.bot.send_message(chat_id=chat_id, text=f"Good! Your result is saved")

            return ConversationHandler.END

    '''
        /load_table function
    '''

    def load_table(self, update, context):
        chat_id, user_id = self.get_id(update)

        self.bot.send_message(chat_id=chat_id,
                              text='Ok, how many days do you want upload?. If you want to cancel type /cancel')
        return conv_states["TYPING"]

    def process_load_table(self, update, context, category):
        chat_id, user_id = self.get_id(update)

        self.save_text[user_id] = update.message.text

        if not (self.save_text[user_id].isdigit()):
            self.bot.send_message(chat_id=chat_id,
                                  text='It is not number. Please try again!')
            return conv_states["TYPING"]
        else:
            data = self.load_data(update)
            data = data[data["cat"] == category]
            last_time = int(time.time()) - int(self.save_text[user_id]) * MIN * HOURS * SEC
            data = data[data['date'] > last_time]

            self.save_temp_data(data, update)

            self.send_temp_file(update)

            return ConversationHandler.END

    '''
        /write_tasks function
    '''

    def write_tasks(self, update, context):
        chat_id, user_id = self.get_id(update)

        data = self.load_data(update)

        last_note = self.get_last_note(data, 'tasks')
        if len(last_note) == 0:
            self.bot.send_message(chat_id,
                                  text='Start write reflection. If you want to cancel type /cancel')
            self.bot.send_message(chat_id,
                                  text='Could you /task type in format: \n1) Task #1\n2) Task  #2\n3)...')

            return conv_states["TYPING"]

        date_note = time.ctime(int(last_note['date']))
        date_now = time.ctime(time.time())
        # Тут может быть ошибка из-за того что долго не изменялись записи

        if date_now.split(" ")[2] == date_note.split(" ")[2]:
            self.save_text[user_id] = last_note["text"]
            self.bot.send_message(chat_id=chat_id, text='You already have note today')
            self.bot.send_message(chat_id=chat_id,
                                  text=f'''You note is:\n{self.save_text[user_id]}\nAnd date is {date_note}''')

            reply_markup = self.yes_no_buttom()

            update.message.reply_text('Do you want to edit exists tasks?', reply_markup=reply_markup)

            return conv_states["EDIT_EXIST_TASKS"]
        else:
            self.bot.send_message(chat_id=chat_id,
                                  text='Start write reflection. If you want to cancel type /cancel')
            self.bot.send_message(chat_id=chat_id,
                                  text='Could you task type in format: \n1) Task #1\n2) Task  #2\n3)...')

            return conv_states["TYPING"]

    def edit_exist_tasks(self, update, context):
        chat_id, user_id = self.get_id(update)

        if update.callback_query.data == '1':
            self.bot.send_message(chat_id=chat_id, text=f"Ok, now you can typing")
            self.edit = True
            return conv_states["TYPING"]
        else:

            self.bot.send_message(chat_id=chat_id, text=f"Ok, note isn't changed")

            return ConversationHandler.END

    def process_tasks_reply(self, update, context):
        chat_id, user_id = self.get_id(update)

        self.save_text[user_id] = update.message.text

        self.bot.send_message(chat_id=chat_id, text=f'You note is:\n{self.save_text[user_id]}')

        reply_markup = self.yes_no_buttom()

        update.message.reply_text('Do you want to edit?', reply_markup=reply_markup)

        return conv_states["EDIT"]

    def edit_tasks(self, update, text):
        chat_id, user_id = self.get_id(update)

        if update.callback_query.data == '1':
            self.bot.send_message(chat_id=chat_id, text=f"Ok, you could typing:")
            return conv_states["TYPING"]
        else:
            data = self.load_data(update)
            if self.edit == True:
                data = data[data.index != (data[data["cat"] == 'tasks'].index[-1])]
                self.edit = False

            data = self.append_data(data=data, text=self.save_text[user_id], cat='tasks', subcat='None')
            self.save_data(data, update)

            self.bot.send_message(chat_id=chat_id, text=f"Good! Your tasks is saved")

            return ConversationHandler.END

    '''
        /write_reflection function
    '''

    def write_reflection(self, update, context):
        chat_id, user_id = self.get_id(update)

        self.bot.send_message(chat_id=chat_id, text='Start write reflection. If you want to cancel type /cancel')

        keyboard = [[
            InlineKeyboardButton("Notes", callback_data='Notes'),
            InlineKeyboardButton("Emotions", callback_data='Emotions'),
            InlineKeyboardButton("Emotions", callback_data='Notes')
        ]]

        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text('Please choose category:', reply_markup=reply_markup)

        return conv_states["CHOOSING"]

    def write_your_choose(self, update, context):
        chat_id, user_id = self.get_id(update)

        self.subcat[user_id] = update.callback_query.data

        self.bot.send_message(chat_id=chat_id, text=f"Type your notes:")

        return conv_states["TYPING"]

    def process_reflection_reply(self, update, context):
        chat_id, user_id = self.get_id(update)

        self.save_text[user_id] = update.message.text

        self.bot.send_message(chat_id=chat_id, text=f'You note is:\n{self.save_text[user_id]}')

        reply_markup = self.yes_no_buttom()

        update.message.reply_text('Do you want to edit?', reply_markup=reply_markup)

        return conv_states["EDIT"]

    def edit_ref(self, update, context):
        chat_id, user_id = self.get_id(update)

        if update.callback_query.data == '1':
            self.bot.send_message(chat_id=chat_id, text=f"Ok, you could typing:")
            return conv_states["TYPING"]
        else:
            data = self.load_data(update)
            date = int(time.time())
            data = self.append_data(data=data, text=self.save_text[user_id], cat='reflection',
                                    subcat=self.subcat[user_id])
            self.save_data(data, update)

            self.bot.send_message(chat_id=chat_id, text=f"Good! Your tasks is saved")

            return ConversationHandler.END

    '''
        support function
    '''

    def cancel(self, update, context):
        chat_id, user_id = self.get_id(update)

        self.bot.send_message(chat_id=chat_id, text='You cancel typing!')

        return ConversationHandler.END

    def yes_no_buttom(self):
        keyboard = [[
            InlineKeyboardButton("Yes", callback_data='1'),
            InlineKeyboardButton("No", callback_data='2')
        ]]

        reply_markup = InlineKeyboardMarkup(keyboard)

        return reply_markup

    def get_id(self, update):
        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        return chat_id, user_id

if __name__ == "__main__":
    bot = RefNotesNot()
