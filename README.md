# Glyphica Community Patches

Glyphica（《指尖急速：打字狂潮》）社区补丁，持续更新中。

## 已更新补丁

| 补丁 | 作用 |
| --- | --- |
| `microsoft-shuangpin` | 修复 ü 到 y 、üe 到 t 的映射问题 |

## 准备

Python 3.9+ ， Node.js 18+  

## 快速开始

将示例路径替换为你自己的游戏目录：

```sh
python glyphica_patch.py list
python glyphica_patch.py status --game-dir "/path/to/SteamLibrary/steamapps/common/Glyphica"
python glyphica_patch.py check --patch patch-name --game-dir "/path/to/SteamLibrary/steamapps/common/Glyphica"
python glyphica_patch.py apply --patch patch-name --game-dir "/path/to/SteamLibrary/steamapps/common/Glyphica"
```

`list` 查看补丁列表
`status` 查看脚本是否支持

- `already-patched` 补丁正常
- `applicable` 补丁被覆盖了，请重新安装。
- `unsupported` 需更新补丁工具

`check` 检查兼容性、运行测试
`apply` 通过检查后备份并安装。

## 备份与还原

```sh
python glyphica_patch.py restore --game-dir "/path/to/SteamLibrary/steamapps/common/Glyphica"
```

卸载最后安装的补丁

## English

Community patches for Glyphica: Typing Survival.

### Available patches

| ID | Description |
| --- | --- |
| `microsoft-shuangpin` | Fixes the ü → y mapping and adds the t/v mappings for üe and related syllable aliases. |

### Requirements

Python 3.9+ and Node.js 18+.

### Quick start

Replace the example path with your game directory and `patch-name` with a patch ID from `list`, such as `microsoft-shuangpin`:

```sh
python3 glyphica_patch.py list
python3 glyphica_patch.py status --game-dir "/path/to/SteamLibrary/steamapps/common/Glyphica"
python3 glyphica_patch.py check --patch patch-name --game-dir "/path/to/SteamLibrary/steamapps/common/Glyphica"
python3 glyphica_patch.py apply --patch patch-name --game-dir "/path/to/SteamLibrary/steamapps/common/Glyphica"
```

- `list`: List available patches.
- `status`: Check whether the game scripts are supported or already patched.
- `check`: Check compatibility and run tests without changing game files.
- `apply`: Back up the game archive and install the patch after validation passes.

### Backup and restore

```sh
python3 glyphica_patch.py restore --game-dir "/path/to/SteamLibrary/steamapps/common/Glyphica"
```

Undo the most recent patch installed by this tool.
