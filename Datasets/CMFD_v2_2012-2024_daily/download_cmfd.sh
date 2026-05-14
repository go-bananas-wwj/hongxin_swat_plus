#!/bin/bash
# CMFD v2.0 日数据批量下载脚本 (2012-2024)

FTP_URL="ftp://download_4545878:17766766@ftp2.tpdc.ac.cn:6201/Data_forcing_01dy_010deg"
FILELIST="filelist.txt"
DOWNLOAD_DIR="/workspace/hongxin_swaw_plus/Datasets/CMFD_v2_2012-2024_daily"
LOG="download.log"

TOTAL=$(wc -l < "$FILELIST")
COUNT=0

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 开始下载 CMFD v2.0 日数据，共 $TOTAL 个文件" | tee -a "$LOG"

while IFS= read -r FILENAME; do
    COUNT=$((COUNT + 1))
    FILEPATH="$DOWNLOAD_DIR/$FILENAME"

    if [ -f "$FILEPATH" ] && [ -s "$FILEPATH" ]; then
        echo "[$COUNT/$TOTAL] 已存在，跳过: $FILENAME" | tee -a "$LOG"
        continue
    fi

    echo "[$COUNT/$TOTAL] 下载中: $FILENAME ..." | tee -a "$LOG"
    curl -C - -o "$FILEPATH" "$FTP_URL/$FILENAME" 2>&1 | tail -n 5 >> "$LOG"

    if [ $? -eq 0 ] && [ -f "$FILEPATH" ] && [ -s "$FILEPATH" ]; then
        echo "[$COUNT/$TOTAL] 完成: $FILENAME ($(du -h "$FILEPATH" | cut -f1))" | tee -a "$LOG"
    else
        echo "[$COUNT/$TOTAL] 失败: $FILENAME，将在下一轮重试" | tee -a "$LOG"
    fi

done < "$FILELIST"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 下载完成/中断，已下载 $COUNT/$TOTAL" | tee -a "$LOG"
