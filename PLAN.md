# 红心村 SWAT+ 建模项目 — 执行计划

> 状态: 待审批  
> 创建: 2026-05-14  
> 所有决策已与项目负责人确认，详见 `details.md`

---

## 项目概述

构建一个 **config-driven、可复用的 SWAT+ 自动建模框架**，应用于红心村流域（2012–2022）水文模拟。

**核心交付物：**
1. `swatplus_auto/` — 通用 Python 工具包（GitHub）
2. `configs/hongxin.yaml` — 红心村项目配置
3. 完整可运行的 SWAT+ TxtInOut 目录
4. ModelScope 双层数据集（原始数据 + 处理数据）
5. Dockerfile 环境复现配置

---

## 阶段划分

### 🔧 阶段 0：环境准备（预计 1–2 小时）

| 任务 | 说明 | 依赖 |
|------|------|------|
| 0.1 安装 TauDEM | 编译/安装 TauDEM 命令行工具（pitremove, d8flowdir, aread8, threshold, streamnet, watershed） | 无 |
| 0.2 安装 openmpi | `apt install openmpi-bin`（TauDEM 依赖） | 无 |
| 0.3 安装 Python 依赖 | geopandas, rasterio, xarray, netcdf4, scipy, pyproj, shapely | 无 |
| 0.4 初始化 GitHub 仓库 | `git init` + 关联 remote + 初始 commit（.gitignore, README 模板） | 无 |

**交付物**: 可运行的 TauDEM + Python 环境

---

### 📦 阶段 1：数据整理与原始数据上传（预计 2–3 小时）

| 任务 | 说明 | 依赖 |
|------|------|------|
| 1.1 创建规范目录结构 | 按 `data/01_raw/` + `data/02_processed/` 组织 | 无 |
| 1.2 迁移现有数据 | DEM、土地利用、土壤、CMFD 移至规范位置 | 1.1 |
| 1.3 解压 CDAT | 解压 `cdat.zip` → `data/01_raw/cdat/`（嵌套 zip 逐层解压） | 1.1 |
| 1.4 下载 All-sky 2019–2022 | Zenodo Tmax/Tmin 共 8 个 zip（~21 GB） | 1.1 |
| 1.5 原始数据上传 ModelScope | `01_raw_data/` 目录上传至 `WeijieWu/hongxin_swat` | 1.2–1.4 |

**交付物**: 
- 规范的本地数据目录
- ModelScope `01_raw_data/` 数据集

---

### 🏗️ 阶段 2：工具框架搭建（预计 3–4 小时）

| 任务 | 说明 | 依赖 |
|------|------|------|
| 2.1 创建包结构 | `swatplus_auto/` 模块 + `tests/` + `configs/` | 无 |
| 2.2 实现 `config.py` | YAML 解析、配置验证、默认值填充、路径检查 | 2.1 |
| 2.3 实现 CLI 入口 | `python -m swatplus_auto --config <file> --step <step>` | 2.2 |
| 2.4 实现日志系统 | 结构化日志（每步独立日志文件） | 2.1 |
| 2.5 编写 `hongxin.yaml` | 红心村完整配置 | 2.2 |
| 2.6 编写 Dockerfile | TauDEM + Python 环境一键复现 | 2.1 |

**交付物**:
- 可 import 的 `swatplus_auto` 包
- `configs/hongxin.yaml`
- `Dockerfile`

---

### 🗺️ 阶段 3：流域划分（预计 2–3 小时）

| 任务 | 说明 | 依赖 |
|------|------|------|
| 3.1 DEM 预处理 | TauDEM `pitremove` → `d8flowdir` → `aread8` | 0.1 |
| 3.2 设定流域出口 | 根据 config `outlet_coords` 生成 outlet shapefile | 3.1 |
| 3.3 流域划分 | TauDEM `threshold` → `streamnet` → `watershed` | 3.2 |
| 3.4 子流域矢量化 | GDAL 栅格转矢量，生成 `subbasins.shp` | 3.3 |
| 3.5 河道网络提取 | 生成 `channels.shp` | 3.3 |
| 3.6 坡度计算 | 从 DEM 计算坡度栅格 | 3.1 |

**交付物**:
- `subbasins.shp`（子流域）
- `channels.shp`（河道网络）
- `slope.tif`（坡度）
- 流域统计报告（子流域数量、面积等）

---

### 🌡️ 阶段 4：气象数据处理（预计 4–6 小时）

| 任务 | 说明 | 依赖 |
|------|------|------|
| 4.1 CMFD 单位转换 | temp(K→°C), prec(kg/m²/s→mm/day), rhum(%→0~1), srad(W/m²→MJ/m²/day) | 1.2 |
| 4.2 CMFD 流域裁剪 | 用流域边界裁剪 8 变量 .nc 文件 | 3.4 |
| 4.3 生成虚拟气象站 | 按 0.1° 间隔生成流域内格点，命名 `wx001`... | 3.4 |
| 4.4 CMFD 提取到站点 | 每个虚拟站提取时间序列（除 temp） | 4.2, 4.3 |
| 4.5 CDAT 处理 | 解压 → 裁剪 → 提取 2012–2018 Tmax/Tmin 到虚拟站 | 1.3, 4.3 |
| 4.6 All-sky 处理 | 下载 → 解压 → 重采样到 0.1° → 裁剪 → 提取 2019–2022 Tmax/Tmin | 1.4, 4.3 |
| 4.7 温度数据拼接 | 合并 CDAT(2012-18) + All-sky(2019-22) 为完整 Tmax/Tmin 序列 | 4.5, 4.6 |
| 4.8 生成 .cli 文件 | 按 SWAT+ 格式生成 `pcp.cli`, `tmp.cli`, `slr.cli`, `hmd.cli`, `wnd.cli` | 4.4, 4.7 |

