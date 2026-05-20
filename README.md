# App Muter

通过全局快捷键 **只静音当前前台应用** 的 Windows 工具。不影响其他程序的音量。

## 功能

- **全局热键**：一键静音/恢复当前活跃窗口的应用音量
- **系统托盘**：左键切换静音，右键菜单
- **设置界面**：自定义快捷键、应用过滤（白名单/黑名单）、OSD 屏幕指示器、开机自启
- **多架构兼容**：支持 Electron、WebView2、UWP、普通 Win32 应用

## 使用方法

### 直接运行

下载 [Releases](https://github.com/JimmyRowe13/AppMuter/releases) 中的 `AppMuter.exe`，双击运行。

- 按下 `Ctrl+Shift+F12` 切换前台应用静音
- 右键系统托盘图标 → **Settings...** 进入设置

### 从源码运行

```bash
# 安装依赖
pip install -r requirements.txt

# 启动 App Muter
python app_muter/app_muter.py

# 或启动原有的音频设备切换工具
python audio_switcher.py
```

### 构建 exe

```bash
# App Muter
build_muter.bat

# Audio Switcher（音频设备切换）
build.bat
```

## 实现原理

通过 Windows Core Audio API (`ISimpleAudioVolume`) 控制单个应用的音频会话，而非系统总音量。

找到前台应用音频会话的三重搜索策略：
1. **进程树匹配**：遍历前台进程及所有子进程
2. **子窗口匹配**：枚举前台窗口的子窗口进程（覆盖 WebView2）
3. **文件名回退**：按可执行文件名模糊匹配

## 依赖

- Python 3.8+
- [pycaw](https://github.com/AndreMiras/pycaw) — Windows Core Audio API 封装
- [keyboard](https://github.com/boppreh/keyboard) — 全局热键
- [pystray](https://github.com/moses-palmer/pystray) — 系统托盘
- [Pillow](https://python-pillow.org/) — 托盘图标
- [psutil](https://github.com/giampaolo/psutil) — 进程管理
