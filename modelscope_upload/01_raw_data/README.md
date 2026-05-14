# 原始数据目录 (01_raw_data)

本目录存放 SWAT+ 红心村流域建模所需的全部原始数据，未经任何处理。

---

## 目录结构

```
01_raw/
├── cmfd_v2_daily/          # CMFD v2.0 中国区域地面气象要素驱动数据集
├── cdat/                   # 中国近地表日气温数据集 (2012-2018)
├── allsky_temp/            # All-sky 气温数据集 (2019-2022, 下载中)
├── dem/                    # 数字高程模型 (Copernicus GLO-30)
├── landuse/                # 土地利用数据 (CLCD 2018)
├── soil/                   # 土壤数据 (HWSD2) + 查找表
├── watershed_shapes/       # 现有流域矢量数据（参考用，将重新生成）
└── hydrology/              # 流量实测数据（预留，待补充）
```

---

## 数据详情

### cmfd_v2_daily/

**中国区域地面气象要素驱动数据集 v2.0**
- 来源: 国家青藏高原科学数据中心
- 时间范围: 2012–2024
- 分辨率: 0.1° 日值
- 变量: lrad, prec, pres, rhum, shum, srad, temp, wind
- 引用: 何杰等. (2024). 中国区域地面气象要素驱动数据集 v2.0. https://doi.org/10.11888/Atmos.tpdc.302088

### cdat/

**中国近地表日气温数据集**
- 来源: 国家气象科学数据中心
- 时间范围: 2012–2018
- 格式: GeoTIFF (.tif), 每日一景
- 变量: Tmax (最高气温), Tmin (最低气温)
- 分辨率: 0.1°

### allsky_temp/

**All-sky daily ambient air temperature datasets**
- 来源: Zenodo
- 时间范围: 2019–2022（仅下载此范围）
- 格式: GeoTIFF (.tif), 每日一景
- 分辨率: 1km（需重采样到 0.1°）
- 单位: 0.1°C

### dem/

**Copernicus GLO-30 Digital Elevation Model**
- 分辨率: 30m
- 投影: WGS_1984
- 文件: `output_hh_utm51N_hongxinClip2.tif`

### landuse/

**China Land Cover Dataset (CLCD) 2018**
- 来源: 武汉大学杨杰教授团队
- 分辨率: 30m
- 投影: Albert（需转换到 UTM_51N）
- 文件: `CLCD_2018_clip_hongxin.tif`

### soil/

**HWSD2 (Harmonized World Soil Database v2)**
- 分辨率: 1km → 90m
- 投影: UTM 51N
- 文件: `HWSD2_clip_utm51n_90m.tif`
- 查找表:
  - `usersoil.csv` — SWAT+ 土壤参数
  - `soil_lookup.csv` — 土壤编码映射
  - `landuse_lookup.csv` — 土地利用编码映射

---

## 使用条款

所有数据仅供学术研究使用。原始数据版权归原作者/机构所有。
