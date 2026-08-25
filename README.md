# SCS Blog - Telegram Bot - Cloudflare Worker

A lightweight Cloudflare Worker that automatically monitors the official **SCS Software Blog**, detects newly published articles, converts them into Telegram Rich Messages, and delivers them directly to a Telegram channel.

---

# Features

- Automatically detects new SCS Blog post
- Fetches and parses the complete article
- Sends the original hero image before the article
- Converts Blogger HTML into Telegram Rich Message format
- Preserves article links and formatting
- Uses Cloudflare KV to prevent duplicate posts
- Supports scheduled checks with Cloudflare Cron Triggers
- Supports Telegram webhook

---

# How It Works

```text
Cloudflare Cron
      │
      ▼
Latest SCS Article
      │
      ▼
Already Posted?
   │        │
  Yes       No
   │        │
   ▼        ▼
 Finish   Fetch Article
              │
              ▼
         Clean HTML
              │
              ▼
       Send Hero Image
              │
              ▼
      Send Rich Message
              │
              ▼
      Save to Cloudflare KV
```

---

# Environment Variables

```text
BOT_TOKEN
ALLOWED_USER
CHANNEL_ID
POST_TO_CHANNEL (true or false)
```

---

# Deployment

```bash
uv run pywrangler deploy
```

---

# License

This project is licensed under the [MIT License](https://github.com/MehdiAnti/scs-blog-worker/blob/main/LICENSE).

---

**Powered by**

- Python
- Telegram Bot API
- Cloudflare Workers
- Cloudflare KV

Special thanks to **SCS Software** for creating amazing games and maintaining their official blog.

Happy Trucking! 🚛
