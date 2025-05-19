import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ConversationHandler

# Состояния
NAME, RATING, COMMENT, ADMIN_PASSWORD = range(4)

# Подключение к БД
conn = sqlite3.connect("data.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS reviews (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        rating INTEGER,
        comment TEXT
    )
''')
conn.commit()

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 Написать отзыв", callback_data='write')],
        [InlineKeyboardButton("📋 Посмотреть отзывы", callback_data='view')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Здравствуйте.", reply_markup=reply_markup)

# Обработка кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'write':
        await query.message.reply_text("Пожалуйста, введите ваше имя:")
        return NAME

    elif query.data == 'view':
        cursor.execute("SELECT * FROM reviews")
        reviews = cursor.fetchall()
        if reviews:
            msg = ""
            for r in reviews:
                msg += f"{r[0]}. Имя: {r[1]} | Оценка: {r[2]} | Отзыв: {r[3]}\n"
        else:
            msg = "Пока нет отзывов."
        await query.message.reply_text(msg)
        return ConversationHandler.END

    elif query.data == 'delete_all':
        cursor.execute("DELETE FROM reviews")
        conn.commit()
        await query.message.reply_text("Все отзывы были удалены.")
        return ConversationHandler.END

# Имя
async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    context.user_data['name'] = name

    if name.lower() == "админ":
        await update.message.reply_text("Введите пароль:")
        return ADMIN_PASSWORD

    # Обычный пользователь
    buttons = [[KeyboardButton(str(i))] for i in range(1, 6)]
    await update.message.reply_text("Оцените, пожалуйста, от 1 до 5:",
        reply_markup=ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
    )
    return RATING

# Пароль админа
async def check_admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text.strip()
    if password == "0808":
        keyboard = [[InlineKeyboardButton("❌ Удалить все отзывы", callback_data='delete_all')]]
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Добро пожаловать, админ!", reply_markup=markup)
    else:
        await update.message.reply_text("Неверный пароль.")
    return ConversationHandler.END

# Оценка
async def get_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['rating'] = int(update.message.text)
    await update.message.reply_text("Пожалуйста, оставьте отзыв:")
    return COMMENT

# Отзыв
async def get_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data['name']
    rating = context.user_data['rating']
    comment = update.message.text

    cursor.execute("INSERT INTO reviews (name, rating, comment) VALUES (?, ?, ?)", (name, rating, comment))
    conn.commit()

    await update.message.reply_text("Спасибо за оценку!")

    keyboard = [
        [InlineKeyboardButton("📝 Написать отзыв", callback_data='write')],
        [InlineKeyboardButton("📋 Посмотреть отзывы", callback_data='view')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Что вы хотите сделать дальше?", reply_markup=reply_markup)

    return ConversationHandler.END

# Отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено.")
    return ConversationHandler.END

# Запуск
if __name__ == "__main__":
    TOKEN = "8052836652:AAF1reVL92MM5QMH_DrVEk-5p-6EA7KN0hg"
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            ADMIN_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_admin_password)],
            RATING: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_rating)],
            COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_comment)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)

    print("Бот запущен...")
    app.run_polling()
