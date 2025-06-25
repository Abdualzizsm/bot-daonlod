#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import re
import tempfile
import asyncio
import hashlib
import shutil
import json
import threading
import time
import random
import fcntl  # لحماية الملفات
import atexit
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Dict, Any
from datetime import datetime
import yt_dlp
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaVideo, InputMediaAudio
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode, ChatAction
from telegram.error import TelegramError, Conflict
from dotenv import load_dotenv

# === نظام الإحصائيات المدمج ===
STATS_ENABLED = True
STATS_FILE = "bot_stats.json"
bot_stats = {
    "total_users": 0,
    "total_downloads": 0,
    "video_downloads": 0,
    "audio_downloads": 0,
    "start_time": time.time(),
    "daily_stats": {}
}

def load_stats():
    """تحميل الإحصائيات من الملف"""
    global bot_stats
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r', encoding='utf-8') as f:
                loaded_stats = json.load(f)
                bot_stats.update(loaded_stats)
                
                # تحويل قائمة المستخدمين إلى set للمعالجة السريعة
                if 'users' in bot_stats and isinstance(bot_stats['users'], list):
                    bot_stats['users'] = set(bot_stats['users'])
                    
                print("✅ تم تحميل الإحصائيات بنجاح")
        else:
            save_stats()
            print("📊 تم إنشاء ملف إحصائيات جديد")
    except Exception as e:
        print(f"⚠️ خطأ في تحميل الإحصائيات: {e}")

