# hongxin_swat_plus — Agent 协作指南

> 本项目目标：基于 SWAT+ 构建**红心村流域水文模型**，进行流域水文过程模拟（2012–2022）。

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
- 当前工作目录 `/workspace/hongxin_swaw_plus/` **已初始化 git**

---

## 流域概况

| 属性 | 值 |
|------|-----|
| 研究区 | 红心村流域（内蒙古/吉林交界） |
| 投影坐标系 | WGS_1984_UTM_51N |
| 流域范围 | 119.8°–122.6°E, 45.6°–47.2°N |
| 流域出口 | 镇西站 (122.371902, 45.849787) |
| 子流域数 | 282 |
| HRU 数 | 2,356 |
| 气象站数 | 448（虚拟格点站） |
| 水库 | 察尔森水库 (res12) |
| 模拟时段 | 2012–2022（共 11 年） |

---

## 数据清单

### 基础地理数据

| 数据 | 来源 | 分辨率 | 位置 |
|------|------|--------|------|
| DEM | Copernicus GLO-30 | 30m | `data/01_raw/dem/` |
| 水系 | 全国4、5级水系 | — | `data/01_raw/watershed_shapes/` |
| 土地利用 | CLCD (2018) | 30m | `data/01_raw/landuse/` |
| 土壤 | HWSD2 | 1km→90m | `data/01_raw/soil/` |

### 气象驱动数据

| 数据 | 变量 | 时间范围 | 分辨率 | 位置 |
|------|------|----------|--------|------|
| CMFD v2.0 | lrad, prec, rhum, srad, wind | 2012–2022 | 0.1° 日值 | `data/01_raw/cmfd_v2_daily/` |
| CDAT | Tmax, Tmin | 2012–2018 | 0.1° | `datasets/cdat.zip` |
| All-sky | Tmax, Tmin | 2019–2022 | 1km→0.1° | `data/01_raw/allsky_temp/` |

> 温度数据拼接：**CDAT (2012–2018) + All-sky (2019–2022)**，最终写入 `data/02_processed/weather_stations/tmax/` 和 `tmin/`。

### 观测数据
- 8 个水文站流量数据 + 3 个站输沙量数据
- 位置: `datasets/processed_hydro/`
- 已上传 ModelScope

---

## 数据处理规范

### CMFD 单位转换

| 变量 | 原始单位 | 转换后 | 公式 |
|------|----------|--------|------|
| temp | K | °C | `temp - 273.15` |
| prec | kg/m²/s | mm/day | `prec * 86400` |
| rhum | % | 0~1 | `rhum / 100` |
| srad | W/m² | MJ/m²/day | `srad * 0.0864` |
| wind | m/s | m/s | 无需转换 |
| lrad | W/m² | MJ/m²/day | `lrad * 0.0864` |

### All-sky 单位
- 原始数据为 **Int16**，比例因子为 **0.1**（即 `raw * 0.1 = °C`）
- NoData: -9999

### 虚拟气象站
- 每隔 0.1° 设置一个格点，共 **448** 个虚拟气象站
- 命名: `wx001` ~ `wx448`
- 坐标文件: `data/02_processed/weather_stations/stations.csv`

---

## 工作规范（必须遵守）

### 1. Git 同步规范 ⭐

**每次改动必须同步到 GitHub。**

```bash
# 添加所有变更
git add -A

# 提交（写有意义的 commit message）
git commit -m "type: description"

# 推送到远程
git push origin main
```

**Commit message 规范**：
- `feat:` — 新功能/新脚本
- `fix:` — Bug 修复
- `docs:` — 文档更新（README, AGENTS.md）
- `data:` — 数据更新/处理
- `chore:` — 杂项（清理、配置等）

**例外**：`data/02_processed/TxtInOut_v61/` 下的输入文件（`.tmp`, `.cli` 等）体积大，已加入 `.gitignore`，不提交到 git。

### 2. 中间文件管理规范 ⭐

SWAT+ 每次运行会产生大量输出文件。为节省磁盘空间，**运行完成后必须清理中间文件**。

#### 保留文件（输入 + 关键输出）

| 类型 | 文件模式 | 说明 |
|------|----------|------|
| 输入 | `*.cio`, `*.bsn`, `*.cha`, `*.con`, `*.hru`, `*.hyd`, `*.sol`, `*.lum`, `*.sch`, `*.ops`, `*.plt`, `*.wgn`, `*.cli` | SWAT+ 核心配置文件 |
| 输入 | `*.tmp`, `*.pcp`, `*.slr`, `*.hmd`, `*.wnd` | 气象数据文件 |
| 输出 | `simulation.out` | 运行摘要 |
| 输出 | `basin_*.txt`, `hru_wb_aa.txt`, `hru_nb_aa.txt` 等 | 标准统计输出（体积小） |
| 输出 | `mgt_out.txt` | 管理操作记录 |

