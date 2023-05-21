import requests
import schedule
import time
import pickle
from telegram import ReplyKeyboardMarkup, KeyboardButton, ParseMode

header_called = False

# Переменная для хранения адреса кошелька
pool_address = None


# Функция для сохранения адреса
def save_pool_address():
    with open("pool_address.pickle", "wb") as file:
        pickle.dump(pool_address, file)

# Функция для загрузки адреса
def load_pool_address():
    global pool_address
    try:
        with open("pool_address.pickle", "rb") as file:
            pool_address = pickle.load(file)
    except FileNotFoundError:
        pass

# Загрузка адреса при запуске программы
load_pool_address()

# Функция для получения данных о майнинге с пула
def get_mining_data():
    if pool_address:
        url = f"http://vmi761386.contaboserver.net/api/miner/{pool_address}/workers"
        response = requests.get(url)
        if response.ok:
            data = response.json()
            return data
        else:
            print(f"Error: {response.status_code} - {response.text}")
    return None

# Функция для получения статистики выплат с пула
def get_payment_statistics():
    if pool_address:
        url = f"http://vmi761386.contaboserver.net/api/miner/{pool_address}/payments"
        response = requests.get(url)
        if response.ok:
            data = response.json()
            return data
        else:
            print(f"Error: {response.status_code} - {response.text}")
    return None

# Функция для отображения данных о ферме
def format_farm_data(farm):
    global header_called
    if not header_called:
        header_called = True
        header = "<code>\n⚙️ Статистика работы ригов:</code>\n\n"
    else:
        header = ""
    name = farm["Name"]
    hashrate = round(float(farm["Hashrate"]))
    last_seen = farm["LastSeen"]
    return f"<b>{header}<code>Ферма:</code>{name}\n<code>Хэшрейт:</code>{hashrate} KH/s\n<code>Время последней шары:</code>{last_seen}\n</b>"

# Функция для отображения статистики выплат
def format_payment_statistics(statistics, limit=None):
    response = "\n<code>💸 Статистика выплат монет Ixian за последние 24 часа:</code>\n\n"
    total_sum = 0
    if limit is not None:
        statistics = statistics[:limit]
    for payment in statistics:
        timestamp = payment["TimeStamp"]
        value = round(float(payment["Value"]))
        response += f"<code>Время:</code> {timestamp}\n"
        response += f"<code>Сумма:</code>{value} Ixian\n"
        response += "---------------------------------------------\n"
        total_sum += round(value)
    response += f"<code>Общая сумма выплат:</code> {total_sum} Ixian\n"
    return response

# Функция для проверки статуса фермы и отправки сообщения в Telegram-бота
def check_farm_status(context):
    mining_data = get_mining_data()
    offline_farms = []

    # Отслеживание времени последней шары, больше 2 минут нет шар отправка в бот уведомления
    if mining_data:
        for farm in mining_data:
            last_seen = farm["LastSeen"]
            if "minutes" in last_seen:
                minutes_ago = int(last_seen.split(" ")[0])
                if minutes_ago > 2:
                    offline_farms.append(farm)

        if len(offline_farms) > 0:
            response = "<code>🔴 Фермы OFFLINE:</code>\n"
            for farm in offline_farms:
                response += format_farm_data(farm) + "\n"
            context.bot.send_message(chat_id="774390944", text=response)

    # Отслеживание хэшрейтов, если "0" отправка в бот сообщения
    for farm in mining_data:
        worker_name = farm["Name"]
        current_hashrate = round(float(farm["Hashrate"]))
        if current_hashrate == 0:
            message = f"<code>🔴 Внимание: Ферма '{worker_name}' остановилась.</code>"
            context.bot.send_message(chat_id="774390944", text=message)

    # Отправка статистики выплат
    if get_payment_statistics():
        response = format_payment_statistics(get_payment_statistics())
        context.bot.send_message(chat_id="774390944", text=response, parse_mode="HTML")


