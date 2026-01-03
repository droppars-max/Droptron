from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
import sqlite3

# ---------- تنظیمات ----------
TOKEN = "7572200133:AAEDAnslQifBjVxRDwqiEcKRF1gAfca8nWE"
BOT_USERNAME = "Drop_trx_rbot"
CHANNEL_ID = "@varizitrxdrop"
REGISTER_REWARD = 0.5
INVITE_REWARD = 0.5
MIN_WITHDRAW = 5
ADMINS = [6960872391]

# ---------- دیتابیس ----------
conn = sqlite3.connect("users.db", check_same_thread=False)
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance REAL DEFAULT 0,
    invited_by INTEGER,
    invites INTEGER DEFAULT 0,
    waiting_wallet INTEGER DEFAULT 0
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS withdrawals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    wallet TEXT,
    amount REAL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# ---------- کیبورد‌ها ----------
def get_main_keyboard(user_id):
    buttons = [
        [KeyboardButton("💰 موجودی"), KeyboardButton("📥 برداشت")],
        [KeyboardButton("📢 لینک دعوت")]
    ]
    if user_id in ADMINS:
        buttons.append([KeyboardButton("⚙️ پنل ادمین")])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def get_admin_keyboard():
    buttons = [
        [KeyboardButton("📊 آمار کاربران")],
        [KeyboardButton("💸 لیست برداشت‌ها")],
        [KeyboardButton("🎁 هدیه به کاربر")],
        [KeyboardButton("🔙 بازگشت")]
    ]
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

# ---------- ثبت نام ----------
async def start(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    first_name = update.effective_user.first_name
    args = context.args
    inviter_id = None
    if args:
        try:
            inviter_id = int(args[0])
        except:
            inviter_id = None

    cur.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    if cur.fetchone():
        await update.message.reply_text(f"🚨 {first_name} عزیز، شما قبلاً ثبت‌نام کردید.", reply_markup=get_main_keyboard(user_id))
        return

    cur.execute("INSERT INTO users (user_id, balance, invited_by) VALUES (?, ?, ?)", (user_id, REGISTER_REWARD, inviter_id))
    conn.commit()

    text = f"🎉 سلام {first_name}! خوش اومدی 💎\n💰 همین الان {REGISTER_REWARD} TRX به حسابت اضافه شد!"
    
    if inviter_id and inviter_id != user_id:
        cur.execute("UPDATE users SET balance = balance + ?, invites = invites + 1 WHERE user_id=?", (INVITE_REWARD, inviter_id))
        conn.commit()
        try:
            await context.bot.send_message(chat_id=inviter_id, text=f"🙌 شما یک نفر را دعوت کردید و {INVITE_REWARD} TRX به موجودی‌تان اضافه شد!")
        except:
            pass

    await update.message.reply_text(text, reply_markup=get_main_keyboard(user_id))

# ---------- موجودی ----------
async def balance(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    cur.execute("SELECT balance, invites FROM users WHERE user_id=?", (user_id,))
    result = cur.fetchone()
    if result:
        balance, invites = result
        referral_link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
        await update.message.reply_text(
            f"💰 موجودی: {balance} TRX\n👥 تعداد دوستان دعوت‌شده: {invites}\n\n📢 لینک دعوت اختصاصی:\n{referral_link}\n\n✨ وقتی موجودیت به {MIN_WITHDRAW} TRX برسه می‌تونی برداشت بزنی 🙌",
            reply_markup=get_main_keyboard(user_id)
        )
    else:
        await update.message.reply_text("❌ شما هنوز ثبت‌نام نکردید.", reply_markup=get_main_keyboard(user_id))

# ---------- برداشت ----------
async def withdraw(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    cur.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    result = cur.fetchone()
    if not result:
        await update.message.reply_text("❌ شما ثبت‌نام نکردید.", reply_markup=get_main_keyboard(user_id))
        return

    balance = result[0]
    if balance < MIN_WITHDRAW:
        await update.message.reply_text(f"🚨 حداقل برداشت {MIN_WITHDRAW} TRX است.\n💰 موجودی: {balance}", reply_markup=get_main_keyboard(user_id))
        return

    cur.execute("UPDATE users SET waiting_wallet=2 WHERE user_id=?", (user_id,))
    conn.commit()
    await update.message.reply_text(f"📥 موجودی: {balance} TRX\n✅ لطفاً مقدار برداشت را وارد کنید:", reply_markup=get_main_keyboard(user_id))

# ---------- ورود مقدار و کیف پول ----------
async def handle_wallet(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    cur.execute("SELECT balance, waiting_wallet FROM users WHERE user_id=?", (user_id,))
    result = cur.fetchone()
    if not result:
        return
    balance, waiting_wallet = result

    if waiting_wallet == 2:
        try:
            amount = float(text)
        except:
            await update.message.reply_text("❌ لطفاً عدد معتبر وارد کنید.", reply_markup=get_main_keyboard(user_id))
            return
        if amount < MIN_WITHDRAW:
            await update.message.reply_text(f"🚨 حداقل برداشت {MIN_WITHDRAW} TRX است.", reply_markup=get_main_keyboard(user_id))
            return
        if amount > balance:
            await update.message.reply_text(f"🚨 موجودی کافی ندارید.\n💰 موجودی: {balance}", reply_markup=get_main_keyboard(user_id))
            return
        context.user_data['withdraw_amount'] = amount
        cur.execute("UPDATE users SET waiting_wallet=1 WHERE user_id=?", (user_id,))
        conn.commit()
        await update.message.reply_text(f"✅ مقدار {amount} TRX ثبت شد.\n📥 لطفاً آدرس کیف پول خود را ارسال کنید.", reply_markup=get_main_keyboard(user_id))
        return

    if waiting_wallet == 1:
        wallet = text
        amount = context.user_data.get('withdraw_amount', balance)
        cur.execute("INSERT INTO withdrawals (user_id, wallet, amount) VALUES (?, ?, ?)", (user_id, wallet, amount))
        cur.execute("UPDATE users SET balance=balance-?, waiting_wallet=0 WHERE user_id=?", (amount, user_id))
        conn.commit()

        await update.message.reply_text(f"🎉 درخواست برداشتت ثبت شد!\n💰 {amount} TRX\n📥 {wallet}\n⏳ در صف بررسی ...", reply_markup=get_main_keyboard(user_id))

        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("✅ تایید", callback_data=f"approve_{user_id}"),
                                          InlineKeyboardButton("❌ رد", callback_data=f"reject_{user_id}")]])
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"📢 برداشت جدید:\n👤 {user_id}\n💰 {amount} TRX\n📥 {wallet}\n⏳ در صف پرداخت", reply_markup=keyboard)
        for admin in ADMINS:
            try:
                await context.bot.send_message(chat_id=admin, text=f"📢 برداشت جدید:\n👤 {user_id}\n💰 {amount} TRX\n📥 {wallet}\n⏳ در صف پرداخت", reply_markup=keyboard)
            except:
                pass
                # ---------- هندلر تایید یا رد برداشت ----------
