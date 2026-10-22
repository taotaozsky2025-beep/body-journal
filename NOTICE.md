# 致谢与来源 / Attribution

Body Journal（轻衡）是一套社区扩展工具，依赖已有开源基础，不能归为本仓库维护者独自完成的成果。它不是小米官方客户端，也不代表上游作者为本项目提供支持或背书。

## 核心上游

- **AlexxIT / Alexey Khit — [SmartScaleConnect](https://github.com/AlexxIT/SmartScaleConnect)**：提供体重数据标准、跨生态导入导出能力及本项目调用的 JSON→CSV 转换器。本项目开发时参考了其小米云端认证、协议和数据结构实现。MIT，原始版权 **Copyright (c) 2025 Alexey Khit**，完整原文保留在 [LICENSES/SmartScaleConnect-MIT.txt](LICENSES/SmartScaleConnect-MIT.txt)。固定依赖 v0.4.1。
- **AlexxIT / Alexey Khit — [go2rtc](https://github.com/AlexxIT/go2rtc)**：提供本机 Xiaomi 登录与验证流程，本项目只使用其本机认证辅助能力。MIT，原始版权 **Copyright (c) 2022 Alexey Khit**，完整原文见 [LICENSES/go2rtc-MIT.txt](LICENSES/go2rtc-MIT.txt)。固定依赖 v1.9.14。
- SmartScaleConnect 的 README 还致谢了 [lswiderski](https://github.com/lswiderski) 的系列项目。本项目保留这一来源说明，未因此假定额外授权或背书。
- **Python / Python Software Foundation 及贡献者**：本项目运行于 Python；便携版从 python.org 下载，遵循其 [PSF 许可](https://docs.python.org/3/license.html)。

## 本仓库新增部分

HD01S 只读历史适配、本地长期追加归档、Windows 启动与计划任务、私有数据仓库同步、科技风看板和日/周/月统计由本仓库维护者与贡献者扩展。初始实现通过维护者提供的设备测试和 Codex 辅助开发完成；上游成果的作者身份与许可不因这些扩展而改变。

HD01S 的字段映射参考了该设备官方米家插件的实际调用与数据格式；本仓库不分发插件包、反编译包、用户原始响应或其资源文件。

根目录 [LICENSE](LICENSE) 使用 MIT，并同时保留上游及本仓库新增部分的版权声明。二进制依赖不打入源码库；来源和固定校验值见 [THIRD_PARTY.md](THIRD_PARTY.md)。
