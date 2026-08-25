import re

import httpx

from bs4 import BeautifulSoup
from email.utils import parsedate_to_datetime

from config import (
    BLOG_URL,
    RSS_URL,
    USER_AGENT,
)


HEADERS = {
    "User-Agent": USER_AGENT,
}


async def _get(url):
    async with httpx.AsyncClient(
        headers=HEADERS,
        follow_redirects=True,
        timeout=30.0,
    ) as client:

        response = await client.get(url)

        response.raise_for_status()

        return response.text


async def _get_latest_post_homepage():

    html = await _get(BLOG_URL)

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    post = soup.select_one(
        "h3.post-title.entry-title a"
    )

    if not post:
        raise Exception("No post found")

    return {
        "title": post.get_text(strip=True),
        "url": post.get("href", ""),
        "date": "",
    }


async def _get_latest_post_rss():
    """
    Supports Atom and RSS feeds.
    """

    html = await _get(RSS_URL)

    soup = BeautifulSoup(
        html,
        "xml",
    )

    # Atom

    entry = soup.find("entry")

    if entry:

        title = ""

        if entry.title:
            title = entry.title.get_text(
                strip=True
            )

        url = ""

        for link in entry.find_all("link"):

            if link.get("rel") == "alternate":

                url = (
                    link.get("href")
                    or ""
                )

                break

        pub_date = ""

        updated = entry.find("updated")

        if updated:
            pub_date = updated.get_text(
                strip=True
            )

        return {
            "title": title,
            "url": url,
            "date": pub_date,
        }

    # RSS

    item = soup.find("item")

    if item:

        title = ""

        if item.title:
            title = item.title.get_text(
                strip=True
            )

        url = ""

        if item.link:
            url = item.link.get_text(
                strip=True
            )

        pub_date = ""

        if item.pubDate:

            try:
                pub_date = (
                    parsedate_to_datetime(
                        item.pubDate.text
                    ).isoformat()
                )

            except Exception:
                pub_date = item.pubDate.text

        return {
            "title": title,
            "url": url,
            "date": pub_date,
        }

    raise Exception(
        "No feed entries found"
    )


async def get_latest_post():

    try:

        return await _get_latest_post_homepage()

    except Exception as e:

        print(
            f"Homepage failed: {e}"
        )

        return await _get_latest_post_rss()


def _get_teaser(text, limit=400):

    text = re.sub(
        r"\s+",
        " ",
        text,
    ).strip()

    if len(text) <= limit:
        return text

    return (
        text[:limit]
        .rsplit(" ", 1)[0]
        + "..."
    )


async def fetch_article(url):

    html = await _get(url)

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    title = ""

    title_tag = soup.select_one(
        "h3.post-title.entry-title"
    )

    if title_tag:
        title = title_tag.get_text(
            strip=True
        )

    body = (
        soup.select_one(".post-body")
        or
        soup.select_one(".entry-content")
    )

    if not body:
        raise Exception(
            "Post body not found"
        )

    hero_image = None

    for img in body.find_all("img"):

        parent = img.parent

        if (
            parent
            and parent.name == "a"
            and parent.get("href")
        ):

            hero_image = parent["href"]

            break

        src = (
            img.get("data-src")
            or img.get("src")
        )

        if src:

            hero_image = src

            break

    for img in body.find_all("img"):

        parent = img.parent

        if (
            parent
            and parent.name == "a"
            and parent.get("href")
        ):

            img["src"] = parent["href"]

    article_text = body.get_text(
        "\n",
        strip=True,
    )

    teaser = _get_teaser(
        article_text,
        limit=400,
    )

    return {
        "title": title,
        "url": url,
        "hero_image": hero_image,
        "teaser": teaser,
        "html": str(body),
    }
