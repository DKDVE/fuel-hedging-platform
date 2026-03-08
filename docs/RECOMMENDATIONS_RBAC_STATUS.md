# Recommendations Page Improvements - Implementation Status

**Date**: March 3, 2026  
**Status**: 🟡 **IN PROGRESS** (3/13 tasks complete)

---

## ✅ Completed Tasks

### 1. Plain-English Narrative Layer (`frontend/src/lib/recommendationNarrative.ts`)
- ✅ `generateExecutiveSummary()` - Converts optimal_hr to plain English
- ✅ `generateRiskNarrative()` - Agent findings in human language
- ✅ `generateActionStatement()` - Approve/Reject/Defer implications
- ✅ `formatInstrumentMixNarrative()` - Instrument allocation description
- ✅ `generateAgentPlainEnglish()` - Per-agent plain English summaries

### 2. Backend RBAC (`python_engine/app/auth/permissions.py`)
- ✅ Permission enum with 9 permission types
- ✅ ROLE_PERMISSIONS mapping (analyst, risk_manager, cfo, admin)
- ✅ `require_permission()` FastAPI dependency
- ✅ `require_any_permission()` for multi-access endpoints
- ✅ `get_current_user()` dependency in `app/auth.py`

### 3. Frontend Permissions (`frontend/src/constants/permissions.ts`)
- ✅ Permission and UserRole types
- ✅ ROLE_PERMISSIONS mapping (mirrors backend)
- ✅ ROLE_LABELS for human-readable role names
- ✅ Helper functions: `hasPermission()`, `hasAnyPermission()`, etc.

---

## 🔄 Remaining Tasks

### CRITICAL: Apply Backend Permissions (Blocks Testing)

Need to update ALL routers with `require_permission()`:

**Recommendations Router** (`python_engine/app/routers/recommendations.py`):
```python
from app.auth.permissions import Permission, require_permission

@router.get("/recommendations")
async def list_recommendations(
    user: UserResponse = Depends(require_permission(Permission.READ_ANALYTICS))
):
    ...

@router.get("/recommendations/pending")
async def pending_recommendations(
    user: UserResponse = Depends(require_permission(Permission.APPROVE_REC))
):
    ...

@router.patch("/recommendations/{id}/decision")
async def decide_recommendation(
    user: UserResponse = Depends(require_permission(Permission.APPROVE_REC))
):
    ...
```

**Analytics Router** - Add `require_permission(Permission.READ_ANALYTICS)` to ALL GET endpoints  
**Positions Router** - Add `require_permission(Permission.READ_POSITIONS)` to ALL endpoints  
**Audit Router** - Add `require_permission(Permission.READ_AUDIT)` to ALL endpoints  
**Config Router** - Mixed permissions (READ_ANALYTICS for GET, EDIT_CONFIG for PATCH, MANAGE_USERS for user endpoints)

### CRITICAL: Update mock_backend.py with RBAC

Add to `mock_backend.py`:
```python
from jose import jwt, JWTError
from datetime import datetime, timedelta

MOCK_USERS = {
    "analyst@airline.com": {"role": "analyst", "password": "analyst123"},
    "risk@airline.com": {"role": "risk_manager", "password": "risk123"},
    "cfo@airline.com": {"role": "cfo", "password": "cfo123"},
    "admin@airline.com": {"role": "admin", "password": "admin123"},
    "test@airline.com": {"role": "risk_manager", "password": "testpass123"},
}

ROLE_PERMISSIONS = {
    'analyst': {'read:analytics', 'read:positions'},
    'risk_manager': {'read:analytics', 'read:positions', 'read:audit', 'approve:recommendation', 'export:data'},
    'cfo': {'read:analytics', 'read:positions', 'read:audit', 'approve:recommendation', 'escalate:recommendation', 'export:data'},
    'admin': {'read:analytics', 'read:positions', 'read:audit', 'approve:recommendation', 'escalate:recommendation', 'edit:config', 'manage:users', 'trigger:pipeline', 'export:data'},
}

def check_permission(request: Request, required_permission: str):
    """Check if user has required permission. Raise 403 if not."""
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        payload = jwt.decode(token, "dev-secret-key-change-in-production", algorithms=["HS256"])
        role = payload.get("role")
        permissions = ROLE_PERMISSIONS.get(role, set())
        
        if required_permission not in permissions:
            raise HTTPException(
                status_code=403,
                detail={
                    "detail": f"Your role ({role}) does not have permission to perform this action.",
                    "error_code": "insufficient_permissions",
                    "required_permission": required_permission
                }
            )
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Then add check_permission() to EVERY protected endpoint
```