def save_stats():
    """حفظ الإحصائيات في الملف"""
    try:
        # تحويل set إلى list للحفظ في JSON
        stats_to_save = bot_stats.copy()
        if 'users' in stats_to_save and isinstance(stats_to_save['users'], set):
            stats_to_save['users'] = list(stats_to_save['users'])
            
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(stats_to_save, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ خطأ في حفظ الإحصائيات: {e}")

def update_stats(stat_type: str, user_id: int = None):
    """تحديث الإحصائيات"""
    if not STATS_ENABLED:
        return
    
    try:
        if stat_type == 'total_users' and user_id:
            # إضافة مستخدم جديد
            if 'users' not in bot_stats:
                bot_stats['users'] = set()
            
            if user_id not in bot_stats['users']:
                bot_stats['users'].add(user_id)
                bot_stats['total_users'] = len(bot_stats['users'])
                
        elif stat_type == 'video_downloads':
            bot_stats['video_downloads'] = bot_stats.get('video_downloads', 0) + 1
            bot_stats['total_downloads'] = bot_stats.get('total_downloads', 0) + 1
            
            # إحصائيات يومية
            today = datetime.now().strftime("%Y-%m-%d")
            if 'daily_stats' not in bot_stats:
                bot_stats['daily_stats'] = {}
            bot_stats['daily_stats'][today] = bot_stats['daily_stats'].get(today, 0) + 1
            
        elif stat_type == 'audio_downloads':
            bot_stats['audio_downloads'] = bot_stats.get('audio_downloads', 0) + 1
            bot_stats['total_downloads'] = bot_stats.get('total_downloads', 0) + 1
            
            # إحصائيات يومية
            today = datetime.now().strftime("%Y-%m-%d")
            if 'daily_stats' not in bot_stats:
                bot_stats['daily_stats'] = {}
            bot_stats['daily_stats'][today] = bot_stats['daily_stats'].get(today, 0) + 1
        
        # حفظ الإحصائيات
        save_stats()
        
    except Exception as e:
        logging.getLogger(__name__).error(f"خطأ في تحديث الإحصائيات: {e}")

def add_user(user_id):
    """إضافة مستخدم جديد"""
    if STATS_ENABLED:
        update_stats('total_users', user_id)

def add_download(download_type):
    """إضافة تحميل جديد"""
    if STATS_ENABLED:
        update_stats(download_type)

def get_stats():
    """الحصول على الإحصائيات"""
    if not STATS_ENABLED:
        return {}
    
    uptime_hours = round((time.time() - bot_stats.get("start_time", time.time())) / 3600, 1)
    today = datetime.now().strftime("%Y-%m-%d")
    today_downloads = bot_stats.get("daily_stats", {}).get(today, 0)
    
    return {
        "total_users": bot_stats.get("total_users", 0),
        "total_downloads": bot_stats.get("total_downloads", 0),
        "video_downloads": bot_stats.get("video_downloads", 0),
        "audio_downloads": bot_stats.get("audio_downloads", 0),
        "uptime_hours": uptime_hours,
        "today_downloads": today_downloads
    }

# استيراد Flask للوحة التحكم
try:
    from flask import Flask, render_template_string, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    print("تحذير: Flask غير مثبت - لوحة التحكم غير متاحة")
    FLASK_AVAILABLE = False

# === لوحة التحكم Flask ===
if FLASK_AVAILABLE:
    dashboard_app = Flask(__name__)
    
    # قالب HTML للوحة التحكم
    DASHBOARD_HTML = """
    <!DOCTYPE html>
    <html lang="ar" dir="rtl">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>لوحة تحكم البوت</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { text-align: center; color: white; margin-bottom: 30px; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
            .stat-card { background: white; border-radius: 15px; padding: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.1); transition: transform 0.3s ease; }
            .stat-card:hover { transform: translateY(-5px); }
            .stat-number { font-size: 2.5em; font-weight: bold; color: #667eea; margin-bottom: 10px; }
            .stat-label { color: #666; font-size: 1.1em; }
            .refresh-btn { background: #667eea; color: white; border: none; padding: 12px 25px; border-radius: 25px; cursor: pointer; font-size: 16px; margin: 20px auto; display: block; }
            .refresh-btn:hover { background: #5a67d8; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🤖 لوحة تحكم بوت التحميل</h1>
                <p>مراقبة إحصائيات البوت في الوقت الفعلي</p>
            </div>
            
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number" id="total-users">0</div>
                    <div class="stat-label">👥 إجمالي المستخدمين</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-number" id="total-downloads">0</div>
                    <div class="stat-label">📥 إجمالي التحميلات</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-number" id="video-downloads">0</div>
                    <div class="stat-label">🎥 تحميلات الفيديو</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-number" id="audio-downloads">0</div>
                    <div class="stat-label">🎵 تحميلات الصوت</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-number" id="uptime">0</div>
                    <div class="stat-label">⏰ وقت التشغيل (ساعات)</div>
                </div>
                
                <div class="stat-card">
                    <div class="stat-number" id="today-downloads">0</div>
                    <div class="stat-label">📅 تحميلات اليوم</div>
                </div>
            </div>
            
            <button class="refresh-btn" onclick="loadStats()">🔄 تحديث الإحصائيات</button>
        </div>
        
        <script>
            function loadStats() {
                fetch('/api/stats')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('total-users').textContent = data.total_users || 0;
                        document.getElementById('total-downloads').textContent = data.total_downloads || 0;
                        document.getElementById('video-downloads').textContent = data.video_downloads || 0;
                        document.getElementById('audio-downloads').textContent = data.audio_downloads || 0;
                        document.getElementById('uptime').textContent = data.uptime_hours || 0;
                        document.getElementById('today-downloads').textContent = data.today_downloads || 0;
                    })
                    .catch(error => console.error('خطأ في تحميل الإحصائيات:', error));
            }
            
            // تحديث تلقائي كل 30 ثانية
            setInterval(loadStats, 30000);
            
            // تحميل أولي
            loadStats();
        </script>
    </body>
    </html>
    """
    
    @dashboard_app.route('/')
    def dashboard():
        return render_template_string(DASHBOARD_HTML)
    
    @dashboard_app.route('/api/stats')
    def api_stats():
        stats = get_stats()
        return jsonify(stats)
    
    def run_dashboard():
        """تشغيل خادم لوحة التحكم"""
        try:
            port = int(os.environ.get('PORT', 5002))
            dashboard_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)
        except Exception as e:
            print(f"❌ خطأ في تشغيل لوحة التحكم: {e}")

# إعداد اللوغيغ
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تحميل متغيرات البيئة
load_dotenv()

# إعداد مجلد التحميل المؤقت
DOWNLOAD_PATH = tempfile.mkdtemp()

# متغير لحفظ الروابط مؤقتاً
TEMP_URLS = {}

# المنصات المدعومة
SUPPORTED_PLATFORMS = {
    'youtube.com': '🎬 يوتيوب',
    'youtu.be': '🎬 يوتيوب',
    'tiktok.com': '🎵 تيك توك',
    'instagram.com': '📸 انستاغرام',
    'facebook.com': '📚 فيسبوك',
    'twitter.com': '🐦 تويتر',
    'x.com': '🐦 X (تويتر)',
    'soundcloud.com': '🎵 ساوند كلاود',
    'vimeo.com': '🎥 فيميو'
}

async def reset_webhook():
    """إعادة تعيين الويب هوك"""
    try:
        bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if not bot_token:
            logger.error("لم يتم العثور على توكن البوت")
            return
            
        url = f"https://api.telegram.org/bot{bot_token}/deleteWebhook"
        response = requests.post(url)
        if response.status_code == 200:
            logger.info("تم حذف الويب هوك بنجاح")
        else:
            logger.error(f"فشل في حذف الويب هوك: {response.text}")
    except Exception as e:
        logger.error(f"خطأ في إعادة تعيين الويب هوك: {e}")

