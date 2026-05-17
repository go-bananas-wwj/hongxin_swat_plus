# SWAT+ Channel Routing 诊断报告

## 问题概述

**当前模型无法生成可用于校准的日河道流量（`channel_day.txt`）。**

`basin_wb_day.txt` 中的 `wateryld` 是流域总产水量（未汇流），与实测流量（镇西站）对比得到 NSE=-84, PBIAS=+403%，不具备校准价值。

---

## 根本原因

水文路由系统（channel routing）**完全没有配置**。模型仅运行了 HRU 尺度的产流计算，但未将产流汇集到河道并演算到流域出口。

### 具体证据

| 检查项 | 预期状态 | 实际状态 | 结论 |
|--------|----------|----------|------|
| `object.cnt` — `cha` | >0 (如 283) | **0** | 未创建 channel 对象 |
| `object.cnt` — `res` | >0 (如 1) | **0** | 未创建 reservoir 对象 |
| `file.cio` — `channel` | `channel.cha` 等 | **全部 null** | 未注册 channel 文件 |
| `file.cio` — `reservoir` | `reservoir.res` 等 | **全部 null** | 未注册 reservoir 文件 |
| `file.cio` — `connect` | `hru.con` + `channel.con` | **仅 hru.con** | 缺少 channel 连接 |
| `hru.con` — `out_tot` | ≥1 (HRU→channel) | **全部为 0** | HRU 产流不进入任何 channel |
| `channel.cha` | 包含几何参数 | **全部为 0** | channel 属性未计算 |
| `channel.con` / `chandeg.con` | 存在 | **不存在** | 缺少拓扑连接 |
| `channel_day.txt` | 有数据 | **不存在** | 无 channel 日输出 |
| `hydin_aa.txt` / `hydout_aa.txt` | 有数据 | **仅表头** | 无任何对象的水文交换 |

---

## 数据一致性检查

项目中的 subbasin / channel / HRU 编号系统**严重不一致**，说明 QSWAT+ 导出过程存在错误：

| 数据源 | 数量 | ID 范围 | 说明 |
|--------|------|---------|------|
| `channel.cha` | 283 | 1–283 | channel 定义（全为 0） |
| `hru.con` gis_id | 281 个唯一值 | 2–374 | HRU 所属 subbasin |
| `watershed_deli8drainage.csv` | 265 | 0–287 | subbasin 拓扑 |
| `streams.shp` | 376 | WSNO 0–375 | 河流段 |
| `subbasins.shp` | 430 (376 唯一) | 0–375 | subbasin 矢量 |

**关键矛盾：**
- `channel.cha` 有 283 条记录，但 `drainage.csv` 只有 265 条拓扑记录（缺失 21 个 ID）
- `hru.con` 的 gis_id 范围是 2–374，只有 205 个落在 channel.cha 的 1–283 范围内
- 93 个 hru gis_id 超出了 channel.cha 的编号范围

这意味着**不存在安全的自动映射关系**来连接 HRU → channel → outlet。

---

## 为什么 `wateryld` 不能替代河道流量

`basin_wb_day.txt` 的 `wateryld` 是流域尺度的**总产水量**（地表径流 + 侧向流 + 地下水），未经过：
1. **汇流延迟**（不同 HRU 的产流到出口时间不同）
2. **河道演算**（Muskingum 等方法的流量平滑和延迟）
3. **水库调蓄**（察尔森水库的蓄泄调节）
4. **蒸发和渗漏损失**（河道水面蒸发、河床渗漏）

因此，`wateryld` 在物理上**不可能**与实测河道流量匹配，尤其对于一个 25,498 km² 的大流域。

---

## 修复方案

### 方案 1：重新用 QSWAT+ 导出（推荐 ⭐）

这是最可靠的方法。在 QSWAT+ 中重新执行以下步骤：

1. **打开 QSWAT+ 项目**，检查 `Watershed → Configure → Channels`
   - 确认 channel routing 已启用
   - 检查 channel 参数是否已计算（非零值）

2. **检查连接文件**
   - 确保导出时包含 `channel.con`（或 `chandeg.con`）
   - 确保 `object.cnt` 中 `cha` 和 `res` 的值正确

3. **重新导出 TxtInOut**
   - 对比新旧版本的 `channel.cha`、`object.cnt`、`file.cio`、`hru.con`
   - 确认 `hru.con` 中 `out_tot ≥ 1`

