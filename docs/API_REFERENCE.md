# API Reference

Полная справка по публичному API `itd-sdk`.

SDK асинхронный и построен на `aiohttp`.
Все методы API-объектов `client.account`, `client.users`, `client.auth`, `client.posts`,
`client.comments`, `client.notifications`, `client.social`, `client.search`, `client.files`,
`client.reports`, `client.platform` и `client.raw` ниже являются асинхронными и вызываются через `await`.

## ITDClient

Конструктор:

- `ITDClient(origin: str = "https://итд.com", access_token: str | None = None, cookies: str | Mapping[str, str] | None = None, device_id: str | None = None, timeout: float = 30.0, headers: Mapping[str, str] | None = None, auto_refresh: bool = True)`
  Создает клиент SDK.

Параметры:

- `origin`
  Базовый origin сайта. По умолчанию `https://итд.com`.
- `access_token`
  Bearer token для приватных методов.
- `cookies`
  Cookie header строкой или словарем. Нужны для refresh-сценария.
- `device_id`
  Явный `X-Device-Id`. Если не передан, SDK сгенерирует UUID.
- `timeout`
  Таймаут запросов в секундах.
- `headers`
  Дополнительные HTTP-заголовки.
- `auto_refresh`
  Разрешить авто-refresh на `401` при наличии нужных cookies.

Свойства:

- `client.access_token -> str | None`
  Текущий access token клиента.
- `client.device_id -> str`
  Текущий `X-Device-Id`.

Методы:

- `client.set_access_token(access_token: str | None) -> None`
  Установить или очистить access token.
- `client.set_cookies(cookies: str | Mapping[str, str]) -> None`
  Загрузить cookies в HTTP-клиент.
- `await client.open() -> ITDClient`
  Явно открыть внутреннюю `aiohttp.ClientSession`.
- `await client.close() -> None`
  Закрыть внутренний HTTP-клиент.

Контекстный менеджер:

- `async with ITDClient(...) as client: ...`
  На выходе вызывает `close()`.

API-объекты:

- `client.account`
- `client.users`
- `client.auth`
- `client.posts`
- `client.comments`
- `client.notifications`
- `client.social`
- `client.search`
- `client.files`
- `client.reports`
- `client.platform`
- `client.raw`

Пример:

```python
import asyncio

from itd_sdk import ITDClient


async def main() -> None:
    async with ITDClient(access_token="...") as client:
        print(client.device_id)


asyncio.run(main())
```

## SDKObject

`SDKObject` это обертка над JSON-объектом с доступом через атрибуты и ключи.

Поддержка доступа:

- `obj.id`
- `obj["id"]`
- `obj.get("id")`
- `obj.to_dict()`

Публичные методы:

- `obj.get(key: str, default: Any = None) -> Any`
  Вернуть поле по ключу.
- `obj.to_dict() -> dict[str, Any]`
  Преобразовать объект обратно в обычный `dict`.

Пример:

```python
async def example(client) -> None:
    post = await client.posts.get_post("post-id")
    print(post.id)
    print(post["id"])
    print(post.to_dict())
```

## Page

Пагинируемый контейнер.

Поля:

- `items: list[T]`
  Текущая страница данных.
- `next_cursor: str | None`
  Курсор следующей страницы.

Пример:

```python
async def example(client) -> None:
    page = await client.posts.get_feed(limit=20)
    print(page.items)
    print(page.next_cursor)
```

## ApiError

Исключение SDK для HTTP/API ошибок.

Поля:

- `status_code`
- `message`
- `code`
- `errors`
- `payload`

Пример:

```python
import asyncio

from itd_sdk import ApiError, ITDClient


async def main() -> None:
    try:
        async with ITDClient(access_token="...") as client:
            await client.account.get_me()
    except ApiError as exc:
        print(exc.status_code)
        print(exc.code)
        print(exc.message)


asyncio.run(main())
```

## Account

Объект: `client.account`  
Алиас: `client.users`

### `async account.check_username(username: str) -> bool`