def is_supported_url(url: str) -> bool:
    """التحقق من دعم الرابط"""
    try:
        parsed_url = urlparse(url.lower())
        domain = parsed_url.netloc.replace('www.', '')
        return any(platform in domain for platform in SUPPORTED_PLATFORMS.keys())
    except:
        return False

def get_platform_name(url: str) -> str:
    """الحصول على اسم المنصة"""
    try:
        parsed_url = urlparse(url.lower())
        domain = parsed_url.netloc.replace('www.', '')
        for platform, name in SUPPORTED_PLATFORMS.items():
            if platform in domain:
                return name
        return "🌐 غير محدد"
    except:
        return "🌐 غير محدد"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر البداية"""
    user = update.effective_user
    
    # تحديث إحصائيات المستخدمين
    add_user(user.id)
    
    welcome_message = f"""
🎉 *أهلاً وسهلاً {user.first_name}!*

🤖 *بوت التحميل الاحترافي*
━━━━━━━━━━━━━━━━━━━━━

✨ *المميزات:*
🎬 تحميل فيديو بأعلى جودة متوفرة
🎵 استخراج الصوت بجودة عالية
📱 واجهة بسيطة وسهلة الاستخدام
⚡ سرعة تحميل فائقة

🌐 *المنصات المدعومة:*
• يوتيوب (YouTube)
• تيك توك (TikTok)  
• انستاغرام (Instagram)
• فيسبوك (Facebook)
• تويتر/X (Twitter)
• ساوند كلاود (SoundCloud)
• فيميو (Vimeo)

📝 *طريقة الاستخدام:*
1️⃣ أرسل رابط الفيديو
2️⃣ اختر نوع التحميل
3️⃣ انتظر التحميل والإرسال

