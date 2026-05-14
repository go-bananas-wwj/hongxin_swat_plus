# hongxin_swat_plus — Agent 协作指南

> 本项目目标：基于 SWAT+ 构建**红心村流域水文模型**，进行流域水文过程模拟。

## 项目资产

| 资产类型 | 位置 | 说明 |
|---------|------|------|
| **参考文档** | [飞书 Wiki](https://my.feishu.cn/wiki/O70MwX8y0ipwfYkXeyDcFcxYn6g) | 项目详细数据说明与处理流程 |
| **数据集托管** | [ModelScope](https://modelscope.cn/datasets/WeijieWu/hongxin_swat) | 整理后的数据集上传至此 |
| **代码仓库** | [GitHub](https://github.com/go-bananas-wwj/hongxin_swat_plus) | `git@github.com:go-bananas-wwj/hongxin_swat_plus.git` |

### ModelScope 访问
- Token: `ms-399d1804-1cb3-446a-a3f7-dfc4dc70d977`
- 数据集名: `WeijieWu/hongxin_swat`

### GitHub 访问
- SSH 已配置，可直接 `git@github.com:go-bananas-wwj/hongxin_swat_plus.git` 推送
- 当前工作目录 `/workspace/hongxin_swaw_plus/` 尚未初始化 git

## 流域概况

| 属性 | 值 |
|------|-----|
| 研究区 | 红心村流域（内蒙古/吉林交界） |
| 投影坐标系 | WGS_1984_UTM_51N |
| 流域范围 | 119.8°–122.6°E, 45.6°–47.2°N |
| 流域出口 | 镇西站 (122.371902, 45.849787) |
| 水库 | 察尔森水库 (res12) |

## 数据清单（按飞书文档）

### 基础地理数据
| 数据 | 来源 | 分辨率 | 状态 |
|------|------|--------|------|
| DEM | Copernicus GLO-30 | 30m | `Datasets/swat_data/Watershed/Rasters/DEM/` |
| 水系 | 全国4、5级水系 | — | `Datasets/swat_data/Watershed/Shapes/` |
| 土地利用 | CLCD (2018) | 30m | `Datasets/swat_data/Watershed/Rasters/Landuse/` |
| 土壤 | HWSD2 | 1km→90m | `Datasets/swat_data/Watershed/Rasters/Soil/` |

### 气象驱动数据
| 数据 | 变量 | 时间范围 | 分辨率 | 位置 |
|------|------|----------|--------|------|
| CMFD v2.0 | lrad, prec, **pres, rhum, shum**, srad, temp, wind | 2012–2024 | 0.1° 日值 | `Datasets/CMFD_v2_2012-2024_daily/` |
| CDAT | 日气温 (max/min) | 2012–2018 | 0.1° | `datasets/cdat.zip` |
| All-sky min temp | 日最低温 | 2013–2022 | 1km→0.1° | 待确认 |

> **注意**：CMFD 实际下载了 8 个变量（含 pres 气压、shum 比湿），飞书文档提及 6 个变量。需确认 pres/shum 是否用于 SWAT+。

### 观测数据
- 9 个水文站流量实测数据（待定位）

## 数据处理规范（已确认）

### CMFD 单位转换
| 变量 | 原始单位 | 转换后 | 公式 |
|------|----------|--------|------|
| temp | K | °C | `temp - 273.15` |
| prec | kg/m²/s | mm/day | `prec * 86400` |
| rhum | % | 0~1 | `rhum / 100` |
| srad | W/m² | MJ/m²/day | `srad * 0.0864` |
| wind | m/s | m/s | 无需转换 |
| lrad | W/m² | MJ/m²/day | 待确认 |

### 虚拟气象站
- 每隔 0.1° 设置一个格点，共约 400+ 个虚拟气象站
- 用流域边界裁剪后，为每个子流域匹配最近的虚拟站

## 代码规范

- 数据处理脚本使用 Python（推荐 conda env `hongxin_swat`）
- SWAT+ 模型编译使用 Intel oneAPI ifx 2024.1.2
- 每次代码修改后必须 commit + push 到 GitHub

## 待澄清事项

（由 Agent 维护，每次会话后更新）

1. **CMFD 变量取舍**：实际下载了 8 个变量（lrad/prec/pres/rhum/shum/srad/temp/wind），飞书文档说 6 个（无 pres/shum）。pres/shum 是否保留？
2. **CDAT 数据处理**：cdat.zip 内是嵌套 zip（2012–2018 每年 max/min 各一个），如何解压、裁剪、与 CMFD 拼接？
3. **All-sky 气温数据**：飞书提到补充 2019–2022 年，当前是否已下载？
4. **流量实测数据**：9 个水文站实测数据文件在哪里？格式是 CSV/Excel？
5. **土地利用**：CLCD 仅 2018 年一景，还是需要多年序列（如 2012–2024）？
6. **最终目标**：构建可运行的 SWAT+ 项目文件 → 运行模拟 → 校准 → 验证？还是仅整理数据集？
7. **代码仓库内容**：是否包含：① Python 数据处理脚本 ② SWAT+ 项目配置文件 ③ 完整可运行的 TxtInOut？
8. **ModelScope 数据集结构**：按原始数据分类上传（DEM/气象/土地利用/土壤/观测），还是按 SWAT+ 输入格式组织？
