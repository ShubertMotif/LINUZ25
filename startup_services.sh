#!/bin/bash

# Attiva ambiente virtuale
source /home/mattia/PycharmProjects/LINUZ25/15MAR/GPTvenv/bin/activate

# Attiva ambiente virtuale
source /home/mattia/PycharmProjects/autotrade/AUTOTRADEvenv/bin/activate


# Avvia AutoTrade
echo "[AUTO] Avvio AutoTrade..."
nohup python3 /home/mattia/PycharmProjects/AutoTrade/app.py > /home/mattia/log_autotrade.txt 2>&1 &

# Avvia IA con Telegram
echo "[IA] Avvio bot Telegram..."
nohup python3 /home/mattia/PycharmProjects/LINUZ25/15MAR/app3.py telegram > /home/mattia/log_bot.txt 2>&1 &


