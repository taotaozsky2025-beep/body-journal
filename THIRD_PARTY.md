# 依赖来源

所有依赖在首次使用时从官方来源下载，不把便携运行时和程序二进制存入数据仓库。

| 依赖 | 版本 | 来源 | ZIP SHA-256 |
| --- | --- | --- | --- |
| Python Windows x64 embeddable | 3.14.4 | https://www.python.org/ftp/python/3.14.4/python-3.14.4-embeddable-amd64.zip | `fa2e63e9f0607e34d8841cc8080641069b71d2bddb5a69fa30c24eb5599da9fe` |
| SmartScaleConnect Windows | 0.4.1 | https://github.com/AlexxIT/SmartScaleConnect/releases/tag/v0.4.1 | `83e76a5fc74e9fdfa3f6456f15243ab7aa3f27e39a4bfd339736babd0173126d` |
| go2rtc Windows x64 | 1.9.14 | https://github.com/AlexxIT/go2rtc/releases/tag/v1.9.14 | `dd4167d75cb04abe618855b7c71f8658bd009f60c1a71835d134d2c11c939907` |

Python校验值取自官方发布清单 https://www.python.org/ftp/python/3.14.4/windows-3.14.4.json 。SmartScaleConnect和go2rtc校验值取自对应GitHub官方release asset digest。

SmartScaleConnect和go2rtc由AlexxIT维护，各自许可见上游仓库。根目录保留SmartScaleConnect的MIT许可文本。HD01S只读适配根据用户设备的官方米家插件实际调用方式实现，仓库不分发设备插件包。
