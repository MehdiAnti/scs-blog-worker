import html
import re
import time

from urllib.parse import (
    urlparse,
    urljoin,
)

from bs4 import (
    BeautifulSoup,
    NavigableString,
)

from store_ids import (
    STORE_IDS,
)


REMOVE_TEXTS = [
    "Email This",
    "BlogThis",
    "Share to X",
    "Share to Facebook",
    "Share to Pinterest",
    "No comments",
    "Post a Comment",
]


SUPPORTED_TAGS = {
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "p",
    "a",
    "b",
    "strong",
    "i",
    "em",
    "u",
    "ins",
    "s",
    "strike",
    "del",
    "blockquote",
    "ul",
    "ol",
    "li",
    "br",
    "img",
    "tg-button",
    "tg-button-row",
}


MAX_RICH_HTML_LENGTH = 32000


def _normalize_url(
    url,
    base_url=None,
):

    if not url:
        return None

    url = url.strip()

    if re.match(
        r"^https?://@",
        url,
        re.IGNORECASE,
    ):

        url = re.sub(
            r"^https?://@",
            "https://",
            url,
            count=1,
            flags=re.IGNORECASE,
        )

    if base_url:

        url = urljoin(
            base_url,
            url,
        )

    return url


def _is_safe_url(url):

    if not url:
        return False

    try:

        parsed = urlparse(url)

    except Exception:

        return False

    if parsed.scheme not in (
        "http",
        "https",
    ):

        return False

    if not parsed.netloc:
        return False

    if "@" in parsed.netloc:
        return False

    try:

        hostname = parsed.hostname

    except ValueError:

        return False

    if not hostname:
        return False

    return True


def _remove_unwanted_blocks(soup):

    for text in REMOVE_TEXTS:

        nodes = soup.find_all(
            string=lambda s: (
                s
                and text.lower()
                in s.lower()
            )
        )

        for node in nodes:

            parent = node.parent

            if parent:

                parent.decompose()

    return soup


def _create_button(
    soup,
    text,
    url,
    style="primary",
):

    url = _normalize_url(url)

    if not _is_safe_url(url):

        print(
            f"WARNING: Invalid button URL skipped: {url}"
        )

        return None

    button = soup.new_tag(
        "tg-button"
    )

    button["type"] = "url"
    button["style"] = style
    button["url"] = url

    button.string = text

    row = soup.new_tag(
        "tg-button-row"
    )

    row.append(button)

    return row


def _create_inline_button(
    soup,
    text,
    url,
):

    url = _normalize_url(url)

    if not _is_safe_url(url):

        print(
            f"WARNING: Invalid inline URL skipped: {url}"
        )

        return None

    button = soup.new_tag(
        "tg-button"
    )

    button["type"] = "url"
    button["url"] = url

    button.string = text

    return button


def _convert_iframes(soup):

    for iframe in soup.find_all("iframe"):

        src = iframe.get(
            "src",
            "",
        )

        if not src:
            iframe.decompose()
            continue

        if (
            "youtube.com" in src
            or
            "youtu.be" in src
        ):

            match = re.search(
                r"youtube\.com/embed/([^?&/]+)",
                src,
            )

            if match:

                src = (
                    "https://youtu.be/"
                    f"{match.group(1)}"
                )

            button = _create_button(
                soup,
                "View Video",
                src,
                style="primary",
            )

        elif (
            "store.steampowered.com/widget/"
            in src
        ):

            appid = re.search(
                r"/widget/(\d+)/",
                src,
            )

            if not appid:
                iframe.decompose()
                continue

            app_id = appid.group(1)

            src = (
                "https://store.steampowered.com/app/"
                f"{app_id}/"
            )

            name = STORE_IDS.get(
                app_id
            )

            button_text = (
                f"View {name} in Store"
                if name
                else "View Store"
            )

            button = _create_button(
                soup,
                button_text,
                src,
                style="success",
            )

        else:

            iframe.decompose()
            continue

        if button:

            iframe.replace_with(
                button
            )

        else:

            iframe.decompose()

    return soup


def _clean_tags(soup):

    for tag in soup.find_all(True):

        if tag.name in (
            "html",
            "body",
        ):
            continue

        if tag.name not in SUPPORTED_TAGS:

            if tag.name in (
                "script",
                "style",
                "iframe",
                "svg",
                "noscript",
            ):

                tag.decompose()

            else:

                tag.unwrap()

    return soup


