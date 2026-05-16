# SWAT+ Automated Setup Tool

一个基于 YAML 配置文件的 SWAT+ 流域建模自动化工具，实现从流域划分 (Delineation) → HRU 生成 → TxtInOut 导出的完整工作流。

## 特性

- **完全绕过 QSWATPlus GUI**：使用 Python + GDAL 直接处理，支持纯命令行/服务器环境
- **YAML 配置驱动**：所有参数通过单个 YAML 文件管理，便于复现和批量处理
- **兼容现有 QSWATPlus 项目**：可读取 QSWATPlus 生成的 shapefile、SQLite lookup 表和旧 TxtInOut 模板
- **自动生成 SWAT+ 输入文件**：包括拓扑文件 (`.con`)、参数文件 (`.cha`) 和对象计数文件
- **SWAT+ v61 验证**：已在 SWAT+ v61.0.2 上验证可运行

## 环境要求

- Python 3.9+
- GDAL (with Python bindings)
- PyYAML
- NumPy

## 安装

```bash
pip install pyyaml numpy
# GDAL 通常通过系统包管理器安装，例如：
# apt-get install python3-gdal
```

## 快速开始

### 1. 准备配置文件

复制 `config.yaml` 并根据你的项目修改路径和参数：

```yaml
project:
  name: "my_project"
  output_dir: "./output"
  use_existing_delineation: true
  template_txtinout: "/path/to/old/TxtInOut"

inputs:
  dem:
    path: "/path/to/dem.tif"
  outlets:
    path: "/path/to/outlets.shp"
  landuse:
    raster: "/path/to/landuse.tif"
    lookup_sqlite: "/path/to/project.sqlite"
    lookup_table: "landuse_lookup"
  soil:
    raster: "/path/to/soil.tif"
    lookup_sqlite: "/path/to/project.sqlite"
    lookup_table: "soil_lookup"
  slope:
    raster: "/path/to/slope.tif"
    limits: [0, 2, 5, 999]

delineation:
  existing:
    channel_shp: "/path/to/channel.shp"
    stream_shp: "/path/to/stream.shp"
    subbasin_shp: "/path/to/subbasins.shp"

hru:
  mode: "multiple"
  min_area_ha: 0.0

swatplus:
  start_date: "2018-01-01"
  end_date: "2020-12-31"
```

### 2. 运行工具

```bash
python swatplus_setup.py --config config.yaml
```

可选参数：
- `--step delineation`：仅运行流域划分
- `--step hru`：仅运行 HRU 生成（需要先完成 delineation）
- `--step txtinout`：仅运行 TxtInOut 生成
- `--verbose`：显示详细日志

### 3. 运行 SWAT+

```bash
cd output/TxtInOut
/path/to/swatplus
```

## 配置文件详解

### `project` 段

| 参数 | 说明 |
|------|------|
| `name` | 项目名称，用于生成文件头 |
| `output_dir` | 输出根目录 |
| `use_existing_delineation` | `true` 时读取已有 shapefile，`false` 时运行 TauDEM（尚未实现） |
| `template_txtinout` | 旧 TxtInOut 目录，用于复制 soils.sol、plants.plt 等参数模板 |

### `inputs` 段

| 参数 | 说明 |
|------|------|
| `dem.path` | DEM 栅格路径 |
| `outlets.path` | 出水口/监测站点 shapefile |
| `landuse.raster` | 土地利用栅格 |
| `soil.raster` | 土壤栅格 |
| `slope.raster` | 坡度栅格 |
| `slope.limits` | 坡度分级界限（百分比），如 `[0, 2, 5, 999]` |

### `delineation` 段

| 参数 | 说明 |
|------|------|
| `existing.channel_shp` | 河道 shapefile（需含 LINKNO/DSLINKNO/USLINKNO1/USLINKNO2） |
| `existing.subbasin_shp` | 子流域 shapefile（需含 Subbasin 字段） |
| `taudem_bin` | TauDEM 可执行文件目录（未来用于自动划分） |
| `stream_threshold` | 河流阈值（栅格单元数） |
| `channel_threshold` | 河道阈值（栅格单元数） |

### `hru` 段

| 参数 | 说明 |
|------|------|
| `mode` | `"multiple"` 为多 HRU 模式，`"dominant"` 为单 HRU 模式 |
| `min_area_ha` | 最小 HRU 面积（公顷），小于此值的 HRU 会被合并 |
| `min_percent` | 最小 HRU 占比（%） |

### `swatplus` 段

| 参数 | 说明 |
|------|------|
| `start_date` / `end_date` | 模拟起止日期 |
| `time_step` | `0`=日, `1`=月, `2`=年 |
| `warmup_years` | 预热年数 |

## 输出结构

```
output/
├── delineation/
│   └── watershed.tif          # 子流域栅格（从 subbasin shapefile 栅格化生成）
├── hrus/
│   ├── landuse_aligned.tif    # 重投影后的土地利用栅格
│   ├── soil_aligned.tif       # 重投影后的土壤栅格
│   ├── slope_aligned.tif      # 重投影后的坡度栅格
│   └── hru_report.txt         # HRU 统计报告
└── TxtInOut/
    ├── channel.con            # 河道连接文件
    ├── hru.con                # HRU 连接文件
    ├── outlet.con             # 出水口文件
    ├── object.cnt             # 对象计数
    ├── channel.cha            # 河道参数索引
    ├── hydrology.cha          # 水文参数（ slope/length 从 shapefile 提取）
    ├── hru-data.hru           # HRU 数据
    ├── file.cio               # 主控制文件
    ├── time.sim               # 时间配置
    └── [从模板复制的参数文件]  # soils.sol, plants.plt, landuse.lum 等
```

## 与 QSWATPlus 的区别

本工具与 QSWATPlus 的主要差异：

1. **不依赖 QGIS/QSWATPlus GUI**：可在无图形界面的服务器上运行
2. **Channel 合并逻辑简化**：QSWATPlus 会根据阈值合并短河道，本工具保留所有正长度河道
3. **Lake 处理**：本工具不处理湖泊（假设无湖泊），QSWATPlus 支持复杂湖泊逻辑
4. **HRU 移除策略**：使用面积阈值合并，与 QSWATPlus 的百分比/目标数模式略有不同
5. **气象数据**：本工具不生成或修改气象数据，需提前准备或在旧模板中配置

## 已知限制

- TauDEM 自动划分尚未实现，目前需手动运行 TauDEM 后提供 shapefile
- 不支持 grid-based 模型（仅支持 subbasin-based）
- 不支持点源 (point source)、水库 (reservoir) 等高级对象
- 景观单元 (LSU) 和洪泛区 (floodplain) 分割尚未实现

## 调试技巧

如果 SWAT+ 运行报错，常见检查点：

1. **channel.con / hru.con 行数** 应与 object.cnt 中的 cha/hru 数量一致
2. **hydrology.cha 条目数** 应等于 channel.con 中的 channel 数量
3. **hru-data.hru 中的 soil/lu_mgt 名称** 应与 soils.sol / landuse.lum 中的定义匹配
4. **file.cio 中的 object 数量** 应等于 hru + cha + out + ...

## 许可证

本工具为项目内部使用开发，基于 SWAT+ 开源模型和 TauDEM 地形分析工具。
