#!/bin/bash

# تنشيط البيئة الافتراضية
python3 -m venv venv
source venv/bin/activate

# تثبيت المتطلبات
pip install --upgrade pip
pip install -r requirements.txt

# بدء البوت
python3 bot.py
