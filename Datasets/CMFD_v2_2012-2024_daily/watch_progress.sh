#!/bin/bash
DIR="/workspace/hongxin_swaw_plus/Datasets/CMFD_v2_2012-2024_daily"
LOG="$DIR/download.log"
TOTAL=104

echo "=== CMFD v2.0 下载实时进度 ==="
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

# 统计已下载文件
DOWNLOADED=$(ls $DIR/*.nc 2>/dev/null | wc -l)
SIZE=$(du -sh $DIR 2>/dev/null | cut -f1)

echo "总体进度: $DOWNLOADED / $TOTAL 文件 ($(( DOWNLOADED * 100 / TOTAL ))%)"
echo "已下载大小: $SIZE"
echo ""

# 显示正在运行的下载进程
echo "正在运行的下载进程:"
ps aux | grep 'curl.*ftp2' | grep -v grep | wc -l | xargs -I{} echo "  活跃 curl 进程数: {}"
echo ""

# 显示最新日志
echo "最近日志 (最近20行):"
tail -n 20 "$LOG" 2>/dev/null

echo ""
echo "提示: 每 60 秒刷新一次，运行 bash watch_progress.sh 查看更新"
