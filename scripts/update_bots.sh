#!/usr/bin/env bash

set -Eeuo pipefail

trap 'echo "Error: deployment failed at line $LINENO while running: $BASH_COMMAND" >&2' ERR

readonly FF_DIR="/home/arbaaz/Projects/Fanfiction-Finder"
readonly QF_DIR="/home/arbaaz/Projects/Quote-Finder"
readonly BRANCH="main"
readonly UV="/home/arbaaz/.local/bin/uv"

log() {
    printf '\n[%s] %s\n' \
        "$(date '+%Y-%m-%d %H:%M:%S')" \
        "$*"
}

require_executable() {
    local executable="$1"

    if [[ ! -x "$executable" ]]; then
        echo "Error: Required executable not found: $executable" >&2
        exit 1
    fi
}

sync_repository() {
    local project_directory="$1"

    if [[ ! -d "$project_directory/.git" ]]; then
        echo "Error: $project_directory is not a Git repository." >&2
        return 1
    fi

    log "Syncing $project_directory with origin/$BRANCH"

    cd "$project_directory"

    git fetch --prune origin "$BRANCH"
    git reset --hard "origin/$BRANCH"
    git clean -fd
}

sync_dependencies() {
    local project_directory="$1"

    cd "$project_directory"

    log "Synchronizing dependencies for $project_directory"

    "$UV" sync --frozen

    if [[ ! -x ".venv/bin/python" ]]; then
        echo "Error: Virtual environment was not created in $project_directory." >&2
        return 1
    fi
}

run_quote_finder_migrations() {
    cd "$QF_DIR"

    if [[ ! -f "alembic.ini" ]]; then
        return 0
    fi

    if [[ ! -x ".venv/bin/alembic" ]]; then
        echo "Error: alembic.ini exists but .venv/bin/alembic was not found." >&2
        return 1
    fi

    log "Running Quote Finder database migrations"

    .venv/bin/alembic upgrade head
}

install_unit() {
    local project_directory="$1"
    local unit="$2"
    local unit_file="$project_directory/$unit"

    if [[ ! -f "$unit_file" ]]; then
        echo "Error: Unit file not found: $unit_file" >&2
        return 1
    fi

    log "Installing systemd unit: $unit"

    sudo ln -sfn \
        "$unit_file" \
        "/etc/systemd/system/$unit"
}

check_active_unit() {
    local unit="$1"

    sleep 2

    if sudo systemctl is-failed --quiet "$unit"; then
        echo "Error: $unit entered a failed state." >&2
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

deploy_fanfiction_finder() {
    log "Starting Fanfiction Finder deployment"

    sync_repository "$FF_DIR"
    sync_dependencies "$FF_DIR"

    install_unit \
        "$FF_DIR" \
        "Fanfiction-Finder.service"

    sudo systemctl daemon-reload

    log "Enabling Fanfiction-Finder.service"
    sudo systemctl enable Fanfiction-Finder.service

    log "Restarting Fanfiction-Finder.service"
    sudo systemctl restart Fanfiction-Finder.service

    check_active_unit "Fanfiction-Finder.service"

    log "Fanfiction Finder deployment completed"
}

deploy_quote_finder() {
    log "Starting Quote Finder deployment"

    sync_repository "$QF_DIR"
    sync_dependencies "$QF_DIR"
    run_quote_finder_migrations

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

    log "Enabling quote-finder-bot.service"
    sudo systemctl enable quote-finder-bot.service

    log "Restarting quote-finder-bot.service"
    sudo systemctl restart quote-finder-bot.service

    check_active_unit "quote-finder-bot.service"

    log "Enabling quote-finder-maintenance.timer"
    sudo systemctl enable quote-finder-maintenance.timer

    log "Restarting quote-finder-maintenance.timer"
    sudo systemctl restart quote-finder-maintenance.timer

    check_active_unit "quote-finder-maintenance.timer"

    # Do not enable or start quote-finder-maintenance.service directly.
    # The timer starts the one-shot service.

    log "Quote Finder deployment completed"
}

usage() {
    echo "Usage: $0 {all|qf|ff}"
}

main() {
    if [[ $# -ne 1 ]]; then
        usage
        exit 1
    fi

    require_executable "$UV"

    log "Validating sudo access"
    sudo -v

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
            echo "Error: Invalid option: $1" >&2
            usage
            exit 1
            ;;
    esac
}

main "$@"