async def handle_approval(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data
    admin_id = query.from_user.id

    if admin_id not in ADMINS:
        await query.edit_message_text("❌ شما ادمین نیستید.")
        return

    action, user_id_str = data.split("_")
    user_id = int(user_id_str)

    cur.execute("SELECT id, amount, wallet, status FROM withdrawals WHERE user_id=? AND status='pending' ORDER BY id DESC LIMIT 1", (user_id,))
    wd = cur.fetchone()
    if not wd:
        await query.edit_message_text("⏳ هیچ درخواست فعالی برای این کاربر وجود ندارد.")
        return

    wid, amount, wallet, status = wd

    if action == "approve":
        cur.execute("UPDATE withdrawals SET status='paid' WHERE id=?", (wid,))
        conn.commit()
        await query.edit_message_text(f"✅ برداشت {amount} TRX توسط ادمین تایید شد.")
        try:
            await context.bot.send_message(chat_id=user_id, text=f"🎉 برداشت شما به مبلغ {amount} TRX توسط ادمین تایید شد و پرداخت انجام شد!")
            await context.bot.send_message(chat_id=CHANNEL_ID, text=f"💸 برداشت کاربر {user_id} ✅ پرداخت شد.\n💰 {amount} TRX\n📥 {wallet}")
        except:
            pass

    elif action == "reject":
        cur.execute("UPDATE withdrawals SET status='rejected' WHERE id=?", (wid,))
        cur.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (amount, user_id))
        conn.commit()
        await query.edit_message_text(f"❌ برداشت {amount} TRX توسط ادمین رد شد.")
        try:
            await context.bot.send_message(chat_id=user_id, text=f"❌ برداشت شما به مبلغ {amount} TRX توسط ادمین رد شد و موجودی به حسابت بازگشت داده شد.")
            await context.bot.send_message(chat_id=CHANNEL_ID, text=f"💸 برداشت کاربر {user_id} ❌ رد شد.\n💰 {amount} TRX\n📥 {wallet}")
        except:
            pass