Проверяет доступность username.

Параметры:

- `username`
  Проверяемый username.

Возвращает:

- `True`, если username свободен.
- `False`, если занят.

### `async account.create_profile(payload: Mapping[str, Any]) -> SDKObject`

Создает профиль.

Параметры:

- `payload`
  Словарь полей профиля.

Возвращает:

- `SDKObject` с ответом API.

### `async account.get_me() -> SDKObject`

Возвращает текущий профиль.

Возвращает:

- `SDKObject` профиля.

### `async account.update_me(payload: Mapping[str, Any]) -> SDKObject`

Обновляет текущий профиль.

Параметры:

- `payload`
  Словарь изменяемых полей.

Возвращает:

- `SDKObject` с ответом API.

### `async account.get_profile(username: str) -> SDKObject`

Получает профиль по username.

Параметры:

- `username`
  Username профиля.

Возвращает:

- `SDKObject` профиля.

### `async account.follow(user_id: str) -> None`

Подписывает на пользователя.

Параметры:

- `user_id`
  ID пользователя.

### `async account.unfollow(user_id: str) -> None`

Отписывает от пользователя.

Параметры:

- `user_id`
  ID пользователя.

### `async account.get_privacy_settings() -> SDKObject`

Возвращает настройки приватности.

Поля результата:

- `isPrivate`
- `showLastSeen`
- `whoCanPostOnWall`
- `whoCanSeeMyPostReactions`

### `async account.update_privacy_settings(show_last_seen: bool | None = None, who_can_post_on_wall: str | None = None, who_can_see_my_post_reactions: str | None = None) -> None`

Обновляет настройки приватности.

Параметры:

- `show_last_seen`
  Показывать last seen.
- `who_can_post_on_wall`
  Кто может писать на стене.
- `who_can_see_my_post_reactions`
  Кто может видеть реакции на посты.

### `async account.get_verification_status() -> SDKObject | None`

Получает статус верификации.

Возвращает:

- `SDKObject`, если статус есть.
- `None`, если endpoint отвечает `404`.

### `async account.submit_verification_request(video_url: str) -> SDKObject`

Отправляет запрос на верификацию.

Параметры:

- `video_url`
  URL видео для верификации.

Возвращает:

- `SDKObject` с ответом API.

### `async account.get_my_pins() -> SDKObject`

Возвращает pin-конфигурацию аккаунта.

Поля результата:

- `pins`
- `activePin`

### `async account.set_active_pin(slug: str) -> None`

Делает pin активным.

Параметры:

- `slug`
  Slug pin-объекта.

### `async account.remove_active_pin() -> None`

Удаляет активный pin.

### `async account.delete_account() -> None`

Удаляет аккаунт.

### `async account.restore_account() -> None`

Восстанавливает аккаунт.

## Auth

Объект: `client.auth`

SDK не поддерживает credential-based auth flow через e-mail и пароль.
Для авторизованных сценариев используйте `access_token`, `refresh_token` в `cookies`
и `auth.refresh_session()`.

### `async auth.refresh_session() -> SDKObject`

Пытается обновить access token через серверную сессию.

Возвращает:

- `SDKObject` ответа API.

### `async auth.logout() -> None`

Выходит из текущей сессии.

Примечание:

- локальный `access_token` клиента очищается всегда.

### `async auth.logout_all() -> None`

Выходит из всех сессий.

Примечание:

- локальный `access_token` клиента очищается всегда.

## Posts

Объект: `client.posts`

### `async posts.get_feed(tab: str = "global", limit: int = 20, cursor: str | None = None) -> Page[SDKObject]`

Получает ленту.

Параметры:

- `tab`
  `global`, `clan` или `following`.
- `limit`
  Размер страницы.
- `cursor`
  Курсор следующей страницы.

Возвращает:

- `Page[SDKObject]`

Пример:

```python
async def example(client) -> None:
    feed = await client.posts.get_feed(tab="global", limit=10)
    for post in feed.items:
        print(post.id, post.text)
```