### Frontend: Update AuthContext

**File**: `frontend/src/contexts/AuthContext.tsx`

Add to interface:
```typescript
interface AuthContextValue {
  user: UserResponse | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  permissions: Set<Permission>;       // ADD THIS
  hasPermission: (p: Permission) => boolean;  // ADD THIS
  isRole: (role: UserRole) => boolean;        // ADD THIS
}
```

Compute permissions from user role:
```typescript
const permissions = user ? getRolePermissions(user.role as UserRole) : new Set();
const hasPermission = (p: Permission) => permissions.has(p);
const isRole = (role: UserRole) => user?.role === role;
```

### Frontend: Create Unauthorized Page

**File**: `frontend/src/pages/Unauthorized.tsx`

Clean 403 page with:
- Lock icon
- "Access Restricted" heading
- "Your role ({role}) does not have access to this area."
- "Back to Dashboard" button

### Frontend: Update ProtectedRoute

**File**: `frontend/src/components/layout/ProtectedRoute.tsx`

```typescript
interface ProtectedRouteProps {
  children: ReactElement;
  roles?: UserRole[];
  permissions?: Permission[];
  redirectTo?: string;
  unauthorizedMessage?: string;
}

// Check both roles AND permissions
// Redirect to /unauthorized if fails
```

### Frontend: Apply RBAC to Sidebar

**File**: `frontend/src/components/layout/Sidebar.tsx`

Conditional rendering for each nav item:
```tsx
{hasPermission('read:analytics') && (
  <NavItem to="/recommendations">Recommendations</NavItem>
)}
{hasPermission('read:positions') && (
  <NavItem to="/positions">Positions</NavItem>
)}
{hasPermission('read:audit') && (
  <NavItem to="/audit">Audit Log</NavItem>
)}
{(hasPermission('edit:config') || hasPermission('manage:users')) && (
  <NavItem to="/settings">Settings</NavItem>
)}
```

### Frontend: Update Recommendations Page

**File**: `frontend/src/pages/RecommendationsPage.tsx` (or wherever it lives)

MASSIVE UPDATE REQUIRED:

1. **Add Summary/Detail Toggle**
```tsx
const [viewMode, setViewMode] = useState<'summary' | 'detail'>(
  isRole('analyst') || isRole('admin') ? 'detail' : 'summary'
);
```

2. **Summary View** - Use `recommendationNarrative.ts` functions:
```tsx
const summary = generateExecutiveSummary(recommendation);
const risks = generateRiskNarrative(recommendation.agent_outputs);
const actions = generateActionStatement(recommendation);

// Show urgency banner if needed
{summary.urgency !== 'routine' && <UrgencyBanner />}

// Show headline and context
<h2>{summary.headline}</h2>
<p>{summary.context}</p>

// Show instrument mix narrative
<p>{formatInstrumentMixNarrative(recommendation.instrument_mix)}</p>

// Show confidence badge with tooltip
<Badge confidence={summary.confidence} reason={summary.confidence_reason} />

// Show risk findings
{risks.map(risk => (
  <RiskCard key={risk.agent_label} {...risk} />
))}

// Show action statements
<div>
  <h3>If you approve:</h3>
  <p>{actions.approve_means}</p>
  
  <h3>If you reject:</h3>
  <p>{actions.reject_means}</p>
  
  <h3>If you defer:</h3>
  <p>{actions.defer_means}</p>
  
  <Note>{actions.deadline_context}</Note>
</div>
```

