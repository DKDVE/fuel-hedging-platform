# 🔐 SECURITY CHECKLIST - Fuel Hedging Platform

**Version**: 1.0  
**Last Updated**: March 3, 2026  
**Purpose**: Ensure security best practices before committing code or deploying to production

---

## 📋 TABLE OF CONTENTS

1. [Pre-Commit Checklist](#pre-commit-checklist)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Production Checklist](#production-checklist)
4. [Ongoing Security](#ongoing-security)
5. [Incident Response](#incident-response)
6. [Security Tools](#security-tools)

---

## ✅ PRE-COMMIT CHECKLIST

**Complete BEFORE your first `git push` and BEFORE every commit with sensitive changes.**

### **1. Environment Files**

- [ ] `.env` file is in `.gitignore`
  ```bash
  # Verify
  git check-ignore -v .env
  # Should output: .gitignore:X:.env    .env
  ```

- [ ] `.env.local` is in `.gitignore` (if used)

- [ ] `.env.production` is in `.gitignore` (if used)

- [ ] `frontend/.env` is in `.gitignore`

- [ ] No `.env` files in git history:
  ```bash
  git log --all --full-history -- "*/.env*"
  # Should return empty
  ```

### **2. Secrets & Credentials**

- [ ] No API keys in code files:
  ```bash
  # Search for common patterns
  grep -r "API_KEY\s*=\s*['\"]" --include="*.py" --include="*.ts" --include="*.tsx"
  # Should return empty or only template files
  ```

- [ ] No passwords in code:
  ```bash
  grep -ri "password\s*=\s*['\"]" --include="*.py" --include="*.ts" --exclude="*test*"
  ```

- [ ] No tokens in code:
  ```bash
  grep -ri "token\s*=\s*['\"]" --include="*.py" --include="*.ts"
  ```

- [ ] No database connection strings in code:
  ```bash
  grep -ri "postgresql://" --include="*.py" --exclude="*.md"
  ```

- [ ] All secrets loaded from environment variables:
  ```python
  # ✅ GOOD
  api_key = os.getenv("EIA_API_KEY")
  api_key = config.EIA_API_KEY
  
  # ❌ BAD
  api_key = "abc123xyz"
  ```

### **3. Detect-Secrets Tool**

- [ ] `detect-secrets` pre-commit hook installed:
  ```bash
  pre-commit install
  ```

- [ ] Baseline scan run:
  ```bash
  detect-secrets scan > .secrets.baseline
  ```

- [ ] Baseline committed:
  ```bash
  git add .secrets.baseline
  git commit -m "Add detect-secrets baseline"
  ```

- [ ] Pre-commit hook triggers on commit:
  ```bash
  git commit -m "Test"
  # Should run detect-secrets-hook
  ```

### **4. Git History Clean**

- [ ] No secrets in git history:
  ```bash
  # Install truffleHog (optional but recommended)
  pip install truffleHog
  
  # Scan entire git history
  truffleHog --regex --entropy=True file://$(pwd)
  ```

- [ ] If secrets found in history, use BFG Repo-Cleaner:
  ```bash
  # Install BFG
  brew install bfg  # macOS
  # OR download from https://rtyley.github.io/bfg-repo-cleaner/
  
  # Remove secrets
  bfg --replace-text passwords.txt
  git reflog expire --expire=now --all
  git gc --prune=now --aggressive
  ```

### **5. Dependencies**

- [ ] No known vulnerabilities in Python dependencies:
  ```bash
  pip install pip-audit
  pip-audit --requirement python_engine/requirements.txt
  ```

- [ ] No known vulnerabilities in Node dependencies:
  ```bash
  cd frontend
  npm audit --audit-level=high
  ```

- [ ] All dependencies pinned to exact versions:
  ```bash
  # Python (requirements.txt)
  # ✅ GOOD: fastapi==0.110.0
  # ❌ BAD:  fastapi>=0.110.0
  
  # Node (package.json)
  # ✅ GOOD: "react": "18.2.0"
  # ❌ BAD:  "react": "^18.2.0"
  ```

### **6. Code Review**

- [ ] All SQL queries use parameterized queries (SQLAlchemy ORM):
  ```python
  # ✅ GOOD (SQLAlchemy ORM)
  users = session.query(User).filter(User.email == email).all()
  
  # ✅ GOOD (SQLAlchemy Core with params)
  result = connection.execute(
      text("SELECT * FROM users WHERE email = :email"),
      {"email": email}
  )
  
  # ❌ BAD (SQL injection vulnerable)
  query = f"SELECT * FROM users WHERE email = '{email}'"
  result = connection.execute(query)
  ```

- [ ] All user inputs validated with Pydantic:
  ```python
  # ✅ GOOD
  class LoginRequest(BaseModel):
      email: str = Field(..., regex=r"^[\w\.-]+@[\w\.-]+\.\w+$")
      password: str = Field(..., min_length=8)
      model_config = ConfigDict(extra='forbid')
  
  # ❌ BAD (no validation)
  def login(email: str, password: str):
      ...
  ```

- [ ] No `eval()` or `exec()` usage:
  ```bash
  grep -r "eval(" --include="*.py"
  grep -r "exec(" --include="*.py"
  # Should return empty
  ```

- [ ] No shell command injection:
  ```python
  # ✅ GOOD
  subprocess.run(["ls", "-l", user_input], shell=False)
  
  # ❌ BAD
  os.system(f"ls -l {user_input}")
  subprocess.run(f"ls -l {user_input}", shell=True)
  ```

### **7. Frontend Security**

- [ ] No secrets in frontend code:
  ```bash
  grep -r "API_KEY" frontend/src/
  # Should return empty or only import.meta.env references
  ```

- [ ] Sensitive data never in localStorage:
  ```typescript
  // ❌ BAD
  localStorage.setItem('access_token', token);
  
  // ✅ GOOD (httpOnly cookies set by backend)
  // No manual token storage needed
  ```

- [ ] No `dangerouslySetInnerHTML` without sanitization:
  ```bash
  grep -r "dangerouslySetInnerHTML" frontend/src/
  # If found, verify content is sanitized with DOMPurify
  ```

---

## 🚀 PRE-DEPLOYMENT CHECKLIST

**Complete BEFORE deploying to production for the first time.**

### **1. GitHub Secrets**

- [ ] All 10 GitHub Secrets added:
  - [ ] `RENDER_DEPLOY_HOOK_API`
  - [ ] `RENDER_DEPLOY_HOOK_N8N`
  - [ ] `RENDER_DATABASE_URL`
  - [ ] `VITE_API_BASE_URL`
  - [ ] `VITE_WS_URL`
  - [ ] `EIA_API_KEY`
  - [ ] `CME_API_KEY`
  - [ ] `OPENAI_API_KEY`
  - [ ] `SLACK_WEBHOOK_URL`
  - [ ] `GH_PAT`

- [ ] GitHub Secrets not exposed in logs:
  ```yaml
  # ✅ GOOD (secrets are masked)
  - name: Deploy
    run: curl ${{ secrets.RENDER_DEPLOY_HOOK_API }}
  
  # ❌ BAD (secret would be visible in logs)
  - name: Deploy
    run: echo ${{ secrets.RENDER_DEPLOY_HOOK_API }}
  ```

### **2. Render Environment Variables**

- [ ] All required env vars set in Render dashboard
  - [ ] `DATABASE_URL` (from database connection)
  - [ ] `REDIS_URL` (from Redis connection)
  - [ ] `JWT_SECRET_KEY` (generated, never reused)
  - [ ] `JWT_ALGORITHM` = `HS256`
  - [ ] `ACCESS_TOKEN_EXPIRE_MINUTES` = `30`
  - [ ] `REFRESH_TOKEN_EXPIRE_DAYS` = `7`
  - [ ] `EIA_API_KEY`
  - [ ] `CME_API_KEY`
  - [ ] `OPENAI_API_KEY`
  - [ ] `N8N_WEBHOOK_SECRET` (generated, never reused)
  - [ ] `FRONTEND_ORIGIN` (exact URL, no wildcard)
  - [ ] `ENVIRONMENT` = `production`
  - [ ] `LOG_LEVEL` = `INFO`

- [ ] Env vars marked as secret (Render hides values in logs)

- [ ] `render.yaml` uses `sync: false` for all secrets:
  ```yaml
  # ✅ GOOD
  - key: JWT_SECRET_KEY
    sync: false  # Set manually in dashboard
  
  # ❌ BAD
  - key: JWT_SECRET_KEY
    value: hard-coded-secret  # Never do this
  ```

### **3. JWT Configuration**

- [ ] `JWT_SECRET_KEY` generated with strong entropy:
  ```bash
  openssl rand -hex 32
  # Output: 64 hex characters (256 bits)
  ```

- [ ] `JWT_SECRET_KEY` is unique (never reused from another project)

- [ ] `JWT_SECRET_KEY` is different between development and production

- [ ] `JWT_ALGORITHM` = `HS256` (not `none` or `HS512`)

- [ ] Token expiration configured:
  - Access token: 30 minutes
  - Refresh token: 7 days

### **4. N8N Configuration**

- [ ] `N8N_WEBHOOK_SECRET` generated:
  ```bash
  openssl rand -hex 32
  ```

- [ ] `N8N_WEBHOOK_SECRET` same in both API and N8N services

- [ ] `N8N_BASIC_AUTH_ACTIVE` = `true`

- [ ] `N8N_BASIC_AUTH_PASSWORD` is strong (16+ characters, mixed case, numbers, symbols)

- [ ] N8N UI accessible only with basic auth

### **5. CORS Configuration**

- [ ] `FRONTEND_ORIGIN` is exact URL (not wildcard):
  ```python
  # ✅ GOOD
  FRONTEND_ORIGIN = "https://username.github.io"
  
  # ❌ BAD
  FRONTEND_ORIGIN = "*"
  FRONTEND_ORIGIN = "https://*.github.io"
  ```

- [ ] `allow_credentials=True` in CORS middleware

- [ ] No additional origins in production:
  ```python
  # ✅ GOOD
  app.add_middleware(
      CORSMiddleware,
      allow_origins=[config.FRONTEND_ORIGIN],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```

### **6. Security Headers**

- [ ] Security headers middleware enabled in `main.py`:
  ```python
  # Should include:
  # - Strict-Transport-Security
  # - X-Content-Type-Options: nosniff
  # - X-Frame-Options: DENY
  # - Content-Security-Policy
  ```

- [ ] CSP policy configured:
  ```
  default-src 'self';
  connect-src 'self' wss://hedge-api.onrender.com;
  script-src 'self' 'unsafe-inline';
  style-src 'self' 'unsafe-inline';
  img-src 'self' data: https:;
  ```

### **7. Code Owners**

- [ ] `.github/CODEOWNERS` file created

- [ ] Critical files protected:
  - [ ] `python_engine/app/constants.py`
  - [ ] `python_engine/app/analytics/`
  - [ ] `.cursorrules`
  - [ ] `render.yaml`
  - [ ] `.github/workflows/`
  - [ ] `python_engine/app/auth/`

- [ ] Branch protection rules enabled:
  - [ ] Require pull request reviews
  - [ ] Require code owner review
  - [ ] Require status checks to pass
  - [ ] Require branches to be up to date

---

## 🏭 PRODUCTION CHECKLIST

**Complete AFTER successful deployment, BEFORE going live with real data.**

### **1. Database Security**

- [ ] Database backups enabled (Render Starter plan includes automatic backups)

- [ ] Database accessible only via internal Render network (not exposed publicly)

- [ ] Database connection uses SSL:
  ```bash
  psql "$DATABASE_URL?sslmode=require"
  ```

- [ ] Strong database password (auto-generated by Render)

- [ ] Database user has minimum required permissions (no superuser)

### **2. API Security**

- [ ] Rate limiting configured and working:
  ```bash
  # Test rate limit
  for i in {1..10}; do
    curl -X POST https://hedge-api.onrender.com/api/v1/auth/login \
      -H "Content-Type: application/json" \
      -d '{"email":"test@test.com","password":"wrong"}'
  done
  # Should return 429 Too Many Requests after 5 attempts
  ```

- [ ] API documentation disabled in production:
  ```bash
  curl https://hedge-api.onrender.com/docs
  # Should return 404 or redirect
  ```

- [ ] Health endpoint does not expose sensitive info:
  ```bash
  curl https://hedge-api.onrender.com/api/v1/health
  # Should NOT include: database credentials, API keys, internal IPs
  ```

- [ ] Error responses do not expose stack traces:
  ```bash
  curl https://hedge-api.onrender.com/api/v1/nonexistent
  # Should return generic error message, not full stack trace
  ```

### **3. Authentication**

- [ ] Login endpoint rate limited (5 attempts per minute):
  ```bash
  # Test with invalid credentials 6 times
  # 6th attempt should return 429
  ```

- [ ] Cookies are httpOnly + Secure + SameSite=Strict:
  ```bash
  curl -v https://hedge-api.onrender.com/api/v1/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@airline.com","password":"Admin123!"}'
  # Check Set-Cookie header for: HttpOnly; Secure; SameSite=Strict
  ```

- [ ] Access tokens expire after 30 minutes

- [ ] Refresh tokens expire after 7 days

- [ ] Logout clears all cookies

### **4. Authorization**

- [ ] Role-based access control working:
  - [ ] Analyst can view Dashboard, Recommendations, Analytics, Positions
  - [ ] Analyst cannot view Audit Log or Settings
  - [ ] Risk Manager can approve recommendations
  - [ ] CFO can view Audit Log
  - [ ] Admin can access all pages

- [ ] API endpoints enforce permissions:
  ```bash
  # Log in as analyst
  TOKEN="<analyst-token>"
  
  # Try to access admin endpoint (should fail with 403)
  curl https://hedge-api.onrender.com/api/v1/config/users \
    -H "Authorization: Bearer $TOKEN"
  # Expected: {"detail": "Insufficient permissions", "error_code": "insufficient_permissions"}
  ```

### **5. Data Protection**

- [ ] All sensitive data encrypted at rest (Render manages disk encryption)

- [ ] All connections use HTTPS/WSS (not HTTP/WS)

- [ ] No sensitive data in logs:
  ```bash
  # Check Render logs for:
  # - Passwords (should be "***")
  # - API keys (should be "***")
  # - JWT tokens (should be "***")
  ```

- [ ] Audit log captures all state-changing actions:
  ```sql
  SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 10;
  # Should include: login, logout, recommendation_decision, config_update, etc.
  ```

### **6. Monitoring & Alerting**

- [ ] Slack notifications working:
  ```bash
  # Test webhook
  curl -X POST $SLACK_WEBHOOK_URL \
    -H "Content-Type: application/json" \
    -d '{"text": "Test alert from fuel hedging platform"}'
  ```

- [ ] Nightly validation runs Mon-Fri at 23:00 UTC

- [ ] Nightly validation posts to Slack (success or failure)

- [ ] LSTM retrain runs Sunday at 02:00 UTC

- [ ] Sentry configured (optional but recommended):
  ```python
  import sentry_sdk
  sentry_sdk.init(dsn=config.SENTRY_DSN)
  ```

### **7. Incident Response**

- [ ] Incident response plan documented (see `RUNBOOK.md`)

- [ ] On-call rotation defined

- [ ] Emergency contacts documented

- [ ] Rollback procedure tested

- [ ] Database restore procedure tested

---

## 🔄 ONGOING SECURITY

**Regular maintenance to keep the platform secure.**

### **Weekly**

- [ ] Review audit log for suspicious activity:
  ```sql
  SELECT user_id, action, resource_type, COUNT(*)
  FROM audit_log
  WHERE created_at > NOW() - INTERVAL '7 days'
  GROUP BY user_id, action, resource_type
  ORDER BY COUNT(*) DESC;
  ```

- [ ] Check for failed login attempts:
  ```sql
  SELECT ip_address, COUNT(*)
  FROM audit_log
  WHERE action = 'login_failed'
    AND created_at > NOW() - INTERVAL '7 days'
  GROUP BY ip_address
  HAVING COUNT(*) > 10;
  ```

### **Monthly**

- [ ] Update dependencies:
  ```bash
  # Python
  pip list --outdated
  pip install --upgrade <package>
  
  # Node
  npm outdated
  npm update
  ```

- [ ] Run security scans:
  ```bash
  # Python
  pip-audit
  
  # Node
  npm audit
  
  # Fix vulnerabilities
  npm audit fix
  ```

- [ ] Review user access:
  - Deactivate users who left company
  - Adjust roles for users with changed responsibilities
  - Remove test users

- [ ] Rotate secrets (optional, for high-security environments):
  - Generate new `JWT_SECRET_KEY`
  - Update in Render dashboard
  - All users forced to re-login

### **Quarterly**

- [ ] Security audit:
  - Review all GitHub Secrets
  - Review all Render environment variables
  - Review API permissions
  - Review database permissions

- [ ] Penetration testing (optional):
  - Hire external security firm
  - Test for OWASP Top 10 vulnerabilities

- [ ] Update this checklist based on:
  - New threats discovered
  - New features added
  - Lessons learned from incidents

---

## 🚨 INCIDENT RESPONSE

**If a security incident occurs:**

### **Immediate Actions (< 5 minutes)**

1. **Stop the breach**:
   - If API compromised: Pause Render service
   - If credentials leaked: Rotate immediately
   - If database compromised: Disconnect database

2. **Notify stakeholders**:
   - Post to #fuel-hedging-alerts Slack channel
   - Notify security team
   - Notify management

3. **Preserve evidence**:
   - Export logs before they rotate
   - Take screenshots
   - Document timeline

### **Investigation (< 1 hour)**

1. **Identify root cause**:
   - What was compromised?
   - How did attacker gain access?
   - What data was accessed?

2. **Assess impact**:
   - Which users affected?
   - What data was stolen?
   - How long was access active?

3. **Check audit log**:
   ```sql
   SELECT * FROM audit_log
   WHERE created_at > '<incident-time>'
   ORDER BY created_at;
   ```

### **Remediation (< 24 hours)**

1. **Fix vulnerability**:
   - Patch code
   - Rotate all secrets
   - Update permissions

2. **Deploy fix**:
   - Test thoroughly
   - Deploy to production
   - Verify fix effective

3. **Notify affected users** (if applicable):
   - Email notification
   - Password reset required
   - Explain what happened and what you did

### **Post-Incident (< 1 week)**

1. **Post-mortem**:
   - Document timeline
   - Document root cause
   - Document lessons learned
   - Update security checklist

2. **Implement improvements**:
   - Additional monitoring
   - Additional tests
   - Additional training

3. **Regulatory reporting** (if required):
   - GDPR breach notification (< 72 hours if EU users)
   - SOC 2 incident report (if certified)

---

## 🛠️ SECURITY TOOLS

### **Required Tools**

| Tool | Purpose | Installation |
|------|---------|--------------|
| `detect-secrets` | Prevent secrets in git | `pip install detect-secrets` |
| `pip-audit` | Python dependency scanning | `pip install pip-audit` |
| `npm audit` | Node dependency scanning | Built into npm |
| `pre-commit` | Git hooks | `pip install pre-commit` |

### **Recommended Tools**

| Tool | Purpose | Installation |
|------|---------|--------------|
| `truffleHog` | Git history secret scanning | `pip install truffleHog` |
| `BFG Repo-Cleaner` | Remove secrets from git history | Download from rtyley.github.io |
| `act` | Test GitHub Actions locally | `brew install act` |
| Sentry | Error tracking & monitoring | sentry.io |

### **Optional Tools (Enterprise)**

| Tool | Purpose | Cost |
|------|---------|------|
| Snyk | Continuous security monitoring | Free tier available |
| Dependabot | Automated dependency updates | Free (GitHub feature) |
| SonarQube | Code quality & security analysis | Free Community Edition |
| Burp Suite | Web application security testing | $399/year |

---

## 📊 SECURITY METRICS

Track these metrics to measure security posture:

| Metric | Target | Measurement |
|--------|--------|-------------|
| Known vulnerabilities | 0 HIGH/CRITICAL | `pip-audit` + `npm audit` |
| Secrets in git | 0 | `detect-secrets` |
| Failed login attempts | < 50/day | Audit log query |
| API error rate | < 1% | Render metrics |
| Security incidents | 0/month | Incident log |
| Mean time to patch | < 24 hours | Incident timeline |
| Dependency freshness | < 30 days old | `pip list --outdated` |

---

## ✅ FINAL PRE-LAUNCH CHECKLIST

**Complete this checklist immediately before going live:**

- [ ] All items in "Pre-Commit Checklist" ✅
- [ ] All items in "Pre-Deployment Checklist" ✅
- [ ] All items in "Production Checklist" ✅
- [ ] Default admin password changed
- [ ] Test accounts removed
- [ ] Backup and restore tested
- [ ] Incident response plan reviewed
- [ ] Team trained on security procedures
- [ ] Security contact information documented
- [ ] This checklist reviewed and signed off by security team

**Sign-off**:
- Developer: _____________ Date: _______
- Security Lead: _____________ Date: _______
- Platform Admin: _____________ Date: _______

---

## 📚 REFERENCES

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **CWE Top 25**: https://cwe.mitre.org/top25/
- **NIST Cybersecurity Framework**: https://www.nist.gov/cyberframework
- **FastAPI Security**: https://fastapi.tiangolo.com/tutorial/security/
- **Render Security**: https://render.com/docs/security

---

**Security Checklist Version**: 1.0  
**Last Updated**: March 3, 2026  
**Next Review**: April 1, 2026 (or after any security incident)

---

## 📞 SECURITY CONTACTS

- **Security Team**: security@airline.com
- **Platform Admin**: platform-admin@airline.com
- **Emergency**: PagerDuty rotation
- **Render Support**: https://render.com/support

---

**END OF SECURITY CHECKLIST**
