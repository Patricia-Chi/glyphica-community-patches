# 补丁目录

## microsoft-shuangpin

游戏拼音库的双拼解析存在问题，如将“旅客”一词转为 `lv + ke`。双拼转换函数在拆分声韵母之前，直接返回长度为 2 的拼音， `lv/nv` 会跳过已有的 `v → y` 映射。

参考实现：[Rime 微软双拼方案](https://github.com/rime/rime-double-pinyin/blob/master/double_pinyin_mspy.schema.yaml)。