# Функция для обработки команды /start
def start(update, context):
    global pool_address
    chat_id = update.message.chat_id
    mining_data = get_mining_data()

    # Сортировка данных по имени в алфавитном порядке
    if mining_data:
        sorted_data = sorted(mining_data, key=lambda farm: farm["Name"])
    else:
        sorted_data = []

    total_hashrate = 0
    total_workers = 0
    response = ""

    for farm in sorted_data:
        response += format_farm_data(farm) + "\n"
        hashrate = round(float(farm["Hashrate"]))
        total_hashrate += hashrate
        total_workers += 1

    response += f"\n<code>Общий хешрейт:</code> {total_hashrate} kH/s"
    response += f"\n<code>Количество ферм в работе:</code> {total_workers}"

    # Создание кнопок
    button_start = KeyboardButton('⛏ Статистика работы ферм')
    button_add_address = KeyboardButton('📗 Добавить адрес')
    button_remove_address = KeyboardButton('📕 Удалить адрес')
    button_view_addresses = KeyboardButton('📖 Текущий адрес')
    button_view_payments = KeyboardButton('💸 Просмотреть выплаты')


    # Создание разметки клавиатуры ответа
    reply_markup = ReplyKeyboardMarkup(
        [[button_start, button_view_payments],[button_add_address, button_remove_address,button_view_addresses]],
        resize_keyboard=True
    )

    context.bot.send_message(chat_id=chat_id, text=response, reply_markup=reply_markup, parse_mode="HTML")

# Функция для обработки нажатия кнопки "Добавить адрес"
def add_address(update, context):
    global pool_address
    chat_id = update.message.chat_id
    message = "<code>📗 Пожалуйста,введите адрес кошелька:</code>"
    context.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")

# Функция для обработки нажатия кнопки "Удалить адрес"
def remove_address(update, context):
    global pool_address
    chat_id = update.message.chat_id
    pool_address = None
    save_pool_address()  # Save the updated pool address
    message = "<code>📕 Адрес кошелька удален.</code>"
    context.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")

 # Функция для просмотра сохраненного адреса
def view_addresses(update, context):
    global pool_address
    chat_id = update.message.chat_id

    if pool_address:
        message = f"<code>📖 Текущий сохраненный адрес:\n{pool_address}</code>"
    else:
        message = "<code>🔴 Нет сохраненного адреса.</code>"

    # Создание кнопок для сохраненных адресов
    keyboard = []
    if pool_address:
        keyboard.append([pool_address])

    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    context.bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup, parse_mode="HTML")

# Функция для просмотра статистики выплат
def view_payments(update, context):
    global pool_address
    chat_id = update.message.chat_id
    payment_statistics = get_payment_statistics()

    if payment_statistics:
        response = format_payment_statistics(payment_statistics, limit=24)  # Limit to 24 lines
        context.bot.send_message(chat_id=chat_id, text=response, parse_mode="HTML")
    else:
        message = "<code>🔴 Нет данных о выплатах.</code>"
        context.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")

# Функция для обработки ввода пользователя для добавления адреса кошелька
def handle_address_input(update, context):
    global pool_address
    chat_id = update.message.chat_id
    address = update.message.text
    pool_address = address
    save_pool_address()  # Save the updated pool address
    message = f'<code>📖 Выбран адрес:\n{pool_address}</code>'
    context.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")
    start(update, context)  # Call the start function after setting the pool address

# Функция для обработки выбора сохраненного адреса
def handle_select_address(update, context):
    chat_id = update.message.chat_id
    selected_option = int(update.message.text.split(".")[0].strip())

    global pool_address
    pool_address = address
    save_pool_address()

    message = f"<code>📖 Адрес '{address}' успешно выбран.</code>"
    context.bot.send_message(chat_id=chat_id, text=message, parse_mode="HTML")

    # Вызов check_farm_status для получения информации о майнинге и отправки сообщений

    check_farm_status(context)

    start(update, context)


# Основная функция для запуска бота
def main():
    from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

    # Инициализация бота и добавление обработчиков команд
    updater = Updater("6156741689:AAG2oxo_PU9Xnw4ArkXnVa8ekRXN5YNOwRs", use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.regex('^⛏ Статистика работы ферм$'), start))
    dp.add_handler(MessageHandler(Filters.regex('^📗 Добавить адрес$'), add_address))
    dp.add_handler(MessageHandler(Filters.regex('📕 Удалить адрес$'), remove_address))
    dp.add_handler(MessageHandler(Filters.regex('^📖 Текущий адрес$'), view_addresses))
    dp.add_handler(MessageHandler(Filters.regex('^💸 Просмотреть выплаты$'), view_payments))
    dp.add_handler(MessageHandler(Filters.text & (~Filters.command), handle_address_input))
    dp.add_handler(MessageHandler(Filters.regex('^(. Address 1)$'), handle_select_address))

    # Запуск бота
    updater.start_polling()

    # Запуск периодической задачи для проверки статуса ферм
    schedule.every(15).seconds.do(check_farm_status, context=updater)

    # Запуск периодической задачи в отдельном потоке
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    main()

# pip install python-telegram-bot==13.13
# pip install schedule
# pip install requests