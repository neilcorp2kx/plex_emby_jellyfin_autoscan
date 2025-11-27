# Security Fixes Quick Reference

**🔒 Critical Security Fixes Implemented - Quick Guide**

---

## ✅ What Was Fixed

### 1. Command Injection (CRITICAL)
- **Before:** `os.system()` with string concatenation ❌
- **After:** `requests.post()` with proper JSON encoding ✅
- **Impact:** Eliminates critical RCE vulnerability

### 2. Rate Limiting
- **Added:** Flask-Limiter on all endpoints
- **Limits:** 30/min (webhooks), 10/min (manual), 60/min (health)
- **Impact:** Prevents DoS and abuse

### 3. Credential Logging
- **Before:** Secrets logged in plaintext ❌
- **After:** Only logs "present/missing" indicators ✅
- **Impact:** No credential leakage in logs

### 4. Webhook Authentication (Optional)
- **Added:** HMAC signature verification
- **Supports:** GitHub, Slack, Generic webhooks
- **Impact:** Prevents webhook spoofing

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Test Installation
```bash
python3 -m py_compile scan.py validators.py
```

### 3. Optional: Enable Webhook Signatures
```bash
# Generate secret
python3 -c "import secrets; print('WEBHOOK_SECRET=' + secrets.token_hex(32))"

# Add to .env
echo "WEBHOOK_SECRET=your_generated_secret" >> .env
```

---

## 📋 Files Modified

| File | Changes |
|------|---------|
| `scan.py` | Command injection fix, rate limiting, credential sanitization, HMAC integration |
| `validators.py` | New HMAC verification function |
| `requirements.txt` | Added Flask-Limiter |
| `.env.example` | Added WEBHOOK_SECRET documentation |

---

## 🧪 Testing Checklist

- [ ] Install dependencies: `pip install -r requirements.txt`
- [ ] Syntax check: `python3 -m py_compile scan.py validators.py`
- [ ] Test manual scan (if enabled)
- [ ] Test webhook endpoint
- [ ] Verify rate limiting (exceed limits)
- [ ] Check logs for sanitized credentials
- [ ] Test Jellyfin/Emby integration

---

## 📊 Rate Limits (Per IP)

| Endpoint | Limit | Use Case |
|----------|-------|----------|
| `/health` | 60/min | Health monitoring |
| `/api/{SERVER_PASS}` | 30/min | API calls |
| `/{SERVER_PASS}` GET | 10/min | Manual scan page |
| `/{SERVER_PASS}` POST | 30/min | Webhooks |

**To adjust:** Edit `@limiter.limit()` decorators in `scan.py`

---

## 🔐 Environment Variables

### Required (Already Set)
```bash
SECRET_KEY=your_secret_key
SERVER_PASS=your_server_password
```

### Optional (New)
```bash
WEBHOOK_SECRET=your_webhook_secret  # Enable HMAC verification
```

---

## ⚠️ Breaking Changes

**None.** All changes are backward compatible.

---

## 🐛 Troubleshooting

### ImportError: flask_limiter
```bash
pip install flask-limiter~=3.5.0
```

### Rate limit too strict
Edit `scan.py`, increase limits:
```python
@limiter.limit("60 per minute")  # was 30
```

### Webhook signatures failing
- Check `WEBHOOK_SECRET` is set
- Verify webhook provider sends signatures
- Check header name matches (X-Hub-Signature-256, etc.)

---

## 📈 Monitoring

### Check rate limiting
```bash
grep "429" plex_autoscan.log
```

### Check signature failures
```bash
grep "Webhook signature verification failed" plex_autoscan.log
```

### Check Jellyfin/Emby errors
```bash
grep "Failed to send Jellyfin/Emby scan request" plex_autoscan.log
```

---

## 📞 Need Help?

1. Review `SECURITY_FIXES_SUMMARY.md` for detailed documentation
2. Check logs: `tail -f plex_autoscan.log`
3. Test endpoints: `curl http://localhost:3467/health`

---

**Last Updated:** 2025-11-26
**Status:** Production Ready ✅