# ---------- پنل ادمین ----------
async def admin_stats(update: Update, context: CallbackContext):
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*), SUM(amount) FROM withdrawals WHERE status='pending'")
    wd_count, total_amount = cur.fetchone()
    total_amount = total_amount if total_amount else 0
    await update.message.reply_text(
        f"📊 آمار سیستم:\n👥 کاربران ثبت‌نامی: {total_users}\n💸 درخواست‌های برداشت در صف: {wd_count}\n✅ مجموع مبلغ در صف: {total_amount} TRX",
        reply_markup=get_admin_keyboard()
    )

async def admin_withdrawals(update: Update, context: CallbackContext):
    cur.execute("SELECT id, user_id, amount, wallet, status FROM withdrawals ORDER BY id DESC LIMIT 5")
    rows = cur.fetchall()
    if not rows:
        await update.message.reply_text("⏳ هیچ درخواستی نیست.", reply_markup=get_admin_keyboard())
        return
    for r in rows:
        wid, uid, amount, wallet, status = r
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ تایید", callback_data=f"approve_{uid}"),
             InlineKeyboardButton("❌ رد", callback_data=f"reject_{uid}")]
        ])
        msg = f"👤 {uid} | 💰 {amount} TRX | 📥 {wallet} | ⏳ وضعیت: {status}"
        await update.message.reply_text(msg, reply_markup=keyboard)

# ---------- هدیه به کاربر توسط ادمین ----------
async def gift(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in ADMINS:
        await update.message.reply_text("❌ شما ادمین نیستید.", reply_markup=get_main_keyboard(user_id))
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text("❌ دستور درست: /gift <user_id> <amount>", reply_markup=get_main_keyboard(user_id))
        return
    try:
        target_user = int(args[0])
        amount = float(args[1])
    except:
        await update.message.reply_text("❌ مقدار یا آی‌دی معتبر نیست.", reply_markup=get_main_keyboard(user_id))
        return

    cur.execute("SELECT balance FROM users WHERE user_id=?", (target_user,))
    if not cur.fetchone():
        await update.message.reply_text("❌ کاربر وجود ندارد.", reply_markup=get_main_keyboard(user_id))
        return

    cur.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, target_user))
    conn.commit()
    await update.message.reply_text(f"✅ {amount} TRX به کاربر {target_user} هدیه داده شد.", reply_markup=get_main_keyboard(user_id))
    try:
        await context.bot.send_message(chat_id=target_user, text=f"🎁 {amount} TRX از طرف ادمین دریافت کردید!")
    except:
        pass

# ---------- هندلر منو ----------
async def menu_handler(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    text = update.message.text

    if text == "💰 موجودی":
        await balance(update, context)
    elif text == "📥 برداشت":
        await withdraw(update, context)
    elif text == "📢 لینک دعوت":
        await balance(update, context)
    elif text == "⚙️ پنل ادمین" and user_id in ADMINS:
        await update.message.reply_text("⚙️ پنل مدیریت:", reply_markup=get_admin_keyboard())
    elif text == "📊 آمار کاربران" and user_id in ADMINS:
        await admin_stats(update, context)
    elif text == "💸 لیست برداشت‌ها" and user_id in ADMINS:
        await admin_withdrawals(update, context)
    elif text == "🎁 هدیه به کاربر" and user_id in ADMINS:
        await update.message.reply_text("📌 دستور:\n/gift <user_id> <amount>", reply_markup=get_admin_keyboard())
    elif text == "🔙 بازگشت":
        await update.message.reply_text("⬅️ بازگشت به منو اصلی", reply_markup=get_main_keyboard(user_id))
    else:
        await handle_wallet(update, context)

# ---------- راه‌اندازی ----------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("gift", gift))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_handler))
    app.add_handler(CallbackQueryHandler(handle_approval))

    print("✅ ربات روشن شد ...")
    app.run_polling()

if __name__ == "__main__":
    main()
