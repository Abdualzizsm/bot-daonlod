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
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Dict, Any
from datetime import datetime
import atexit

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
                print("✅ تم تحميل الإحصائيات بنجاح")
        else:
            save_stats()
            print("📊 تم إنشاء ملف إحصائيات جديد")
    except Exception as e:
        print(f"⚠️ خطأ في تحميل الإحصائيات: {e}")

def save_stats():
    """حفظ الإحصائيات في الملف"""
    try:
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(bot_stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ خطأ في حفظ الإحصائيات: {e}")

def add_user(user_id):
    """إضافة مستخدم جديد"""
    if STATS_ENABLED:
        bot_stats["total_users"] = len(set(bot_stats.get("users", [])))
        if "users" not in bot_stats:
            bot_stats["users"] = []
        if user_id not in bot_stats["users"]:
            bot_stats["users"].append(user_id)
            bot_stats["total_users"] = len(bot_stats["users"])
            save_stats()

def add_download(download_type):
    """إضافة تحميل جديد"""
    if STATS_ENABLED:
        bot_stats["total_downloads"] += 1
        if download_type == "video":
            bot_stats["video_downloads"] += 1
        elif download_type == "audio":
            bot_stats["audio_downloads"] += 1
        
        # إحصائيات يومية
        today = datetime.now().strftime("%Y-%m-%d")
        if "daily_stats" not in bot_stats:
            bot_stats["daily_stats"] = {}
        if today not in bot_stats["daily_stats"]:
            bot_stats["daily_stats"][today] = 0
        bot_stats["daily_stats"][today] += 1
        
        save_stats()

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
    url = update.message.text.strip()
    user = update.effective_user
    
    logger.info(f"تم استلام رابط من المستخدم {user.id}: {url}")
    
    if not is_supported_url(url):
        await update.message.reply_text(
            "❌ *عذراً، هذا الرابط غير مدعوم*\n\n"
            "🌐 *المنصات المدعومة:*\n"
            "• YouTube\n• TikTok\n• Instagram\n• Facebook\n• Twitter/X\n• SoundCloud\n• Vimeo\n\n"
            "📝 تأكد من صحة الرابط وأنه من إحدى المنصات المدعومة",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # إنشاء معرف قصير للرابط
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    TEMP_URLS[url_hash] = url
    
    logger.info(f"تم حفظ الرابط بالمعرف: {url_hash}")
    
    platform_name = get_platform_name(url)
    
    # إنشاء أزرار التحميل
    keyboard = [
        [
            InlineKeyboardButton("🎬 فيديو بأعلى جودة", callback_data=f"video_{url_hash}"),
            InlineKeyboardButton("🎵 صوت فقط", callback_data=f"audio_{url_hash}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = f"""
✅ *تم اكتشاف الرابط بنجاح!*

🌐 *المنصة:* {platform_name}
🔗 *الرابط:* `{url[:50]}...`

📥 *اختر نوع التحميل:*
"""
    
    await update.message.reply_text(
        message_text,
        reply_markup=reply_markup,
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
    
    url = TEMP_URLS[url_hash]
    logger.info(f"تم العثور على الرابط: {url}")
    
    # تحديث إحصائيات التحميل
    add_download(download_type)
    
    # بدء التحميل
    if download_type == "video":
        await download_video(query, url, "best[ext=mp4]/best")
    elif download_type == "audio":
        await download_audio(query, url)
    
    # حذف الرابط من الذاكرة المؤقتة
    del TEMP_URLS[url_hash]

MAX_FILE_SIZE = 50 * 1024 * 1024

async def download_video(query, url, format_selector):
    """تحميل الفيديو"""
    try:
        await query.edit_message_text("🎬 *بدء تحميل الفيديو...*", parse_mode=ParseMode.MARKDOWN)
        
        # إعدادات yt-dlp المحدثة لتجنب مشاكل YouTube
        ydl_opts = {
            'format': format_selector,
            'outtmpl': os.path.join(DOWNLOAD_PATH, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'extract_flat': False,
            'writethumbnail': False,
            'writeinfojson': False,
            'ignoreerrors': True,
            'no_warnings': False,
            'quiet': False,
            # إعدادات خاصة بـ YouTube لتجنب bot detection
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_skip': ['configs', 'webpage'],
                    'player_client': ['android', 'web']
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip,deflate',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                'Keep-Alive': '300',
                'Connection': 'keep-alive',
            },
            'extractor_retries': 3,
            'fragment_retries': 3,
            'retry_sleep_functions': {
                'http': lambda n: min(4 ** n, 60),
                'fragment': lambda n: min(4 ** n, 60),
                'extractor': lambda n: min(4 ** n, 60)
            },
            # إعدادات إضافية لتجنب القيود
            'sleep_interval': 1,
            'max_sleep_interval': 5,
            'sleep_interval_subtitles': 0
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # الحصول على معلومات الفيديو أولاً
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            uploader = info.get('uploader', 'Unknown')
            
            # التحقق من حجم الفيديو المتوقع
            filesize = info.get('filesize') or info.get('filesize_approx', 0)
            if filesize and filesize > MAX_FILE_SIZE:
                await query.edit_message_text(
                    f"❌ *خطأ:* حجم الملف كبير جداً ({filesize / (1024*1024):.1f} MB)\n"
                    f"الحد الأقصى المسموح: {MAX_FILE_SIZE / (1024*1024):.0f} MB",
                    parse_mode=ParseMode.MARKDOWN
                )
                return
            
            # عرض معلومات الفيديو
            info_text = f"📹 *{title}*\n"
            if duration:
                info_text += f"⏱️ المدة: {duration//60}:{duration%60:02d}\n"
            if uploader:
                info_text += f"👤 القناة: {uploader}\n"
            info_text += f"📥 *جاري التحميل...*"
            
            await query.edit_message_text(info_text, parse_mode=ParseMode.MARKDOWN)
            
            # تحميل الفيديو
            ydl.download([url])
            
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
                        caption=f"🎬 {title}",
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
        
        # إعدادات yt-dlp المحدثة لتجنب مشاكل YouTube
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(DOWNLOAD_PATH, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'extract_flat': False,
            'writethumbnail': False,
            'writeinfojson': False,
            'ignoreerrors': True,
            'no_warnings': False,
            'quiet': False,
            # إعدادات خاصة بـ YouTube لتجنب bot detection
            'extractor_args': {
                'youtube': {
                    'skip': ['dash', 'hls'],
                    'player_skip': ['configs', 'webpage'],
                    'player_client': ['android', 'web']
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
                'Accept-Encoding': 'gzip,deflate',
                'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.7',
                'Keep-Alive': '300',
                'Connection': 'keep-alive',
            },
            'extractor_retries': 3,
            'fragment_retries': 3,
            'retry_sleep_functions': {
                'http': lambda n: min(4 ** n, 60),
                'fragment': lambda n: min(4 ** n, 60),
                'extractor': lambda n: min(4 ** n, 60)
            },
            # إعدادات إضافية لتجنب القيود
            'sleep_interval': 1,
            'max_sleep_interval': 5,
            'sleep_interval_subtitles': 0,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # الحصول على معلومات الفيديو أولاً
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)
            uploader = info.get('uploader', 'Unknown')
            
            # عرض معلومات الصوت
            info_text = f"🎵 *{title}*\n"
            if duration:
                info_text += f"⏱️ المدة: {duration//60}:{duration%60:02d}\n"
            if uploader:
                info_text += f"👤 القناة: {uploader}\n"
            info_text += f"🎧 *جاري استخراج الصوت...*"
            
            await query.edit_message_text(info_text, parse_mode=ParseMode.MARKDOWN)
            
            # تحميل واستخراج الصوت
            ydl.download([url])
            
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
                        caption=f"🎵 {title}",
                        title=title,
                        performer=uploader if uploader != 'Unknown' else None
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

def main():
    """تشغيل البوت مع نظام الإحصائيات"""
    # تحميل الإحصائيات
    load_stats()
    
    # تشغيل لوحة التحكم في thread منفصل
    if FLASK_AVAILABLE:
        port = int(os.environ.get('PORT', 5002))
        dashboard_thread = threading.Thread(target=run_dashboard, daemon=True)
        dashboard_thread.start()
        print(f"✅ تم تشغيل لوحة التحكم على: http://localhost:{port}")
    
    # إنشاء التطبيق
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_other_messages))
    
    # تشغيل البوت مع إعادة المحاولة
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            print("🚀 بدء تشغيل البوت...")
            print("📊 نظام الإحصائيات: مفعل" if STATS_ENABLED else "📊 نظام الإحصائيات: غير مفعل")
            port = int(os.environ.get('PORT', 5002))
            print(f"🌐 لوحة التحكم: متاحة على http://localhost:{port}" if FLASK_AVAILABLE else "🌐 لوحة التحكم: غير متاحة")
            print("✅ البوت يعمل الآن! اضغط Ctrl+C للإيقاف")
            
            application.run_polling(drop_pending_updates=True)
            break
            
        except Conflict:
            retry_count += 1
            if retry_count < max_retries:
                print(f"⚠️ تعارض في البوت، محاولة إعادة التشغيل ({retry_count}/{max_retries})...")
                time.sleep(5)
            else:
                print("❌ فشل في حل تعارض البوت بعد عدة محاولات")
                break
        except KeyboardInterrupt:
            print("\n🛑 تم إيقاف البوت بواسطة المستخدم")
            break
        except Exception as e:
            retry_count += 1
            if retry_count < max_retries:
                print(f"⚠️ خطأ في البوت، محاولة إعادة التشغيل ({retry_count}/{max_retries}): {e}")
                time.sleep(5)
            else:
                print(f"❌ فشل في تشغيل البوت بعد عدة محاولات: {e}")
                break

if __name__ == '__main__':
    main()
