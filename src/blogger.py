import asyncio
import re
import time

import httpx

from urllib.parse import urljoin

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

    for attempt in range(3):

        try:

            async with httpx.AsyncClient(
                headers=HEADERS,
                follow_redirects=True,
                timeout=30.0,
            ) as client:

                response = await client.get(url)

            if response.status_code == 503:

                if attempt < 2:

                    wait_time = 3 * (
                        attempt + 1
                    )

                    print(
                        f"HTTP 503 for {url} "
                        f"- retrying in "
                        f"{wait_time}s "
                        f"({attempt + 1}/2)"
                    )

                    await asyncio.sleep(
                        wait_time
                    )

                    continue

                print(
                    f"HTTP 503 for {url} "
                    f"- giving up"
                )

                return None

            response.raise_for_status()

            return response.text

        except httpx.HTTPError as e:

            if attempt < 2:

                wait_time = 3 * (
                    attempt + 1
                )

                print(
                    f"HTTP error for {url}: "
                    f"{e} - retrying in "
                    f"{wait_time}s "
                    f"({attempt + 1}/2)"
                )

                await asyncio.sleep(
                    wait_time
                )

                continue

            print(
                f"HTTP request failed for "
                f"{url}: {e}"
            )

            return None

    return None


async def probe_image(url):

    if not url:
        return {
            "url": "",
            "status": None,
            "content_type": "",
            "size": None,
            "error": "No image URL",
        }

    result = {
        "url": url,
        "status": None,
        "content_type": "",
        "size": None,
        "error": "",
    }

    try:

        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=20.0,
            headers=HEADERS,
        ) as client:

            response = await client.head(
                url
            )

            if response.status_code in (
                405,
                403,
            ):

                response = await client.get(
                    url,
                    headers={
                        **HEADERS,
                        "Range": "bytes=0-0",
                    },
                )

        result["status"] = (
            response.status_code
        )

        result["content_type"] = (
            response.headers.get(
                "content-type",
                "",
            )
        )

        result["size"] = (
            response.headers.get(
                "content-length",
                "",
            )
        )

        result["final_url"] = str(
            response.url
        )

        if not response.is_success:

            result["error"] = (
                f"HTTP {response.status_code}"
            )

        elif not result["content_type"].lower().startswith(
            "image/"
        ):

            result["error"] = (
                "URL does not return an image"
            )

    except Exception as e:

        result["error"] = str(e)

    return result


async def _get_latest_post_homepage():

    html = await _get(BLOG_URL)

    if html is None:
        raise Exception(
            "Homepage unavailable"
        )

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
        "url": urljoin(
            BLOG_URL,
            post.get("href", ""),
        ),
        "date": "",
    }


async def _get_latest_post_rss():
    """
    Supports Atom and RSS feeds.
    """

    html = await _get(RSS_URL)

    if html is None:
        raise Exception(
            "RSS feed unavailable"
        )

    soup = BeautifulSoup(
        html,
        "xml",
    )

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
            "url": urljoin(
                BLOG_URL,
                url,
            ),
            "date": pub_date,
        }

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
            "url": urljoin(
                BLOG_URL,
                url,
            ),
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


def _get_srcset_url(srcset):

    if not srcset:
        return None

    candidates = []

    for item in srcset.split(","):

        parts = item.strip().split()

        if not parts:
            continue

        url = parts[0]
        quality = 0

        if len(parts) > 1:

            descriptor = parts[1]

            match = re.match(
                r"(\d+(?:\.\d+)?)(w|x)",
                descriptor,
            )

            if match:

                quality = float(
                    match.group(1)
                )

        candidates.append(
            (quality, url)
        )

    if not candidates:
        return None

    candidates.sort(
        key=lambda item: item[0]
    )

    return candidates[-1][1]


def _get_image_url(img, base_url):

    candidates = [
        img.get("data-src"),
        img.get("data-original"),
        img.get("data-lazy-src"),
        img.get("src"),
        _get_srcset_url(
            img.get("srcset")
        ),
    ]

    for candidate in candidates:

        if not candidate:
            continue

        candidate = candidate.strip()

        if (
            not candidate
            or candidate.startswith("data:")
            or candidate.startswith("blob:")
        ):
            continue

        return urljoin(
            base_url,
            candidate,
        )

    return None


def _prepare_images(body, base_url):

    hero_image = None

    for img in body.find_all("img"):

        image_url = _get_image_url(
            img,
            base_url,
        )

        if not image_url:
            continue

        img["src"] = image_url

        for attribute in (
            "data-src",
            "data-original",
            "data-lazy-src",
            "data-srcset",
            "srcset",
            "loading",
        ):

            img.attrs.pop(
                attribute,
                None,
            )

        if hero_image is None:

            hero_image = image_url

    print(
        f"Images prepared | "
        f"Count={len(body.find_all('img'))} | "
        f"Hero={hero_image}"
    )

    return hero_image


async def fetch_article(url):

    started = time.perf_counter()

    url = urljoin(
        BLOG_URL,
        url,
    )

    html = await _get(url)

    if html is None:
        raise Exception(
            f"Article unavailable: {url}"
        )

    download_time = (
        time.perf_counter()
        - started
    )

    parse_started = time.perf_counter()

    print(
        f"Original HTML size: {len(html)}"
    )

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

    element_count = len(
        body.find_all(True)
    )

    hero_image = _prepare_images(
        body,
        url,
    )

    article_text = body.get_text(
        "\n",
        strip=True,
    )

    teaser = _get_teaser(
        article_text,
        limit=400,
    )

    parse_time = (
        time.perf_counter()
        - parse_started
    )

    print(
        f"Article fetched | "
        f"Download={download_time:.3f}s | "
        f"Parsing={parse_time:.3f}s | "
        f"Elements={element_count} | "
        f"HTML={len(html)}"
    )

    return {
        "title": title,
        "url": url,
        "hero_image": hero_image,
        "teaser": teaser,
        "html": str(body),
        "original_html_length": len(html),
        "element_count": element_count,
    }
