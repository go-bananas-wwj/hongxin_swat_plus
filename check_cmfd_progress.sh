#!/bin/bash
# CMFD 下载进度检查脚本

DIR="/workspace/hongxin_swaw_plus/Datasets/CMFD_v2_2012-2024_daily"
LOG="$DIR/download.log"
TOTAL=104

echo "=== CMFD v2.0 下载进度 ==="
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 检查下载进程
PID=$(pgrep -f "download_cmfd_manager.py" | head -1)
if [ -n "$PID" ]; then
    echo "下载进程: 运行中 (PID: $PID)"
    ps -p $PID -o pid,etime,cmd | tail -1
else
    echo "下载进程: 未运行"
fi

echo ""

# 统计文件
if [ -d "$DIR" ]; then
    COMPLETE=$(grep -c "✅ 完成" "$LOG" 2>/dev/null || echo 0)
    FAILED=$(grep -c "❌ 失败" "$LOG" 2>/dev/null || echo 0)
    FILE_COUNT=$(ls "$DIR"/*.nc 2>/dev/null | wc -l)
    TOTAL_SIZE=$(du -sh "$DIR" 2>/dev/null | cut -f1)
    
    echo "文件统计:"
    echo "  已完成: $COMPLETE / $TOTAL"
    echo "  失败: $FAILED"
    echo "  目录中 .nc 文件: $FILE_COUNT"
    echo "  总大小: $TOTAL_SIZE"
    
    # 计算速度（如果进程在运行）
    if [ -n "$PID" ]; then
        SIZE1=$(du -sb "$DIR" 2>/dev/null | cut -f1)
        sleep 10
        SIZE2=$(du -sb "$DIR" 2>/dev/null | cut -f1)
        SPEED_KB=$(( (SIZE2 - SIZE1) / 10 / 1024 ))
        echo "  当前速度: ${SPEED_KB} KB/s"
        
        # 估算剩余时间
        if [ "$SPEED_KB" -gt 0 ]; then
            # 假设剩余约 40GB - 已下载
            REM_MB=$(( 40550 - SIZE2 / 1024 / 1024 ))
            REM_SEC=$(( REM_MB * 1024 / SPEED_KB ))
            REM_HOUR=$(( REM_SEC / 3600 ))
            REM_MIN=$(( (REM_SEC % 3600) / 60 ))
            echo "  预计剩余: ${REM_HOUR}小时 ${REM_MIN}分钟"
        fi
    fi
else
    echo "目录不存在: $DIR"
fi

echo ""
echo "=== 最近日志 ==="
tail -10 "$LOG" 2>/dev/null || echo "无日志"
