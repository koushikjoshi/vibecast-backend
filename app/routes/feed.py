from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()

_PLACEHOLDER_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
  <channel>
    <title>VibeCast</title>
    <description>Newsroom-as-a-service. Autonomous AI agents produce daily podcast episodes.</description>
    <language>en-us</language>
    <itunes:author>VibeCast</itunes:author>
  </channel>
</rss>
"""


@router.get("/feed.xml")
async def rss_feed() -> Response:
    return Response(content=_PLACEHOLDER_RSS, media_type="application/rss+xml")
