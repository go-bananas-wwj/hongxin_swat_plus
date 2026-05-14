# 红星村 SWAT+ 建模项目 — 详细决策记录

> 本文档记录与项目负责人的沟通细节和所有关键决策。如有歧义，以本文档为准。
> 创建时间: 2026-05-14

---

## 一、项目目标

基于 SWAT+ 构建**红心村流域水文模型**，进行流域水文过程模拟。

- **模拟期**: 2012 年 – 2022 年
- **研究区**: 红心村流域（内蒙古/吉林交界）
- **投影坐标系**: WGS_1984_UTM_51N
- **流域范围**: 119.8°–122.6°E, 45.6°–47.2°N
- **流域出口**: 镇西站 (122.371902, 45.849787)
- **水库**: 察尔森水库 (res12)

---

## 二、项目资产

| 资产类型 | 位置/链接 | 说明 |
|---------|-----------|------|
| **参考文档** | [飞书 Wiki](https://my.feishu.cn/wiki/O70MwX8y0ipwfYkXeyDcFcxYn6g) | 项目详细数据说明与处理流程 |
| **数据集托管** | [ModelScope](https://modelscope.cn/datasets/WeijieWu/hongxin_swat) | 整理后的数据集上传至此 |
| **代码仓库** | [GitHub](https://github.com/go-bananas-wwj/hongxin_swat_plus) | `git@github.com:go-bananas-wwj/hongxin_swat_plus.git` |

### 访问凭证
- **ModelScope Token**: `ms-399d1804-1cb3-446a-a3f7-dfc4dc70d977`
- **GitHub SSH**: 已配置，可直接推送

---

## 三、数据清单与决策

### 3.1 基础地理数据

| 数据 | 来源 | 分辨率 | 当前位置 | 决策 |
|------|------|--------|----------|------|
| **DEM** | Copernicus GLO-30 | 30m | `Datasets/swat_data/Watershed/Rasters/DEM/` | 保留，投影为 UTM_51N |
| **水系** | 全国4、5级水系 | — | `Datasets/swat_data/Watershed/Shapes/` | 保留 |
| **土地利用** | CLCD 2018 | 30m | `Datasets/swat_data/Watershed/Rasters/Landuse/` | **只需2018年一景，无需多年序列** |
| **土壤** | HWSD2 | 1km→90m | `Datasets/swat_data/Watershed/Rasters/Soil/` | 保留 |

### 3.2 气象驱动数据

#### CMFD v2.0（核心气象数据）

| 变量 | 原始单位 | 转换后 | 转换公式 | 是否保留 |
|------|----------|--------|----------|----------|
| **lrad** | W/m² | MJ/m²/day | `lrad * 0.0864` | ✅ 保留 |
| **prec** | kg/m²/s | mm/day | `prec * 86400` | ✅ 保留 |
| **pres** | hPa/Pa | — | 待调研 | ✅ 保留（能留就留） |
| **rhum** | % | 0~1 | `rhum / 100` | ✅ 保留 |
| **shum** | kg/kg | — | 待调研 | ✅ 保留（能留就留） |
| **srad** | W/m² | MJ/m²/day | `srad * 0.0864` | ✅ 保留 |
| **temp** | K | °C | `temp - 273.15` | ❌ **去掉**（SWAT+ 不需要平均气温） |
| **wind** | m/s | m/s | 无需转换 | ✅ 保留 |

- **时间范围**: 2012–2024（但模拟只用 2012–2022）
- **分辨率**: 0.1° 日值
- **位置**: `Datasets/CMFD_v2_2012-2024_daily/`
- **文件数**: 104 个 `.nc`（8 变量 × 13 年）
- **决策**: **原始数据上传 ModelScope 备份**，同时处理成 SWAT+ 格式

#### CDAT（补充温度：2012–2018）

- **来源**: `datasets/cdat.zip`
- **内容**: 2012–2018 每年一个 max.zip 和一个 min.zip，共 16 个嵌套 zip
- **格式**: 解压后为 **GeoTIFF**（.tif + .tfw），每日一景（每年 ~365–366 个文件）
- **用途**: 提供 **2012–2018 年的 Tmax 和 Tmin**
- **分辨率**: 0.1°（与 CMFD 相同）
- **决策**: 解压后裁剪到流域范围，提取 Tmax/Tmin

#### All-sky 气温数据（补充温度：2019–2022）

| 数据集 | Record ID | 时间范围 | 大小 | 格式 | 用途 |
|--------|-----------|----------|------|------|------|
| **Tmax** | [10983207](https://doi.org/10.5281/zenodo.10983207) | 2013–2022 | 27.1 GB | GeoTIFF (1km) | 提取 **2019–2022 Tmax** |
| **Tmin** | [10983199](https://doi.org/10.5281/zenodo.10983199) | 2013–2022 | 25.7 GB | GeoTIFF (1km) | 提取 **2019–2022 Tmin** |

- **下载范围**: **仅 2019–2022**（4 年），约 21 GB
  - Tmax: Tem-MAX_2019.zip, 2020.zip, 2021.zip, 2022.zip
  - Tmin: Tem-MIN_2019.zip, 2020.zip, 2021.zip, 2022.zip
- **单位**: 0.1°C（存储值需除以 10）
- **投影**: WGS84
- **处理**: 下载 → 解压 → **重采样到 0.1°** → 裁剪到流域范围

#### 温度数据最终拼接方案

| 年份 | Tmax 来源 | Tmin 来源 | 状态 |
|------|-----------|-----------|------|
| 2012 | CDAT | CDAT | 已就绪 |
| 2013–2018 | CDAT | CDAT | 已就绪 |
| 2019–2022 | All-sky (Zenodo) | All-sky (Zenodo) | ⏳ 需下载 |

### 3.3 观测数据（流量实测）

- **9 个水文站点**：五岔沟、索伦、察尔森下、乌兰浩特、镇西（出口）、大石寨、阿力得尔、保隆
- **当前状态**: ❌ **尚未找到文件**
- **负责人承诺**: 如未找到，将重新上传
- **待补充**: 文件格式（CSV/Excel）、时间范围、字段定义

---

## 四、数据处理规范

### 4.1 单位转换（CMFD → SWAT+）

| 变量 | 原始单位 | 目标单位 | 公式 |
|------|----------|----------|------|
| temp | K | °C | `temp - 273.15` |
| prec | kg/m²/s | mm/day | `prec * 86400` |
| rhum | % | 0~1 | `rhum / 100` |
| srad | W/m² | MJ/m²/day | `srad * 0.0864` |
| wind | m/s | m/s | 无需转换 |
| lrad | W/m² | MJ/m²/day | `lrad * 0.0864` |

### 4.2 虚拟气象站

| 参数 | 值 |
|------|-----|
| 格点间隔 | 0.1° |
| 理论格点数 | ~493 个（29 × 17） |
| **实际保留** | **仅流域边界内的格点**（预计 200–400 个） |
| 气象站 ID 命名 | ✅ 已解决 | **wx + 3位序号**，如 `wx001`, `wx002` |

### 4.3 气象数据输出格式

- **采用方式**: **单文件多站点（.cli 格式）**
- **文件列表**:
  - `pcp.cli` — 降水
  - `tmp.cli` — 温度（Tmax + Tmin）
  - `slr.cli` — 太阳辐射
  - `hmd.cli` — 相对湿度
  - `wnd.cli` — 风速
  - `lrad.cli` — 长波辐射（如 SWAT+ 支持）
- **原因**: SWAT+ 官方推荐，管理几百个站点更方便

### 4.4 空间处理

- **统一投影**: WGS_1984_UTM_51N
- **裁剪范围**: 流域边界（从 Shapefile 读取）
- **重采样**: All-sky 1km → 0.1°（与 CMFD 对齐）

---

## 五、目录结构规划（阶段一：规范化）

```
hongxin_swaw_plus/
├── data/                          ← 统一数据目录
│   ├── 01_raw/                    ← 原始数据（不改名、不转换）
│   │   ├── cmfd_v2_daily/         ← CMFD 8变量原始 .nc
│   │   ├── cdat/                  ← CDAT 解压后原始数据
│   │   ├── allsky_temp/           ← All-sky Tmax/Tmin 下载数据
│   │   ├── dem/
│   │   ├── landuse/
│   │   ├── soil/
│   │   └── hydrology/             ← 流量实测数据（待补充）
│   ├── 02_processed/              ← 处理后的数据
│   │   ├── cmfd_basin_cropped/    ← 流域裁剪后的 CMFD
│   │   ├── weather_stations/      ← 虚拟气象站坐标 + 数据
│   │   └── swatplus_input/        ← SWAT+ 格式气象文件 (.cli)
│   └── README.md                  ← 数据清单与说明
├── scripts/                       ← Python 处理脚本
├── model/                         ← SWAT+ 模型文件（后续生成）
├── AGENTS.md                      ← Agent 协作指南
└── details.md                     ← 本文件
```

---

## 六、待办事项

- [ ] 调研 SWAT+ 对 pres/shum 的需求
- [ ] 调研 SWAT+ 气象输入的完整规范（.cli 文件格式）
- [ ] 下载 All-sky Tmax/Tmin 2019–2022（~21 GB）
- [ ] 解压 CDAT 嵌套 zip
- [ ] 生成流域边界 Shapefile 裁剪掩膜
- [ ] 生成虚拟气象站坐标列表
- [ ] CMFD 单位转换 + 流域裁剪
- [ ] All-sky 重采样到 0.1° + 裁剪
- [ ] 温度数据拼接（CDAT + All-sky）
- [ ] 生成 SWAT+ .cli 气象文件
- [ ] 等待流量实测数据上传
- [ ] 原始数据上传 ModelScope
- [ ] Python 脚本 push 到 GitHub

---

## 七、问题追踪（已解决 / 待解决）

| # | 问题 | 状态 | 决策 |
|---|------|------|------|
| 1 | CMFD 变量取舍（8个 vs 6个） | ✅ 已解决 | **8个全保留**，temp 去掉 |
| 2 | 温度数据拼接逻辑 | ✅ 已解决 | CDAT(2012-18) + All-sky(2019-22) |
| 3 | 模拟时间范围 | ✅ 已解决 | **2012–2022** |
| 4 | All-sky 下载范围 | ✅ 已解决 | **仅 2019–2022** |
| 5 | CLCD 是否需要多年 | ✅ 已解决 | **只需2018年** |
| 6 | SWAT+ 气象格式 | ✅ 已解决 | **单文件 .cli 格式** |
| 7 | 虚拟气象站范围 | ✅ 已解决 | **仅流域内格点** |
| 8 | 气象站 ID 命名 | ✅ 已解决 | **wx + 3位序号**（wx001, wx002...），简洁且 SWAT+ .cli 文件单独记录坐标 |
| 9 | 流量实测数据位置 | ✅ 已解决 | **以后补充**，预留目录 `data/01_raw/hydrology/` |
| 10 | ModelScope 上传结构 | ✅ 已解决 | **方案 A（双层结构）**：`01_raw_data/` + `02_swatplus_ready/` |
| 11 | GitHub 仓库内容 | ✅ 已解决 | **Python脚本 + SWAT+配置 + Notebooks + Dockerfile**，不含原始数据和二进制 |
| 12 | SWAT+ 对 lrad/pres/shum 的需求 | ⏳ 待调研 | Agent 负责调研 |
| 13 | 流域建模方案 | ✅ 已解决 | **方案 B**：TauDEM + Python 全自动化 |
| 14 | 工具封装架构 | ✅ 已解决 | **通用框架**，YAML config，CLI + Python API，分步执行 |
| 15 | 校准模块 | ✅ 已解决 | **预留接口**，流量数据到后实现 |
