# `itd-sdk`

Асинхронный Python SDK для `итд.com`.

`itd-sdk` дает более удобный клиент для REST API сайта с:

- транспортом на `aiohttp`
- async-first API
- object-style ответами через `SDKObject`
- пагинацией через `Page`
- автоматическим refresh токена при наличии auth cookies
- низкоуровневым доступом через `client.raw`

## Установка

Из GitHub:

```bash
pip install git+https://github.com/th1ks/itd-sdk.git
```

Для локальной разработки:

```bash
pip install -e .
```

## Быстрый старт

Публичные методы:

```python
import asyncio

from itd_sdk import ITDClient


async def main() -> None:
    async with ITDClient() as client:
        changelog = await client.platform.get_changelog()
        hashtags = await client.search.get_trending_hashtags(limit=5)

        print(changelog[0].version if changelog else None)
        for hashtag in hashtags:
            print(hashtag.name, hashtag.count)


asyncio.run(main())
```

Авторизованный сценарий:

```python
import asyncio

from itd_sdk import ITDClient


async def main() -> None:
    async with ITDClient(
        access_token="your_access_token",
        cookies={"refresh_token": "..."},
    ) as client:
        me = await client.account.get_me()
        print(me.displayName)


asyncio.run(main())
```

Пост с медиа:

```python
import asyncio

from itd_sdk import ITDClient


async def main() -> None:
    async with ITDClient(access_token="your_access_token") as client:
        media = await client.files.upload_media("image.jpg")
        post = await client.posts.create_post(
            text="Пост с вложением",
            attachment_ids=[media.id],
        )
        print(post.id, post.text)


asyncio.run(main())
```

## Модель ответов

High-level методы возвращают `SDKObject` и `Page`:

```python
post.id
post.text
post["id"]
post.get("text")
post.to_dict()
```

`client.raw` остается низкоуровневым и возвращает сырой payload API.

## API клиента

Доступные группы методов:

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

`client.account` это алиас для `client.users`.

## Авторизация

Клиент поддерживает:

- `access_token` для bearer-авторизации
- `cookies` для refresh-сценариев
- `device_id` для явной установки `X-Device-Id`
- `auto_refresh=True` для повтора запросов после `401`, если доступны refresh cookies

Credential-based auth flow через `email/password` в SDK не поддерживается.
Для авторизованных сценариев используйте `access_token`, `refresh_token`
и `client.auth.refresh_session()`.

Пример:

```python
client = ITDClient(
    access_token="...",
    cookies={"refresh_token": "..."},
    auto_refresh=True,
)
```

## Обработка ошибок

HTTP- и API-ошибки выбрасываются как `ApiError`.

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

### Telegram чат: https://t.me/+uEi6Dj_Qc4tkNmRi

## Документация

- Полная справка по API: [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md)
- Оглавление документации: [`docs/README.md`](docs/README.md)
