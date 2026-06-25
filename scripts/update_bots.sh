```bash
#!/usr/bin/env bash

set -Eeuo pipefail

readonly FF_DIR="/home/arbaaz/Projects/Fanfiction-Finder"
readonly QF_DIR="/home/arbaaz/Projects/Quote-Finder"
readonly BRANCH="main"

log() {
    printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

install_unit() {
    local project_directory="$1"
    local unit="$2"
    local unit_file="$project_directory/$unit"

    if [[ ! -f "$unit_file" ]]; then
        echo "Error: Unit file not found: $unit_file" >&2
        return 1
    fi

    log "Symlinking $unit"

    sudo ln -sfn \
        "$unit_file" \
        "/etc/systemd/system/$unit"
}

check_unit() {
    local unit="$1"

    sleep 2

    if sudo systemctl is-failed --quiet "$unit"; then
        echo "Error: $unit failed." >&2
        sudo systemctl status "$unit" --no-pager || true
        sudo journalctl -u "$unit" -n 50 --no-pager || true
        return 1
    fi

    if ! sudo systemctl is-active --quiet "$unit"; then
        echo "Error: $unit is not active." >&2
        sudo systemctl status "$unit" --no-pager || true
        sudo journalctl -u "$unit" -n 50 --no-pager || true
        return 1
    fi
}

sync_project() {
    local project_directory="$1"

    if [[ ! -d "$project_directory/.git" ]]; then
        echo "Error: $project_directory is not a Git repository." >&2
        return 1
    fi

    log "Deploying $project_directory"

    cd "$project_directory"

    log "Syncing with origin/$BRANCH"

    git fetch --prune origin "$BRANCH"
    git reset --hard "origin/$BRANCH"
    git clean -fd

    if [[ -f "requirements.txt" ]]; then
        if [[ ! -x ".venv/bin/python" ]]; then
            echo "Error: Missing virtual environment: $project_directory/.venv" >&2
            return 1
        fi

        log "Updating Python dependencies"

        .venv/bin/python -m pip install \
            --disable-pip-version-check \
            -r requirements.txt
    fi

    if [[ -f "alembic.ini" ]]; then
        if [[ ! -x ".venv/bin/alembic" ]]; then
            echo "Error: alembic.ini exists but .venv/bin/alembic was not found." >&2
            return 1
        fi

        log "Running database migrations"
        .venv/bin/alembic upgrade head
    fi
}

deploy_fanfiction_finder() {
    sync_project "$FF_DIR"

    install_unit \
        "$FF_DIR" \
        "Fanfiction-Finder.service"

    sudo systemctl daemon-reload

    log "Enabling and restarting Fanfiction-Finder.service"

    sudo systemctl enable Fanfiction-Finder.service
    sudo systemctl restart Fanfiction-Finder.service

    check_unit "Fanfiction-Finder.service"

    log "Fanfiction-Finder.service successfully deployed"
}

deploy_quote_finder() {
    sync_project "$QF_DIR"

    install_unit \
        "$QF_DIR" \
        "quote-finder-bot.service"

    install_unit \
        "$QF_DIR" \
        "quote-finder-maintenance.service"

    install_unit \
        "$QF_DIR" \
        "quote-finder-maintenance.timer"

    sudo systemctl daemon-reload

    log "Enabling and restarting quote-finder-bot.service"

    sudo systemctl enable quote-finder-bot.service
    sudo systemctl restart quote-finder-bot.service

    check_unit "quote-finder-bot.service"

    log "Enabling and restarting quote-finder-maintenance.timer"

    sudo systemctl enable quote-finder-maintenance.timer
    sudo systemctl restart quote-finder-maintenance.timer

    check_unit "quote-finder-maintenance.timer"

    # Deliberately do not enable or start:
    # quote-finder-maintenance.service
    #
    # The timer starts this one-shot service according to its schedule.

    log "Quote Finder successfully deployed"
}

usage() {
    echo "Usage: $0 {all|qf|ff}"
}

main() {
    if [[ $# -ne 1 ]]; then
        usage
        exit 1
    fi

    case "$1" in
        all)
            deploy_fanfiction_finder
            deploy_quote_finder
            ;;

        qf)
            deploy_quote_finder
            ;;

        ff)
            deploy_fanfiction_finder
            ;;

        *)
            echo "Invalid option: $1" >&2
            usage
            exit 1
            ;;
    esac
}

main "$@"
```
