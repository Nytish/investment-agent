# APEX — Gmail Alert Setup (OAuth2)

Your Gmail password is **never used or stored**.  
APEX uses Google OAuth2 — a revocable token with send-only permission.

---

## What this grants

- ✅ Send emails from your Gmail address
- ❌ Cannot read your emails
- ❌ Cannot delete anything
- ❌ Cannot access Drive, Calendar, or any other Google service

You can revoke access in 10 seconds at any time.

---

## One-time setup (~5 minutes)

### Step 1 — Enable the Gmail API

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (name it anything, e.g. "APEX Alerts")
3. Go to **APIs & Services → Library**
4. Search for **Gmail API** → Enable it

### Step 2 — Create OAuth credentials

1. Go to **APIs & Services → Credentials**
2. Click **+ Create Credentials → OAuth 2.0 Client ID**
3. Application type: **Desktop app**
4. Name: `APEX` (or anything)
5. Click **Create**
6. Click **Download JSON**
7. Save the file as `data/gmail_credentials.json` inside your APEX folder

> `data/gmail_credentials.json` is gitignored — it never leaves your Mac.

### Step 3 — Configure consent screen (if prompted)

1. Go to **OAuth consent screen**
2. User type: **External**
3. Fill in App name: `APEX`, your email, save
4. Add your Gmail address as a **Test user**

### Step 4 — Run setup

```bash
cd ~/apex
python -m notify.gmail_alert --setup
```

A browser window opens. Sign in with your Google account → click **Allow**.  
The token is saved to `data/gmail_token.json` (also gitignored).

That's it. APEX will send alerts silently from now on.

---

## Revoking access

Go to [myaccount.google.com/permissions](https://myaccount.google.com/permissions)  
Find **APEX** → Remove access. Token is immediately invalidated.

---

## If you skip this

Leave `data/gmail_credentials.json` absent.  
Alerts will print to the console and appear in the Streamlit dashboard.  
Email is optional — the dashboard shows everything.
