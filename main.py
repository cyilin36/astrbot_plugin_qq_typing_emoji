from collections import OrderedDict
from dataclasses import dataclass

from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.provider import LLMResponse, ProviderRequest
from astrbot.api.star import Context, Star


@dataclass
class PendingReaction:
    emoji_id: int | str
    state: str = 'processing'


class QQTypingEmojiPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.pending_reactions: OrderedDict[str, PendingReaction] = OrderedDict()

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

    def _get_max_pending_reactions(self) -> int:
        value = self.config.get('max_pending_reactions', 100)
        try:
            limit = int(value)
            if limit < 1:
                raise ValueError
            return limit
        except (TypeError, ValueError):
            logger.warning(
                f'[qq_typing_emoji] invalid max_pending_reactions={value!r}, fallback to 100'
            )
            return 100

    def _get_message_key(self, event: AstrMessageEvent) -> str | None:
        message_obj = getattr(event, 'message_obj', None)
        message_id = getattr(message_obj, 'message_id', None)
        if not message_id:
            return None
        return str(message_id)

    def _trim_pending_reactions(self):
        limit = self._get_max_pending_reactions()
        while len(self.pending_reactions) > limit:
            message_id, pending = self.pending_reactions.popitem(last=False)
            logger.warning(
                '[qq_typing_emoji] pending reaction limit exceeded, '
                f'evict oldest message {message_id} (state={pending.state})'
            )

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

        message_id = self._get_message_key(event)
        if message_id is None or message_id in self.pending_reactions:
            return

        emoji_id = self._get_processing_emoji_id()
        success = await self._set_message_reaction(event, message_id, emoji_id, True)
        if success:
            self.pending_reactions[message_id] = PendingReaction(emoji_id=emoji_id)
            self._trim_pending_reactions()

    @filter.on_llm_response()
    async def on_llm_response(self, event: AstrMessageEvent, resp: LLMResponse):
        if not self._is_supported_event(event):
            return

        message_id = self._get_message_key(event)
        if message_id is None:
            return

        pending = self.pending_reactions.get(message_id)
        if pending is None:
            return

        if getattr(resp, 'is_chunk', False):
            return

        if getattr(resp, 'role', None) != 'assistant':
            return

        pending.state = 'ready_to_clear'

    @filter.after_message_sent()
    async def after_message_sent(self, event: AstrMessageEvent):
        if not self._is_supported_event(event):
            return

        message_id = self._get_message_key(event)
        if message_id is None:
            return

        pending = self.pending_reactions.get(message_id)
        if pending is None or pending.state != 'ready_to_clear':
            return

        success = await self._set_message_reaction(event, message_id, pending.emoji_id, False)
        if success:
            self.pending_reactions.pop(message_id, None)

    async def terminate(self):
        self.pending_reactions.clear()
