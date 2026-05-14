#!/bin/bash
# CMFD v2.0 日数据并行下载脚本 (2012-2024)
# 使用 4 个并行进程加速下载

FTP_URL="ftp://download_4545878:17766766@ftp2.tpdc.ac.cn:6201/Data_forcing_01dy_010deg"
FILELIST="filelist.txt"
DOWNLOAD_DIR="/workspace/hongxin_swaw_plus/Datasets/CMFD_v2_2012-2024_daily"
LOG="$DOWNLOAD_DIR/download.log"
JOBS=4
TOTAL=$(wc -l < "$FILELIST")

# 记录开始时间
START_TIME=$(date +%s)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] === 开始并行下载 CMFD v2.0 日数据 ===" | tee "$LOG"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 总文件数: $TOTAL, 并行进程: $JOBS" | tee -a "$LOG"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] 预估总量: ~40 GB" | tee -a "$LOG"

# 定义下载单个文件的函数
download_file() {
    local FILENAME=$1
    local NUM=$2
    local FILEPATH="$DOWNLOAD_DIR/$FILENAME"
    local TMPLOG="$DOWNLOAD_DIR/.tmp_$NUM.log"

    if [ -f "$FILEPATH" ] && [ -s "$FILEPATH" ]; then
        local SIZE=$(du -h "$FILEPATH" 2>/dev/null | cut -f1)
        echo "[$NUM/$TOTAL] ✅ 已存在 ($SIZE): $FILENAME" >> "$TMPLOG"
        return 0
    fi

    echo "[$NUM/$TOTAL] ⏳ 下载中: $FILENAME" >> "$TMPLOG"
    curl -C - -o "$FILEPATH" "$FTP_URL/$FILENAME" --silent --show-error 2>> "$TMPLOG"

    if [ -f "$FILEPATH" ] && [ -s "$FILEPATH" ]; then
        local SIZE=$(du -h "$FILEPATH" 2>/dev/null | cut -f1)
        echo "[$NUM/$TOTAL] ✅ 完成 ($SIZE): $FILENAME" >> "$TMPLOG"
    else
        echo "[$NUM/$TOTAL] ❌ 失败: $FILENAME" >> "$TMPLOG"
    fi
}

# 导出函数以便 xargs 使用
export -f download_file
export FTP_URL DOWNLOAD_DIR LOG TOTAL

# 使用 xargs 并行下载
cat "$FILELIST" | xargs -P $JOBS -I{} bash -c 'download_file "$@" $(grep -n "^$@$" "$DOWNLOAD_DIR/filelist.txt" | cut -d: -f1)' _ {}

# 汇总日志
for f in "$DOWNLOAD_DIR"/.tmp_*.log; do
    [ -f "$f" ] && cat "$f" >> "$LOG" && rm -f "$f"
done

# 统计
END_TIME=$(date +%s)
ELAPSED=$((END_TIME - START_TIME))
HOURS=$((ELAPSED / 3600))
MINUTES=$(((ELAPSED % 3600) / 60))
DOWNLOADED=$(ls "$DOWNLOAD_DIR"/*.nc 2>/dev/null | wc -l)
SIZE=$(du -sh "$DOWNLOAD_DIR" 2>/dev/null | cut -f1)

echo "" >> "$LOG"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] === 下载汇总 ===" | tee -a "$LOG"
echo "完成文件: $DOWNLOADED / $TOTAL" | tee -a "$LOG"
echo "总大小: $SIZE" | tee -a "$LOG"
echo "耗时: ${HOURS}小时 ${MINUTES}分钟" | tee -a "$LOG"
