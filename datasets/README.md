# 数据集归档目录 (datasets)

本目录存放原始数据集的大型归档文件和已处理的数据产品。

---

## 目录结构

```
datasets/
├── CMFD_2012-2024.zip              # CMFD v2.0 完整原始数据（备份）
├── cdat.zip                        # CDAT 原始数据（2012-2018）
├── hongxin_hydro_discharge_sediment_2012_2022_daily.zip  # 水文观测数据
├── new.zip                         # 原始 Excel 水文数据（121 个 workbook）
├── new_extracted/                  # 解压后的原始 Excel 文件
├── processed_hydro/                # 处理后的水文观测 CSV
├── swat_data.zip                   # 原始 SWAT 项目数据（含 DEM/土地利用/土壤）
├── Tem-MAX_2019.zip ~ Tem-MAX_2022.zip   # All-sky 日最高气温
└── Tem-MIN_2019.zip ~ Tem-MIN_2022.zip   # All-sky 日最低气温
```

---

## 原始数据集

### CMFD_2012-2024.zip

**中国区域地面气象要素驱动数据集 v2.0**
- 时间范围: 2012–2024
- 变量: lrad, prec, pres, rhum, shum, srad, temp, wind
- 格式: NetCDF
- 分辨率: 0.1° 日值
- 大小: ~104 个 .nc 文件

---

### cdat.zip

**中国近地表日气温数据集**
- 时间范围: 2012–2018
- 变量: Tmax (日最高气温), Tmin (日最低气温)
- 格式: GeoTIFF (.tif + .tfw)
- 分辨率: 0.1°
- 结构: 嵌套 zip，每年一个 `max.zip` 和一个 `min.zip`

---

### All-sky 气温数据 (Tem-MAX/MIN_20{19-2022}.zip)

**All-sky daily ambient air temperature**
- 来源: Zenodo
- 时间范围: 2019–2022
- 变量: Tmax, Tmin
- 格式: GeoTIFF
- 分辨率: 1km
- 单位: 0.1°C（Int16）
- 投影: WGS84

| 文件 | 年份 | 变量 | 大小 |
|------|------|------|------|
| `Tem-MAX_2019.zip` | 2019 | Tmax | ~5.4 GB |
| `Tem-MAX_2020.zip` | 2020 | Tmax | ~5.4 GB |
| `Tem-MAX_2021.zip` | 2021 | Tmax | ~5.4 GB |
| `Tem-MAX_2022.zip` | 2022 | Tmax | ~5.4 GB |
| `Tem-MIN_2019.zip` | 2019 | Tmin | ~5.1 GB |
| `Tem-MIN_2020.zip` | 2020 | Tmin | ~5.1 GB |
| `Tem-MIN_2021.zip` | 2021 | Tmin | ~5.1 GB |
| `Tem-MIN_2022.zip` | 2022 | Tmin | ~5.1 GB |

---

### swat_data.zip

**原始 SWAT 项目基础地理数据**
- DEM (Copernicus GLO-30, 30m)
- 土地利用 (CLCD 2018, 30m)
- 土壤 (HWSD2, 1km→90m)
- 水系矢量数据

---

## 处理后数据产品

### processed_hydro/

**水文观测日值 CSV**

从 121 个 Excel workbook 提取并转换的标准长格式 CSV。

| 文件名 | 站名 | 变量 | 时间范围 |
|--------|------|------|----------|
| `五岔沟_discharge_2012_2022_daily.csv` | 五岔沟 | 流量 | 2012–2022 |
| `保隆_discharge_2012_2022_daily.csv` | 保隆 | 流量 | 2012–2022 |
| `保隆_sediment_2012_2022_daily.csv` | 保隆 | 输沙量 | 2012–2022 |
| `大石寨_discharge_2012_2022_daily.csv` | 大石寨 | 流量 | 2012–2022 |
| `大石寨_sediment_2012_2022_daily.csv` | 大石寨 | 输沙量 | 2012–2022 |
| `察尔森下_discharge_2012_2022_daily.csv` | 察尔森下 | 流量 | 2012–2022 |
| `察尔森_discharge_2012_2022_daily.csv` | 察尔森 | 流量 | 2012–2022 |
| `索伦_discharge_2012_2022_daily.csv` | 索伦 | 流量 | 2012–2022 |
| `镇西_discharge_2012_2022_daily.csv` | 镇西 | 流量 | 2012–2022 |
| `镇西_sediment_2012_2022_daily.csv` | 镇西 | 输沙量 | 2012–2022 |
| `阿力得尔_discharge_2012_2022_daily.csv` | 阿力得尔 | 流量 | 2012–2022 |

**文件格式**：
```csv
date,value
2012-01-01,0.0
2012-01-02,1.23
...
```

- `date`: 日期（YYYY-MM-DD）
- `value`: 流量（m³/s）或输沙量（t）

---

## ModelScope 上传清单

以下数据已上传至 [ModelScope 数据集](https://modelscope.cn/datasets/WeijieWu/hongxin_swat)：

| 数据 | 路径 | 文件数 | 状态 |
|------|------|--------|------|
| 水文观测 | `hongxin_hydro_discharge_sediment_2012_2022_daily.zip` | 1 | ✅ 已上传 |
| All-sky 气温 | `allsky_temperature/Tem-{MAX,MIN}_20{19-2022}.zip` | 8 | ✅ 已上传 |
| CMFD v2.0 | `01_raw_data/cmfd_v2_daily/` | ~100 | ✅ 已上传 |
| CDAT | `01_raw_data/cdat/` | ~28 | ✅ 已上传 |
| DEM | `01_raw_data/dem/` | 3 | ✅ 已上传 |
| 土地利用 | `01_raw_data/landuse/` | 4 | ✅ 已上传 |
| 土壤 | `01_raw_data/soil/` | 6 | ✅ 已上传 |
| 流域矢量 | `01_raw_data/watershed_shapes/` | 19 | ✅ 已上传 |

> **注意**: `data/02_processed/weather_stations/` 下的 448 站点 CSV 数据（约 3000+ 个小文件）暂未上传 ModelScope，如需备份请告知。

---

## 使用条款

所有数据仅供学术研究使用。原始数据版权归原作者/机构所有。
