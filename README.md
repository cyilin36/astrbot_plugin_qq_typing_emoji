# astrbot_plugin_qq_typing_emoji

在 NapCat / aiocqhttp 群聊中，AstrBot 开始请求 LLM 时为用户原消息添加一个表情回应；当主 LLM 处理完成且后续真正发出回复消息后，移除该表情回应。

## 特性

- 仅支持 `aiocqhttp`
- 仅支持群聊消息
- 使用 AstrBot 的 `on_llm_request`、`on_llm_response` 与 `after_message_sent` 钩子
- 通过 WebUI 配置 `processing_emoji_id`
- 通过 WebUI 配置 `max_pending_reactions`

## 配置

- `processing_emoji_id`：处理中表情 ID，默认值为 `60`
- `max_pending_reactions`：最大待处理消息数，默认值为 `100`
  > `ID` 获取可以查看[QQ机器人官方文档](https://bot.q.qq.com/wiki/develop/pythonsdk/model/emoji.html)

## 说明

- 表情加在用户原始消息上，不加在机器人回复消息上。
- 只有在主 LLM 已完成，并且随后真正发出回复消息后，表情才会移除。
- 若 LLM 已开始处理但最终没有完成，表情可能残留；这是当前版本的设计取舍。
- 超过最大待处理消息数后，最早进入的内存追踪记录会被移除，但不会主动撤销对应 QQ 表情。
