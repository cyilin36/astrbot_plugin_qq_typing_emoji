from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.provider import ProviderRequest
from astrbot.api.star import Context, Star


class QQTypingEmojiPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.pending_reactions: dict[str, int | str] = {}

    def _is_supported_event(self, event: AstrMessageEvent) -> bool:
        return event.get_platform_name() == 'aiocqhttp' and bool(event.get_group_id())

    def _get_processing_emoji_id(self) -> int:
        value = self.config.get('processing_emoji_id', 60)
        try:
            return int(value)
        except (TypeError, ValueError):
            logger.warning(
                f'[qq_typing_emoji] invalid processing_emoji_id={value!r}, fallback to 60'
            )
            return 60

    async def _set_message_reaction(
        self,
        event: AstrMessageEvent,
        message_id: int | str,
        emoji_id: int | str,
        enabled: bool,
    ) -> bool:
        client = getattr(event, 'bot', None)
        api = getattr(client, 'api', None)
        if api is None:
            logger.warning('[qq_typing_emoji] aiocqhttp client API is unavailable')
            return False

        try:
            await api.call_action(
                'set_msg_emoji_like',
                message_id=message_id,
                emoji_id=emoji_id,
                set=enabled,
            )
            return True
        except Exception as exc:
            action = 'set' if enabled else 'clear'
            logger.error(
                f'[qq_typing_emoji] failed to {action} emoji reaction for message '
                f'{message_id}: {exc}'
            )
            return False

    @filter.on_llm_request()
    async def on_llm_request(self, event: AstrMessageEvent, req: ProviderRequest):
        if not self._is_supported_event(event):
            return

        del req

        message_id = event.message_obj.message_id
        if not message_id or message_id in self.pending_reactions:
            return

        emoji_id = self._get_processing_emoji_id()
        success = await self._set_message_reaction(event, message_id, emoji_id, True)
        if success:
            self.pending_reactions[str(message_id)] = emoji_id

    @filter.after_message_sent()
    async def after_message_sent(self, event: AstrMessageEvent):
        if not self._is_supported_event(event):
            return

        message_id = event.message_obj.message_id
        if not message_id:
            return

        pending_key = str(message_id)
        emoji_id = self.pending_reactions.pop(pending_key, None)
        if emoji_id is None:
            return

        await self._set_message_reaction(event, message_id, emoji_id, False)

    async def terminate(self):
        self.pending_reactions.clear()
