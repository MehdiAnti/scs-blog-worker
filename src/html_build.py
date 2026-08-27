import re

from bs4 import BeautifulSoup


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

            try:

                parent = node.parent

                if parent:
                    parent.decompose()

            except Exception:
                pass

    return soup


def _create_button(
    soup,
    text,
    url,
    style="primary",
):

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
                "▶️ View Video",
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

            src = (
                "https://store.steampowered.com/app/"
                f"{appid.group(1)}/"
            )

            button = _create_button(
                soup,
                "🛒 View Store",
                src,
                style="success",
            )

        else:

            iframe.decompose()
            continue

        iframe.replace_with(
            button
        )

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


def _cleanup_images_and_links(soup):

    for img in soup.find_all("img"):

        src = img.get(
            "src",
            "",
        )

        if ".gif" in src.lower():

            button = _create_button(
                soup,
                "🎞 View Animation",
                src,
                style="primary",
            )

            img.replace_with(
                button
            )

    for link in soup.find_all("a"):
        
        if link.find("tg-button-row"):
            link.unwrap()

        if not link.get_text(
            strip=True
        ):

            if link.find("img"):

                link.unwrap()

            else:

                link.decompose()

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


def clean_article(article_html):

    soup = BeautifulSoup(
        article_html,
        "html.parser",
    )

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
        soup
    )

    soup = _strip_attributes(
        soup
    )

    if soup.body:

        html = soup.body.decode_contents()

    else:

        html = str(soup)

    html = html.strip()

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

    print(
        f"Article cleaned | Length={len(html)}"
    )

    return html


def build_preview(
    title,
    article_url,
    teaser,
):

    return (
        f"<b>{title}</b>\n\n"
        f"{teaser}\n\n"
        f"🔗 {article_url}\n\n"
        f"🐳\n"
        f"Join: @SCSSoftwareFeed"
    )


def build_rich_article(article_html):

    html = article_html.strip()

    if len(html) > 32000:

        html = html[:32000]

    return html