### `async posts.get_post(post_id: str) -> SDKObject`

Получает один пост.

Параметры:

- `post_id`

Возвращает:

- `SDKObject` поста.

### `async posts.get_user_wall(user_id: str, limit: int | None = None, cursor: str | None = None, pinned_post_id: str | None = None) -> Page[SDKObject]`

Получает стену пользователя.

Параметры:

- `user_id`
- `limit`
- `cursor`
- `pinned_post_id`

Возвращает:

- `Page[SDKObject]`

### `async posts.get_user_posts(user_id: str, limit: int | None = None, cursor: str | None = None, sort: str | None = None, pinned_post_id: str | None = None) -> Page[SDKObject]`

Получает посты пользователя.

Параметры:

- `user_id`
- `limit`
- `cursor`
- `sort`
- `pinned_post_id`

Возвращает:

- `Page[SDKObject]`

### `async posts.get_user_liked_posts(user_id: str, limit: int | None = None, cursor: str | None = None) -> Page[SDKObject]`

Получает посты, лайкнутые пользователем.

Параметры:

- `user_id`
- `limit`
- `cursor`

Возвращает:

- `Page[SDKObject]`

### `async posts.get_posts_by_hashtag(hashtag: str, limit: int | None = None, cursor: str | None = None) -> Page[SDKObject]`

Получает посты по хэштегу.

Параметры:

- `hashtag`
- `limit`
- `cursor`

Возвращает:

- `Page[SDKObject]`

### `async posts.create_post(text: str, spans: list[dict] | None = None, wall_owner_id: str | None = None, attachment_ids: list[str] | None = None, poll: dict | None = None) -> SDKObject`

Создает пост.

Параметры:

- `text`
- `spans`
- `wall_owner_id`
- `attachment_ids`
- `poll`

Возвращает:

- `SDKObject` созданного поста.

### `async posts.create_repost(post_id: str, content: str | None = None) -> SDKObject`

Создает репост.

Параметры:

- `post_id`
- `content`

Возвращает:

- `SDKObject` созданного репоста.

### `async posts.edit_post(post_id: str, text: str | None = None, content: str | None = None, spans: list[dict] | None = None) -> None`

Редактирует пост.

Параметры:

- `post_id`
- `text`
- `content`
- `spans`

### `async posts.delete_post(post_id: str) -> None`

Удаляет пост.

Параметры:

- `post_id`

### `async posts.restore_post(post_id: str) -> None`

Восстанавливает пост.

Параметры:

- `post_id`

### `async posts.like(post_id: str) -> None`

Ставит лайк посту.

Параметры:

- `post_id`

### `async posts.unlike(post_id: str) -> None`

Снимает лайк с поста.

Параметры:

- `post_id`

### `async posts.pin(post_id: str) -> None`

Закрепляет пост.

Параметры:

- `post_id`

### `async posts.unpin(post_id: str) -> None`

Открепляет пост.

Параметры:

- `post_id`

### `async posts.vote_poll(post_id: str, option_ids: list[str]) -> SDKObject`

Голосует в опросе.

Параметры:

- `post_id`
- `option_ids`

Возвращает:

- `SDKObject` ответа API.

### `async posts.unrepost(post_id: str) -> None`

Удаляет репост.

Параметры:

- `post_id`

### `async posts.track_view(post_id: str) -> None`

Отправляет просмотр поста.

Параметры:

- `post_id`

### `async posts.track_views_batch(post_ids: list[str]) -> None`

Отправляет просмотры нескольких постов.

Параметры:

- `post_ids`

Примечание:

- отправляет просмотры батчами с ограниченной параллельностью через `track_view()`.

## Comments

Объект: `client.comments`

### `async comments.get_comments(post_id: str, limit: int | None = None, sort: str | None = None, cursor: str | None = None) -> Page[SDKObject]`

Получает комментарии поста.

Параметры:

- `post_id`
- `limit`
- `sort`
  `new`, `old` или `popular`.
- `cursor`

Возвращает:

