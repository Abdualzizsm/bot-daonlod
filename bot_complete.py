#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import re
import tempfile
import asyncio
import hashlib
import shutil
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional, Dict, Any
from datetime import datetime
import time

import yt_dlp
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaVideo, InputMediaAudio
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from telegram.constants import ParseMode, ChatAction
from telegram.error import TelegramError, Conflict
from dotenv import load_dotenv

# استيراد نظام الإحصائيات
try:
    from stats_system import bot_stats
    STATS_ENABLED = True
except ImportError:
    print("تحذير: لم يتم العثور على نظام الإحصائيات")
    STATS_ENABLED = False

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
    if STATS_ENABLED:
        bot_stats.add_user(user.id)
    
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
    if STATS_ENABLED:
        bot_stats.add_download(download_type)
    
    # بدء التحميل
    if download_type == "video":
        await download_video(query, url, "best")
    elif download_type == "audio":
        await download_audio(query, url)
    
    # حذف الرابط من الذاكرة المؤقتة
    del TEMP_URLS[url_hash]

async def download_video(query, url: str, quality: str):
    """تحميل الفيديو"""
    try:
        await query.edit_message_text("🎬 *بدء تحميل الفيديو...*", parse_mode=ParseMode.MARKDOWN)
        
        # إعداد yt-dlp للفيديو
        ydl_opts = {
            'format': 'best[ext=mp4]/best',
            'outtmpl': os.path.join(DOWNLOAD_PATH, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'extract_flat': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # استخراج معلومات الفيديو
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'فيديو')
            duration = info.get('duration', 0)
            uploader = info.get('uploader', 'غير محدد')
            
            # تحديث الرسالة
            await query.edit_message_text(
                f"📥 *جاري تحميل الفيديو...*\n\n"
                f"📝 *العنوان:* {title[:50]}...\n"
                f"⏱️ *المدة:* {duration//60}:{duration%60:02d}\n"
                f"👤 *المنشئ:* {uploader}",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # تحميل الفيديو
            ydl.download([url])
            
            # البحث عن الملف المحمل
            for file in os.listdir(DOWNLOAD_PATH):
                if file.endswith(('.mp4', '.mkv', '.webm', '.avi')):
                    file_path = os.path.join(DOWNLOAD_PATH, file)
                    
                    # التحقق من حجم الملف
                    file_size = os.path.getsize(file_path)
                    if file_size > 50 * 1024 * 1024:  # 50 MB
                        await query.edit_message_text(
                            "❌ *الملف كبير جداً*\n\n"
                            f"📊 *الحجم:* {file_size/1024/1024:.1f} MB\n"
                            "⚠️ *الحد الأقصى:* 50 MB\n\n"
                            "💡 جرب تحميل الصوت فقط",
                            parse_mode=ParseMode.MARKDOWN
                        )
                        os.remove(file_path)
                        return
                    
                    # رفع الفيديو
                    await query.edit_message_text("📤 *جاري رفع الفيديو...*", parse_mode=ParseMode.MARKDOWN)
                    
                    with open(file_path, 'rb') as video_file:
                        await query.message.reply_video(
                            video=video_file,
                            caption=f"🎬 *{title}*\n\n⏱️ المدة: {duration//60}:{duration%60:02d}\n👤 المنشئ: {uploader}",
                            parse_mode=ParseMode.MARKDOWN
                        )
                    
                    # حذف الملف
                    os.remove(file_path)
                    
                    await query.edit_message_text(
                        "✅ *تم تحميل الفيديو بنجاح!*\n\n"
                        "🎉 استمتع بالمشاهدة!",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
            
            await query.edit_message_text("❌ لم يتم العثور على ملف الفيديو")
            
    except Exception as e:
        logger.error(f"خطأ في تحميل الفيديو: {e}")
        await query.edit_message_text(
            f"❌ *خطأ في تحميل الفيديو*\n\n"
            f"🔍 *السبب:* {str(e)[:100]}...\n\n"
            "💡 جرب رابطاً آخر أو تحميل الصوت فقط",
            parse_mode=ParseMode.MARKDOWN
        )

async def download_audio(query, url: str):
    """تحميل الصوت"""
    try:
        await query.edit_message_text("🎵 *بدء استخراج الصوت...*", parse_mode=ParseMode.MARKDOWN)
        
        # إعداد yt-dlp للصوت
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(DOWNLOAD_PATH, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'extract_flat': False,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # استخراج معلومات الفيديو
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'صوت')
            duration = info.get('duration', 0)
            uploader = info.get('uploader', 'غير محدد')
            
            # تحديث الرسالة
            await query.edit_message_text(
                f"🎵 *جاري استخراج الصوت...*\n\n"
                f"📝 *العنوان:* {title[:50]}...\n"
                f"⏱️ *المدة:* {duration//60}:{duration%60:02d}\n"
                f"👤 *المنشئ:* {uploader}",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # تحميل واستخراج الصوت
            ydl.download([url])
            
            # البحث عن الملف الصوتي
            for file in os.listdir(DOWNLOAD_PATH):
                if file.endswith('.mp3'):
                    file_path = os.path.join(DOWNLOAD_PATH, file)
                    
                    # التحقق من حجم الملف
                    file_size = os.path.getsize(file_path)
                    if file_size > 50 * 1024 * 1024:  # 50 MB
                        await query.edit_message_text(
                            "❌ *الملف الصوتي كبير جداً*\n\n"
                            f"📊 *الحجم:* {file_size/1024/1024:.1f} MB\n"
                            "⚠️ *الحد الأقصى:* 50 MB",
                            parse_mode=ParseMode.MARKDOWN
                        )
                        os.remove(file_path)
                        return
                    
                    # رفع الملف الصوتي
                    await query.edit_message_text("📤 *جاري رفع الملف الصوتي...*", parse_mode=ParseMode.MARKDOWN)
                    
                    with open(file_path, 'rb') as audio_file:
                        await query.message.reply_audio(
                            audio=audio_file,
                            caption=f"🎵 *{title}*\n\n⏱️ المدة: {duration//60}:{duration%60:02d}\n👤 المنشئ: {uploader}",
                            parse_mode=ParseMode.MARKDOWN
                        )
                    
                    # حذف الملف
                    os.remove(file_path)
                    
                    await query.edit_message_text(
                        "✅ *تم استخراج الصوت بنجاح!*\n\n"
                        "🎧 استمتع بالاستماع!",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
            
            await query.edit_message_text("❌ لم يتم العثور على الملف الصوتي")
            
    except Exception as e:
        logger.error(f"خطأ في استخراج الصوت: {e}")
        await query.edit_message_text(
            f"❌ *خطأ في استخراج الصوت*\n\n"
            f"🔍 *السبب:* {str(e)[:100]}...\n\n"
            "💡 جرب رابطاً آخر",
            parse_mode=ParseMode.MARKDOWN
        )

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
    """الدالة الرئيسية"""
    # التحقق من وجود التوكن
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        logger.error("❌ لم يتم العثور على TELEGRAM_BOT_TOKEN في ملف .env")
        return
    
    logger.info("🚀 بدء تشغيل البوت...")
    
    # إعادة تعيين الويب هوك
    asyncio.run(reset_webhook())
    
    # إنشاء التطبيق
    application = Application.builder().token(bot_token).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # معالج الروابط
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    application.add_handler(MessageHandler(
        filters.TEXT & filters.Regex(url_pattern), 
        handle_url
    ))
    
    # معالج الرسائل الأخرى
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        handle_other_messages
    ))
    
    logger.info("✅ تم تشغيل البوت بنجاح!")
    if STATS_ENABLED:
        logger.info("📊 نظام الإحصائيات مفعل")
    
    # تشغيل البوت
    try:
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
    except Conflict:
        logger.error("❌ تعارض في getUpdates - يرجى إيقاف النسخ الأخرى من البوت")
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل البوت: {e}")

if __name__ == '__main__':
    main()