**交付物**:
- `weather_stations.csv`（虚拟站坐标列表）
- 5 个 `.cli` 气象文件
- 气象数据质控报告（缺失值、异常值统计）

---

### 🧱 阶段 5：HRU 生成与 TxtInOut 构建（预计 4–6 小时）

| 任务 | 说明 | 依赖 |
|------|------|------|
| 5.1 土地利用重分类 | CLCD → SWAT+ 类别（如 AGRL, FRST 等），生成查找表 | 1.2 |
| 5.2 土壤数据处理 | HWSD2 → SWAT+ usersoil 格式 | 1.2 |
| 5.3 HRU 生成 | 子流域 × 土地利用 × 土壤 × 坡度 → HRU 划分 | 3.4, 5.1, 5.2 |
| 5.4 生成 `file.cio` | SWAT+ 主控文件 | 2.3 |
| 5.5 生成子流域文件 | `.sub`, `.pnd`, `.rte`, `.wq` 等 | 5.3 |
| 5.6 生成 HRU 文件 | `.hru`, `.mgt`, `.sol`, `.gw`, `.chm`, `.sdr`, `.sep`, `.lw` | 5.3 |
| 5.7 生成河道文件 | `.cha`, `.aqu`, `.rec` | 3.5 |
| 5.8 生成水库文件 | 察尔森水库 `res12` | 3.5 |
| 5.9 整合 TxtInOut | 所有文件按 SWAT+ 规范命名、校验 | 5.4–5.8 |

**交付物**:
- 完整的 `TxtInOut/` 目录（数百个配置文件）
- `hru_summary.csv`（HRU 统计）
- 输入校验报告

---

### ▶️ 阶段 6：SWAT+ 运行与验证（预计 1–2 小时）

| 任务 | 说明 | 依赖 |
|------|------|------|
| 6.1 运行 SWAT+ | 编译好的 `swatplus` 二进制执行 TxtInOut | 5.9 |
| 6.2 检查输出 | 验证 `channel_sd_day.txt` 等输出文件正常生成 | 6.1 |
| 6.3 水量平衡检查 | 降水 → 蒸散发 → 径流 → 地下水，检查闭合 | 6.2 |
| 6.4 初步可视化 | 出口断面流量过程线、月平均流量 | 6.2 |

**交付物**:
- `output/` 目录（模拟结果）
- 水量平衡报告
- 流量过程线图

---

### 📤 阶段 7：GitHub 推送（预计 1 小时）

| 任务 | 说明 | 依赖 |
|------|------|------|
| 7.1 整理代码 | 格式化、注释、类型提示 | 2–6 |
| 7.2 编写 README | 项目说明、安装指南、使用示例、数据下载链接 | 7.1 |
| 7.3 编写 Notebook | 结果可视化示例 | 6.4 |
| 7.4 Push 到 GitHub | `git add -A && git commit && git push origin main` | 7.1–7.3 |

**交付物**:
- [github.com/go-bananas-wwj/hongxin_swat_plus](https://github.com/go-bananas-wwj/hongxin_swat_plus)

---

### ☁️ 阶段 8：ModelScope 处理数据上传（预计 1–2 小时）

| 任务 | 说明 | 依赖 |
|------|------|------|
| 8.1 整理 `02_swatplus_ready/` | 裁剪后的栅格、.cli 文件、TxtInOut、流域 Shapefiles | 5–6 |
| 8.2 编写数据集 README | 说明每个文件的用途和格式 | 8.1 |
| 8.3 上传 ModelScope | `02_swatplus_ready/` → `WeijieWu/hongxin_swat` | 8.1–8.2 |

**交付物**:
- ModelScope 双层数据集完整版

---

### 🔬 阶段 9：模型校准（待流量数据补充后执行）

| 任务 | 说明 | 依赖 |
|------|------|------|
| 9.1 导入观测流量 | 9 个水文站日流量 | 流量数据 |
| 9.2 敏感性分析 | 识别关键参数 | 9.1 |
| 9.3 自动校准 | SWAT-CUP 或自定义校准脚本 | 9.2 |
| 9.4 验证 | 分率定期/验证期评估 | 9.3 |
| 9.5 最佳参数上传 | 校准后的 TxtInOut → ModelScope | 9.4 |

**交付物**:
- 校准报告（NSE, R², PBIAS）
- 最优参数文件
- 模拟 vs 观测对比图

---

## 时间线总览

```
Day 1 (~8h):  阶段 0 → 阶段 1 → 阶段 2
Day 2 (~8h):  阶段 3 → 阶段 4
Day 3 (~8h):  阶段 5 → 阶段 6 → 阶段 7 → 阶段 8
Day ?:        阶段 9（待流量数据）
```

> **总计约 3 个工作日**（不含 All-sky 下载等待时间和阶段 9）

---

## 风险与应对

| 风险 | 概率 | 影响 | 应对 |
|------|------|------|------|
| All-sky 下载慢/失败 | 中 | 阶段 4 延迟 | 自动重试 + 断点续传；备选：用 CMFD temp 估算 |
| TauDEM 编译失败 | 低 | 阶段 3 阻塞 | 使用预编译二进制或 Docker 镜像 |
| TxtInOut 格式不兼容 | 中 | 阶段 5 返工 | 对照 SWAT+ 官方示例逐项校验 |
| SWAT+ 运行崩溃 | 中 | 阶段 6 返工 | 逐文件检查输入格式，对照验证案例 |

---

## 需要审批的内容

1. ✅ 上述 10 个阶段的工作范围是否正确？
2. ✅ 时间预估是否合理？
3. ✅ 是否有遗漏的关键任务？
4. ✅ 是否同意按此计划执行？

**请在确认后，我将从阶段 0 开始逐步执行。**
