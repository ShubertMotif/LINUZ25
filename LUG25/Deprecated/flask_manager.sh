#!/bin/bash

# Flask App Manager Script
# Gestisce ambiente virtuale, avvio app e monitoraggio

# Configurazioni
APP_FILE="app2.py"
VENV_DIR="venv"
APP_PORT=5000
APP_HOST="127.0.0.1"
CHECK_INTERVAL=120  # 2 minuti in secondi
LOG_FILE="flask_app.log"
PID_FILE="flask_app.pid"

# Colori per output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funzione per logging
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Funzione per stampa colorata
print_color() {
    echo -e "${2}${1}${NC}"
}

# Controllo se l'app è in esecuzione
check_app_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0  # App running
        else
            rm -f "$PID_FILE"
            return 1  # App not running
        fi
    else
        return 1  # PID file not found
    fi
}

# Controllo se l'app risponde via HTTP
check_app_responding() {
    local response=$(curl -s -o /dev/null -w "%{http_code}" "http://${APP_HOST}:${APP_PORT}" 2>/dev/null)
    if [ "$response" == "200" ]; then
        return 0  # App responding
    else
        return 1  # App not responding
    fi
}

# Creazione ambiente virtuale
setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        print_color "📦 Creazione ambiente virtuale..." "$BLUE"
        python3 -m venv "$VENV_DIR"
        if [ $? -eq 0 ]; then
            print_color "✅ Ambiente virtuale creato con successo" "$GREEN"
        else
            print_color "❌ Errore nella creazione dell'ambiente virtuale" "$RED"
            exit 1
        fi
    else
        print_color "📦 Ambiente virtuale già esistente" "$YELLOW"
    fi
}

# Attivazione ambiente virtuale
activate_venv() {
    print_color "🔧 Attivazione ambiente virtuale..." "$BLUE"
    source "$VENV_DIR/bin/activate"
    if [ $? -eq 0 ]; then
        print_color "✅ Ambiente virtuale attivato" "$GREEN"
    else
        print_color "❌ Errore nell'attivazione dell'ambiente virtuale" "$RED"
        exit 1
    fi
}

# Installazione dipendenze
install_dependencies() {
    print_color "📚 Installazione dipendenze..." "$BLUE"
    pip install flask flask-sqlalchemy flask-login
    if [ $? -eq 0 ]; then
        print_color "✅ Dipendenze installate con successo" "$GREEN"
    else
        print_color "❌ Errore nell'installazione delle dipendenze" "$RED"
        exit 1
    fi
}

# Avvio dell'applicazione
start_app() {
    if check_app_running; then
        print_color "⚠️  L'app è già in esecuzione (PID: $(cat $PID_FILE))" "$YELLOW"
        return 0
    fi

    print_color "🚀 Avvio applicazione Flask..." "$BLUE"
    log "Avvio applicazione Flask"

    # Avvia l'app in background e salva il PID
    nohup python "$APP_FILE" > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"

    # Aspetta un po' per verificare che l'app si sia avviata
    sleep 3

    if check_app_running; then
        print_color "✅ Applicazione avviata con successo (PID: $(cat $PID_FILE))" "$GREEN"
        log "Applicazione avviata con successo (PID: $(cat $PID_FILE))"

        # Aspetta che l'app sia pronta a rispondere
        print_color "⏳ Attesa risposta dell'applicazione..." "$BLUE"
        local attempts=0
        while [ $attempts -lt 10 ]; do
            if check_app_responding; then
                print_color "🌐 Applicazione online e funzionante su http://${APP_HOST}:${APP_PORT}" "$GREEN"
                log "Applicazione online e funzionante"
                return 0
            fi
            sleep 2
            attempts=$((attempts + 1))
        done

        print_color "⚠️  Applicazione avviata ma non risponde alle richieste HTTP" "$YELLOW"
        return 1
    else
        print_color "❌ Errore nell'avvio dell'applicazione" "$RED"
        log "Errore nell'avvio dell'applicazione"
        return 1
    fi
}

# Stop dell'applicazione
stop_app() {
    if check_app_running; then
        local pid=$(cat "$PID_FILE")
        print_color "🛑 Arresto applicazione (PID: $pid)..." "$YELLOW"
        log "Arresto applicazione (PID: $pid)"
        kill "$pid"
        sleep 2

        if ! check_app_running; then
            print_color "✅ Applicazione arrestata con successo" "$GREEN"
            log "Applicazione arrestata con successo"
            rm -f "$PID_FILE"
        else
            print_color "⚠️  Forzo l'arresto dell'applicazione..." "$YELLOW"
            kill -9 "$pid"
            rm -f "$PID_FILE"
            print_color "✅ Applicazione arrestata forzatamente" "$GREEN"
            log "Applicazione arrestata forzatamente"
        fi
    else
        print_color "ℹ️  L'applicazione non è in esecuzione" "$BLUE"
    fi
}

