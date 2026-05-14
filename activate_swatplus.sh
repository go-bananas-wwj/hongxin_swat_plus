#!/bin/bash
# SWAT+ 61.0.2 环境激活脚本
# 用法: source /workspace/hongxin_swaw_plus/activate_swatplus.sh

# 激活 conda 环境
source /opt/conda/etc/profile.d/conda.sh
conda activate hongxin_swat

# 加载 Intel oneAPI 编译器环境（ifx 2024.1.2）
source /opt/intel/oneapi/setvars.sh >/dev/null 2>&1

# 设置 SWAT+ 可执行文件路径
export SWATPLUS_EXE="/workspace/hongxin_swaw_plus/swatplus-61.0.2/build/swatplus-unknown-ifx-lin_x86_64-Rel"
export PATH="/workspace/hongxin_swaw_plus/swatplus-61.0.2/build:$PATH"

echo "SWAT+ 61.0.2 环境已激活"
echo "  编译器: $(ifx --version | head -n 1)"
echo "  Python: $(python3 --version)"
echo "  可执行文件: $SWATPLUS_EXE"
echo ""
echo "使用方法: 进入场景目录，直接运行 swatplus-unknown-ifx-lin_x86_64-Rel"