def _cleanup_images_and_links(
    soup,
    base_url=None,
):

    for img in soup.find_all("img"):

        src = _normalize_url(
            img.get("src", ""),
            base_url,
        )

        if not _is_safe_url(src):

            img.decompose()
            continue

        img["src"] = src

        if ".gif" in src.lower():

            button = _create_button(
                soup,
                "View Animation",
                src,
                style="primary",
            )

            if button:

                parent = img.parent

                if (
                    parent
                    and parent.name == "a"
                ):

                    parent.replace_with(
                        button
                    )

                else:

                    img.replace_with(
                        button
                    )

    for link in soup.find_all("a"):

        href = _normalize_url(
            link.get("href", ""),
            base_url,
        )

        text = link.get_text(
            strip=True
        )

        if not text:

            if link.find("img"):

                if _is_safe_url(href):

                    link["href"] = href

                else:

                    link.unwrap()

            else:

                link.decompose()

            continue

        if not _is_safe_url(href):

            link.unwrap()
            continue

        button = _create_inline_button(
            soup,
            text,
            href,
        )

        if button:

            link.replace_with(
                button
            )

        else:

            link.unwrap()

    for paragraph in soup.find_all("p"):

        if (
            not paragraph.get_text(
                strip=True
            )
            and not paragraph.find("img")
            and not paragraph.find(
                "tg-button"
            )
        ):

            paragraph.decompose()

    for heading in soup.find_all([
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
    ]):

        if not heading.get_text(
            strip=True
        ):

            heading.decompose()

    return soup


def _strip_attributes(soup):

    for tag in soup.find_all(True):

        if tag.name == "a":

            href = tag.get("href")

            tag.attrs = {}

            if href:
                tag["href"] = href

        elif tag.name == "img":

            src = tag.get("src")

            tag.attrs = {}

            if src:
                tag["src"] = src

        elif tag.name == "tg-button":

            button_type = tag.get(
                "type"
            )

            style = tag.get(
                "style"
            )

            url = tag.get(
                "url"
            )

            tag.attrs = {}

            if button_type:
                tag["type"] = button_type

            if style:
                tag["style"] = style

            if url:
                tag["url"] = url

        elif tag.name == "tg-button-row":

            tag.attrs = {}

        else:

            tag.attrs = {}

    return soup


def clean_article(
    article_html,
    base_url=None,
):

    started = time.perf_counter()

    original_length = len(
        article_html
    )

    soup = BeautifulSoup(
        article_html,
        "html.parser",
    )

    element_count = len(
        soup.find_all(True)
    )

    stage_started = time.perf_counter()

    soup = _remove_unwanted_blocks(
        soup
    )

    soup = _convert_iframes(
        soup
    )

    soup = _clean_tags(
        soup
    )

    soup = _cleanup_images_and_links(
        soup,
        base_url,
    )

    soup = _strip_attributes(
        soup
    )

    processing_time = (
        time.perf_counter()
        - stage_started
    )

    if soup.body:

        result = soup.body.decode_contents()

    else:

        result = str(soup)

    result = result.strip()

    if not soup.find([
        "p",
        "h1",
        "h2",
        "h3",
        "li",
    ]):

        print(
            "WARNING: No text blocks found"
        )

    elapsed = (
        time.perf_counter()
        - started
    )

    print(
        f"Article cleaned | "
        f"Original={original_length} | "
        f"Cleaned={len(result)} | "
        f"Elements={element_count} | "
        f"Processing={processing_time:.4f}s | "
        f"Total={elapsed:.4f}s"
    )

    return result


def build_preview(
    title,
    article_url,
    teaser,
):

    title = html.escape(
        title or ""
    )

    article_url = html.escape(
        article_url or ""
    )

    teaser = html.escape(
        teaser or ""
    )

    teaser = teaser[:500]

    preview = (
        f"<b>{title}</b>\n\n"
        f"{teaser}\n\n"
        f"🔗 {article_url}\n\n"
        f"🐳\n"
        f"Join: @SCSSoftwareFeed"
    )

    if len(preview) > 1024:

        preview = (
            f"<b>{title[:200]}</b>\n\n"
            f"{teaser[:300]}\n\n"
            f"🔗 {article_url}\n\n"
            f"🐳\n"
            f"Join: @SCSSoftwareFeed"
        )

    return preview


def _truncate_soup(soup, max_length):

    while len(
        soup.decode_contents()
    ) > max_length:

        strings = soup.find_all(
            string=True
        )

        if strings:

            last = strings[-1]

            excess = (
                len(soup.decode_contents())
                - max_length
            )

            remove_count = max(
                excess,
                1,
            )

            value = str(last)

            if len(value) > remove_count:

                last.replace_with(
                    value[:-remove_count]
                )

            else:

                last.extract()

        elif soup.contents:

            soup.contents[-1].decompose()

        else:

            break

    return soup.decode_contents()


def build_rich_article(article_html):

    html_content = (
        article_html.strip()
    )

    if len(html_content) <= MAX_RICH_HTML_LENGTH:
        return html_content

    print(
        f"Rich HTML exceeds limit | "
        f"Original={len(html_content)}"
    )

    soup = BeautifulSoup(
        html_content,
        "html.parser",
    )

    html_content = _truncate_soup(
        soup,
        MAX_RICH_HTML_LENGTH,
    )

    print(
        f"Rich HTML truncated safely | "
        f"Final={len(html_content)}"
    )

    return html_content