4. **验证**
   - 运行模型后检查是否生成 `channel_day.txt`
   - 检查 `channel_day.txt` 最后一行（出口 subbasin）的流量是否合理

**优点：** 所有参数和拓扑由 QSWAT+ 自动计算，可靠性最高  
**缺点：** 需要 QSWAT+ 环境，可能需要重新配置部分参数

---

### 方案 2：手动修复（高风险 ⚠️）

如果无法重新导出，可尝试手动构建 routing 配置：

#### 步骤 A：填充 `channel.cha` 参数

从 `streams.shp` 提取：
- `len` = `Length` (m)
- `slope` = `Slope` (m/m)
- `lat`, `lon` = 河段中心点
- `area` = `DSContArea` / 10000 (ha，需确认单位)

用经验公式估算：
- `bot_wid` = 2.5 × A^0.5  (m, A in km²)
- `dep` = 0.6 × A^0.4  (m, A in km²)
- `side_slp` = 2.0
- `hyd_rad` 由梯形断面公式计算

**风险：** channel ID 与 stream segment 的映射关系不明确，可能将错误的参数分配给错误的 subbasin。

#### 步骤 B：生成 `channel.con`

格式参考：
```
channel.con: Hongxin
      id  name                gis_id          area           lat           lon          elev       cha               wst       cst      ovfl      rule   out_tot  obtyp_out  obtypno_out  htyp_out  frac_out
       1  channel0001                 1     7292.2603      47.129698     119.975122       200.00        1           null         0         0         0         1        cha            2         tot         1.0
```

**风险：** `watershed_deli8drainage.csv` 只有 265 条记录，而 channel.cha 有 283 条，拓扑无法完全匹配。

#### 步骤 C：修改其他文件

- `object.cnt`：将 `cha` 设为 283（或实际数量）
- `file.cio`：`channel` 行注册 `channel.cha`，`connect` 行注册 `channel.con`
- `hru.con`：为每个 HRU 添加 `out_tot=1`，`obtyp_out=cha`，`obtypno_out=<channel_id>`，`htyp_out=surq`（或 `tot`），`frac_out=1.0`

**风险：** hru gis_id 与 channel ID 的映射关系不明确，大量 HRU 可能无法正确连接。

---

### 方案 3：使用 landscape unit routing（探索性 🔍）

如果项目本意是使用 landscape unit routing（如 Ames 示例），则：
- 不需要 `channel.cha` 和 `channel.con`
- 但需要 `ls_unit.ele` 正确定义 routing unit
- 输出为 `ls_unit_day.txt`，仍不是标准的河道流量

当前 `ls_unit.ele` 将每个 HRU 作为独立 unit（`OBJ_TYP=hru`），且 `hru.con` 中 `out_tot=0`，因此也没有有效的 routing 输出。

**结论：** 此方案不适合当前项目。

---

## 建议操作

**强烈推荐执行方案 1（重新用 QSWAT+ 导出）。**

手动修复（方案 2）在当前数据不一致的情况下风险过高，可能导致：
- 模型运行时崩溃（除零、数组越界等）
- 产生物理上不合理的流量过程
- 浪费大量调试时间

如果必须手动修复，建议先建立一个**最小可运行测试案例**（如只保留 5–10 个 subbasin），验证 routing 配置正确后再扩展到全流域。

---

## 附录：相关文件清单

| 文件 | 路径 | 状态 |
|------|------|------|
| `channel.cha` | `data/02_processed/TxtInOut_v61/channel.cha` | ⚠️ 全为 0 |
| `object.cnt` | `data/02_processed/TxtInOut_v61/object.cnt` | ❌ cha=0, res=0 |
| `file.cio` | `data/02_processed/TxtInOut_v61/file.cio` | ❌ channel/reservoir 全 null |
| `hru.con` | `data/02_processed/TxtInOut_v61/hru.con` | ❌ out_tot=0 |
| `watershed_deli8drainage.csv` | `data/01_raw/watershed_shapes/watershed_deli8drainage.csv` | ⚠️ 265 条，不完整 |
| `streams.shp` | `workspace/streams.shp` | ✅ 376 条，含 Length/Slope |
| `subbasins.shp` | `workspace/subbasins.shp` | ⚠️ 430 个 feature，编号混乱 |
