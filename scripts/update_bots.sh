#!/usr/bin/env bash

set -Eeuo pipefail

readonly FF_DIR="/home/arbaaz/Projects/Fanfiction-Finder"
readonly QF_DIR="/home/arbaaz/Projects/Quote-Finder"
readonly BRANCH="main"

log() {
    printf '\n[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"
}

deploy_project() {
    local project_directory="$1"
    shift

    local systemd_units=("$@")

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
        log "Updating Python dependencies"

        if [[ -x ".venv/bin/python" ]]; then
            .venv/bin/python -m pip install \
                --disable-pip-version-check \
                -r requirements.txt
        elif [[ -x "/home/arbaaz/.pyenv/versions/fanfic-finder-bot/bin/python" \
            && "$project_directory" == "$FF_DIR" ]]; then
            /home/arbaaz/.pyenv/versions/fanfic-finder-bot/bin/python \
                -m pip install \
                --disable-pip-version-check \
                -r requirements.txt
        else
            echo "Error: No Python environment found for $project_directory." >&2
            return 1
        fi
    fi

    if [[ -f "alembic.ini" ]]; then
        if [[ -x ".venv/bin/alembic" ]]; then
            log "Running database migrations"
            .venv/bin/alembic upgrade head
        else
            echo "Error: alembic.ini exists but .venv/bin/alembic was not found." >&2
            return 1
        fi
    fi

    for unit in "${systemd_units[@]}"; do
        local unit_file="$project_directory/$unit"

        if [[ ! -f "$unit_file" ]]; then
            echo "Error: Unit file not found: $unit_file" >&2
            return 1
        fi

        log "Symlinking $unit"

        sudo ln -sf "$unit_file" "/etc/systemd/system/$unit"
    done

    sudo systemctl daemon-reload

    for unit in "${systemd_units[@]}"; do
        if ! sudo systemctl is-enabled --quiet "$unit" 2>/dev/null; then
            log "Enabling $unit (if applicable)"
            sudo systemctl enable "$unit" 2>/dev/null || true
        fi

        log "Restarting $unit"

        sudo systemctl restart "$unit"

        sleep 2

        if sudo systemctl is-failed --quiet "$unit"; then
            echo "Error: $unit failed to start." >&2
            sudo systemctl status "$unit" --no-pager || true
            sudo journalctl -u "$unit" -n 50 --no-pager || true
            return 1
        fi
        
        # For non-oneshot services like the bot, ensure they are actively running
        if [[ "$unit" != *"maintenance.service" ]] && ! sudo systemctl is-active --quiet "$unit"; then
            echo "Error: $unit is not active." >&2
            sudo systemctl status "$unit" --no-pager || true
            sudo journalctl -u "$unit" -n 50 --no-pager || true
            return 1
        fi

        log "$unit successfully processed"
    done
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
            deploy_project \
                "$FF_DIR" \
                "Fanfiction-Finder.service"

            deploy_project \
                "$QF_DIR" \
                "quote-finder-bot.service" \
                "quote-finder-maintenance.service" \
                "quote-finder-maintenance.timer"
            ;;

        qf)
            deploy_project \
                "$QF_DIR" \
                "quote-finder-bot.service" \
                "quote-finder-maintenance.service" \
                "quote-finder-maintenance.timer"
            ;;

        ff)
            deploy_project \
                "$FF_DIR" \
                "Fanfiction-Finder.service"
            ;;

        *)
            echo "Invalid option: $1" >&2
            usage
            exit 1
            ;;
    esac
}

main "$@"
