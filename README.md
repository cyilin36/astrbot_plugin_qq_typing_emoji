# astrbot_plugin_qq_typing_emoji

在 NapCat / aiocqhttp 群聊中，AstrBot 开始请求 LLM 时为用户原消息添加一个表情回应；当 AstrBot 发出第一条回复消息后，移除该表情回应。

## 特性

- 仅支持 `aiocqhttp`
- 仅支持群聊消息
- 使用 AstrBot 的 `on_llm_request` 与 `after_message_sent` 钩子
- 通过 WebUI 配置 `processing_emoji_id`

## 配置

- `processing_emoji_id`：处理中表情 ID，默认值为 `60`

## 说明

- 表情加在用户原始消息上，不加在机器人回复消息上。
- 当第一条回复成功发出后就会移除表情。
- 若 LLM 已开始处理但最终没有任何消息成功发出，表情可能残留；这是当前版本的设计取舍。
