#!/bin/bash
# Monitor SWAT+ simulation running in tmux session "swatplus_run"
# Logs progress to stdout and kills the session if it hangs

SESSION="swatplus_run"
LOG="/workspace/hongxin_swaw_plus/data/02_processed/TxtInOut_v61/monitor.log"
TXTDIR="/workspace/hongxin_swaw_plus/data/02_processed/TxtInOut_v61"

> "$LOG"

last_line=""
stuck_count=0
max_stuck=6  # 6 min without progress = hang

while true; do
    if ! tmux has-session -t "$SESSION" 2>/dev/null; then
        echo "$(date '+%H:%M:%S') - tmux session $SESSION ended" | tee -a "$LOG"
        break
    fi

    # Capture last line of tmux pane
    current_line=$(tmux capture-pane -t "$SESSION" -p | grep "Original Simulation" | tail -1)
    
    if [ -n "$current_line" ]; then
        if [ "$current_line" = "$last_line" ]; then
            stuck_count=$((stuck_count + 1))
        else
            stuck_count=0
            last_line="$current_line"
        fi
        echo "$(date '+%H:%M:%S') - $current_line" | tee -a "$LOG"
    fi

    if [ "$stuck_count" -ge "$max_stuck" ]; then
        echo "$(date '+%H:%M:%S') - Simulation appears hung. Killing tmux session." | tee -a "$LOG"
        tmux kill-session -t "$SESSION"
        break
    fi

    sleep 60
done

echo "$(date '+%H:%M:%S') - Monitor exiting" | tee -a "$LOG"
