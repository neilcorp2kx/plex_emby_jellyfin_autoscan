# Plex/Emby/Jellyfin Autoscan - Security & Modernization Project

## Project Status: Phase 1 Complete ✅

**Last Updated:** 2025-10-07
**Current Branch:** `feature/dependency-updates`
**Active PR:** #14

---

## 📋 Project Overview

This project modernizes and secures the Plex/Emby/Jellyfin Autoscan application by:
1. Updating 5+ year old dependencies (2019 → 2025)
2. Fixing critical security vulnerabilities
3. Implementing modern security best practices
4. Improving code quality and maintainability

---

## 🎯 GitHub Issues Created

### Security Issues (Critical/High Priority)
- **Issue #1**: [Security] Insecure Session Cookie Configuration
- **Issue #2**: [Security] Path Traversal and Injection Risks
- **Issue #12**: [Security] Store Secrets in Environment Variables
- **Issue #13**: [Enhancement] Add Input Validation and Sanitization

### Dependency Updates
- **Issue #3**: [Dependencies] Update All Outdated Dependencies ✅ **PR #14 Created**

### Code Quality Improvements
- **Issue #4**: [Code Quality] Remove Python 2 Compatibility Code
- **Issue #5**: [Code Quality] Add Request Timeouts to HTTP Calls
- **Issue #10**: [Code Quality] Move Inline HTML to Jinja2 Templates
- **Issue #11**: [Enhancement] Implement Database Connection Pooling

### Closed/Duplicate Issues
- Issues #6-9: Closed as duplicates

---

## 📊 Execution Plan - 3 Phase Approach

### ✅ PHASE 1: Dependencies (COMPLETED)
**Status:** Pull Request Created
**Branch:** `feature/dependency-updates`
**PR:** #14
**Issue:** #3

**Completed Work:**
- Updated `requirements.txt` with modern versions:
  - Flask: 1.1.1 → 3.0.3
  - Werkzeug: 0.16.0 → 3.0.4
  - Jinja2: 2.10 → 3.1.4
  - peewee: 2.10.2 → 3.17.6
  - requests: 2.22.0 → 2.32.3
  - urllib3: 1.25.7 → 2.2.2
  - certifi: 2019.9.11 → 2024.8.30
- Added new security dependencies:
  - python-dotenv 1.0.1
  - flask-talisman 1.1.0
  - flask-wtf 1.2.1
- Created `MIGRATION_GUIDE.md`
- Committed and pushed to remote
- Created PR #14

**Next Steps:**
1. Review PR #14
2. Test in development environment
3. Merge to master
4. All other branches will rebase on updated master

---

### 🚀 PHASE 2: Security Fixes (READY TO START)
**Status:** Awaiting Phase 1 merge
**Approach:** 4 parallel sub-agents

#### Parallel Batch 1 (Security Focus):

**Agent 1 - Session Security**
- **Branch:** `feature/session-security`
- **Issue:** #1
- **Files:** `scan.py` (configuration)
- **Task:** Configure secure session cookies
- **Estimated Time:** 2 hours
- **Changes:**
  ```python
  app.config.update(
      SECRET_KEY=secrets.token_hex(32),
      SESSION_COOKIE_SECURE=True,
      SESSION_COOKIE_HTTPONLY=True,
      SESSION_COOKIE_SAMESITE='Lax',
      PERMANENT_SESSION_LIFETIME=600
  )
  ```

**Agent 2 - Environment Secrets**
- **Branch:** `feature/env-secrets`
- **Issue:** #12
- **Files:** `config.py`, `scan.py`, `.env.example`, `.gitignore`
- **Task:** Move secrets to environment variables
- **Estimated Time:** 3 hours
- **Changes:**
  - Install python-dotenv
  - Create `.env.example`
  - Update config loading
  - Update `.gitignore`

**Agent 3 - Python 2 Removal**
- **Branch:** `feature/remove-python2`
- **Issue:** #4
- **Files:** `scan.py:15-17`
- **Task:** Remove Python 2 compatibility code
- **Estimated Time:** 1 hour
- **Changes:**
  - Remove `raw_input` compatibility block
  - Verify no other Python 2 code exists

