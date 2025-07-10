#!/bin/bash

# Impostazioni
WORKDIR="/home/mattia/PycharmProjects/LINUZ25/15MAR"
VENV="$WORKDIR/GPTvenv/bin/activate"
SCRIPT="app5.py"
DEFAULT_MODE="telegram"
CURRENT_MODE="$DEFAULT_MODE"

export PYTORCH_CUDA_ALLOC_CONF="expandable_segments:True"

cd "$WORKDIR"

while true; do
  echo "⏳ Modalità corrente: $CURRENT_MODE"
  read -t 30 -p "➕ Nuova modalità ('telegram', 'flask', 'db_manage') o INVIO per mantenere [$CURRENT_MODE]: " NEW_MODE

  # Se utente ha digitato una nuova modalità valida
  if [[ "$NEW_MODE" == "telegram" || "$NEW_MODE" == "flask" || "$NEW_MODE" == "db_manage" ]]; then
    CURRENT_MODE="$NEW_MODE"
    echo "🔄 Cambiata modalità in: $CURRENT_MODE"
  fi

  # Chiude eventuale processo precedente
  PID=$(pgrep -f "$SCRIPT $CURRENT_MODE")
  if [[ -n "$PID" ]]; then
    echo "🛑 Uccido processo $PID con modalità $CURRENT_MODE..."
    kill "$PID"
    sleep 2
  fi

  # Avvio nuovo processo
  echo "🚀 Avvio $SCRIPT in modalità: $CURRENT_MODE"
  source "$VENV"
  nohup python3 "$SCRIPT" "$CURRENT_MODE" >> app_log.txt 2>&1 &

  # Attesa prima del prossimo ciclo
  sleep 60
done
