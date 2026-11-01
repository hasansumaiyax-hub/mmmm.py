import os
import random
import string
import datetime
import asyncio
import pyotp
import pandas as pd
import openpyxl
import pymongo
from bson.objectid import ObjectId
from flask import Flask
from threading import Thread
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler, 
    ConversationHandler, filters, CallbackQueryHandler
)

# ----------------- CONFIGURATION & PREMIUM EMOJI TAGS -----------------
BOT_TOKEN = "9288377749:AAHrbEM2cVkC3EXZncQVS2T4P2yFqN2ZkMo"
ADMIN_ID = 8279212458
MIN_WITHDRAW = 20.0
WITHDRAW_FEE = 5.0

# 🌟 Telegram Official Premium & Animated Emoji Tags
EMOJI_WALLET = '<tg-emoji emoji-id="5769403330761593044">👛</tg-emoji>'     # ওয়ালেট / পার্স
EMOJI_MONEY = '<tg-emoji emoji-id="5409048419211682843">💵</tg-emoji>'      # ডলার / টাকা
EMOJI_STAR = '<tg-emoji emoji-id="5438496463044752972">⭐</tg-emoji>'       # স্টার / প্রিমিয়াম
EMOJI_WORK = '<tg-emoji emoji-id="5341715473882955310">⚙️</tg-emoji>'       # কাজ / সেটিংস
EMOJI_REFER = '<tg-emoji emoji-id="5224450179368767019">🌐</tg-emoji>'      # রেফারেল / নেটওয়ার্ক
EMOJI_SUPPORT = '<tg-emoji emoji-id="538367538735104399">🎧</tg-emoji>'    # সাপোর্ট
EMOJI_METHOD = '<tg-emoji emoji-id="5413879192267803083">📚</tg-emoji>'     # মেথড
EMOJI_INSTA = '<tg-emoji emoji-id="5206383450977750405">📷</tg-emoji>'      # ইনস্টাগ্রাম অফিশিয়াল
EMOJI_FB = '<tg-emoji emoji-id="5206208353751024833">📘</tg-emoji>'         # ফেসবুক অফিশিয়াল
EMOJI_SHIELD = '<tg-emoji emoji-id="580553293066299632">🛡️</tg-emoji>'    # সিকিউরিটি / এডমিন
EMOJI_GIFT = '<tg-emoji emoji-id="542243931196834318">💡</tg-emoji>'      # বোনাস / আইডিয়া

# 🌐 MongoDB Connection
MONGO_URI = "mongodb+srv://hasansumaiyax_db_user:dZHnDk1nbSzlGaxo@cluster0.kjouetx.mongodb.net/"
client = pymongo.MongoClient(MONGO_URI)
db_mongo = client["insta_bot_db"]

users_col = db_mongo["users"]
tasks_col = db_mongo["tasks"]
withdraws_col = db_mongo["withdraws"]
config_col = db_mongo["config"]
reports_col = db_mongo["reports"]
methods_col = db_mongo["methods"]
# -----------------

def get_config():
    conf = config_col.find_one({"id": "settings"})
    if not conf:
        default_conf = {
            "id": "settings",
            "active_date": datetime.datetime.now().strftime("%d-%m-%Y"),
            "insta_rates": [5.0, 6.0, 7.0],
            "fb_rates": [5.0, 6.0, 7.0, 8.0],
            "insta_pass": "InstaPass123!",
            "fb_pass": "FbPass123!",
            "support_link": "https://t.me/telegram",
            "insta_task_active": True,
            "fb_task_active": True
        }
        config_col.insert_one(default_conf)
        return default_conf
    
    updates = {}
    if "active_date" not in conf: updates["active_date"] = datetime.datetime.now().strftime("%d-%m-%Y")
    if "fb_rates" not in conf: updates["fb_rates"] = [5.0, 6.0, 7.0, 8.0]
    if "fb_pass" not in conf: updates["fb_pass"] = "FbPass123!"
    if "insta_rates" not in conf and "rates" in conf: updates["insta_rates"] = conf["rates"]
    if "insta_pass" not in conf and "default_pass" in conf: updates["insta_pass"] = conf["default_pass"]
    if "support_link" not in conf: updates["support_link"] = "https://t.me/telegram"
    if "insta_task_active" not in conf: updates["insta_task_active"] = True
    if "fb_task_active" not in conf: updates["fb_task_active"] = True

    if updates:
        config_col.update_one({"id": "settings"}, {"$set": updates})
        conf.update(updates)

    return conf

def get_custom_date():
    conf = get_config()
    return conf.get("active_date", datetime.datetime.now().strftime("%d-%m-%Y"))

def get_user(user_id, referred_by=None):
    user = users_col.find_one({"user_id": user_id})
    if not user:
        user_data = {
            "user_id": user_id,
            "balance": 0.0, 
            "pending_withdraw": 0.0, 
            "completed": 0, 
            "review": 0,
            "total_earned": 0.0,
            "referred_by": referred_by,
            "total_refers": 0
        }
        users_col.insert_one(user_data)
        if referred_by:
            users_col.update_one({"user_id": referred_by}, {"$inc": {"total_refers": 1}})
        return user_data
    return user

def generate_random_username():
    prefix = "insta_" + "".join(random.choices(string.ascii_lowercase, k=4))
    digits = "".join(random.choices(string.digits, k=4))
    return f"{prefix}_{digits}"

def generate_random_fb_name():
    first_names = ["Tanvir", "Sabbir", "Arif", "Mehedi", "Nayan", "Rakib", "Shakil", "Mahfuz"]
    last_names = ["Hossain", "Ahmed", "Islam", "Rahman", "Khan", "Chowdhury", "Sheikh"]
    return random.choice(first_names), random.choice(last_names)

# 🔄 Conversation States
_states_list = [
    "WORK_SELECT_PLATFORM", "WORK_SELECT_TYPE", "WORK_SELECT_RATE", "ENTERING_2FA", "TASK_CONFIRM",
    "FB_SELECT_TYPE", "FB_SELECT_COOKIE_TYPE", "FB_SELECT_RATE", "FB_ENTER_UID", "FB_ENTER_COOKIES", "FB_TASK_CONFIRM",
    "ADMIN_SET_INSTA_PASS", "ADMIN_SET_FB_PASS", "ADMIN_SET_INSTA_RATE", "ADMIN_SET_FB_RATE",
    "ADMIN_SELECT_FILE_PLATFORM", "ADMIN_GET_DATE_FILE", "ADMIN_SELECT_REPORT_PLATFORM", "ADMIN_GET_DATE_REPORT", "ADMIN_UPLOAD_REPORT",
    "WITHDRAW_METHOD", "WITHDRAW_NUMBER", "WITHDRAW_AMOUNT",
    "ADMIN_SET_SUPPORT", 
    "METHOD_SELECT_PLATFORM", "METHOD_AVAILABLE_MENU", "METHOD_SEND_VIDEO", "ADMIN_METHOD_MENU", "ADMIN_ADD_METHOD_PLATFORM", "ADMIN_ADD_METHOD_NAME", "ADMIN_ADD_METHOD_FILE", 
    "ADMIN_DEL_METHOD_PLATFORM", "ADMIN_DEL_METHOD_SELECT",
    "ADMIN_BROADCAST_MSG", "ADMIN_SET_DATE",
    "ADMIN_TASK_ON_OFF_MENU",
    "ADMIN_USER_MGMT_INPUT", "ADMIN_USER_EDIT_CHOICE", "ADMIN_USER_EDIT_VALUE",
    "DB_ALL_FILES_PLATFORM"
]
globals().update({name: idx for idx, name in enumerate(_states_list)})

# ----------------- KEYBOARDS -----------------
def main_keyboard():
    return ReplyKeyboardMarkup([
        ["💼 কাজ শুরু করুন", "💎 আমার ব্যালেন্স"],
        ["💳 টাকা উত্তোলন", "⚡ রেফারেল লিংক"],
        ["🎧 হেল্প ও সাপোর্ট", "📚 মেথড"]
    ], resize_keyboard=True)

def admin_keyboard():
    return ReplyKeyboardMarkup([
        ["⚙️ কাজ কাস্টমাইজ", "💸 উইথড্র কন্ট্রোল"],
        ["📁 অল টাস্ক সেন্টার", "👥 ইউজার কন্ট্রোল"],
        ["🗄️ ডাটাবেজ ম্যানেজমেন্ট", "👥 মোট ইউজার"],
        ["📁 অল ফাইল", "📢 ব্রডকাস্ট মেসেজ"],
        ["🔙 মূল মেনু"]
    ], resize_keyboard=True)

def admin_custom_keyboard():
    return ReplyKeyboardMarkup([
        ["📅 তারিখ সেট করুন", "🔌 কাজ অন/অফ"],
        ["🔑 ইন্সটাগ্রাম পাসওয়ার্ড", "🔑 ফেসবুক পাসওয়ার্ড"],
        ["💵 ইন্সটাগ্রাম রেট", "💵 ফেসবুক রেট"],
        ["🎧 সাপোর্ট লিংক সেট", "📁 মেথড ম্যানেজমেন্ট"],
        ["🔙 এডমিন মেনু"]
    ], resize_keyboard=True)

def admin_all_tasks_keyboard():
    return ReplyKeyboardMarkup([
        ["📥 ফাইল ডাউনলোড", "📤 রিপোর্ট জমা দিন"],
        ["🔙 এডমিন মেনু"]
    ], resize_keyboard=True)

def platform_choice_keyboard():
    return ReplyKeyboardMarkup([
        ["📸 Instagram", "📘 Facebook"],
        ["❌ বাতিল"]
    ], resize_keyboard=True)

