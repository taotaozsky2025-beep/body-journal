# 轻衡 · Body Journal

Windows 上的本地身体指标看板、智能秤云端读取和个人历史归档。开源程序与私人身体数据分离。

**基于 [AlexxIT / Alexey Khit 的 SmartScaleConnect](https://github.com/AlexxIT/SmartScaleConnect) 和 [go2rtc](https://github.com/AlexxIT/go2rtc) 构建。感谢原作者与开源贡献者；这不是本仓库维护者独自完成的成果。** 来源、贡献范围与许可证见 [NOTICE.md](NOTICE.md)。本项目为独立社区扩展，不是官方客户端。

> 初始公开版本，面向 Windows 10/11 x64。目前实机验证范围只有中国大陆米家区域的辉鼎 HD01（内部型号 `bairen.scales.hd01s`）。HD01-B、其他秤、其他区域不保证兼容。不能仅修改型号字符串就宣称支持新设备。

## 能做什么

- 读取 HD01S 米家云端历史，保存体重、BMI、体脂率、肌肉量等指标；云端没有上传的记录无法读取。
- CSV 长期保存在本地，按成员和日期时间去重，保留旧值并追加新记录；同一天可测多次。
- 科技风看板，按日、自然周或日历月显示均值和 ±1 样本标准差；无数据的周期留空，单次测量不画误差棒。
- 界面「一键同步」：读取米家 → 本地追加 → 合并私人 GitHub 历史 → 上传新增记录 → 刷新看板。
- 可选 Windows 每日定时任务。电脑需开机、联网，当前 Windows 用户需已登录。

## 快速开始

需要 Windows 10/11 x64、Git for Windows，以及可访问 GitHub 和 python.org 的网络。不需要 Codex、不需要手工安装 Python；首次使用会下载固定版本并校验 SHA-256。

```powershell
git clone https://github.com/taotaozsky2025-beep/body-journal.git
cd body-journal
```

1. 双击 **`开始使用.cmd`**：生成本机 `settings.json`，准备便携运行时，打开空看板。没有演示数据或他人的身体记录。
2. 双击 **`米家登录.cmd`**：在本机浏览器选择 Xiaomi，输入自己的账号并完成验证。不要向本仓库维护者、Issue 或聊天发送密码、token、验证码。保留双重验证。
3. 首次成功读取后即可看趋势。手机是否必须打开 App、点击开始测量，取决于秤和插件；本项目不提供后台蓝牙采集。
4. 如需跨电脑同步，在自己的 GitHub 创建一个**空的私人仓库**，使用 `main` 分支，然后运行：

```powershell
powershell -NoProfile -ExecutionPolicy RemoteSigned -File .\Setup-DataSync.ps1
```

按提示输入你自己的私人数据仓库 HTTPS 地址，并通过 Git Credential Manager 登录 GitHub。地址只保存在忽略目录 `.local/`。不要把私人仓库地址改成这个公开代码库。

5. 点击看板的 **「一键同步」**。未授权米家的电脑只同步私人 GitHub 历史；未配置 GitHub 的电脑只做本地归档，并明确提示。
6. 可选定时任务：首次真实导出成功后运行 `powershell -NoProfile -ExecutionPolicy RemoteSigned -File .\Register-SyncTask.ps1`。每日本地时间 09:00 执行，不存 Windows 密码。

另一台 Windows 电脑同样克隆本公开程序、连接**同一个私人数据仓库**后即可查看历史。只查看历史不必登录米家。需要采集米家记录的电脑才单独完成本机米家授权。

## 本机配置

`settings.example.json` 是公开模板；`settings.json` 在本机生成并被 Git 忽略。当前适配器只允许 `Region: cn` 和 `Model: bairen.scales.hd01s`。

- `DeviceId: null`：仅当账号内恰好有一台目标型号的自有秤时自动选择。多台秤时需在本机填对应设备 ID；不要公开上传该 ID。
- `PrimaryProfile: null`：仅当有历史的成员唯一时自动选择。多个成员都有历史时，先根据本机生成的 `weights_full_keyid_*.csv` 选择目标成员，将对应 `keyid_...` 填入本机配置后重试。成员历史不混为一个人。
- 时间和聚合当前使用北京时间。跨时区显示与亚秒时间戳是后续计划，不静默丢弃精度。

## 数据与隐私

| 内容 | 位置 | 是否上传 |
| --- | --- | --- |
| 开源代码、模板、说明和纯合成测试 | 这个公开仓库 | 公开 |
| `weights*.csv` | 本地程序目录 | 仅在配置后上传至使用者自己的私人数据仓库 |
| 私人数据仓库工作副本 | `.local/data-repository/` | 仅私人库 |
| 米家授权 `token.dpapi` | 本机，Windows DPAPI 加密 | 不上传；不可跨电脑复制使用 |
| 原始响应、快照、本机账号、登录辅助配置 | 忽略目录及忽略文件 | 不上传 |

源码库从第一笔提交起就不包含真实测量、截图、账号或旧私人仓库历史。公开 `.gitignore` 忽略所有 CSV 和授权文件。同步器只操作独立的私人数据工作副本，每次同步和推送前通过 GitHub API 检查其为 private；不会把数据推到本公开库。

私人 GitHub 数据仍是 GitHub 上的明文 CSV，不是端到端加密保险箱；有仓库读取权限的人可以看到记录。若不想把健康数据交给 GitHub，保持未配置状态，使用本地归档即可。请勿强制 `git add -f` 添加私人文件。

本机看板仅监听 `127.0.0.1:19842`，固定同步接口带来源和随机请求令牌检查。首次登录和授权过期需要人工完成正常验证，不能承诺永远无感。

## 型号适配与贡献

请先看 [兼容性矩阵](docs/COMPATIBILITY.md)、[适配路线图](docs/ROADMAP.md)、[贡献说明](CONTRIBUTING.md) 和 [安全说明](SECURITY.md)。上游支持其他生态不代表本项目界面已经适配它们。

本地测试：`python -m unittest discover -s tests -v`，以及 `node tests/stats.cjs`。测试只使用合成数据，不登录真实账号。Windows CI 执行相同检查。

程序更新：关闭旧看板程序后运行 `git pull --ff-only` 并重新双击启动。代码更新与私人数据同步分开，避免同步数据时执行远程程序更新。

## 许可与致谢

MIT，见 [LICENSE](LICENSE)。保留 Alexey Khit 的版权与完整原始许可文本；本仓库新增部分使用相同许可。依赖版本、官方来源与校验值见 [THIRD_PARTY.md](THIRD_PARTY.md)。完整来源说明见 [NOTICE.md](NOTICE.md)。