**Agent 4 - Path Validation**
- **Branch:** `feature/path-validation`
- **Issue:** #2
- **Files:** `plex.py`, `utils.py`, `scan.py`
- **Task:** Add path validation and sanitization
- **Estimated Time:** 4 hours
- **Changes:**
  - Use `werkzeug.utils.secure_filename()`
  - Validate file paths
  - Add path traversal protection

**Merge Order:** #3 → #12 → #1 → #2 → #4

---

### 🔧 PHASE 3: Code Quality (READY TO START)
**Status:** Awaiting Phase 1 & 2 completion
**Approach:** 4 parallel sub-agents

#### Parallel Batch 2 (Code Quality Focus):

**Agent 5 - Request Timeouts**
- **Branch:** `feature/request-timeouts`
- **Issue:** #5
- **Files:** `plex.py`, `scan.py`
- **Task:** Add timeouts to all HTTP requests
- **Estimated Time:** 3 hours
- **Changes:**
  ```python
  requests.get(url, timeout=(5, 30))
  requests.post(url, timeout=(5, 30))
  ```

**Agent 6 - Jinja Templates**
- **Branch:** `feature/jinja-templates`
- **Issue:** #10
- **Files:** `scan.py` (routes), `templates/*`
- **Task:** Move inline HTML to Jinja2 templates
- **Estimated Time:** 5 hours
- **Changes:**
  - Create `templates/` directory
  - Extract HTML to template files
  - Update routes to use `render_template()`

**Agent 7 - Database Pooling**
- **Branch:** `feature/db-pooling`
- **Issue:** #11
- **Files:** `db.py`, `config.py`
- **Task:** Implement connection pooling
- **Estimated Time:** 2 hours
- **Changes:**
  ```python
  from playhouse.pool import PooledSqliteDatabase
  db = PooledSqliteDatabase('my_app.db', max_connections=8)
  ```

**Agent 8 - Input Validation**
- **Branch:** `feature/input-validation`
- **Issue:** #13
- **Files:** `scan.py`, `utils.py`
- **Task:** Add comprehensive input validation
- **Estimated Time:** 6 hours
- **Changes:**
  - Create validation functions
  - Apply to all user inputs
  - Add error handling

**Merge Order:** #4 → #11 → #5 → #13 → #10

---

## 🔄 Dependency Matrix

```
Issue #3 (Dependencies) → COMPLETED ✅ PR #14
    ↓
    ├─ Issue #1 (Sessions) → No dependencies
    ├─ Issue #2 (Paths) → No dependencies
    ├─ Issue #4 (Python 2) → No dependencies
    ├─ Issue #5 (Timeouts) → Depends on #3
    ├─ Issue #10 (Templates) → Depends on #3
    ├─ Issue #11 (Pooling) → Depends on #3
    ├─ Issue #12 (Secrets) → No dependencies
    └─ Issue #13 (Validation) → No dependencies
```

---

## 🎯 Next Session: Launch Parallel Agents

### To Resume Work:

1. **Verify Phase 1 Status:**
   ```bash
   cd "/srv/dev-disk-by-uuid-8f70058d-bad5-42d5-9652-0584223ca05d/Config/AI Projects/plex_emby_jellyfin_autoscan"
   git status
   gh pr view 14
   ```

2. **Check if PR #14 is merged:**
   ```bash
   git checkout master
   git pull origin master
   ```

3. **Launch Phase 2 Parallel Agents:**

   **Option A: If PR #14 is merged:**
   ```
   Launch 4 sub-agents in parallel:
   - Agent 1: Issue #1 (Session Security)
   - Agent 2: Issue #12 (Environment Variables)
   - Agent 3: Issue #4 (Python 2 Removal)
   - Agent 4: Issue #2 (Path Validation)
   ```

   **Option B: If PR #14 still pending:**
   ```
   - Review and merge PR #14
   - Then proceed with parallel agents
   ```