#### 必须删除的中间文件

| 文件模式 | 说明 | 典型大小 |
|----------|------|----------|
| `run*.log` | 运行日志（可重新生成） | 1–3 MB |
| `fort.*` | Fortran 临时文件 | 0–1 MB |
| `hru_plc_stat.txt` | 植物碳状态（每日） | **~7 GB** |
| `hru_resc_stat.txt` | 残留碳状态（每日） | **~6 GB** |
| `hru_soilc_stat.txt` | 土壤碳状态（每日） | **~8 GB** |
| `checker.out` | 检查器输出 | ~400 KB |
| `diagnostics.out` | 诊断输出 | 极小 |
| `erosion.out` | 侵蚀输出 | 极小 |
| `area_calc.out` | 面积计算 | 空 |
| `files_out.out` | 文件列表 | 极小 |
| `lu_change_out.txt` | 土地利用变化 | 极小 |
| `yield.out` | 产量输出 | 空 |
| `reservoir_sed.txt` | 水库泥沙 | 空 |

#### 清理策略

- **效果不好的运行**（崩溃、参数错误、未跑完）：**删除所有中间文件**，保留 `simulation.out` 用于调试
- **成功的运行**：保留标准统计输出，删除 `run.log` 和 `hru_*_stat.txt` 等巨大文件
- **清理命令示例**：
  ```bash
  cd data/02_processed/TxtInOut_v61
  rm -f run*.log fort.* hru_plc_stat.txt hru_resc_stat.txt hru_soilc_stat.txt
  rm -f checker.out diagnostics.out erosion.out area_calc.out files_out.out
  rm -f lu_change_out.txt yield.out reservoir_sed.txt
  ```

### 3. 长时间任务运行规范 ⭐

SWAT+ 全流域 11 年模拟需要 **2–4 小时**。必须使用 **tmux** 运行，防止 SSH/session 断开导致模拟中断。

```bash
# 1. 安装 tmux（如未安装）
apt-get install -y tmux

# 2. 在 TxtInOut 目录创建 detached tmux session
cd data/02_processed/TxtInOut_v61
tmux new-session -d -s swatplus_run './swatplus61.exe'

# 3. 查看实时进度
tmux attach -t swatplus_run
# （按 Ctrl+B 然后 D  detach，不要按 Ctrl+C 终止！）

# 4. 后台检查进度（不 attach）
tmux capture-pane -t swatplus_run -p | tail -10

# 5. 模拟结束后清理 session
tmux kill-session -t swatplus_run
```

**禁止**：直接用 `./swatplus61.exe &` 或 `nohup` 运行——session 超时后进程会被 SIGTERM 杀死。

### 4. 代码规范

- 数据处理脚本使用 Python（推荐 conda env `hongxin_swat`）
- SWAT+ 模型编译使用 Intel oneAPI ifx 2024.1.2
- 每次代码修改后必须 commit + push 到 GitHub

---

## 已知问题与注意事项

### 温度数据边缘站点
- `wx281`, `wx309`, `wx337` 位于 All-sky 数据覆盖范围外
- 2019–2022 数据通过最近邻插值填充（分别来自 `wx282`, `wx310`, `wx338`）
- 这些站点在精度分析中应标记为"插值"

### SWAT+ 源码修复
- `pl_fert.f90`: 已修复 `chem_app.ops` 空指针问题
- `climate_control.f90`: 已修复除零保护

### 当前模拟状态
- **2019-01-01 `floating invalid` 已修复**：根因为温度输入存在 NaN（All-sky 边缘站点），已填充并验证。
- **碳输出已关闭**：`codes.bsn` 中 `carbon=0`，`print.prt` 中 `hru_nb` avann 关闭，避免 `hru_*_stat.txt` 占用数十 GB 磁盘。
- **日输出已配置**：`print.prt` 中 `channel` 和 `channel_sd` daily 设为 `y`，可生成 `channel_sd_day.txt` 用于校准。
- **2012–2022 全时段模拟已成功完成**：`Execution successfully completed`，共 4021 天输出（`basin_wb_day.txt`）。
- **注意**：当前配置缺少 `channel.con`，未生成 `channel_day.txt` 日径流输出。如需 channel 日流量用于校准，需补充 channel 连接配置。

---

## 待澄清事项

（由 Agent 维护，每次会话后更新）

1. **pres/shum 使用**：CMFD 的 pres（气压）和 shum（比湿）当前未用于 SWAT+，是否保留仅作备份？
2. **ModelScope 备份**：`data/02_processed/weather_stations/` 下 3000+ 个 CSV 小文件是否需要打包上传 ModelScope？
