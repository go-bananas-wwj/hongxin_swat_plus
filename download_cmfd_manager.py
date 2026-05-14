#!/usr/bin/env python3
"""
CMFD v2.0 日数据下载管理器
- 并发限制: 4 (服务器单IP限5连接)
- 自动重试失败任务
- 断点续传
- 进度报告
"""

import os
import sys
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from ftplib import FTP

# 配置
FTP_HOST = "ftp3.tpdc.ac.cn"
FTP_PORT = 6201
FTP_USER = "download_4545878"
FTP_PASS = "17766766"
FTP_PATH = "Data_forcing_01dy_010deg"
DOWNLOAD_DIR = "/workspace/hongxin_swaw_plus/Datasets/CMFD_v2_2012-2024_daily"
FILELIST = os.path.join(DOWNLOAD_DIR, "filelist.txt")
LOG_FILE = os.path.join(DOWNLOAD_DIR, "download.log")
JOBS = 4
MAX_RETRIES = 3
CONNECT_TIMEOUT = 60
MAX_TIME = 7200  # 2小时/文件

def log(msg):
    """记录日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def get_all_remote_sizes(files):
    """获取所有远程文件大小"""
    sizes = {}
    try:
        ftp = FTP(timeout=30)
        ftp.connect(FTP_HOST, FTP_PORT)
        ftp.login(FTP_USER, FTP_PASS)
        ftp.cwd(FTP_PATH)
        
        for i, filename in enumerate(files):
            try:
                size = ftp.size(filename)
                sizes[filename] = size
                if (i + 1) % 10 == 0:
                    log(f"  已获取 {i+1}/{len(files)} 个文件大小")
            except Exception as e:
                log(f"  警告: 无法获取 {filename} 大小: {e}")
                sizes[filename] = None
        
        ftp.quit()
    except Exception as e:
        log(f"  错误: FTP 连接失败: {e}")
    
    return sizes

def download_file(filename, remote_size, retry_count=0):
    """下载单个文件，返回 (filename, success, message)"""
    filepath = os.path.join(DOWNLOAD_DIR, filename)
    url = f"ftp://{FTP_USER}:{FTP_PASS}@{FTP_HOST}:{FTP_PORT}/{FTP_PATH}/{filename}"
    
    # 检查本地文件
    local_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
    
    if remote_size and local_size == remote_size:
        return (filename, True, f"已存在且完整 ({local_size/1024/1024:.1f} MB)")
    
    if retry_count > 0:
        log(f"⏳ 重试 {retry_count}/{MAX_RETRIES}: {filename}")
    else:
        if local_size > 0:
            log(f"⏳ 续传中: {filename} (已下载 {local_size/1024/1024:.1f} MB / {remote_size/1024/1024:.1f} MB)")
        else:
            log(f"⏳ 下载中: {filename}")
    
    cmd = [
        "curl", "-C", "-", "-o", filepath, url,
        "--silent", "--show-error",
        "--max-time", str(MAX_TIME),
        "--connect-timeout", str(CONNECT_TIMEOUT)
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=MAX_TIME+60)
        
        if result.returncode == 0:
            new_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            if remote_size and new_size != remote_size:
                return (filename, False, f"大小不匹配: 本地 {new_size/1024/1024:.1f} MB != 远程 {remote_size/1024/1024:.1f} MB")
            return (filename, True, f"完成 ({new_size/1024/1024:.1f} MB)")
        else:
            stderr = result.stderr.strip() if result.stderr else "未知错误"
            return (filename, False, f"curl 错误 (码 {result.returncode}): {stderr[:100]}")
    except subprocess.TimeoutExpired:
        return (filename, False, "超时")
    except Exception as e:
        return (filename, False, f"异常: {str(e)[:100]}")

def main():
    # 读取文件列表
    if not os.path.exists(FILELIST):
        log(f"错误: 文件列表不存在: {FILELIST}")
        sys.exit(1)
    
    with open(FILELIST) as f:
        files = [line.strip() for line in f if line.strip()]
    
    total = len(files)
    log(f"=== CMFD v2.0 下载管理器启动 ===")
    log(f"服务器: {FTP_HOST}:{FTP_PORT}")
    log(f"总文件数: {total}, 并发: {JOBS}, 最大重试: {MAX_RETRIES}")
    
    # 获取远程文件大小
    log("获取远程文件大小...")
    remote_sizes = get_all_remote_sizes(files)
    known_sizes = {k: v for k, v in remote_sizes.items() if v is not None}
    log(f"成功获取 {len(known_sizes)}/{total} 个文件大小")
    if known_sizes:
        avg_size = sum(known_sizes.values()) / len(known_sizes)
        log(f"平均文件大小: {avg_size/1024/1024:.1f} MB")
        log(f"预估总量: {avg_size * total / 1024/1024/1024:.1f} GB")
    
    # 检查已下载文件
    existing_files = {}
    for f in files:
        filepath = os.path.join(DOWNLOAD_DIR, f)
        if os.path.exists(filepath):
            existing_files[f] = os.path.getsize(filepath)
    
    if existing_files:
        complete = sum(1 for f, s in existing_files.items() if remote_sizes.get(f) and s == remote_sizes[f])
        partial = len(existing_files) - complete
        log(f"已存在文件: {len(existing_files)} (完整: {complete}, 部分: {partial})")
    
    # 第一轮：下载所有文件
    failed = []
    completed = 0
    
    with ThreadPoolExecutor(max_workers=JOBS) as executor:
        futures = {
            executor.submit(download_file, f, remote_sizes.get(f)): f 
            for f in files
        }
        for future in as_completed(futures):
            filename, success, msg = future.result()
            if success:
                completed += 1
                log(f"✅ [{completed}/{total}] {filename}: {msg}")
            else:
                failed.append(filename)
                log(f"❌ [{completed}/{total}] {filename}: {msg}")
    
    # 重试失败的文件
    retry_round = 0
    while failed and retry_round < MAX_RETRIES:
        retry_round += 1
        log(f"=== 第 {retry_round} 轮重试，失败文件: {len(failed)} ===")
        
        current_failed = failed[:]
        failed = []
        
        with ThreadPoolExecutor(max_workers=JOBS) as executor:
            futures = {
                executor.submit(download_file, f, remote_sizes.get(f), retry_round): f 
                for f in current_failed
            }
            for future in as_completed(futures):
                filename, success, msg = future.result()
                if success:
                    completed += 1
                    log(f"✅ [{completed}/{total}] {filename}: {msg}")
                else:
                    failed.append(filename)
                    log(f"❌ [{completed}/{total}] {filename}: {msg}")
    
    # 最终统计
    log(f"=== 下载完成 ===")
    log(f"成功: {completed}/{total}")
    log(f"失败: {len(failed)}/{total}")
    if failed:
        log(f"失败文件列表:")
        for f in failed:
            log(f"  - {f}")
    
    total_size = sum(
        os.path.getsize(os.path.join(DOWNLOAD_DIR, f)) 
        for f in os.listdir(DOWNLOAD_DIR) if f.endswith('.nc')
    )
    log(f"总下载大小: {total_size/1024/1024/1024:.2f} GB")

if __name__ == "__main__":
    main()
