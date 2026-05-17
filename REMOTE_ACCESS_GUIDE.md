# noVNC 远程桌面访问指南

## 服务状态

| 组件 | 状态 | 端口 | 说明 |
|------|------|------|------|
| TigerVNC | ✅ 运行中 | 5901 (localhost only) | XFCE 桌面 |
| noVNC/websockify | ✅ 运行中 | 6080 | 浏览器访问入口 |
| QGIS | ✅ 已安装 | - | 3.22.4-Białowieża |
| QSWATPlus | ✅ 已安装 | - | 插件 + 编译好的 Cython 扩展 |
| SWAT+ Editor | ✅ 已安装 | - | v3.2.3，命令 `swatplus-editor` |

## 访问方式

### 浏览器访问（推荐）

```
http://<服务器IP>:6080/vnc.html
```

当前服务器 IP：`172.20.0.10`

**操作步骤：**
1. 打开浏览器，访问 `http://172.20.0.10:6080/vnc.html`
2. 点击页面上的 **"Connect"** 按钮
3. 输入 VNC 密码：`hongxin2024`
4. 即可看到 XFCE 桌面

### 端口映射说明

如果你的服务器在防火墙/NAT 后面，需要将服务器的 **6080 端口** 映射到外部可访问的地址：

- **云服务器**：在安全组/防火墙规则中放行 TCP 6080
- **Docker**：启动容器时加 `-p 6080:6080`
- **SSH 隧道**（如果无法直接暴露端口）：
  ```bash
  ssh -L 6080:localhost:6080 user@服务器IP
  # 然后在本地浏览器访问 http://localhost:6080/vnc.html
  ```

## 在远程桌面中使用 QGIS + QSWAT+

1. **启动 QGIS**：点击桌面左下角的菜单 → "Graphics" → "QGIS Desktop"
   或在终端中运行：`qgis &`

2. **启用 QSWATPlus 插件**（首次使用）：
   - QGIS 菜单 → Plugins → Manage and Install Plugins
   - 在 "Installed" 标签中找到 **QSWATPlus**
   - 勾选启用
   - 重启 QGIS

3. **设置 SWATPlus 目录**（如果提示）：
   - QSWATPlus → Parameters
   - 设置 SWATPlus directory 为 `/usr/local/share/SWATPlus`

4. **打开现有项目或重新导出**：
   - 你的项目数据在 `/workspace/hongxin_swaw_plus/`
   - GIS 数据在 `workspace/` 和 `Datasets/swat_data/Watershed/Shapes/`

## 使用 SWAT+ Editor

在终端中运行：
```bash
swatplus-editor
```

或在菜单中搜索 "SWATPlus Editor"。

## 服务管理

所有服务由 **supervisor** 管理，崩溃后会自动重启：

```bash
# 查看状态
supervisorctl status

# 手动重启 VNC
supervisorctl restart vncserver

# 手动重启 noVNC
supervisorctl restart websockify
```

## 安全提示

- **VNC 密码**：当前为 `hongxin2024`，建议首次登录后通过 `vncpasswd` 修改
- **网络暴露**：6080 端口目前监听在所有接口 (`0.0.0.0`)。如果服务器有公网 IP，建议：
  - 限制防火墙规则，只允许可信 IP 访问 6080
  - 或在前面加 Nginx 反向代理 + Basic Auth
- **不暴露 5901**：VNC 原生端口只监听 localhost，不会直接暴露

## 故障排查

| 问题 | 解决 |
|------|------|
| 浏览器无法连接 6080 | 检查端口映射/防火墙，确认 `supervisorctl status` 中 websockify 为 RUNNING |
| 连接后黑屏 | VNC 可能未启动，运行 `supervisorctl restart vncserver` |
| QGIS 启动报错 | 检查 DISPLAY 环境变量，在 VNC 桌面内的终端运行 `echo $DISPLAY` 应显示 `:1` |
| QSWATPlus 插件不显示 | 确认插件在 Plugins → Manage 中已勾选启用 |

## 磁盘占用

```
XFCE + TigerVNC + noVNC    ~ 600 MB
QGIS + 依赖                ~ 1.5 GB
SWAT+ Editor               ~ 180 MB
QSWATPlus + 数据库         ~ 30 MB
总计                       ~ 2.3 GB
```