3. **Detail View** - Keep existing technical metrics

4. **Conditional Approval Buttons**:
```tsx
{hasPermission('approve:recommendation') ? (
  <>
    <Button onClick={approve}>✓ Approve This Recommendation</Button>
    <Button onClick={reject}>✗ Reject</Button>
    <Button onClick={defer}>⏸ Defer 24 Hours</Button>
  </>
) : (
  <Banner>
    You have read access to this recommendation. Contact your Risk Manager to approve.
  </Banner>
)}

{hasPermission('escalate:recommendation') && (
  <Button onClick={escalate}>⬆ Escalate to CFO</Button>
)}
```

### Frontend: Add Role Badge to Header

**File**: `frontend/src/components/layout/Header.tsx` (or Navbar)

```tsx
import { getRoleLabel } from '@/constants/permissions';

<div className="flex items-center gap-2">
  <span>{user.full_name}</span>
  <Badge>{getRoleLabel(user.role as UserRole)}</Badge>
</div>
```

---

## 📋 Acceptance Criteria Checklist

### Real-Time Data (Already Tested)
- [x] Price chart loads with 100 historical ticks
- [x] DataSourceBadge shows "Simulated"
- [x] Counter resets every 2s
- [x] Auto-reconnect works

### Plain-English Recommendations (Not Yet Tested)
- [ ] CFO/risk_manager default to Summary view
- [ ] Analyst/admin default to Detail view
- [ ] Headline matches optimal_hr logic
- [ ] Agent labels are human-readable (not agent_id)
- [ ] "If you approve/reject/defer" paragraphs visible
- [ ] Technical Detail view still shows all metrics
- [ ] Plain-English sub-labels under metrics in Detail

### RBAC (Not Yet Testable - Backend Not Applied)
- [ ] analyst@airline.com: No Audit Log or Settings in sidebar
- [ ] analyst visits /audit: redirect to 403 page
- [ ] analyst on /recommendations: NO approval buttons
- [ ] Read-only banner for analyst: "Contact your Risk Manager"
- [ ] risk_manager: Audit Log visible, Settings NOT visible
- [ ] cfo: Escalate button visible, Settings NOT visible
- [ ] admin: ALL pages and buttons visible
- [ ] 403 returns correct JSON with error_code
- [ ] Role badge visible in header for all users
- [ ] No TypeScript errors

---

## 🚀 Next Steps

**PRIORITY 1**: Apply backend permissions to all routers  
**PRIORITY 2**: Update mock_backend.py with RBAC  
**PRIORITY 3**: Update AuthContext with permissions  
**PRIORITY 4**: Create Unauthorized page  
**PRIORITY 5**: Update ProtectedRoute  
**PRIORITY 6**: Apply RBAC to Sidebar  
**PRIORITY 7**: Massive update to Recommendations page  
**PRIORITY 8**: Add role badge to header  
**PRIORITY 9**: Full testing of all acceptance criteria

---

## 📝 Files Modified So Far

### Created:
1. `frontend/src/lib/recommendationNarrative.ts` ✅
2. `python_engine/app/auth/permissions.py` ✅
3. `frontend/src/constants/permissions.ts` ✅

### Modified:
1. `python_engine/app/auth.py` ✅ (added `get_current_user()`)

### Still Need to Modify:
1. All backend routers (recommendations, analytics, positions, audit, config)
2. `mock_backend.py`
3. `frontend/src/contexts/AuthContext.tsx`
4. `frontend/src/hooks/usePermissions.ts`
5. `frontend/src/pages/Unauthorized.tsx` (create)
6. `frontend/src/components/layout/ProtectedRoute.tsx`
7. `frontend/src/components/layout/Sidebar.tsx`
8. `frontend/src/pages/RecommendationsPage.tsx` (or wherever recommendations live)
9. `frontend/src/components/layout/Header.tsx`

---

**Current Status**: Foundation complete. Need to apply RBAC across all backend and frontend components before testing.

*Last Updated: March 3, 2026*