def withdraw_methods_keyboard():
    return ReplyKeyboardMarkup([
        ["🔷 বিকাশ (Bkash)", "🔶 নগদ (Nagad)", "💜 রকেট (Rocket)"],
        ["❌ বাতিল"]
    ], resize_keyboard=True)

def cancel_keyboard():
    return ReplyKeyboardMarkup([["❌ বাতিল"]], resize_keyboard=True)

# ----------------- HANDLERS WITH HTML REPLY -----------------
async def cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    msg = f"{EMOJI_STAR} <b>আপনার চলতি প্রসেসটি বাতিল করা হয়েছে!</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━\n🏠 <b>আপনাকে মূল ড্যাশবোর্ডে ফিরিয়ে নেওয়া হলো।</b>"
    await update.message.reply_html(msg, reply_markup=main_keyboard())
    return ConversationHandler.END

async def smart_back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    context.user_data.clear()
    
    if text == "🔙 এডমিন মেনু":
        await update.message.reply_html(f"{EMOJI_SHIELD} <b>এডমিন কন্ট্রোল প্যানেল:</b>", reply_markup=admin_keyboard())
        return ConversationHandler.END
    elif text == "🔙 কাস্টমাইজ মেনু":
        await update.message.reply_html(f"{EMOJI_WORK} <b>কাস্টমাইজেশন প্যানেল:</b>", reply_markup=admin_custom_keyboard())
        return ConversationHandler.END
    elif text == "🔙 মূল মেনু":
        await update.message.reply_html("🏠 <b>আপনি মূল ড্যাশবোর্ডে ফিরে এসেছেন।</b>", reply_markup=main_keyboard())
        return ConversationHandler.END
    else:
        await update.message.reply_html("🔙 <b>এক ধাপ পেছনে ফিরে আসা হয়েছে।</b>", reply_markup=admin_custom_keyboard())
        return ConversationHandler.END

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    user_id = update.effective_user.id
    referred_by = None
    if context.args and context.args[0].isdigit():
        ref_id = int(context.args[0])
        if ref_id != user_id: referred_by = ref_id
    
    get_user(user_id, referred_by)
    
    msg = f"{EMOJI_STAR} <b>স্বাগতম! ছোট ছোট টাস্ক সম্পন্ন করে ঘরে বসে নিশ্চিত আয় করুন – সহজ, নিরাপদ ও দ্রুত পেমেন্ট {EMOJI_MONEY}</b>\n\n👇 <b>নিচের মেনু থেকে আপনার পছন্দসই অপশনটি বেছে নিন:</b>"
    await update.message.reply_html(msg, reply_markup=main_keyboard())
    return ConversationHandler.END

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id)
    msg = f"{EMOJI_WALLET} <b>আপনার ব্যক্তিগত ব্যালেন্স ড্যাশবোর্ড</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━\n{EMOJI_MONEY} <b>বর্তমান ব্যালেন্স:</b> <code>{u['balance']:.2f}</code> টাকা\n⏳ <b>পেন্ডিং উইথড্র:</b> <code>{u['pending_withdraw']:.2f}</code> টাকা\n✅ <b>সফল টাস্ক:</b> <code>{u['completed']}</code> টি\n🔍 <b>রিভিউ টাস্ক:</b> <code>{u['review']}</code> টি\n{EMOJI_STAR} <b>মোট অর্জিত আয়:</b> <code>{u['total_earned']:.2f}</code> টাকা\n━━━━━━━━━━━━━━━━━━━━━━━━━"
    await update.message.reply_html(msg, reply_markup=main_keyboard())

async def refer_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    u = get_user(user_id)
    bot_username = (await context.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start={user_id}"
    msg = f"{EMOJI_REFER} <b>স্মার্ট রেফারেল ও ইনভাইট নেটওয়ার্ক</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━\n👥 <b>আপনার রেফারকৃত মোট মেম্বার:</b> <code>{u['total_refers']}</code> জন\n{EMOJI_GIFT} আপনার রেফারকৃত ব্যক্তি আমাদের বট থেকে পেমেন্ট তুললে আপনি আজীবন ৫ টাকা করে কমিশন পাবেন!\n━━━━━━━━━━━━━━━━━━━━━━━━━\n🔗 <b>আপনার ইউনিক ইনভাইট লিংক:</b>\n<code>{ref_link}</code>\n\n🚀 <b>লিংকটি বন্ধুদের সাথে শেয়ার করে ইনকাম বাড়িয়ে নিন!</b>"
    await update.message.reply_html(msg, reply_markup=main_keyboard())

async def support_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conf = get_config()
    admin_url = conf.get("support_link", "https://t.me/telegram").strip()
    if not admin_url.startswith("http://") and not admin_url.startswith("https://"):
        admin_url = f"https://t.me/{admin_url.replace('@', '')}"

    inline_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 এডমিন লাইভ সাপোর্ট", url=admin_url)]
    ])
    
    msg = f"{EMOJI_SUPPORT} <b>অফিশিয়াল সাপোর্ট সেন্টার</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━\nযেকোনো প্রয়োজনে বা সহায়তার জন্য নিচের বাটনে ক্লিক করে সরাসরি যোগাযোগ করুন:"
    await update.message.reply_html(msg, reply_markup=inline_kb)

# --- USER METHOD SYSTEM ---
async def method_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(f"{EMOJI_METHOD} <b>কোন প্ল্যাটফর্মের মেথড দেখতে চান? প্ল্যাটফর্ম সিলেক্ট করুন:</b>", reply_markup=platform_choice_keyboard())
    return METHOD_SELECT_PLATFORM

async def method_platform_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    platform = None
    if text == "📸 Instagram":
        platform = "Instagram"
    elif text == "📘 Facebook":
        platform = "Facebook"
    else:
        await update.message.reply_html("❌ <b>অনুগ্রহ করে সঠিক প্ল্যাটফর্মটি নির্বাচন করুন।</b>", reply_markup=platform_choice_keyboard())
        return METHOD_SELECT_PLATFORM

    context.user_data["user_method_platform"] = platform
    btn_text = "IG Available Method" if platform == "Instagram" else "FB Available Method"
    kb = ReplyKeyboardMarkup([[btn_text], ["❌ বাতিল"]], resize_keyboard=True)
    platform_icon = EMOJI_INSTA if platform == "Instagram" else EMOJI_FB
    await update.message.reply_html(f"{platform_icon} <b>{platform} সিলেক্ট হয়েছে। নিচের বাটনে ক্লিক করুন:</b>", reply_markup=kb)
    return METHOD_AVAILABLE_MENU

async def method_show_titles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "Available Method" not in text:
        await update.message.reply_html("❌ <b>সঠিক বাটনে প্রেস করুন।</b>")
        return METHOD_AVAILABLE_MENU

    platform = context.user_data.get("user_method_platform", "Instagram")
    methods = list(methods_col.find({"platform": platform}))
    
    if not methods:
        await update.message.reply_html(f"⚠️ <b>{platform}-এর জন্য এখনো কোনো মেথড যুক্ত করা হয়নি।</b>", reply_markup=main_keyboard())
        return ConversationHandler.END

    keyboard_rows = []
    for m in methods:
        keyboard_rows.append([m['name']])
    keyboard_rows.append(["❌ বাতিল"])
    
    kb = ReplyKeyboardMarkup(keyboard_rows, resize_keyboard=True)
    await update.message.reply_html(f"{EMOJI_METHOD} <b>{platform} কাজের মেথড লিস্ট:</b>\nনিচের টাইটেলগুলোর ওপর ক্লিক করে মেথড ভিডিও দেখে নিন:", reply_markup=kb)
    return METHOD_SEND_VIDEO

async def method_send_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = update.message.text.strip()
    platform = context.user_data.get("user_method_platform", "Instagram")
    
    method_doc = methods_col.find_one({"platform": platform, "name": title})
    if not method_doc:
        await update.message.reply_html("❌ <b>এই নামের কোনো মেথড পাওয়া যায়নি। সঠিক বাটনটিতে চাপ দিন।</b>")
        return METHOD_SEND_VIDEO

    file_id = method_doc["file_id"]
    try:
        await update.message.reply_video(video=file_id, caption=f"🎬 <b>মেথড টাইটেল:</b> {title}", parse_mode="HTML", reply_markup=main_keyboard())
    except Exception:
        await update.message.reply_html(f"🎬 <b>মেথড: {title}</b>\nফাইল আইডি/লিংক: <code>{file_id}</code>", reply_markup=main_keyboard())
    
    context.user_data.clear()
    return ConversationHandler.END

# ----------------- WORK FLOW SYSTEM -----------------
async def work_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_html(f"{EMOJI_WORK} <b>কাজ শুরু করার জন্য প্ল্যাটফর্ম সিলেক্ট করুন:</b>", reply_markup=platform_choice_keyboard())
    return WORK_SELECT_PLATFORM

async def work_platform_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    conf = get_config()

    if text == "📸 Instagram":
        if not conf.get("insta_task_active", True):
            await update.message.reply_html("⚠️ <b>বর্তমানে ইন্সটাগ্রামের কাজ সাময়িকভাবে বন্ধ রয়েছে। অনুগ্রহ করে পরবর্তীতে চেষ্টা করুন।</b>", reply_markup=main_keyboard())
            return ConversationHandler.END
            
        kb = ReplyKeyboardMarkup([["🔑 INSTA 2FA"], ["❌ বাতিল"]], resize_keyboard=True)
        await update.message.reply_html(f"{EMOJI_INSTA} <b>ইন্সটাগ্রাম কাজের ক্যাটাগরি সিলেক্ট করুন:</b>", reply_markup=kb)
        return WORK_SELECT_TYPE

    elif text == "📘 Facebook":
        if not conf.get("fb_task_active", True):
            await update.message.reply_html("⚠️ <b>বর্তমানে ফেসবুকের কাজ সাময়িকভাবে বন্ধ রয়েছে। অনুগ্রহ করে পরবর্তীতে চেষ্টা করুন।</b>", reply_markup=main_keyboard())
            return ConversationHandler.END

        kb = ReplyKeyboardMarkup([["📱 Number/Anymail"], ["❌ বাতিল"]], resize_keyboard=True)
        await update.message.reply_html(f"{EMOJI_FB} <b>ফেসবুক কাজের ক্যাটাগরি সিলেক্ট করুন:</b>", reply_markup=kb)
        return FB_SELECT_TYPE
    
    await update.message.reply_html("❌ <b>অনুগ্রহ করে সঠিক প্ল্যাটফর্ম সিলেক্ট করুন।</b>")
    return WORK_SELECT_PLATFORM

