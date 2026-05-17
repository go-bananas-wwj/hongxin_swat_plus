# 远程图形化访问调研与执行计划

## 调研结论：可以，最推荐 noVNC 方案

### 别人是怎么做的

通过端口映射远程运行 QGIS + QSWAT+ 有三种主流方案，社区都有成熟案例：

| 方案 | 访问方式 | 客户端需求 | 社区案例 | 评价 |
|------|---------|-----------|---------|------|
| **A. noVNC + TigerVNC + XFCE** | 浏览器 `http://ip:6080` | **仅需浏览器** | QgisStreamMCP (GitHub 1.2k+ stars)、ppc64le-qgis Docker | 最通用，零客户端安装 |
| **B. xrdp + XFCE** | RDP 客户端 (3389 端口) | Windows 自带/macOS 需装 | 大量 Ubuntu 远程桌面教程 | Windows 用户体验最好 |
| **C. VNC + SSH 隧道** | VNC Viewer (5901 端口) | 需安装 VNC 客户端 | 传统 Linux VPS 管理方案 | 较老旧，配置繁琐 |

**关键发现：**
- **QgisStreamMCP**（GitHub `nic01asFr/QgisStreamMCP`）是一个在生产环境中验证的方案：QGIS Desktop 完整运行在 Docker 中，通过 noVNC 在浏览器中提供 GUI，同时提供 MCP API 供 AI 调用
- **DeSciOS** 项目也采用相同的架构（XFCE + noVNC + QGIS）用于科研环境
- 多个教程证实：TigerVNC + noVNC + websockify 的组合在 Ubuntu 22.04 上稳定运行

### 为什么最推荐 noVNC 方案（方案 A）

1. **零客户端门槛**：用户从 Windows/Mac/手机/平板都只需要浏览器，不需要安装 RDP 客户端或 VNC Viewer
2. **端口映射最简单**：只需映射一个 HTTP 端口（6080），不需要处理 RDP 的 3389 或 VNC 的 5901
3. **已被 QGIS 社区验证**：QgisStreamMCP 等项目证明 QGIS 的复杂 GUI（包括插件、地图渲染、对话框）在 noVNC 下完全可用
4. **安全性可控**：noVNC 可以配置密码，且可以只通过反向代理/内网暴露，不直接暴露 VNC 端口
5. **性能可接受**：对于 QSWAT+ 的配置操作（不是高频游戏），noVNC 的性能完全足够

---

## 执行计划

### 阶段 1：安装基础图形环境（~10 分钟）

1. **更新包列表**
   ```bash
   apt-get update
   ```

2. **安装 XFCE4 桌面环境**（轻量级，约 300MB）
   ```bash
   DEBIAN_FRONTEND=noninteractive apt-get install -y \
       xfce4 xfce4-goodies xfce4-terminal \
       dbus-x11 fonts-liberation xfonts-base
   ```

3. **安装 TigerVNC Server**
   ```bash
   apt-get install -y tigervnc-standalone-server tigervnc-common
   ```

4. **安装 noVNC + websockify**
   ```bash
   apt-get install -y novnc websockify python3-numpy
   ```

### 阶段 2：安装 QGIS + QSWAT+（~15 分钟）

5. **安装 QGIS**
   ```bash
   apt-get install -y qgis qgis-plugin-grass
   ```

6. **安装 OpenMPI**（QSWAT+ / TauDEM 必需）
   ```bash
   apt-get install -y openmpi-bin libopenmpi-dev
   ```

7. **下载并安装 QSWAT+ Linux installer**
   - 从 SWAT+ 官网获取最新 `swatplus-linux-installer.tgz`
   - 解压并执行 `./installforall.sh`（安装到系统目录，所有用户可用）
   - 数据将安装到 `/usr/local/share/SWATPlus`

### 阶段 3：配置 VNC + noVNC 服务（~10 分钟）

8. **创建 VNC 用户配置**
   - 设置 VNC 密码（建议强密码）
   - 创建 `~/.vnc/xstartup` 启动脚本，配置启动 XFCE

9. **配置 noVNC 服务**
   - 使用 websockify 将 TigerVNC 的 5901 端口桥接到 HTTP 6080 端口
   - 配置 noVNC 的 vnc.html 页面

10. **配置 Supervisor（进程守护）**
    - 安装 supervisor
    - 配置同时管理：Xvfb（虚拟显示）、TigerVNC、noVNC/websockify
    - 确保服务崩溃后自动重启

### 阶段 4：启动与验证（~5 分钟）

11. **启动服务**
    - 启动 VNC server（显示 :1，端口 5901）
    - 启动 websockify（端口 6080 → 5901）

12. **本地验证**
    - 用 `curl` 检查 6080 端口响应
    - 确认 QGIS 能在 VNC 会话中启动

13. **端口映射说明**
    - 将服务器的 **6080 端口** 映射到公网（或内网可访问地址）
    - 用户通过浏览器访问 `http://<服务器IP>:6080/vnc.html`
    - 输入 VNC 密码后即可看到 XFCE 桌面
    - 在桌面中启动 QGIS → 加载 QSWAT+ 插件 → 操作

### 预期磁盘占用

| 组件 | 预估大小 |
|------|---------|
| XFCE4 桌面 | ~500 MB |
| TigerVNC + noVNC | ~50 MB |
| QGIS + 依赖 | ~1.5 GB |
| QSWAT+ + 数据库 | ~500 MB |
| **总计** | **~2.5 GB** |

### 安全建议

- **VNC 密码**：设置 8 位以上强密码（VNC 密码限制 8 位，但应充分利用）
- **网络暴露**：如果服务器有公网 IP，建议：
  - 仅在内网/VPN 中暴露 6080 端口，或
  - 在前面加 Nginx 反向代理 + Basic Auth，或
  - 使用防火墙限制访问来源 IP
- **不暴露 5901**：只映射 6080（HTTP），不直接暴露 VNC 原生端口

---

## 备选方案：xrdp（如果 noVNC 性能不满意）

如果后续发现 noVNC 在地图渲染时卡顿，可以快速切换到 xrdp：

```bash
apt-get install -y xrdp
systemctl enable xrdp
# 配置 xrdp 使用 xfce4
sed -i 's/test -x \/etc\/X11\/Xsession/#/' /etc/xrdp/startwm.sh
echo "xfce4-session" > /root/.xsession
systemctl restart xrdp
```

然后映射 **3389 端口**，用 Windows 远程桌面连接。