- `Page[SDKObject]`

### `async comments.get_replies(comment_id: str, limit: int | None = None, cursor: str | None = None) -> Page[SDKObject]`

Получает ответы на комментарий.

Параметры:

- `comment_id`
- `limit`
- `cursor`

Возвращает:

- `Page[SDKObject]`

### `async comments.create_comment(post_id: str, content: str, attachment_ids: list[str] | None = None) -> SDKObject`

Создает комментарий.

Параметры:

- `post_id`
- `content`
- `attachment_ids`

Возвращает:

- `SDKObject` созданного комментария.

### `async comments.create_reply(comment_id: str, content: str, reply_to_user_id: str | None = None, attachment_ids: list[str] | None = None) -> SDKObject`

Создает ответ на комментарий.

Параметры:

- `comment_id`
- `content`
- `reply_to_user_id`
- `attachment_ids`

Возвращает:

- `SDKObject` созданного ответа.

### `async comments.edit_comment(comment_id: str, content: str) -> None`

Редактирует комментарий.

Параметры:

- `comment_id`
- `content`

### `async comments.delete_comment(comment_id: str) -> None`

Удаляет комментарий.

Параметры:

- `comment_id`

### `async comments.like(comment_id: str) -> None`

Ставит лайк комментарию.

Параметры:

- `comment_id`

### `async comments.unlike(comment_id: str) -> None`

Снимает лайк с комментария.

Параметры:

- `comment_id`

## Notifications

Объект: `client.notifications`

### `async notifications.get_notifications(limit: int = 20, cursor: str | None = None, offset: int | None = None) -> Page[SDKObject]`

Получает уведомления.

Параметры:

- `limit`
- `cursor`
- `offset`

Возвращает:

- `Page[SDKObject]`

`next_cursor` будет заполнен, если API вернет курсор следующей страницы.

### `async notifications.get_unread_count() -> int`

Возвращает число непрочитанных уведомлений.

### `async notifications.mark_as_read(ids: list[str]) -> int`

Помечает уведомления прочитанными.

Параметры:

- `ids`
  Список ID уведомлений.

Возвращает:

- Количество реально помеченных уведомлений.

### `async notifications.mark_all_as_read() -> int`

Помечает все уведомления прочитанными.

Возвращает:

- Количество помеченных уведомлений.

### `async notifications.get_settings() -> SDKObject`

Получает настройки уведомлений.

Возвращает:

- `SDKObject` с полями `webEnabled`, `soundEnabled`, `preferences`.

### `async notifications.update_settings(web_enabled: bool | None = None, sound_enabled: bool | None = None, preferences: Mapping[str, bool] | None = None) -> None`

Обновляет настройки уведомлений.

Параметры:

- `web_enabled`
- `sound_enabled`
- `preferences`
  Может содержать `follows`, `reactions`, `replies`, `mentions`, `wallPosts`.

## Social

Объект: `client.social`

### `async social.get_followers(user_id: str, limit: int = 20, cursor: str | None = None, page: int | None = None) -> Page[SDKObject]`

Получает подписчиков.

Параметры:

- `user_id`
- `limit`
- `cursor`
  Непрозрачный курсор из предыдущей страницы или строковое число страницы для page-based pagination.
- `page`
  Явный номер страницы для page-based pagination.

Возвращает:

- `Page[SDKObject]`

### `async social.get_following(user_id: str, limit: int = 20, cursor: str | None = None, page: int | None = None) -> Page[SDKObject]`

Получает подписки.

Параметры:

- `user_id`
- `limit`
- `cursor`
  Непрозрачный курсор из предыдущей страницы или строковое число страницы для page-based pagination.
- `page`
  Явный номер страницы для page-based pagination.

Возвращает:

- `Page[SDKObject]`

### `async social.block(user_id: str) -> None`

Блокирует пользователя.

Параметры:

- `user_id`

### `async social.unblock(user_id: str) -> None`

Разблокирует пользователя.

Параметры:

- `user_id`

