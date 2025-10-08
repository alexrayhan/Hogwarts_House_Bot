import random
import aiosqlite
import asyncio
import nest_asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# ---------------------- PATCH LOOP ----------------------
nest_asyncio.apply()

# ---------------------- CONFIG ----------------------
TOKEN = "8422860882:AAG6pvbFbJ3A0qdMjMX-xhg9sxiBbS5p8FI"  # <-- Replace with your bot token
HOUSES = ["Gryffindor 🦁", "Ravenclaw 🦅", "Hufflepuff 🦡", "Slytherin 🐍"]
ADMINS = [123456789]  # <-- Replace with your Telegram ID

muted_users = set()
banned_users = set()

# ---------------------- DATABASE ----------------------
async def init_db():
    async with aiosqlite.connect("hogwarts.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                house TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS points (
                house TEXT PRIMARY KEY,
                score INTEGER
            )
        """)
        for h in HOUSES:
            await db.execute("INSERT OR IGNORE INTO points (house, score) VALUES (?, ?)", (h, 0))
        await db.commit()

# ---------------------- COMMANDS ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"Welcome, {user.first_name}! 🪄\nUse /sortme to get your Hogwarts House or /points to check scores!"
    )

async def sortme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chosen_house = random.choice(HOUSES)
    async with aiosqlite.connect("hogwarts.db") as db:
        await db.execute(
            "INSERT OR REPLACE INTO users (user_id, username, house) VALUES (?, ?, ?)",
            (user.id, user.username or user.first_name, chosen_house)
        )
        await db.commit()
    spark = random.choice(["✨", "⚡", "🪄", "🌟"])
    await update.message.reply_text(
        f"🪄 The Sorting Hat has spoken!\nYou’ve been sorted into *{chosen_house}* {spark}!",
        parse_mode="Markdown"
    )

async def points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with aiosqlite.connect("hogwarts.db") as db:
        async with db.execute("SELECT house, score FROM points ORDER BY score DESC") as cursor:
            rows = await cursor.fetchall()
    message = "🏆 *Current House Points:*\n\n"
    for h, s in rows:
        spark = random.choice(["✨", "⚡", "🪄", "🌟"])
        message += f"{spark} {h}: {s} points {spark}\n"
    await update.message.reply_text(message, parse_mode="Markdown")

# ---------------------- QUIZ ----------------------
QUIZ_QUESTIONS = [
    {"question": "Which blood group is universal donor?", "options": ["A", "B", "AB", "O"], "answer": "O", "points": 10},
    {"question": "Which vitamin deficiency causes scurvy?", "options": ["Vitamin A", "Vitamin B12", "Vitamin C", "Vitamin D"], "answer": "Vitamin C", "points": 10},
]

async def quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in muted_users or user.id in banned_users:
        return
    q = random.choice(QUIZ_QUESTIONS)
    options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(q["options"])])
    await update.message.reply_text(f"❓ {q['question']}\n\n{options_text}\n\nReply with the number of the correct answer.")
    context.chat_data["current_quiz"] = q

async def answer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id in muted_users or user.id in banned_users:
        return
    if "current_quiz" not in context.chat_data:
        return
    q = context.chat_data["current_quiz"]
    text = update.message.text.strip()
    try:
        choice = int(text)
        async with aiosqlite.connect("hogwarts.db") as db:
            async with db.execute("SELECT house FROM users WHERE user_id = ?", (user.id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    await update.message.reply_text("❌ You are not sorted yet. Use /sortme first!")
                    return
                house = row[0]
                if q["options"][choice-1] == q["answer"]:
                    await db.execute("UPDATE points SET score = score + ? WHERE house = ?", (q["points"], house))
                    await db.commit()
                    fireworks = " ".join(random.choices(["🎆", "🎇", "✨", "🌟"], k=5))
                    await update.message.reply_text(f"✅ Correct! {q['points']} points to {house}! {fireworks}")
                else:
                    await update.message.reply_text(f"❌ Incorrect! The correct answer was {q['answer']}.")
    except:
        await update.message.reply_text("⚠️ Reply with the number of your choice!")
    finally:
        context.chat_data.pop("current_quiz", None)

# ---------------------- ADMIN POINTS ----------------------
async def addpoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addpoints <house> <points>")
        return
    house = " ".join(context.args[:-1])
    try:
        points = int(context.args[-1])
    except ValueError:
        await update.message.reply_text("⚠️ Points must be a number!")
        return
    async with aiosqlite.connect("hogwarts.db") as db:
        await db.execute("UPDATE points SET score = score + ? WHERE house = ?", (points, house))
        await db.commit()
    await update.message.reply_text(f"✅ Added {points} points to {house}!")

async def deductpoints(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS:
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /deductpoints <house> <points>")
        return
    house = " ".join(context.args[:-1])
    try:
        points = int(context.args[-1])
    except ValueError:
        await update.message.reply_text("⚠️ Points must be a number!")
        return
    async with aiosqlite.connect("hogwarts.db") as db:
        await db.execute("UPDATE points SET score = score - ? WHERE house = ?", (points, house))
        await db.commit()
    await update.message.reply_text(f"⚠️ Deducted {points} points from {house}!")

# ---------------------- ADMIN SPELLS ----------------------
async def expelliarmus(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    if not context.args: return
    user_id = int(context.args[0])
    muted_users.add(user_id)
    await update.message.reply_text(f"🔇 User {user_id} silenced with Expelliarmus! ⚡✨")

async def avada_kedavra(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    if not context.args: return
    user_id = int(context.args[0])
    banned_users.add(user_id)
    await update.message.reply_text(f"💀 User {user_id} banned with Avada Kedavra! ⚡💥")

async def stupefy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMINS: return
    if not context.args: return
    user_id = int(context.args[0])
    await update.message.reply_text(f"⚡ User {user_id} warned with Stupefy! ✨💫")

# ---------------------- WEEKLY LEADERBOARD ----------------------
async def weekly_leaderboard(app):
    while True:
        await asyncio.sleep(7*24*60*60)  # 7 days
        async with aiosqlite.connect("hogwarts.db") as db:
            async with db.execute("SELECT house, score FROM points ORDER BY score DESC") as cursor:
                rows = await cursor.fetchall()
        msg = "🏆 *Weekly House Leaderboard:* 🏰✨\n\n"
        for h, s in rows:
            spark = random.choice(["✨", "⚡", "🪄", "🌟"])
            msg += f"{spark} {h}: {s} points {spark}\n"
        for admin_id in ADMINS:
            await app.bot.send_message(chat_id=admin_id, text=msg, parse_mode="Markdown")

# ---------------------- RUN BOT ----------------------
if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("sortme", sortme))
    app.add_handler(CommandHandler("points", points))
    app.add_handler(CommandHandler("addpoints", addpoints))
    app.add_handler(CommandHandler("deductpoints", deductpoints))
    app.add_handler(CommandHandler("quiz", quiz))
    app.add_handler(CommandHandler("expelliarmus", expelliarmus))
    app.add_handler(CommandHandler("avada_kedavra", avada_kedavra))
    app.add_handler(CommandHandler("stupefy", stupefy))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), answer_handler))

    print("🏰 Hogwarts House Point System Online!")

    async def main():
        await init_db()
        asyncio.create_task(weekly_leaderboard(app))
        await app.run_polling()

    asyncio.get_event_loop().run_until_complete(main())



