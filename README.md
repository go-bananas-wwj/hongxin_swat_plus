# 红心村流域 SWAT+ 水文模型

[![ModelScope](https://img.shields.io/badge/ModelScope-Dataset-blue)](https://modelscope.cn/datasets/WeijieWu/hongxin_swat)
[![SWAT+](https://img.shields.io/badge/SWAT%2B-v61.0.2-green)](https://swatplus.gitbook.io/docs/)

> 基于 SWAT+ 构建的红心村流域（内蒙古/吉林交界）分布式水文过程模拟项目。

---

## 📋 项目概述

本项目旨在为**红心村流域**构建一个可运行、可复现的 SWAT+ (Soil and Water Assessment Tool Plus) 水文模型，模拟 2012–2022 年期间流域内的水文循环过程，包括降水、蒸散发、径流、泥沙输移等关键过程。

### 流域基本信息

| 属性 | 值 |
|------|-----|
| **研究区** | 红心村流域（内蒙古/吉林交界） |
| **投影坐标系** | WGS_1984_UTM_51N |
| **流域范围** | 119.8°–122.6°E, 45.6°–47.2°N |
| **流域出口** | 镇西站 (122.371902, 45.849787) |
| **子流域数** | 282 |
| **HRU 数** | 2,356 |
| **气象站数** | 448（虚拟格点站） |
| **水库** | 察尔森水库 (res12) |
| **模拟时段** | 2012–2022（共 11 年） |

---

## 🗂️ 数据集

本项目的数据集托管在 **ModelScope** 平台：

🔗 **https://modelscope.cn/datasets/WeijieWu/hongxin_swat**

### 已上传数据

| 数据 | 说明 | 时间范围 |
|------|------|----------|
| `hongxin_hydro_discharge_sediment_2012_2022_daily.zip` | 8 个水文站日流量 + 3 个站日输沙量 | 2012–2022 |

### 数据详情

**流量观测站（8 个）**：
- 五岔沟、保隆、大石寨、察尔森下、察尔森、索伦、镇西、阿力得尔

**输沙量观测站（3 个）**：
- 保隆、大石寨、镇西

> 原始数据来源于 Excel  pivot 表格（行=日，列=月），经 Python 脚本转换为标准 CSV 长格式（`date`, `value`）。

---

## 🏗️ 模型设置

### SWAT+ 版本
- **v61.0.2**，使用 Intel oneAPI `ifx 2024.1.2` 编译（静态链接）

### 基础地理数据

| 数据 | 来源 | 分辨率 |
|------|------|--------|
| DEM | Copernicus GLO-30 | 30 m |
| 土地利用 | CLCD (2018) | 30 m |
| 土壤 | HWSD2 | 1 km → 90 m 重采样 |
| 水系 | 全国 4/5 级水系 | — |

### 气象驱动数据

| 数据 | 变量 | 时间范围 | 分辨率 |
|------|------|----------|--------|
| CMFD v2.0 | lrad, prec, pres, rhum, shum, srad, temp, wind | 2012–2024 | 0.1° 日值 |
| CDAT | 日气温 (max/min) | 2012–2018 | 0.1° |
| All-sky | 日最低温 (Tmax/Tmin) | 2019–2022 | 1 km → 0.1° |

**单位转换**：
- `temp`: K → °C (`temp - 273.15`)
- `prec`: kg/m²/s → mm/day (`prec * 86400`)
- `rhum`: % → 0–1 (`rhum / 100`)
- `srad`: W/m² → MJ/m²/day (`srad * 0.0864`)

---

## 🔧 关键 Bug 修复

在构建可运行模型的过程中，发现并修复了 SWAT+ v61.0.2 源码中的两个关键问题：

### 1. `pl_fert.f90` — 化学施用数据库空指针崩溃

**症状**：当 `chem_app.ops` 为空时，`chemapp_db` 被分配为 `(0:0)`，而 `fert` 操作中的 `fertop` 默认为 0，导致访问 `chemapp_db(0)%surf_frac` 时发生 **SIGSEGV**。

**修复**：
- 在 `chem_app.ops` 中添加默认 `null` 条目（`surf_frac = 0.5`），匹配 `management.sch` 中大量 `null` 类型的施肥操作
- 在 `pl_fert.f90` 中增加安全判断：当 `fertop > 0` 时使用数据库值，否则回退到默认值 `0.5`

### 2. `climate_control.f90` — 除零保护

**症状**：当 `pet_sum` 极小时，`p_pet_rto = precip_sum / pet_sum` 发生浮点除零。

**修复**：增加 `pet_sum > 1.e-12` 判断，避免除零。

---

## 📁 仓库结构

```
hongxin_swat_plus/
├── AGENTS.md                     # Agent 协作指南（内部）
├── README.md                     # 本文件
├── configs/                      # 项目配置文件
├── data/
│   └── 02_processed/
│       ├── TxtInOut_v61/         # SWAT+ v61 项目输入文件（.gitignore）
│       └── weather_stations/     # 虚拟气象站列表
├── datasets/
│   └── processed_hydro/          # 处理后的水文观测 CSV
├── scripts/
│   ├── convert_to_swat61.py      # TxtInOut v59 → v61 转换
│   ├── process_cmfd.py           # CMFD 气象数据处理
│   ├── process_cdat.py           # CDAT 气温数据处理
│   ├── generate_hru.py           # HRU 生成辅助
│   ├── generate_swatplus_cli.py  # .cli 气象文件生成
│   └── download_allsky.py        # All-sky 数据下载
├── swatplus-61.0.2/              # SWAT+ v61.0.2 源码（含修复）
│   └── src/
│       ├── pl_fert.f90           # [修复] 肥料施用崩溃
│       └── climate_control.f90   # [修复] 除零保护
└── details.md                    # 详细技术笔记
```

---

## 🚀 快速开始

### 环境要求

- **操作系统**：Linux (Ubuntu 22.04)
- **Fortran 编译器**：Intel oneAPI `ifx 2024.1.2`
- **Python**：3.11（conda 环境 `hongxin_swat`）
- **关键 Python 包**：`geopandas`, `rasterio`, `xarray`, `netcdf4`, `pandas`, `numpy`

### 编译 SWAT+

```bash
source /opt/intel/oneapi/setvars.sh
cd swatplus-61.0.2/build
cmake .. -DCMAKE_Fortran_COMPILER=ifx
make -j4
```

### 运行模型

```bash
cd data/02_processed/TxtInOut_v61
/path/to/swatplus-unknown-ifx-lin_x86_64-Rel
```

### 运行验证

本项目已在 282 子流域 / 2,356 HRU / 448 气象站 的配置下完成 **2012–2022 共 11 年**的完整模拟，输出文件正常生成（`basin_carbon_all.txt`、`channel_sd_day.txt` 等）。

---

## 📊 观测数据使用

`datasets/processed_hydro/` 目录下包含可直接用于模型校准的日值 CSV：

```csv
date,value
2012-01-01,0.0
2012-01-02,1.23
...
```

文件名格式：`<站名>_<变量>_<起始年>_<结束年>_daily.csv`

- `<站名>`：五岔沟、保隆、大石寨、察尔森下、察尔森、索伦、镇西、阿力得尔
- `<变量>`：`discharge`（流量, m³/s）或 `sediment`（输沙量, t）

---

## 📚 相关资源

| 资源 | 链接 |
|------|------|
| **数据集 (ModelScope)** | https://modelscope.cn/datasets/WeijieWu/hongxin_swat |
| **项目 Wiki (飞书)** | https://my.feishu.cn/wiki/O70MwX8y0ipwfYkXeyDcFcxYn6g |
| **SWAT+ 官方文档** | https://swatplus.gitbook.io/docs/ |
| **SWAT+ 源码** | https://github.com/swat-model/SWATplus |

---

## 📄 许可

本项目代码遵循 MIT License。数据集使用遵循原始数据提供方的许可协议（CMFD 为科学数据共享协议，CLCD/HWSD2 为公开学术数据）。

---

## 🙏 致谢

- 气象驱动数据：[CMFD v2.0](http://www.tpdc.ac.cn)（青藏高原数据中心）
- 土地利用数据：[CLCD](https://zenodo.org/records/5816591)（武汉大学杨杰团队）
- 土壤数据：[HWSD2](https://www.fao.org/soils-portal/data-hub/soil-maps-and-databases/harmonized-world-soil-database-v20/en/)（FAO/IIASA）