### `async social.get_blocked_users(limit: int = 20, cursor: str | None = None, page: int | None = None) -> Page[SDKObject]`

Получает черный список.

Параметры:

- `limit`
- `cursor`
  Непрозрачный курсор из предыдущей страницы или строковое число страницы для page-based pagination.
- `page`
  Явный номер страницы для page-based pagination.

Возвращает:

- `Page[SDKObject]`

### `async social.batch_follow_status(user_ids: list[str]) -> SDKObject`

Получает follow-status пачкой.

Параметры:

- `user_ids`

Возвращает:

- `SDKObject`, где ключи обычно соответствуют user ID.

## Search

Объект: `client.search`

### `async search.get_trending_hashtags(limit: int = 10) -> list[SDKObject]`

Получает популярные хэштеги.

Параметры:

- `limit`

Возвращает:

- Список `SDKObject`.

### `async search.get_top_clans() -> list[SDKObject]`

Получает топ кланов.

Возвращает:

- Список `SDKObject`.

### `async search.search_users(query: str, limit: int = 20, cursor: str | None = None) -> Page[SDKObject]`

Ищет пользователей.

Параметры:

- `query`
- `limit`
- `cursor`

Возвращает:

- `Page[SDKObject]`

`next_cursor` будет заполнен, если API вернет курсор следующей страницы.

### `async search.global_search(query: str, user_limit: int = 5, hashtag_limit: int = 5) -> SDKObject`

Выполняет глобальный поиск по пользователям и хэштегам.

Параметры:

- `query`
- `user_limit`
- `hashtag_limit`

Возвращает:

- `SDKObject` с полями `users` и `hashtags`.

### `async search.search_hashtags(query: str | None = None, limit: int = 10) -> list[SDKObject]`

Ищет хэштеги.

Параметры:

- `query`
- `limit`

Возвращает:

- Список `SDKObject`.

## Files

Объект: `client.files`

### `async files.upload_media(file, filename: str | None = None, content_type: str | None = None) -> SDKObject`

Загружает файл.

Параметры:

- `file`
  Путь (`str` или `Path`), `bytes` или бинарный file-like объект.
- `filename`
  Явное имя файла.
- `content_type`
  Явный mime-type.

Возвращает:

- `SDKObject` загруженного файла.

### `async files.delete_file(file_id: str) -> None`

Удаляет файл.

Параметры:

- `file_id`

## Reports

Объект: `client.reports`

### `async reports.create_report(payload: Mapping[str, Any]) -> SDKObject`

Создает жалобу.

Параметры:

- `payload`
  Словарь, который ожидает endpoint `/reports`.

Возвращает:

- `SDKObject` ответа API.

## Platform

Объект: `client.platform`

### `async platform.get_changelog() -> list[SDKObject]`

Получает changelog платформы.

Возвращает:

- Список `SDKObject`.

Пример:

```python
import asyncio

from itd_sdk import ITDClient


async def main() -> None:
    async with ITDClient() as client:
        changelog = await client.platform.get_changelog()
        print(changelog[0].version)


asyncio.run(main())
```

## Raw

Объект: `client.raw`

### `async raw.request(method: str, path: str, auth: bool = False, json: dict | None = None, params: Mapping[str, Any] | None = None, headers: Mapping[str, str] | None = None, files: Any | None = None) -> Any`

Выполняет произвольный запрос и возвращает сырой JSON.

Параметры:

- `method`
  HTTP-метод.
- `path`
  Путь endpoint'а.
- `auth`
  Если `True`, запрос пойдет через auth-base `/api/v1/auth`.
- `json`
  JSON body.
- `params`
  Query parameters.
- `headers`
  Дополнительные заголовки.
- `files`
  Multipart files.

Возвращает:

- Сырой ответ API без преобразования в `SDKObject`.

Пример:

```python
import asyncio

from itd_sdk import ITDClient


async def main() -> None:
    async with ITDClient() as client:
        raw = await client.raw.request("GET", "/platform/changelog")
        print(raw)


asyncio.run(main())
```