async def work_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔑 INSTA 2FA":
        conf = get_config()
        rate_buttons = [[f"💰 {r} টাকা"] for r in conf["insta_rates"]]
        rate_buttons.append(["❌ বাতিল"])
        kb = ReplyKeyboardMarkup(rate_buttons, resize_keyboard=True)
        await update.message.reply_html(f"{EMOJI_MONEY} <b>আপনার পছন্দের রেট সিলেক্ট করুন:</b>", reply_markup=kb)
        return WORK_SELECT_RATE
    await update.message.reply_html("❌ <b>অকার্যকর অপশন!</b>")
    return WORK_SELECT_TYPE

async def work_rate_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        selected_rate = float(update.message.text.replace("💰", "").replace("টাকা", "").strip())
    except ValueError:
        await update.message.reply_html("❌ <b>বাটন থেকে সঠিক রেট সিলেক্ট করুন।</b>")
        return WORK_SELECT_RATE

    conf = get_config()
    generated_user = generate_random_username()
    password = conf["insta_pass"]
    
    context.user_data["task_platform"] = "Instagram"
    context.user_data["task_rate"] = selected_rate
    context.user_data["task_insta_user"] = generated_user
    context.user_data["task_pass"] = password
    
    msg = f"{EMOJI_INSTA} <b>নতুন ইন্সটাগ্রাম একাউন্ট খোলার তথ্য</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━\n👤 <b>Username:</b> <code>{generated_user}</code>\n🔑 <b>Password:</b> <code>{password}</code>\n{EMOJI_MONEY} <b>রেট:</b> <b>{selected_rate} টাকা</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━\n⚡ <b>উপরের তথ্যগুলো দিয়ে একাউন্ট তৈরি করে 2FA সিকিউরিটি চালু করুন।</b>"
    kb = ReplyKeyboardMarkup([["✅ একাউন্ট খোলা শেষ"], ["❌ বাতিল"]], resize_keyboard=True)
    await update.message.reply_html(msg, reply_markup=kb)
    return ENTERING_2FA