# Restart dell'applicazione
restart_app() {
    print_color "🔄 Riavvio applicazione..." "$BLUE"
    log "Riavvio applicazione"
    stop_app
    sleep 1
    start_app
}

# Monitoraggio continuo
monitor_app() {
    print_color "👁️  Avvio monitoraggio (controllo ogni $CHECK_INTERVAL secondi)..." "$BLUE"
    log "Avvio monitoraggio dell'applicazione"

    while true; do
        if check_app_running && check_app_responding; then
            print_color "✅ $(date '+%H:%M:%S') - App online e funzionante" "$GREEN"
        else
            print_color "❌ $(date '+%H:%M:%S') - App non risponde, riavvio..." "$RED"
            log "App non risponde, eseguo riavvio"
            restart_app
        fi

        sleep "$CHECK_INTERVAL"
    done
}

# Status dell'applicazione
status_app() {
    print_color "📊 Status dell'applicazione:" "$BLUE"

    if check_app_running; then
        local pid=$(cat "$PID_FILE")
        print_color "🟢 Processo: RUNNING (PID: $pid)" "$GREEN"

        if check_app_responding; then
            print_color "🟢 HTTP: RESPONDING (http://${APP_HOST}:${APP_PORT})" "$GREEN"
        else
            print_color "🔴 HTTP: NOT RESPONDING" "$RED"
        fi
    else
        print_color "🔴 Processo: NOT RUNNING" "$RED"
        print_color "🔴 HTTP: NOT AVAILABLE" "$RED"
    fi
}

# Visualizza logs
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        print_color "📄 Ultimi logs dell'applicazione:" "$BLUE"
        tail -n 20 "$LOG_FILE"
    else
        print_color "ℹ️  Nessun log disponibile" "$BLUE"
    fi
}

# Funzione di cleanup
cleanup() {
    print_color "🧹 Cleanup in corso..." "$YELLOW"
    stop_app
    deactivate 2>/dev/null || true
    print_color "👋 Arrivederci!" "$BLUE"
    exit 0
}

# Trap per gestire Ctrl+C
trap cleanup SIGINT SIGTERM

# Menu principale
show_menu() {
    echo
    print_color "🐍 Flask App Manager - Adelchi Group" "$BLUE"
    echo "=================================="
    echo "1) Setup iniziale (crea venv + installa dipendenze)"
    echo "2) Avvia applicazione"
    echo "3) Arresta applicazione"
    echo "4) Riavvia applicazione"
    echo "5) Monitora applicazione (controllo continuo)"
    echo "6) Status applicazione"
    echo "7) Mostra logs"
    echo "8) Esci"
    echo
}

# Main script
main() {
    # Controlla se esiste il file dell'app
    if [ ! -f "$APP_FILE" ]; then
        print_color "❌ File $APP_FILE non trovato!" "$RED"
        exit 1
    fi

    # Menu interattivo se nessun parametro
    if [ $# -eq 0 ]; then
        while true; do
            show_menu
            read -p "Scegli un'opzione (1-8): " choice

            case $choice in
                1)
                    setup_venv
                    activate_venv
                    install_dependencies
                    ;;
                2)
                    activate_venv
                    start_app
                    ;;
                3)
                    stop_app
                    ;;
                4)
                    activate_venv
                    restart_app
                    ;;
                5)
                    activate_venv
                    start_app
                    monitor_app
                    ;;
                6)
                    status_app
                    ;;
                7)
                    show_logs
                    ;;
                8)
                    cleanup
                    ;;
                *)
                    print_color "❌ Opzione non valida" "$RED"
                    ;;
            esac

            if [ "$choice" != "5" ] && [ "$choice" != "8" ]; then
                echo
                read -p "Premi INVIO per continuare..."
            fi
        done
    fi

    # Gestione parametri da linea di comando
    case "$1" in
        "setup")
            setup_venv
            activate_venv
            install_dependencies
            ;;
        "start")
            activate_venv
            start_app
            ;;
        "stop")
            stop_app
            ;;
        "restart")
            activate_venv
            restart_app
            ;;
        "monitor")
            activate_venv
            start_app
            monitor_app
            ;;
        "status")
            status_app
            ;;
        "logs")
            show_logs
            ;;
        "auto")
            # Modalità automatica: setup + start + monitor
            print_color "🤖 Modalità automatica: setup + avvio + monitoraggio" "$BLUE"
            setup_venv
            activate_venv
            install_dependencies
            start_app
            monitor_app
            ;;
        *)
            echo "Uso: $0 [setup|start|stop|restart|monitor|status|logs|auto]"
            echo "Senza parametri avvia il menu interattivo"
            exit 1
            ;;
    esac
}

# Avvia lo script
main "$@"