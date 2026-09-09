---
description: Report the current time and the weather, with the data mode stated.
argument-hint: [location]
---

为 `$ARGUMENTS` 生成时间与天气报告。

未提供地点时使用运行时配置的默认地点。

遵循 `time-and-weather` 技能，报告前检查工具结果。说明实际使用的地点，给出带时区的时间，并注明天气数据模式：`fixture` 或 `live`。

实时查询失败并降级为 fixture 数据时，必须说明这一点，并将答案报告为 fixture 数据。