async def process_account_created(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "✅ একাউন্ট খোলা শেষ":
        await update.message.reply_html("🔐 <b>আপনার ইন্সটাগ্রামের 2FA সিক্রেট কী (Secret Key) সেন্ড করুন:</b>", reply_markup=cancel_keyboard())
        return ENTERING_2FA
        
    user_key = text.strip().replace(" ", "")
    try:
        totp = pyotp.TOTP(user_key)
        live_code = totp.now()
    except Exception:
        await update.message.reply_html("❌ <b>ভুল 2FA সিক্রেট কী! অনুগ্রহ করে সঠিক কী দিন:</b>")
        return ENTERING_2FA

    context.user_data["task_2fa_key"] = user_key
    msg = f"⚡ <b>আপনার লাইভ সিকিউরিটি কোড:</b> <code>{live_code}</code>\n\nকোডটি একাউন্টে সেট করে '✅ কাজ সম্পন্ন হয়েছে' বাটনে প্রেস করুন।"
    kb = ReplyKeyboardMarkup([["✅ কাজ সম্পন্ন হয়েছে"], ["❌ বাতিল"]], resize_keyboard=True)
    await update.message.reply_html(msg, reply_markup=kb)
    return TASK_CONFIRM

async def task_complete_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "✅ কাজ সম্পন্ন হয়েছে":
        user_id = update.effective_user.id
        current_date = get_custom_date()
        
        task_data = {
            "platform": "Instagram",
            "user_id": user_id,
            "name": update.effective_user.full_name,
            "insta_user": context.user_data.get("task_insta_user"),
            "insta_pass": context.user_data.get("task_pass"),
            "key_2fa": context.user_data.get("task_2fa_key"),
            "rate": context.user_data.get("task_rate"),
            "date": current_date,
            "status": "pending",
            "timestamp": datetime.datetime.now()
        }
        
        tasks_col.insert_one(task_data)
        users_col.update_one({"user_id": user_id}, {"$inc": {"review": 1}})
        
        msg = f"{EMOJI_STAR} <b>আপনার টাস্কটি সফলভাবে জমা দেওয়া হয়েছে!</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━\n📅 <b>ফাইল তারিখ:</b> <code>{current_date}</code>\n⏳ <b>২৪ ঘণ্টার মধ্যে রিভিউ সম্পন্ন করে ব্যালেন্স যোগ করে দেওয়া হবে।</b>"
        await update.message.reply_html(msg, reply_markup=main_keyboard())
        return ConversationHandler.END
    return TASK_CONFIRM

async def fb_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "📱 Number/Anymail":
        kb = ReplyKeyboardMarkup([["🍪 FB Cookies"], ["❌ বাতিল"]], resize_keyboard=True)
        await update.message.reply_html(f"{EMOJI_FB} <b>কাজের টাইপ সিলেক্ট করুন:</b>", reply_markup=kb)
        return FB_SELECT_COOKIE_TYPE
    await update.message.reply_html("❌ <b>অকার্যকর অপশন!</b>")
    return FB_SELECT_TYPE

async def fb_cookie_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🍪 FB Cookies":
        conf = get_config()
        rate_buttons = [[f"💰 {r} টাকা"] for r in conf["fb_rates"]]
        rate_buttons.append(["❌ বাতিল"])
        kb = ReplyKeyboardMarkup(rate_buttons, resize_keyboard=True)
        await update.message.reply_html(f"{EMOJI_MONEY} <b>ফেসবুক কাজের রেট সিলেক্ট করুন:</b>", reply_markup=kb)
        return FB_SELECT_RATE
    await update.message.reply_html("❌ <b>অকার্যকর অপশন!</b>")
    return FB_SELECT_COOKIE_TYPE

async def fb_rate_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        selected_rate = float(update.message.text.replace("💰", "").replace("টাকা", "").strip())
    except ValueError:
        await update.message.reply_html("❌ <b>সঠিক রেট সিলেক্ট করুন।</b>")
        return FB_SELECT_RATE

    conf = get_config()
    fname, lname = generate_random_fb_name()
    password = conf["fb_pass"]

    context.user_data["task_platform"] = "Facebook"
    context.user_data["task_rate"] = selected_rate
    context.user_data["fb_fname"] = fname
    context.user_data["fb_lname"] = lname
    context.user_data["fb_pass"] = password

    msg = f"{EMOJI_FB} <b>নতুন ফেসবুক একাউন্ট খোলার তথ্য</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━\n👤 <b>First Name:</b> <code>{fname}</code>\n👤 <b>Last Name:</b> <code>{lname}</code>\n🔑 <b>Password:</b> <code>{password}</code>\n{EMOJI_MONEY} <b>রেট:</b> <b>{selected_rate} টাকা</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━\n⚙️ <b>উপরের তথ্য দিয়ে একটি একাউন্ট খুলে তৈরি হয়ে নিন।</b>"
    kb = ReplyKeyboardMarkup([["✅ একাউন্ট খোলা শেষ"], ["❌ বাতিল"]], resize_keyboard=True)
    await update.message.reply_html(msg, reply_markup=kb)
    return FB_ENTER_UID

async def fb_process_account_created(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "✅ একাউন্ট খোলা শেষ":
        await update.message.reply_html("🆔 <b>আপনার নতুন ফেসবুক একাউন্টের UID দিন:</b>", reply_markup=cancel_keyboard())
        return FB_ENTER_COOKIES
    await update.message.reply_html("❌ <b>বাটনে প্রেস করে সামনের ধাপে যান।</b>")
    return FB_ENTER_UID

async def fb_get_uid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.text.strip()
    context.user_data["fb_uid"] = uid
    await update.message.reply_html("🍪 <b>আপনার ফেসবুক একাউন্টের কপি করা কুকিজ (Cookies) দিন:</b>", reply_markup=cancel_keyboard())
    return FB_TASK_CONFIRM

async def fb_get_cookies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cookies = update.message.text.strip()
    context.user_data["fb_cookies"] = cookies
    
    msg = "✅ <b>কুকিজ সফলভাবে গ্রহণ করা হয়েছে! কাজ ফাইনাল জমা দিতে নিচের বাটনে চাপ দিন।</b>"
    kb = ReplyKeyboardMarkup([["✅ কাজ সম্পূর্ণ"], ["❌ বাতিল"]], resize_keyboard=True)
    await update.message.reply_html(msg, reply_markup=kb)
    return FB_TASK_CONFIRM

async def fb_task_complete_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "✅ কাজ সম্পূর্ণ":
        user_id = update.effective_user.id
        current_date = get_custom_date()
        
        task_data = {
            "platform": "Facebook",
            "user_id": user_id,
            "name": update.effective_user.full_name,
            "fb_uid": context.user_data.get("fb_uid"),
            "fb_pass": context.user_data.get("fb_pass"),
            "fb_cookies": context.user_data.get("fb_cookies"),
            "rate": context.user_data.get("task_rate"),
            "date": current_date,
            "status": "pending",
            "timestamp": datetime.datetime.now()
        }
        
        tasks_col.insert_one(task_data)
        users_col.update_one({"user_id": user_id}, {"$inc": {"review": 1}})
        
        msg = f"{EMOJI_STAR} <b>আপনার ফেসবুক টাস্ক জমা সম্পন্ন হয়েছে!</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━\n📅 <b>ফাইল তারিখ:</b> <code>{current_date}</code>\n⏳ <b>২৪ ঘণ্টার মধ্যে টাকা আপনার অ্যাকাউন্টে যুক্ত হবে।</b>"
        await update.message.reply_html(msg, reply_markup=main_keyboard())
        return ConversationHandler.END
    
    return await fb_get_cookies(update, context)

# ----------------- WITHDRAW SYSTEM -----------------
async def withdraw_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    u = get_user(update.effective_user.id)
    if u["balance"] < (MIN_WITHDRAW + WITHDRAW_FEE):
        msg = f"❌ <b>পর্যাপ্ত ব্যালেন্স নেই!</b>\n\nসর্বনিম্ন উত্তোলন: <b>{MIN_WITHDRAW} টাকা</b> (+ফি {WITHDRAW_FEE} টাকা)"
        await update.message.reply_html(msg)
        return ConversationHandler.END
    await update.message.reply_html(f"{EMOJI_WALLET} <b>পেমেন্ট উত্তোলনের মেথড সিলেক্ট করুন:</b>", reply_markup=withdraw_methods_keyboard())
    return WITHDRAW_METHOD

async def withdraw_select_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["withdraw_method"] = update.message.text
    await update.message.reply_html("📱 <b>আপনার পার্সোনাল অ্যাকাউন্ট নম্বরটি সেন্ড করুন:</b>", reply_markup=cancel_keyboard())
    return WITHDRAW_NUMBER

async def withdraw_get_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["withdraw_number"] = update.message.text
    await update.message.reply_html(f"{EMOJI_MONEY} <b>কত টাকা উত্তোলন করতে চান লিখুন:</b>", reply_markup=cancel_keyboard())
    return WITHDRAW_AMOUNT

async def withdraw_process_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
    except ValueError:
        await update.message.reply_html("❌ <b>সংখ্যার মাধ্যমে সঠিক টাকার পরিমাণ লিখুন:</b>")
        return WITHDRAW_AMOUNT

    user_id = update.effective_user.id
    u = get_user(user_id)
    if u["balance"] < (amount + WITHDRAW_FEE):
        await update.message.reply_html("❌ <b>আপনার একাউন্টে পর্যাপ্ত ব্যালেন্স নেই!</b>")
        return WITHDRAW_AMOUNT

    withdraw_id = withdraws_col.count_documents({}) + 1
    req = {
        "id": withdraw_id,
        "user_id": user_id,
        "name": update.effective_user.full_name,
        "method": context.user_data["withdraw_method"],
        "number": context.user_data["withdraw_number"],
        "amount": amount,
        "fee": WITHDRAW_FEE,
        "status": "pending"
    }
    withdraws_col.insert_one(req)
    users_col.update_one({"user_id": user_id}, {"$inc": {"balance": -(amount+WITHDRAW_FEE), "pending_withdraw": amount}})
    
    msg = f"{EMOJI_STAR} <b>উত্তোলন রিকোয়েস্ট সফলভাবে জমা হয়েছে!</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━\n{EMOJI_MONEY} <b>পরিমাণ:</b> <code>{amount}</code> টাকা\n⚡ এডমিন রিভিউ সম্পন্ন করে দ্রুত পেমেন্ট পাঠিয়ে দেবে।"
    await update.message.reply_html(msg, reply_markup=main_keyboard())
    return ConversationHandler.END

# ----------------- ADMIN PANEL & ACTIONS -----------------
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    await update.message.reply_html(f"{EMOJI_SHIELD} <b>এডমিন কন্ট্রোল প্যানেল:</b>", reply_markup=admin_keyboard())

async def admin_withdraw_custom(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    pendings = list(withdraws_col.find({"status": "pending"}))
    if not pendings:
        await update.message.reply_html("✨ <b>বর্তমানে কোনো পেন্ডিং উত্তোলন রিকোয়েস্ট নেই।</b>")
        return
    for w in pendings:
        msg = f"🆔 <b>আইডি:</b> <code>#{w['id']}</code>\n👤 <b>ইউজার:</b> {w['name']} (<code>{w['user_id']}</code>)\n{EMOJI_MONEY} <b>পরিমাণ:</b> <b>{w['amount']} টাকা</b>\n📞 <b>মেথড ও নম্বর:</b> {w['method']} - <code>{w['number']}</code>\n\n👇 <b>অনুমোদন করতে টাইপ/ক্লিক করুন:</b> <code>/approve_{w['id']}</code>\n👇 <b>বাতিল করতে টাইপ/ক্লিক করুন:</b> <code>/reject_{w['id']}</code>"
        await update.message.reply_html(msg)

async def admin_handle_withdraw_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    text = update.message.text
    if text.startswith("/approve_"):
        wid = int(text.split("_")[1])
        w = withdraws_col.find_one({"id": wid, "status": "pending"})
        if w:
            withdraws_col.update_one({"id": wid}, {"$set": {"status": "approved"}})
            users_col.update_one({"user_id": w["user_id"]}, {"$inc": {"pending_withdraw": -w["amount"]}})
            await update.message.reply_html(f"✅ <b>উত্তোলন আইডি <code>#{wid}</code> অনুমোদন করা হয়েছে!</b>")
            try:
                await context.bot.send_message(w["user_id"], f"🎉 <b>আপনার {w['amount']} টাকার উত্তোলন রিকোয়েস্ট অনুমোদিত ও পেমেন্ট সম্পন্ন হয়েছে!</b>", parse_mode="HTML")
            except Exception: pass
    elif text.startswith("/reject_"):
        wid = int(text.split("_")[1])
        w = withdraws_col.find_one({"id": wid, "status": "pending"})
        if w:
            withdraws_col.update_one({"id": wid}, {"$set": {"status": "rejected"}})
            refund_amount = w["amount"] + w["fee"]
            users_col.update_one({"user_id": w["user_id"]}, {"$inc": {"balance": refund_amount, "pending_withdraw": -w["amount"]}})
            await update.message.reply_html(f"❌ <b>উত্তোলন আইডি <code>#{wid}</code> বাতিল করা হয়েছে এবং টাকা ফেরত দেওয়া হয়েছে।</b>")
            try:
                await context.bot.send_message(w["user_id"], f"❌ <b>আপনার {w['amount']} টাকার উত্তোলন রিকোয়েস্ট বাতিল করা হয়েছে। টাকা ব্যালেন্সে ব্যাক দেওয়া হয়েছে।</b>", parse_mode="HTML")
            except Exception: pass

async def admin_task_on_off_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return ConversationHandler.END
    conf = get_config()
    insta_status = "🟢 ON" if conf.get("insta_task_active", True) else "🔴 OFF"
    fb_status = "🟢 ON" if conf.get("fb_task_active", True) else "🔴 OFF"

    kb = ReplyKeyboardMarkup([
        [f"Instagram: {insta_status}", f"Facebook: {fb_status}"],
        ["🔙 কাস্টমাইজ মেনু"]
    ], resize_keyboard=True)

    await update.message.reply_html(f"{EMOJI_WORK} <b>কাজ অন/অফ কন্ট্রোল প্যানেল</b>\n\nনিচের প্ল্যাটফর্মের ওপর ক্লিক করে টগল (চালু/বন্ধ) করুন:", reply_markup=kb)
    return ADMIN_TASK_ON_OFF_MENU

async def admin_toggle_task_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return ConversationHandler.END
    text = update.message.text
    conf = get_config()

    if "Instagram" in text:
        current = conf.get("insta_task_active", True)
        new_val = not current
        config_col.update_one({"id": "settings"}, {"$set": {"insta_task_active": new_val}})
        status_text = "চালু (ON)" if new_val else "বন্ধ (OFF)"
        await update.message.reply_html(f"✅ ইন্সটাগ্রামের কাজ সফলভাবে <b>{status_text}</b> করা হয়েছে!")
    elif "Facebook" in text:
        current = conf.get("fb_task_active", True)
        new_val = not current
        config_col.update_one({"id": "settings"}, {"$set": {"fb_task_active": new_val}})
        status_text = "চালু (ON)" if new_val else "বন্ধ (OFF)"
        await update.message.reply_html(f"✅ ফেসবুকের কাজ সফলভাবে <b>{status_text}</b> করা হয়েছে!")
    elif text == "🔙 কাস্টমাইজ মেনু":
        await update.message.reply_html(f"{EMOJI_WORK} <b>কাস্টমাইজেশন প্যানেল:</b>", reply_markup=admin_custom_keyboard())
        return ConversationHandler.END

    conf = get_config()
    insta_status = "🟢 ON" if conf.get("insta_task_active", True) else "🔴 OFF"
    fb_status = "🟢 ON" if conf.get("fb_task_active", True) else "🔴 OFF"
    kb = ReplyKeyboardMarkup([
        [f"Instagram: {insta_status}", f"Facebook: {fb_status}"],
        ["🔙 কাস্টমাইজ মেনু"]
    ], resize_keyboard=True)
    await update.message.reply_text("🔌 স্ট্যাটাস আপডেট করা হয়েছে:", reply_markup=kb)
    return ADMIN_TASK_ON_OFF_MENU

# --- ADMIN METHOD MANAGEMENT ---
async def admin_method_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return ConversationHandler.END
    kb = ReplyKeyboardMarkup([
        ["➕ মেথড যোগ করুন", "🗑️ মেথড ডিলিট করুন"],
        ["🔙 কাস্টমাইজ মেনু"]
    ], resize_keyboard=True)
    await update.message.reply_html(f"{EMOJI_METHOD} <b>মেথড ম্যানেজমেন্ট প্যানেল:</b>\nনিচের অপশন থেকে সিলেক্ট করুন:", reply_markup=kb)
    return ADMIN_METHOD_MENU

async def admin_method_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return ConversationHandler.END
    text = update.message.text
    if text == "➕ মেথড যোগ করুন":
        await update.message.reply_html("🔷 <b>কোন প্ল্যাটফর্মে মেথড যোগ করবেন? প্ল্যাটফর্ম সিলেক্ট করুন:</b>", reply_markup=platform_choice_keyboard())
        return ADMIN_ADD_METHOD_PLATFORM
    elif text == "🗑️ মেথড ডিলিট করুন":
        await update.message.reply_html("🔷 <b>কোন প্ল্যাটফর্ম থেকে মেথড ডিলিট করতে চান? প্ল্যাটফর্ম সিলেক্ট করুন:</b>", reply_markup=platform_choice_keyboard())
        return ADMIN_DEL_METHOD_PLATFORM
    elif text == "🔙 কাস্টমাইজ মেনু":
        await update.message.reply_html(f"{EMOJI_WORK} <b>কাস্টমাইজেশন প্যানেল:</b>", reply_markup=admin_custom_keyboard())
        return ConversationHandler.END
    return ADMIN_METHOD_MENU

async def admin_add_method_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ["📸 Instagram", "📘 Facebook"]:
        context.user_data["new_method_platform"] = text.replace("📸 ", "").replace("📘 ", "")
        await update.message.reply_html("✍️ <b>আপনার মেথড এর টাইটেল বা নাম দিন (যেমন: Method 1 - Account Create):</b>", reply_markup=cancel_keyboard())
        return ADMIN_ADD_METHOD_NAME
    await update.message.reply_html("❌ সঠিক প্ল্যাটফর্ম সিলেক্ট করুন।")
    return ADMIN_ADD_METHOD_PLATFORM

async def admin_add_method_name_get(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_method_name"] = update.message.text.strip()
    await update.message.reply_html("📤 <b>এখন আপনার বানানো ভিডিওটি ডিরেক্ট সেন্ড করুন (অথবা ভিডিও ফাইল/লিংক দিন):</b>", reply_markup=cancel_keyboard())
    return ADMIN_ADD_METHOD_FILE

async def admin_save_new_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.video:
        file_id = update.message.video.file_id
    elif update.message.document and update.message.document.mime_type.startswith('video/'):
        file_id = update.message.document.file_id
    elif update.message.text:
        file_id = update.message.text.strip()
    else:
        await update.message.reply_html("❌ <b>সঠিক ভিডিও ফাইল বা লিংক দিন।</b>")
        return ADMIN_ADD_METHOD_FILE

    platform = context.user_data.get("new_method_platform", "Instagram")
    name = context.user_data.get("new_method_name", "Method")

    methods_col.insert_one({
        "platform": platform,
        "name": name,
        "file_id": file_id
    })

    await update.message.reply_html(f"✅ <b>সফলভাবে '{name}' মেথডটি {platform}-এর জন্য সেভ হয়েছে!</b>", reply_markup=admin_custom_keyboard())
    context.user_data.clear()
    return ConversationHandler.END

async def admin_del_method_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text in ["📸 Instagram", "📘 Facebook"]:
        platform = text.replace("📸 ", "").replace("📘 ", "")
        context.user_data["del_method_platform"] = platform
        
        methods = list(methods_col.find({"platform": platform}))
        if not methods:
            await update.message.reply_html(f"⚠️ <b>{platform}-এ ডিলিট করার মতো কোনো মেথড নেই।</b>", reply_markup=admin_custom_keyboard())
            return ConversationHandler.END
        
        keyboard_rows = [[m['name']] for m in methods]
        keyboard_rows.append(["❌ বাতিল"])
        kb = ReplyKeyboardMarkup(keyboard_rows, resize_keyboard=True)
        
        await update.message.reply_html("🗑️ <b>যে মেথডটি ডিলিট করতে চান তার টাইটেল/নামের ওপর চাপ দিন:</b>", reply_markup=kb)
        return ADMIN_DEL_METHOD_SELECT
    
    await update.message.reply_html("❌ সঠিক প্ল্যাটফর্ম সিলেক্ট করুন।")
    return ADMIN_DEL_METHOD_PLATFORM

async def admin_delete_method_exec(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name_to_del = update.message.text.strip()
    platform = context.user_data.get("del_method_platform", "Instagram")
    
    res = methods_col.delete_one({"platform": platform, "name": name_to_del})
    if res.deleted_count > 0:
        await update.message.reply_html(f"✅ <b>'{name_to_del}' মেথডটি সফলভাবে ডিলিট করা হয়েছে!</b>", reply_markup=admin_custom_keyboard())
    else:
        await update.message.reply_html("❌ এই নামের কোনো মেথড পাওয়া যায়নি!", reply_markup=admin_custom_keyboard())
    
    context.user_data.clear()
    return ConversationHandler.END

# ----------------- ADMIN TOTAL USERS EXCEL FILE -----------------
def sync_generate_users_file():
    users = list(users_col.find({}))
    if not users:
        return None

    excel_data = []
    for u in users:
        excel_data.append({
            "Telegram User ID": u.get("user_id"),
            "Account Name": u.get("name", "Unknown"),
            "Balance": u.get("balance", 0.0),
            "Pending Withdraw": u.get("pending_withdraw", 0.0),
            "Completed Tasks": u.get("completed", 0),
            "Total Earned": u.get("total_earned", 0.0),
            "Total Refers": u.get("total_refers", 0)
        })

    df = pd.DataFrame(excel_data)
    filename = f"Total_Users_{datetime.datetime.now().strftime('%d-%m-%Y')}.xlsx"
    df.to_excel(filename, index=False)
    return filename

async def admin_total_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    status_msg = await update.message.reply_html("⏳ <b>ইউজার লিস্টের এক্সেল ফাইল তৈরি করা হচ্ছে...</b>")
    
    filename = await asyncio.to_thread(sync_generate_users_file)
    total_users = users_col.count_documents({})
    
    if not filename:
        await status_msg.edit_text("⚠️ <b>ডাটাবেজে কোনো ইউজার পাওয়া যায়নি।</b>", parse_mode="HTML")
        return

    await status_msg.delete()
    await update.message.reply_document(
        document=open(filename, "rb"),
        caption=f"👥 <b>মোট রেজিস্টার্ড ইউজার ফাইল</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━\n🤖 মোট ইউজার: <code>{total_users}</code> জন",
        parse_mode="HTML"
    )
    if os.path.exists(filename): os.remove(filename)

# ----------------- ADMIN USER MANAGEMENT -----------------
async def admin_prompt_user_mgmt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return ConversationHandler.END
    await update.message.reply_html("👥 <b>ইউজার কন্ট্রোল প্যানেল</b>\n\nযেকোনো ইউজারের তথ্য কন্ট্রোল করতে তার সঠিক <b>Telegram User ID</b> লিখে পাঠান:", reply_markup=cancel_keyboard())
    return ADMIN_USER_MGMT_INPUT

async def admin_get_user_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_html("❌ <b>সঠিক টেলিগ্রাম ইউজার আইডি (সংখ্যায়) দিন:</b>")
        return ADMIN_USER_MGMT_INPUT

    target_id = int(text)
    user = users_col.find_one({"user_id": target_id})
    if not user:
        await update.message.reply_html("⚠️ <b>এই ইউজারআইডি দিয়ে ডাটাবেজে কোনো ইউজার পাওয়া যায়নি! অন্য আইডি দিন:</b>")
        return ADMIN_USER_MGMT_INPUT

    context.user_data["mgmt_user_id"] = target_id
    msg = f"👤 <b>ইউজার প্রোফাইল ও ডাটা</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━\n🆔 <b>User ID:</b> <code>{target_id}</code>\n{EMOJI_MONEY} <b>Balance:</b> <code>{user.get('balance', 0.0)}</code> টাকা\n⏳ <b>Pending Withdraw:</b> <code>{user.get('pending_withdraw', 0.0)}</code> টাকা\n✅ <b>Completed Tasks:</b> <code>{user.get('completed', 0)}</code> টি\n🔍 <b>Review Tasks:</b> <code>{user.get('review', 0)}</code> টি\n{EMOJI_STAR} <b>Total Earned:</b> <code>{user.get('total_earned', 0.0)}</code> টাকা\n━━━━━━━━━━━━━━━━━━━━━━━━━\n👇 <b>কী পরিবর্তন করতে চান সিলেক্ট করুন:</b>"
    kb = ReplyKeyboardMarkup([
        ["💵 ব্যালেন্স পরিবর্তন", "✅ সফল কাজ পরিবর্তন"],
        ["⏳ পেন্ডিং/রিভিউ কাজ পরিবর্তন", "🏆 মোট আয় পরিবর্তন"],
        ["🔙 এডমিন মেনু"]
    ], resize_keyboard=True)
    await update.message.reply_html(msg, reply_markup=kb)
    return ADMIN_USER_EDIT_CHOICE

async def admin_user_edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    choice = update.message.text
    mapping = {
        "💵 ব্যালেন্স পরিবর্তন": "balance",
        "✅ সফল কাজ পরিবর্তন": "completed",
        "⏳ পেন্ডিং/রিভিউ কাজ পরিবর্তন": "review",
        "🏆 মোট আয় পরিবর্তন": "total_earned"
    }
    if choice not in mapping:
        await update.message.reply_html("❌ <b>সঠিক অপশনটি সিলেক্ট করুন।</b>")
        return ADMIN_USER_EDIT_CHOICE

    context.user_data["mgmt_field"] = mapping[choice]
    await update.message.reply_html(f"✍️ <b>আপনি '{choice}' সিলেক্ট করেছেন।</b>\nনতুন মান (Value) কত সেট করতে চান লিখে পাঠান (যেমন: `50` অথবা `-10` কিংবা সরাসরি নতুন সংখ্যা):", reply_markup=cancel_keyboard())
    return ADMIN_USER_EDIT_VALUE

async def admin_user_edit_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        val = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_html("❌ <b>সঠিক সংখ্যা বা পরিমাণ লিখুন:</b>")
        return ADMIN_USER_EDIT_VALUE

    target_id = context.user_data.get("mgmt_user_id")
    field = context.user_data.get("mgmt_field")

    users_col.update_one({"user_id": target_id}, {"$set": {field: val}})
    
    await update.message.reply_html(f"✅ <b>ইউজারের ডাটা সফলভাবে আপডেট করা হয়েছে!</b>\n🎯 ক্ষেত্র: <code>{field}</code> নতুন মান: <code>{val}</code>", reply_markup=admin_keyboard())
    context.user_data.clear()
    return ConversationHandler.END

async def admin_database_management(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    
    total_users = users_col.count_documents({})
    total_tasks = tasks_col.count_documents({})
    total_withdraws = withdraws_col.count_documents({})
    total_methods = methods_col.count_documents({})
    
    pipeline = [{"$group": {"_id": "$date", "count": {"$sum": 1}}}]
    date_stats = list(tasks_col.aggregate(pipeline))
    
    dates_summary = ""
    for stat in date_stats:
        d_date = stat["_id"] if stat["_id"] else "অজানা তারিখ"
        d_count = stat["count"]
        dates_summary += f"📅 তারিখ: <code>{d_date}</code> ➔ টাস্ক সংখ্যা: <code>{d_count}</code> টি\n"
    if not dates_summary:
        dates_summary = "কোনো টাস্ক রেকর্ড পাওয়া যায়নি।"

    msg = f"{EMOJI_SHIELD} <b>ডাটাবেজ ও ফাইল ম্যানেজমেন্ট সেন্টার</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━\n👥 <b>মোট ইউজার রেজিস্টার্ড:</b> <code>{total_users}</code> জন\n📋 <b>মোট টাস্ক/ফাইল জমা:</b> <code>{total_tasks}</code> টি\n💳 <b>মোট উইথড্র রিকোয়েস্ট:</b> <code>{total_withdraws}</code> টি\n{EMOJI_METHOD} <b>মোট মেথড ভিডিও:</b> <code>{total_methods}</code> টি\n━━━━━━━━━━━━━━━━━━━━━━━━━\n📊 <b>তারিখ অনুযায়ী টাস্ক ফাইলের বিবরণী:</b>\n{dates_summary}━━━━━━━━━━━━━━━━━━━━━━━━━\n💡 বট সম্পূর্ণ স্মুথভাবে MongoDB ক্লাউডের সাথে সংযুক্ত রয়েছে।"
    await update.message.reply_html(msg, reply_markup=admin_keyboard())

async def admin_prompt_db_all_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return ConversationHandler.END
    await update.message.reply_html("🔷 <b>কোন প্ল্যাটফর্মের সব ফাইল দেখতে চান? প্ল্যাটফর্ম সিলেক্ট করুন:</b>", reply_markup=platform_choice_keyboard())
    return DB_ALL_FILES_PLATFORM

async def admin_show_db_all_files(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    platform = None
    if text == "📸 Instagram":
        platform = "Instagram"
    elif text == "📘 Facebook":
        platform = "Facebook"
    else:
        await update.message.reply_html("❌ <b>সঠিক প্ল্যাটফর্ম সিলেক্ট করুন!</b>")
        return DB_ALL_FILES_PLATFORM

    tasks = list(tasks_col.find({"platform": platform}).sort("date", -1))
    
    if not tasks:
        await update.message.reply_html(f"⚠️ <b>ডাটাবেজে {platform}-এর কোনো ফাইল বা টাস্ক পাওয়া যায়নি।</b>", reply_markup=admin_keyboard())
        return ConversationHandler.END

    report_text = f"📁 <b>{platform} - সমস্ত ডাটাবেজ ফাইল ও টাস্ক লিস্ট:</b>\n━━━━━━━━━━━━━━━━━━━━━━━━━\n"
    count = 1
    for t in tasks:
        t_date = t.get("date", "অজানা তারিখ")
        t_user = t.get("insta_user") or t.get("fb_uid") or "N/A"
        t_status = t.get("status", "pending")
        t_rate = t.get("rate", 0)
        
        report_text += f"{count}. 📅 তারিখ: <code>{t_date}</code>\n   🆔 আইডি: <code>{t_user}</code>\n   {EMOJI_MONEY} রেট: <code>{t_rate}৳</code> | স্ট্যাটাস: <code>{t_status}</code>\n─────────────────────────\n"
        count += 1
        
        if len(report_text) > 3800:
            await update.message.reply_html(report_text)
            report_text = ""

    if report_text:
        await update.message.reply_html(report_text, reply_markup=admin_keyboard())
    
    context.user_data.clear()
    return ConversationHandler.END

async def admin_prompt_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return ConversationHandler.END
    msg = "📢 <b>ব্রডকাস্ট নোটিশ সেন্ডার</b>\n\nসকল ইউজারদের কাছে পাঠাতে চাওয়া মেসেজটি টাইপ করুন:"
    await update.message.reply_html(msg, reply_markup=cancel_keyboard())
    return ADMIN_BROADCAST_MSG

async def admin_send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_text = update.message.text
    all_users = list(users_col.find({}, {"user_id": 1}))
    
    success, failed = 0, 0
    status_msg = await update.message.reply_html("⏳ <b>ব্রডকাস্ট দ্রুত প্রসেস করা হচ্ছে...</b>")
    
    for u in all_users:
        try:
            broadcast_msg = f"📢 <b>অফিসিয়াল নোটিশ:</b>\n\n{msg_text}"
            await context.bot.send_message(chat_id=u["user_id"], text=broadcast_msg, parse_mode="HTML")
            success += 1
            await asyncio.sleep(0.04)
        except Exception:
            failed += 1

    final_report = f"📢 <b>ব্রডকাস্ট মেসেজ পাঠানো শেষ!</b>\n\n✅ <b>সফল:</b> {success} জন\n❌ <b>ব্যর্থ:</b> {failed} জন"
    await status_msg.edit_text(final_report, parse_mode="HTML")
    await update.message.reply_html(f"{EMOJI_SHIELD} <b>এডমিন কন্ট্রোল প্যানেল:</b>", reply_markup=admin_keyboard())
    return ConversationHandler.END

async def admin_prompt_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return ConversationHandler.END
    curr = get_custom_date()
    msg = f"📅 <b>বর্তমান কাজের সেটিং তারিখ:</b> <code>{curr}</code>\n\nনতুন তারিখটি টাইপ করে দিন (যেমন: `13-08-2026`):"
    await update.message.reply_html(msg, reply_markup=cancel_keyboard())
    return ADMIN_SET_DATE

async def save_admin_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_date = update.message.text.strip()
    config_col.update_one({"id": "settings"}, {"$set": {"active_date": new_date}})
    await update.message.reply_html(f"✅ <b>সফলভাবে নতুন তারিখ সেট হয়েছে:</b> <code>{new_date}</code>", reply_markup=admin_custom_keyboard())
    return ConversationHandler.END

async def admin_prompt_insta_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return ConversationHandler.END
    await update.message.reply_html("🔑 <b>ইন্সটাগ্রামের নতুন ডিফল্ট পাসওয়ার্ড লিখুন:</b>", reply_markup=cancel_keyboard())
    return ADMIN_SET_INSTA_PASS

async def admin_prompt_fb_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return ConversationHandler.END
    await update.message.reply_html("🔑 <b>ফেসবুকের নতুন ডিফল্ট পাসওয়ার্ড লিখুন:</b>", reply_markup=cancel_keyboard())
    return ADMIN_SET_FB_PASS

async def admin_prompt_insta_rates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return ConversationHandler.END
    await update.message.reply_html(f"{EMOJI_MONEY} <b>ইন্সটাগ্রামের রেটসমূহ কমা দিয়ে টাইপ করুন (যেমন: 5, 6, 7):</b>", reply_markup=cancel_keyboard())
    return ADMIN_SET_INSTA_RATE

async def admin_prompt_fb_rates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return ConversationHandler.END
    await update.message.reply_html(f"{EMOJI_MONEY} <b>ফেসবুকের রেটসমূহ কমা দিয়ে টাইপ করুন (যেমন: 5, 6, 7, 8):</b>", reply_markup=cancel_keyboard())
    return ADMIN_SET_FB_RATE

async def admin_prompt_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return ConversationHandler.END
    conf = get_config()
    msg = f"{EMOJI_SUPPORT} <b>সাপোর্ট লিংক কাস্টমাইজ প্যানেল</b>\n\nবর্তমান এডমিন সাপোর্ট লিংক: <code>{conf.get('support_link')}</code>\n\nনতুন এডমিন সাপোর্ট লিংক বা ইউজারনেম পাঠিয়ে দিন:"
    await update.message.reply_html(msg, reply_markup=cancel_keyboard())
    return ADMIN_SET_SUPPORT

async def save_admin_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admin_link = update.message.text.strip()
    config_col.update_one({"id": "settings"}, {"$set": {"support_link": admin_link}})
    await update.message.reply_html("✅ <b>এডমিন সাপোর্ট লিংক সফলভাবে আপডেট করা হয়েছে!</b>", reply_markup=admin_custom_keyboard())
    return ConversationHandler.END

async def save_admin_insta_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config_col.update_one({"id": "settings"}, {"$set": {"insta_pass": update.message.text.strip()}})
    await update.message.reply_html("✅ <b>ইন্সটাগ্রাম পাসওয়ার্ড আপডেট সফল!</b>", reply_markup=admin_custom_keyboard())
    return ConversationHandler.END

async def save_admin_fb_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    config_col.update_one({"id": "settings"}, {"$set": {"fb_pass": update.message.text.strip()}})
    await update.message.reply_html("✅ <b>ফেসবুক পাসওয়ার্ড আপডেট সফল!</b>", reply_markup=admin_custom_keyboard())
    return ConversationHandler.END

async def save_admin_insta_rates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rates = [float(r.strip()) for r in update.message.text.split(",")]
        config_col.update_one({"id": "settings"}, {"$set": {"insta_rates": rates}})
        await update.message.reply_html("✅ <b>ইন্সটাগ্রাম রেটসমূহ সফলভাবে সেভ হয়েছে!</b>", reply_markup=admin_custom_keyboard())
    except ValueError:
        await update.message.reply_html("❌ <b>ভুল ফরম্যাট! কমা দিয়ে সঠিক নম্বর দিন (যেমন: 5, 6, 7)</b>")
        return ADMIN_SET_INSTA_RATE
    return ConversationHandler.END

async def save_admin_fb_rates(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rates = [float(r.strip()) for r in update.message.text.split(",")]
        config_col.update_one({"id": "settings"}, {"$set": {"fb_rates": rates}})
        await update.message.reply_html("✅ <b>ফেসবুক রেটসমূহ সফলভাবে সেভ হয়েছে!</b>", reply_markup=admin_custom_keyboard())
    except ValueError:
        await update.message.reply_html("❌ <b>ভুল ফরম্যাট! কমা দিয়ে সঠিক নম্বর দিন (যেমন: 5, 6, 7, 8)</b>")
        return ADMIN_SET_FB_RATE
    return ConversationHandler.END

async def admin_prompt_file_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return ConversationHandler.END
    await update.message.reply_html("🔷 <b>কোন প্ল্যাটফর্মের ফাইল ডাউনলোড করবেন? প্ল্যাটফর্ম সিলেক্ট করুন:</b>", reply_markup=platform_choice_keyboard())
    return ADMIN_SELECT_FILE_PLATFORM

async def admin_select_file_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📸 Instagram":
        context.user_data["download_platform"] = "Instagram"
    elif text == "📘 Facebook":
        context.user_data["download_platform"] = "Facebook"
    else:
        await update.message.reply_html("❌ <b>সঠিক প্ল্যাটফর্ম সিলেক্ট করুন!</b>")
        return ADMIN_SELECT_FILE_PLATFORM
    
    curr = get_custom_date()
    await update.message.reply_html(f"📅 <b>{context.user_data['download_platform']}-এর ফাইলের তারিখ দিন (ডিফল্ট/বর্তমান: {curr}):</b>", reply_markup=cancel_keyboard())
    return ADMIN_GET_DATE_FILE

def sync_generate_file(date_str, target_platform):
    tasks = list(tasks_col.find({"date": date_str, "platform": target_platform}))
    if not tasks:
        return None

    excel_data = []
    for t in tasks:
        if target_platform == "Facebook":
            excel_data.append({
                "Platform": "Facebook",
                "FB UID": t.get("fb_uid"),
                "Password": t.get("fb_pass"),
                "Cookies": t.get("fb_cookies"),
                "Telegram ID": t.get("user_id"),
                "Name": t.get("name"),
                "Rate": t.get("rate"),
                "Date": t.get("date")
            })
        else:
            excel_data.append({
                "Platform": "Instagram",
                "Instagram Username": t.get("insta_user"),
                "Password": t.get("insta_pass"),
                "2FA Key": t.get("key_2fa"),
                "Telegram ID": t.get("user_id"),
                "Name": t.get("name"),
                "Rate": t.get("rate"),
                "Date": t.get("date")
            })

    df = pd.DataFrame(excel_data)
    filename = f"{target_platform}_Tasks_{date_str}.xlsx"
    df.to_excel(filename, index=False)
    return filename

async def admin_generate_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_str = update.message.text.strip()
    target_platform = context.user_data.get("download_platform", "Instagram")
    
    filename = await asyncio.to_thread(sync_generate_file, date_str, target_platform)
    
    if not filename:
        await update.message.reply_html(f"❌ <b>{date_str} তারিখে {target_platform}-এর কোনো কাজ পাওয়া যায়নি।</b>", reply_markup=admin_all_tasks_keyboard())
        return ConversationHandler.END

    await update.message.reply_document(
        document=open(filename, "rb"), 
        caption=f"📁 <b>{target_platform} টাস্ক ফাইল ({date_str})</b>", 
        parse_mode="HTML"
    )
    if os.path.exists(filename): os.remove(filename)
    await update.message.reply_html(f"{EMOJI_WORK} <b>টাস্ক সেন্টার:</b>", reply_markup=admin_all_tasks_keyboard())
    return ConversationHandler.END

async def admin_prompt_report_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return ConversationHandler.END
    await update.message.reply_html("🔷 <b>কোন প্ল্যাটফর্মের রিপোর্ট জমা দেবেন? প্ল্যাটফর্ম সিলেক্ট করুন:</b>", reply_markup=platform_choice_keyboard())
    return ADMIN_SELECT_REPORT_PLATFORM

async def admin_select_report_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "📸 Instagram":
        context.user_data["report_platform"] = "Instagram"
    elif text == "📘 Facebook":
        context.user_data["report_platform"] = "Facebook"
    else:
        await update.message.reply_html("❌ <b>সঠিক প্ল্যাটফর্ম সিলেক্ট করুন!</b>")
        return ADMIN_SELECT_REPORT_PLATFORM

    curr = get_custom_date()
    await update.message.reply_html(f"📅 <b>{context.user_data['report_platform']} রিপোর্টের তারিখটি টাইপ করুন (ডিফল্ট/বর্তমান: {curr}):</b>", reply_markup=cancel_keyboard())
    return ADMIN_GET_DATE_REPORT

async def admin_receive_report_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    date_str = update.message.text.strip()
    context.user_data["report_date"] = date_str
    target_platform = context.user_data.get("report_platform")
    await update.message.reply_html(f"📤 <b>এখন {target_platform}-এর {date_str} তারিখের কালার করা এক্সেল ফাইল (.xlsx) সেন্ড করুন:</b>")
    return ADMIN_UPLOAD_REPORT

def sync_process_excel_report(file_path, report_date, target_platform):
    wb = openpyxl.load_workbook(file_path)
    sheet = wb.active

    approved_list, rejected_list = [], []

    for row in range(2, sheet.max_row + 1):
        cell = sheet.cell(row=row, column=2)
        target_id = str(cell.value).strip() if cell.value else None
        if not target_id: continue

        query = {"date": report_date, "status": "pending", "platform": target_platform}
        if target_platform == "Facebook":
            query["fb_uid"] = target_id
        else:
            query["insta_user"] = target_id

        task = tasks_col.find_one(query)
        if not task: continue

        is_green = False
        if cell.fill and cell.fill.start_color:
            rgb = str(cell.fill.start_color.rgb)
            if rgb in ["FF00FF00", "00FF00", "FF008000", "92D050", "00B050"] or (len(rgb) == 8 and rgb[2:4] > "80" and rgb[4:6] > "80"):
                is_green = True

        user_id, rate = task["user_id"], task["rate"]

        if is_green:
            tasks_col.update_one({"_id": task["_id"]}, {"$set": {"status": "approved"}})
            users_col.update_one({"user_id": user_id}, {"$inc": {"balance": rate, "total_earned": rate, "completed": 1, "review": -1}})
            approved_list.append((user_id, target_id, rate))
        else:
            tasks_col.update_one({"_id": task["_id"]}, {"$set": {"status": "rejected"}})
            users_col.update_one({"user_id": user_id}, {"$inc": {"review": -1}})
            rejected_list.append((user_id, target_id))

    return approved_list, rejected_list

async def admin_process_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc or not doc.file_name.endswith(('.xlsx', '.xls')):
        await update.message.reply_html("❌ <b>অবশ্যই একটি এক্সেল (.xlsx) ফাইল সেন্ড করুন!</b>")
        return ADMIN_UPLOAD_REPORT

    report_date = context.user_data.get("report_date")
    target_platform = context.user_data.get("report_platform")
    
    status_msg = await update.message.reply_html("⏳ <b>রিপোর্ট হিসাব করে প্রসেস করা হচ্ছে...</b>")

    file = await doc.get_file()
    file_path = "temp_report.xlsx"
    await file.download_to_drive(file_path)

    approved_list, rejected_list = await asyncio.to_thread(sync_process_excel_report, file_path, report_date, target_platform)

    if os.path.exists(file_path): os.remove(file_path)

    for uid, tid, rate in approved_list:
        try:
            msg_approved = f"{EMOJI_STAR} <b>আপনার {target_platform} টাস্কটি অ্যাপ্রুভ হয়েছে!</b>\n\n🆔 <b>আইডি/ইউজার:</b> <code>{tid}</code>\n{EMOJI_MONEY} <b>অ্যাপ্রুভড ব্যালেন্স:</b> <b>+{rate} টাকা</b>"
            await context.bot.send_message(uid, msg_approved, parse_mode="HTML")
            await asyncio.sleep(0.03)
        except Exception: pass

    for uid, tid in rejected_list:
        try:
            msg_rejected = f"❌ <b>আপনার {target_platform} টাস্কটি রিজেক্ট হয়েছে!</b>\n\n🆔 <b>আইডি/ইউজার:</b> <code>{tid}</code>"
            await context.bot.send_message(uid, msg_rejected, parse_mode="HTML")
            await asyncio.sleep(0.03)
        except Exception: pass

    res_msg = f"📊 <b>{target_platform} ({report_date}) তারিখের রিপোর্ট আপডেট সম্পন্ন!</b>\n\n✅ <b>অনুমোদিত:</b> {len(approved_list)} টি\n❌ <b>বাতিল:</b> {len(rejected_list)} টি"
    await status_msg.edit_text(res_msg, parse_mode="HTML")
    await update.message.reply_html(f"{EMOJI_WORK} <b>টাস্ক সেন্টার:</b>", reply_markup=admin_all_tasks_keyboard())
    return ConversationHandler.END

app_flask = Flask('')

@app_flask.route('/')
def home():
    return "Bot is running active and smooth!"

def run_web():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    global_cancel_filter = filters.Regex(r"^❌ বাতিল$")
    global_back_filter = filters.Regex(r"^(🔙 পেছনে যান|🔙 মূল মেনু|🔙 এডমিন মেনু|🔙 কাস্টমাইজ মেনু)$")
    main_menu_filter = filters.Regex(r"^(💎 আমার ব্যালেন্স|⚡ রেফারেল লিংক|🎧 হেল্প ও সাপোর্ট)$")

    conv_method = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^📚 মেথড$"), method_start)],
        states={
            METHOD_SELECT_PLATFORM: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, method_platform_selected)],
            METHOD_AVAILABLE_MENU: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, method_show_titles)],
            METHOD_SEND_VIDEO: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, method_send_video)]
        },
        fallbacks=[
            MessageHandler(global_cancel_filter, cancel_handler),
            MessageHandler(global_back_filter, smart_back_handler),
            MessageHandler(main_menu_filter, cancel_handler)
        ]
    )

    conv_work = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^💼 কাজ শুরু করুন$"), work_start)],
        states={
            WORK_SELECT_PLATFORM: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, work_platform_selected)],
            WORK_SELECT_TYPE: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, work_type_selected)],
            WORK_SELECT_RATE: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, work_rate_selected)],
            ENTERING_2FA: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, process_account_created)],
            TASK_CONFIRM: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, task_complete_done)],
            FB_SELECT_TYPE: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, fb_type_selected)],
            FB_SELECT_COOKIE_TYPE: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, fb_cookie_type_selected)],
            FB_SELECT_RATE: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, fb_rate_selected)],
            FB_ENTER_UID: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, fb_process_account_created)],
            FB_ENTER_COOKIES: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, fb_get_uid)],
            FB_TASK_CONFIRM: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, fb_task_complete_done)],
        },
        fallbacks=[
            MessageHandler(global_cancel_filter, cancel_handler),
            MessageHandler(global_back_filter, smart_back_handler),
            MessageHandler(main_menu_filter, cancel_handler)
        ]
    )

    conv_withdraw = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^💳 টাকা উত্তোলন$"), withdraw_start)],
        states={
            WITHDRAW_METHOD: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, withdraw_select_method)],
            WITHDRAW_NUMBER: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, withdraw_get_number)],
            WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, withdraw_process_amount)],
        },
        fallbacks=[
            MessageHandler(global_cancel_filter, cancel_handler),
            MessageHandler(global_back_filter, smart_back_handler),
            MessageHandler(main_menu_filter, cancel_handler)
        ]
    )

    conv_admin_broadcast = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^📢 ব্রডকাস্ট মেসেজ$"), admin_prompt_broadcast)],
        states={
            ADMIN_BROADCAST_MSG: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, admin_send_broadcast)]
        },
        fallbacks=[
            MessageHandler(global_cancel_filter, cancel_handler),
            MessageHandler(global_back_filter, smart_back_handler)
        ]
    )

    conv_admin_user_mgmt = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^👥 ইউজার কন্ট্রোল$"), admin_prompt_user_mgmt)],
        states={
            ADMIN_USER_MGMT_INPUT: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, admin_get_user_info)],
            ADMIN_USER_EDIT_CHOICE: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, admin_user_edit_choice)],
            ADMIN_USER_EDIT_VALUE: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, admin_user_edit_save)]
        },
        fallbacks=[
            MessageHandler(global_cancel_filter, cancel_handler),
            MessageHandler(global_back_filter, smart_back_handler)
        ]
    )

    conv_db_all_files = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^📁 অল ফাইল$"), admin_prompt_db_all_files)],
        states={
            DB_ALL_FILES_PLATFORM: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, admin_show_db_all_files)]
        },
        fallbacks=[
            MessageHandler(global_cancel_filter, cancel_handler),
            MessageHandler(global_back_filter, smart_back_handler)
        ]
    )

    conv_admin_settings = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r"^📅 তারিখ সেট করুন$"), admin_prompt_date),
            MessageHandler(filters.Regex(r"^🔌 কাজ অন/অফ$"), admin_task_on_off_menu),
            MessageHandler(filters.Regex(r"^🔑 ইন্সটাগ্রাম পাসওয়ার্ড$"), admin_prompt_insta_pass),
            MessageHandler(filters.Regex(r"^🔑 ফেসবুক পাসওয়ার্ড$"), admin_prompt_fb_pass),
            MessageHandler(filters.Regex(r"^💵 ইন্সটাগ্রাম রেট$"), admin_prompt_insta_rates),
            MessageHandler(filters.Regex(r"^💵 ফেসবুক রেট$"), admin_prompt_fb_rates),
            MessageHandler(filters.Regex(r"^🎧 সাপোর্ট লিংক সেট$"), admin_prompt_support),
            MessageHandler(filters.Regex(r"^📁 মেথড ম্যানেজমেন্ট$"), admin_method_menu),
            MessageHandler(filters.Regex(r"^📥 ফাইল ডাউনলোড$"), admin_prompt_file_platform),
            MessageHandler(filters.Regex(r"^📤 রিপোর্ট জমা দিন$"), admin_prompt_report_platform)
        ],
        states={
            ADMIN_SET_DATE: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, save_admin_date)],
            ADMIN_TASK_ON_OFF_MENU: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, admin_toggle_task_status)],
            ADMIN_SET_INSTA_PASS: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, save_admin_insta_pass)],
            ADMIN_SET_FB_PASS: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, save_admin_fb_pass)],
            ADMIN_SET_INSTA_RATE: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, save_admin_insta_rates)],
            ADMIN_SET_FB_RATE: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, save_admin_fb_rates)],
            ADMIN_SET_SUPPORT: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, save_admin_support)],
            ADMIN_METHOD_MENU: [MessageHandler(filters.Text & ~global_cancel_filter & ~global_back_filter, admin_method_actions)],
            ADMIN_ADD_METHOD_PLATFORM: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, admin_add_method_platform)],
            ADMIN_ADD_METHOD_NAME: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, admin_add_method_name_get)],
            ADMIN_ADD_METHOD_FILE: [MessageHandler((filters.VIDEO | filters.Document.VIDEO | filters.TEXT) & ~global_cancel_filter & ~global_back_filter, admin_save_new_method)],
            ADMIN_DEL_METHOD_PLATFORM: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, admin_del_method_platform)],
            ADMIN_DEL_METHOD_SELECT: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, admin_delete_method_exec)],
            ADMIN_SELECT_FILE_PLATFORM: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, admin_select_file_platform)],
            ADMIN_GET_DATE_FILE: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, admin_generate_file)],
            ADMIN_SELECT_REPORT_PLATFORM: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, admin_select_report_platform)],
            ADMIN_GET_DATE_REPORT: [MessageHandler(filters.TEXT & ~global_cancel_filter & ~global_back_filter, admin_receive_report_date)],
            ADMIN_UPLOAD_REPORT: [MessageHandler(filters.Document.ALL & ~global_cancel_filter & ~global_back_filter, admin_process_report)]
        },
        fallbacks=[
            MessageHandler(global_cancel_filter, cancel_handler),
            MessageHandler(global_back_filter, smart_back_handler)
        ]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    
    app.add_handler(MessageHandler(filters.Regex(r"^💎 আমার ব্যালেন্স$"), balance))
    app.add_handler(MessageHandler(filters.Regex(r"^⚡ রেফারেল লিংক$"), refer_info))
    app.add_handler(MessageHandler(filters.Regex(r"^🎧 হেল্প ও সাপোর্ট$"), support_info))
    app.add_handler(MessageHandler(filters.Regex(r"^🗄️ ডাটাবেজ ম্যানেজমেন্ট$"), admin_database_management))
    app.add_handler(MessageHandler(filters.Regex(r"^👥 মোট ইউজার$"), admin_total_users))
    
    app.add_handler(conv_method)
    app.add_handler(conv_work)
    app.add_handler(conv_withdraw)
    app.add_handler(conv_admin_broadcast)
    app.add_handler(conv_admin_user_mgmt)
    app.add_handler(conv_db_all_files)
    app.add_handler(conv_admin_settings)

    app.add_handler(MessageHandler(filters.Regex(r"^⚙️ কাজ কাস্টমাইজ$"), lambda u,c: u.message.reply_html(f"{EMOJI_WORK} <b>কাস্টমাইজেশন প্যানেল:</b>", reply_markup=admin_custom_keyboard())))
    app.add_handler(MessageHandler(filters.Regex(r"^💸 উইথড্র কন্ট্রোল$"), admin_withdraw_custom))
    app.add_handler(MessageHandler(filters.Regex(r"^📁 অল টাস্ক সেন্টার$"), lambda u,c: u.message.reply_html(f"{EMOJI_WORK} <b>টাস্ক ফাইল সেন্টার:</b>", reply_markup=admin_all_tasks_keyboard())))

    app.add_handler(MessageHandler(filters.Regex(r"^/(approve|reject)_\d+$"), admin_handle_withdraw_actions))

    app.add_handler(MessageHandler(global_cancel_filter, cancel_handler))
    app.add_handler(MessageHandler(global_back_filter, smart_back_handler))

    keep_alive()
    print("🚀 ফ্লাস্ক সার্ভার এবং টেলিগ্রাম বট সফলভাবে রান হচ্ছে!")
    app.run_polling()

if __name__ == "__main__":
    main()