4. **Launch Command:**
   ```
   "Launch 4 parallel agents to work on issues #1, #12, #4, and #2.
   Each agent should create its own branch, make changes, commit,
   and create a pull request."
   ```

---

## 📂 Repository Structure

```
plex_emby_jellyfin_autoscan/
├── .claude/
│   └── CLAUDE.md (this file)
├── scan.py (main Flask application)
├── plex.py (Plex integration)
├── db.py (database operations)
├── config.py (configuration)
├── utils.py (utilities)
├── threads.py (threading)
├── rclone.py (rclone integration)
├── requirements.txt (✅ UPDATED)
├── MIGRATION_GUIDE.md (✅ NEW)
└── requirements.txt.backup (backup of old requirements)
```

---

## 🔐 Security Vulnerabilities Identified

### Critical
1. **Command Injection** - `scan.py:127-134` using `os.system()` with user input
2. **Disabled SSL Verification** - Global `urllib3.disable_warnings()`
3. **Outdated Dependencies** - 5+ years old, multiple CVEs

### High
1. **Missing CSRF Protection** - No CSRF tokens on POST endpoints
2. **Insecure Session Cookies** - No secure flags set
3. **Missing Security Headers** - No HSTS, CSP, X-Frame-Options
4. **Path Traversal Risk** - No `secure_filename()` usage
5. **Plaintext Secrets** - API keys in config files
6. **No Input Validation** - User inputs not sanitized
7. **No Request Timeouts** - Risk of indefinite hangs

### Medium
1. **Hardcoded HTML** - XSS risk from inline HTML
2. **Python 2 Code** - Outdated compatibility code
3. **No Connection Pooling** - Performance impact

---

## 📈 Progress Tracking

- [x] Analyze codebase with Context7 MCP
- [x] Identify security vulnerabilities
- [x] Create 13 GitHub issues (9 active)
- [x] Create labels (security, priority levels, dependencies, code-quality)
- [x] Plan parallel work strategy
- [x] Phase 1: Update dependencies ✅
- [x] Create PR #14 ✅
- [ ] Phase 2: Security fixes (4 parallel agents)
- [ ] Phase 3: Code quality (4 parallel agents)
- [ ] Integration testing
- [ ] Documentation updates
- [ ] Final security audit

---

## ⏱️ Estimated Timeline

- **Phase 1 (Dependencies):** ✅ COMPLETE
- **Phase 2 (Security):** 1 day with 4 parallel agents
- **Phase 3 (Code Quality):** 1 day with 4 parallel agents
- **Testing/Integration:** 1 day
- **Total:** ~5 business days vs. ~15 days sequential

---

## 🛠️ Tools & Technologies

- **Language:** Python 3.11.2
- **Framework:** Flask 3.0.3 (updated from 1.1.1)
- **Database:** SQLite with Peewee ORM 3.17.6
- **HTTP Client:** requests 2.32.3
- **Git Workflow:** Feature branches + Pull Requests
- **CI/CD:** GitHub Actions (if configured)

---

## 📚 Key References

- Flask Security: https://flask.palletsprojects.com/en/latest/security/
- Peewee 3.x Changes: http://docs.peewee-orm.com/en/latest/peewee/changes.html
- OWASP Top 10: https://owasp.org/www-project-top-ten/
- Python Security Best Practices: https://docs.python.org/3/library/security_warnings.html

---

## 💡 Notes for Next Session

1. **Before launching parallel agents:**
   - Confirm PR #14 status
   - Ensure master branch is up-to-date
   - Verify all agents have fresh branches from master

2. **Agent coordination:**
   - Each agent works independently
   - No shared files between agents in same batch
   - Sequential merging to avoid conflicts

3. **Testing strategy:**
   - Test each PR individually
   - Integration test after each merge
   - Full regression test after Phase 3

4. **Priority order:**
   - Security fixes before code quality
   - Critical issues before medium priority
   - Dependency updates must be first (already done ✅)

---

**Resume Point:** Launch 4 parallel sub-agents for Phase 2 security fixes after PR #14 is reviewed/merged.

🤖 Generated with Claude Code