🚀 *ابدأ الآن بإرسال أي رابط!*
"""
    
    await update.message.reply_text(
        welcome_message,
        parse_mode=ParseMode.MARKDOWN
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر المساعدة"""
    help_text = """
🆘 *دليل الاستخدام*
━━━━━━━━━━━━━━━━━━━━━

📋 *الأوامر المتاحة:*
• `/start` - بدء استخدام البوت
• `/help` - عرض هذه المساعدة

🔗 *كيفية التحميل:*
1️⃣ انسخ رابط الفيديو من أي منصة مدعومة
2️⃣ أرسل الرابط للبوت
3️⃣ اختر نوع التحميل:
   • 🎬 فيديو بأعلى جودة
   • 🎵 صوت فقط

⚠️ *ملاحظات مهمة:*
• تأكد من صحة الرابط
• الفيديوهات الطويلة قد تستغرق وقتاً أطول
• يتم حذف الملفات تلقائياً بعد الإرسال

🌐 *المنصات المدعومة:*
YouTube, TikTok, Instagram, Facebook, Twitter, SoundCloud, Vimeo

❓ *مشاكل؟* تأكد من أن الرابط صحيح ومن منصة مدعومة
"""
    
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الروابط"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "مجهول"
    url = update.message.text.strip()
    
    # فحص معدل الطلبات
    if not check_rate_limit(user_id):
        remaining_time = RATE_LIMIT_WINDOW - (time.time() - min(user_request_tracker[user_id]))
        await update.message.reply_text(
            f"⏰ *تم تجاوز الحد المسموح من الطلبات*\n\n"
            f"🔄 يمكنك إرسال طلب جديد بعد: {remaining_time/60:.1f} دقيقة\n"
            f"📊 الحد المسموح: {RATE_LIMIT_REQUESTS} طلبات كل {RATE_LIMIT_WINDOW/60:.0f} دقائق\n\n"
            f"💡 *نصيحة:* هذا النظام يحمي البوت من التحميل الزائد",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    logger.info(f"طلب تحميل من المستخدم {username} ({user_id}): {url}")
    
    # التحقق من صحة الرابط
    if not is_supported_url(url):
        await update.message.reply_text(
            "❌ *رابط غير صالح*\n\n"
            "📝 *الروابط المدعومة:*\n"
            "• YouTube\n"
            "• Instagram\n"
            "• TikTok\n"
            "• Twitter/X\n"
            "• Facebook\n"
            "• وغيرها...\n\n"
            "💡 تأكد من نسخ الرابط كاملاً",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # إنشاء hash فريد للرابط
    url_hash = hash(url + str(user_id))
    TEMP_URLS[url_hash] = {
        'url': url,
        'user_id': user_id,
        'timestamp': time.time()
    }
    
    # إنشاء لوحة الخيارات
    keyboard = [
        [
            InlineKeyboardButton("🎬 فيديو عالي الجودة", callback_data=f"video_best_{url_hash}"),
            InlineKeyboardButton("🎵 صوت فقط", callback_data=f"audio_{url_hash}")
        ],
        [
            InlineKeyboardButton("📱 فيديو متوسط الجودة", callback_data=f"video_medium_{url_hash}"),
            InlineKeyboardButton("📺 فيديو منخفض الجودة", callback_data=f"video_low_{url_hash}")
        ],
        [
            InlineKeyboardButton("ℹ️ معلومات الفيديو", callback_data=f"info_{url_hash}")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # إرسال رسالة الخيارات مع معاينة الرابط
    try:
        # محاولة الحصول على معلومات أساسية للمعاينة
        preview_text = f"🔗 *تم استلام الرابط*\n\n"
        preview_text += f"📋 اختر نوع التحميل المطلوب:\n\n"
        preview_text += f"🎯 *نصائح للاستخدام الأمثل:*\n"
        preview_text += f"• الفيديو عالي الجودة قد يكون كبير الحجم\n"
        preview_text += f"• الصوت فقط أسرع في التحميل\n"
        preview_text += f"• الجودة المتوسطة متوازنة\n\n"
        preview_text += f"⚡ *معدل الطلبات:* {len(user_request_tracker.get(user_id, []))}/{RATE_LIMIT_REQUESTS}"
        
        await update.message.reply_text(
            preview_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        
        # تحديث الإحصائيات
        if STATS_ENABLED:
            update_stats('total_users', user_id)
            
    except Exception as e:
        logger.error(f"خطأ في معالجة الرابط: {e}")
        await update.message.reply_text(
            "❌ *خطأ في معالجة الرابط*\n\n"
            "🔄 يرجى المحاولة مرة أخرى\n"
            "أو التأكد من صحة الرابط",
            parse_mode=ParseMode.MARKDOWN
        )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الضغط على الأزرار"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    callback_data = query.data
    
    logger.info(f"تم الضغط على زر من المستخدم {user.id}: {callback_data}")
    
    # تحليل البيانات
    try:
        download_type, url_hash = callback_data.split('_', 1)
    except ValueError:
        await query.edit_message_text("❌ خطأ في تحليل البيانات")
        return
    
    # البحث عن الرابط
    if url_hash not in TEMP_URLS:
        await query.edit_message_text(
            "❌ *انتهت صلاحية الرابط*\n\n"
            "🔄 يرجى إرسال الرابط مرة أخرى",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    url = TEMP_URLS[url_hash]['url']
    logger.info(f"تم العثور على الرابط: {url}")
    
    # تحديث إحصائيات التحميل
    add_download(download_type)
    
    # بدء التحميل
    if download_type == "video_best":
        await download_video(query, url, "best[ext=mp4]/best")
    elif download_type == "video_medium":
        await download_video(query, url, "best[ext=mp4][height<=480]/best")
    elif download_type == "video_low":
        await download_video(query, url, "best[ext=mp4][height<=240]/best")
    elif download_type == "audio":
        await download_audio(query, url)
    elif download_type == "info":
        await get_video_info(query, url)
    
    # حذف الرابط من الذاكرة المؤقتة
    del TEMP_URLS[url_hash]

MAX_FILE_SIZE = 50 * 1024 * 1024

# قائمة User-Agents متنوعة لتجنب الحظر
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36'
]

# قائمة Accept-Language متنوعة
ACCEPT_LANGUAGES = [
    'en-US,en;q=0.9',
    'en-GB,en;q=0.9',
    'en-US,en;q=0.8,ar;q=0.7',
    'en-GB,en;q=0.8,fr;q=0.7',
    'en-US,en;q=0.9,es;q=0.8',
    'en,en-US;q=0.9',
    'en-US,en;q=0.5',
]

# نظام تتبع معدل الطلبات لكل مستخدم
user_request_tracker = {}
RATE_LIMIT_REQUESTS = 5  # عدد الطلبات المسموحة
RATE_LIMIT_WINDOW = 300  # خلال 5 دقائق (بالثواني)

def get_random_headers():
    """إنشاء headers عشوائية لتجنب الحظر"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36'
    ]
    
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': random.choice(['en-US,en;q=0.5', 'ar,en;q=0.9', 'en-GB,en;q=0.8']),
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }

def is_supported_url(url):
    """فحص إذا كان الرابط مدعوماً"""
    supported_domains = [
        'youtube.com', 'youtu.be', 'tiktok.com', 'instagram.com',
        'facebook.com', 'twitter.com', 'x.com', 'soundcloud.com',
        'vimeo.com', 'dailymotion.com', 'twitch.tv'
    ]
    
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        return any(supported in domain for supported in supported_domains)
    except:
        return False

def get_platform_name(url):
    """الحصول على اسم المنصة من الرابط"""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        
        if 'youtube' in domain or 'youtu.be' in domain:
            return "YouTube"
        elif 'tiktok' in domain:
            return "TikTok"
        elif 'instagram' in domain:
            return "Instagram"
        elif 'facebook' in domain:
            return "Facebook"
        elif 'twitter' in domain or 'x.com' in domain:
            return "Twitter/X"
        elif 'soundcloud' in domain:
            return "SoundCloud"
        elif 'vimeo' in domain:
            return "Vimeo"
        else:
            return "منصة مدعومة"
    except:
        return "غير معروف"

def get_advanced_ydl_opts(format_selector: str, output_path: str, is_audio: bool = False) -> Dict[str, Any]:
    """إنشاء إعدادات yt-dlp متقدمة ومحسنة"""
    
    # قائمة User-Agent متنوعة لتجنب bot detection
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36'
    ]
    
    # اختيار User-Agent عشوائي
    selected_user_agent = random.choice(user_agents)
    
    # إعدادات أساسية محسنة
    base_opts = {
        'format': format_selector,
        'outtmpl': output_path,
        'user_agent': selected_user_agent,
        'referer': 'https://www.youtube.com/',
        'http_headers': {
            'User-Agent': selected_user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': random.choice(['en-US,en;q=0.5', 'ar,en;q=0.9', 'en-GB,en;q=0.8']),
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        },
        
        # إعدادات الشبكة المحسنة
        'socket_timeout': 30,
        'retries': 3,
        'fragment_retries': 3,
        'retry_sleep_functions': {
            'http': lambda n: min(4 * (2 ** n), 60) + random.uniform(0, 5),
            'fragment': lambda n: min(2 * (2 ** n), 30) + random.uniform(0, 3),
        },
        
        # إعدادات التحميل
        'http_chunk_size': 1024 * 1024,  # 1MB chunks
        'buffersize': 1024 * 16,  # 16KB buffer
        'concurrent_fragment_downloads': 4,
        
        # تحسينات الأداء
        'no_color': True,
        'no_warnings': True,
        'quiet': True,
        'extract_flat': False,
        'writethumbnail': False,
        'writeinfojson': False,
        'writesubtitles': False,
        'writeautomaticsub': False,
        'writedescription': False,
        'writeannotations': False,
        'writecomments': False,
        
        # إعدادات خاصة بـ YouTube لتجنب bot detection
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web'],
                'player_skip': ['webpage', 'configs'],
                'innertube_host': 'youtubei.googleapis.com',
                'innertube_key': 'AIzaSyA8eiZmM1FaDVjRy-df2KTyQ_vz_yYM39w',
                'skip': ['hls', 'dash'],
            }
        },
    }
    
    # إعدادات خاصة بالصوت
    if is_audio:
        base_opts.update({
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'prefer_ffmpeg': True,
        })
    
    return base_opts

async def download_with_retry(url: str, ydl_opts: Dict[str, Any], max_attempts: int = 3) -> bool:
    """تحميل مع إعادة المحاولة والتعامل مع الأخطاء"""
    for attempt in range(max_attempts):
        try:
            # تغيير User-Agent في كل محاولة
            if attempt > 0:
                user_agents = [
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
                ]
                new_user_agent = random.choice(user_agents)
                ydl_opts['user_agent'] = new_user_agent
                ydl_opts['http_headers']['User-Agent'] = new_user_agent
                
                # انتظار عشوائي بين المحاولات
                wait_time = random.uniform(2, 8) * (attempt + 1)
                await asyncio.sleep(wait_time)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                return True
                
        except yt_dlp.DownloadError as e:
            error_msg = str(e).lower()
            
            # أخطاء مؤقتة قابلة للإعادة
            if any(keyword in error_msg for keyword in [
                'sign in to confirm', 'bot', 'captcha', 'rate limit',
                'too many requests', 'temporary', 'try again'
            ]):
                logger.warning(f"خطأ مؤقت في المحاولة {attempt + 1}: {e}")
                if attempt < max_attempts - 1:
                    continue
            
            # أخطاء دائمة
            logger.error(f"خطأ في التحميل: {e}")
            raise e
            
        except Exception as e:
            logger.error(f"خطأ غير متوقع في المحاولة {attempt + 1}: {e}")
            if attempt < max_attempts - 1:
                continue
            raise e
    
    return False

async def download_video(query, url, format_selector):
    """تحميل الفيديو"""
    try:
        await query.edit_message_text("🎬 *بدء تحميل الفيديو...*", parse_mode=ParseMode.MARKDOWN)
        
        ydl_opts = get_advanced_ydl_opts(format_selector, DOWNLOAD_PATH)
        
        # تحميل الفيديو
        success = await download_with_retry(url, ydl_opts)
        
        if not success:
            await query.edit_message_text("❌ *خطأ في تحميل الفيديو*", parse_mode=ParseMode.MARKDOWN)
            return
        
        # العثور على الملف المحمل
        downloaded_file = None
        for file in os.listdir(DOWNLOAD_PATH):
            if file.endswith(('.mp4', '.mkv', '.webm', '.avi')):
                downloaded_file = os.path.join(DOWNLOAD_PATH, file)
                break
        
        if downloaded_file and os.path.exists(downloaded_file):
            file_size = os.path.getsize(downloaded_file)
            
            if file_size > MAX_FILE_SIZE:
                os.remove(downloaded_file)
                await query.edit_message_text(
                    f"❌ *خطأ:* حجم الملف كبير جداً ({file_size / (1024*1024):.1f} MB)\n"
                    f"الحد الأقصى المسموح: {MAX_FILE_SIZE / (1024*1024):.0f} MB",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            await query.edit_message_text("📤 *جاري رفع الفيديو...*", parse_mode=ParseMode.MARKDOWN)
            
            # إرسال الفيديو
            with open(downloaded_file, 'rb') as video:
                await query.message.reply_video(
                    video=video,
                    caption=f"🎬 {os.path.basename(downloaded_file)}",
                    supports_streaming=True
                )
            
            # حذف الملف المؤقت
            os.remove(downloaded_file)
            await query.edit_message_text("✅ *تم تحميل الفيديو بنجاح!*", parse_mode=ParseMode.MARKDOWN)
            
            # تحديث الإحصائيات
            if STATS_ENABLED:
                update_stats('video_downloads')
        else:
            await query.edit_message_text("❌ *خطأ في تحميل الفيديو*", parse_mode=ParseMode.MARKDOWN)
            
    except yt_dlp.DownloadError as e:
        error_msg = str(e)
        if "Sign in to confirm you're not a bot" in error_msg:
            await query.edit_message_text(
                "❌ *خطأ مؤقت من YouTube*\n\n"
                "🔄 يرجى المحاولة مرة أخرى بعد قليل\n"
                "أو جرب رابط فيديو آخر\n\n"
                "💡 *نصيحة:* هذا خطأ مؤقت من YouTube وليس من البوت",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text(f"❌ *خطأ في التحميل:* {error_msg}", parse_mode=ParseMode.MARKDOWN)
        logger.error(f"خطأ في تحميل الفيديو: {e}")
    except Exception as e:
        await query.edit_message_text(f"❌ *خطأ غير متوقع:* {str(e)}", parse_mode=ParseMode.MARKDOWN)
        logger.error(f"خطأ غير متوقع في تحميل الفيديو: {e}")

async def download_audio(query, url: str):
    """تحميل الصوت"""
    try:
        await query.edit_message_text("🎵 *بدء استخراج الصوت...*", parse_mode=ParseMode.MARKDOWN)
        
        ydl_opts = get_advanced_ydl_opts("bestaudio[ext=m4a]/bestaudio[ext=mp3]/bestaudio", DOWNLOAD_PATH, is_audio=True)
        
        # تحميل واستخراج الصوت
        success = await download_with_retry(url, ydl_opts)
        
        if not success:
            await query.edit_message_text("❌ *خطأ في استخراج الصوت*", parse_mode=ParseMode.MARKDOWN)
            return
        
        # العثور على الملف المحمل
        downloaded_file = None
        for file in os.listdir(DOWNLOAD_PATH):
            if file.endswith(('.mp3', '.m4a', '.opus', '.wav')):
                downloaded_file = os.path.join(DOWNLOAD_PATH, file)
                break
        
        if downloaded_file and os.path.exists(downloaded_file):
            file_size = os.path.getsize(downloaded_file)
            
            if file_size > MAX_FILE_SIZE:
                os.remove(downloaded_file)
                await query.edit_message_text(
                    f"❌ *خطأ:* حجم الملف كبير جداً ({file_size / (1024*1024):.1f} MB)\n"
                    f"الحد الأقصى المسموح: {MAX_FILE_SIZE / (1024*1024):.0f} MB",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            await query.edit_message_text("📤 *جاري رفع الملف الصوتي...*", parse_mode=ParseMode.MARKDOWN)
            
            # إرسال الملف الصوتي
            with open(downloaded_file, 'rb') as audio:
                await query.message.reply_audio(
                    audio=audio,
                    caption=f"🎵 {os.path.basename(downloaded_file)}",
                    title=os.path.basename(downloaded_file),
                    performer="Unknown"
                )
            
            # حذف الملف المؤقت
            os.remove(downloaded_file)
            await query.edit_message_text("✅ *تم استخراج الصوت بنجاح!*", parse_mode=ParseMode.MARKDOWN)
            
            # تحديث الإحصائيات
            if STATS_ENABLED:
                update_stats('audio_downloads')
        else:
            await query.edit_message_text("❌ *خطأ في استخراج الصوت*", parse_mode=ParseMode.MARKDOWN)
            
    except yt_dlp.DownloadError as e:
        error_msg = str(e)
        if "Sign in to confirm you're not a bot" in error_msg:
            await query.edit_message_text(
                "❌ *خطأ مؤقت من YouTube*\n\n"
                "🔄 يرجى المحاولة مرة أخرى بعد قليل\n"
                "أو جرب رابط فيديو آخر\n\n"
                "💡 *نصيحة:* هذا خطأ مؤقت من YouTube وليس من البوت",
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text(f"❌ *خطأ في التحميل:* {error_msg}", parse_mode=ParseMode.MARKDOWN)
        logger.error(f"خطأ في تحميل الصوت: {e}")
    except Exception as e:
        await query.edit_message_text(f"❌ *خطأ غير متوقع:* {str(e)}", parse_mode=ParseMode.MARKDOWN)
        logger.error(f"خطأ غير متوقع في تحميل الصوت: {e}")

async def handle_other_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الرسائل الأخرى"""
    await update.message.reply_text(
        "🤔 *لم أفهم هذه الرسالة*\n\n"
        "📝 *يرجى إرسال:*\n"
        "• رابط فيديو من منصة مدعومة\n"
        "• أمر `/help` للمساعدة\n\n"
        "🌐 *المنصات المدعومة:*\n"
        "YouTube, TikTok, Instagram, Facebook, Twitter, SoundCloud, Vimeo",
        parse_mode=ParseMode.MARKDOWN
    )

def get_platform_name(url):
    """الحصول على اسم المنصة من الرابط"""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        
        if 'youtube' in domain or 'youtu.be' in domain:
            return "YouTube"
        elif 'tiktok' in domain:
            return "TikTok"
        elif 'instagram' in domain:
            return "Instagram"
        elif 'facebook' in domain:
            return "Facebook"
        elif 'twitter' in domain or 'x.com' in domain:
            return "Twitter/X"
        elif 'soundcloud' in domain:
            return "SoundCloud"
        elif 'vimeo' in domain:
            return "Vimeo"
        else:
            return "منصة مدعومة"
    except:
        return "غير معروف"

def check_rate_limit(user_id: int) -> bool:
    """فحص معدل الطلبات للمستخدم"""
    current_time = time.time()
    
    if user_id not in user_request_tracker:
        user_request_tracker[user_id] = []
    
    # إزالة الطلبات القديمة
    user_request_tracker[user_id] = [
        req_time for req_time in user_request_tracker[user_id]
        if current_time - req_time < RATE_LIMIT_WINDOW
    ]
    
    # فحص عدد الطلبات
    if len(user_request_tracker[user_id]) >= RATE_LIMIT_REQUESTS:
        return False
    
    # إضافة الطلب الحالي
    user_request_tracker[user_id].append(current_time)
    return True

async def get_video_info(query, url):
    """الحصول على معلومات الفيديو"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            title = info.get('title', 'غير معروف')
            duration = info.get('duration', 0)
            uploader = info.get('uploader', 'غير معروف')
            view_count = info.get('view_count', 0)
            
            # تحويل المدة إلى تنسيق قابل للقراءة
            if duration:
                minutes, seconds = divmod(duration, 60)
                duration_str = f"{minutes:02d}:{seconds:02d}"
            else:
                duration_str = "غير معروف"
            
            # تنسيق عدد المشاهدات
            if view_count:
                if view_count >= 1000000:
                    view_str = f"{view_count/1000000:.1f}M"
                elif view_count >= 1000:
                    view_str = f"{view_count/1000:.1f}K"
                else:
                    view_str = str(view_count)
            else:
                view_str = "غير معروف"
            
            info_text = f"""
ℹ️ *معلومات الفيديو:*
• *العنوان:* {title}
• *المدة:* {duration_str}
• *المشرف:* {uploader}
• *المشاهدات:* {view_str}
"""
            await query.edit_message_text(info_text, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        logger.error(f"خطأ في الحصول على معلومات الفيديو: {e}")
        await query.edit_message_text("❌ *خطأ في الحصول على معلومات الفيديو*", parse_mode=ParseMode.MARKDOWN)

async def run_bot():
    """تشغيل بوت تلقرام"""
    try:
        print("🤖 بدء تشغيل بوت التحميل...")
        
        # إنشاء التطبيق مع إعدادات محسنة
        application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
        
        # إضافة المعالجات
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CallbackQueryHandler(button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_other_messages))
        
        # إضافة معالج الأخطاء
        application.add_error_handler(error_handler)
        
        # محاولة إيقاف أي webhook موجود
        try:
            await application.bot.delete_webhook(drop_pending_updates=True)
            print("✅ تم حذف webhook إن وجد")
            await asyncio.sleep(2)  # انتظار قصير
        except Exception as e:
            print(f"⚠️ تحذير webhook: {e}")
        
        # تشغيل البوت مع إعادة المحاولة
        max_retries = 5
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                print(f"🔄 محاولة تشغيل البوت ({retry_count + 1}/{max_retries})...")
                
                # تشغيل البوت مع polling
                await application.initialize()
                await application.start()
                await application.updater.start_polling(
                    poll_interval=1.0,
                    timeout=10,
                    bootstrap_retries=3,
                    read_timeout=10,
                    write_timeout=10,
                    connect_timeout=10,
                    pool_timeout=10,
                    drop_pending_updates=True
                )
                
                print("✅ تم تشغيل البوت بنجاح!")
                print(f"📊 لوحة التحكم: http://localhost:5002")
                
                # الحفاظ على البوت يعمل
                await application.updater.idle()
                
            except Conflict as e:
                print(f"⚠️ تضارب في البوت (محاولة {retry_count + 1}): {e}")
                retry_count += 1
                
                if retry_count < max_retries:
                    wait_time = min(30, 5 * retry_count)  # انتظار متزايد
                    print(f"⏳ انتظار {wait_time} ثانية قبل المحاولة التالية...")
                    await asyncio.sleep(wait_time)
                    
                    # محاولة إيقاف التطبيق الحالي
                    try:
                        await application.stop()
                        await application.shutdown()
                    except:
                        pass
                else:
                    print("❌ فشل في حل تضارب البوت بعد عدة محاولات")
                    break
                    
            except Exception as e:
                print(f"❌ خطأ في تشغيل البوت (محاولة {retry_count + 1}): {e}")
                retry_count += 1
                
                if retry_count < max_retries:
                    wait_time = min(15, 3 * retry_count)
                    print(f"⏳ انتظار {wait_time} ثانية قبل المحاولة التالية...")
                    await asyncio.sleep(wait_time)
                else:
                    print(f"❌ فشل في تشغيل البوت بعد عدة محاولات: {e}")
                    break
                    
    except Exception as e:
        print(f"❌ خطأ عام في تشغيل البوت: {e}")
    finally:
        # تنظيف الموارد
        try:
            await application.stop()
            await application.shutdown()
        except:
            pass

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج الأخطاء العام"""
    logger.error(f"Exception while handling an update: {context.error}")
    
    # التعامل مع Telegram Conflict
    if isinstance(context.error, Conflict):
        logger.warning("Telegram Conflict detected - another bot instance might be running")
        return
    
    # إرسال رسالة خطأ للمستخدم
    if update and hasattr(update, 'effective_chat') and update.effective_chat:
        try:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="❌ حدث خطأ مؤقت. يرجى المحاولة مرة أخرى.",
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")

BOT_LOCK_FILE = "/tmp/telegram_bot.lock"
bot_lock_fd = None

def acquire_lock():
    global bot_lock_fd
    try:
        bot_lock_fd = os.open(BOT_LOCK_FILE, os.O_RDWR | os.O_CREAT)
        fcntl.flock(bot_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        print("✅ تم الحصول على قفل البوت")
    except BlockingIOError:
        print("❌ قفل البوت مأخوذ من قبل")
        exit(1)

def release_lock():
    global bot_lock_fd
    if bot_lock_fd:
        fcntl.flock(bot_lock_fd, fcntl.LOCK_UN)
        os.close(bot_lock_fd)
        bot_lock_fd = None
        print("✅ تم إطلاق قفل البوت")

if __name__ == '__main__':
    # تحميل الإحصائيات
    load_stats()
    
    # تشغيل لوحة التحكم في thread منفصل
    if FLASK_AVAILABLE:
        port = int(os.environ.get('PORT', 5002))
        dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
        dashboard_thread.start()
        print(f"✅ تم تشغيل لوحة التحكم على: http://localhost:{port}")
    
    # الحصول على قفل البوت
    acquire_lock()
    
    # تسجيل دالة إطلاق القفل عند الخروج
    atexit.register(release_lock)
    
    try:
        # تشغيل البوت
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n🛑 تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        print(f"❌ خطأ عام: {e}")
    finally:
        # إطلاق قفل البوت
        release_lock()
