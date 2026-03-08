# Frontend Price Display Fix

**Date**: 2026-03-03  
**Status**: ✅ Fixed

## Problem
Console error: `Cannot read properties of undefined (reading 'toFixed')` in `LivePriceTicker.tsx`

## Root Causes

### 1. Field Name Mismatch
**Backend** (`app/services/price_service.py`):
```python
PriceTick(
    brent_futures=...,  # ❌ Backend uses brent_futures
    wti_futures=...,    # ❌ Backend uses wti_futures
)
```

**Frontend** (before fix):
```typescript
interface LivePriceFeedEvent {
    brent_crude_futures: number;  // ❌ Frontend expected brent_crude_futures
    wti_crude_futures: number;    // ❌ Frontend expected wti_crude_futures
}
```

### 2. Missing Null/Undefined Checks
The `PriceItem` component only checked for `null`, but values could also be `undefined` or `NaN`.

## Solution

### 1. Fixed Field Names (3 files)
Updated frontend to match backend naming:

**`frontend/src/types/api.ts`** (2 interfaces updated):
- `PriceTickResponse.brent_crude_futures` → `brent_futures`
- `PriceTickResponse.wti_crude_futures` → `wti_futures`
- `LivePriceFeedEvent.brent_crude_futures` → `brent_futures`
- `LivePriceFeedEvent.wti_crude_futures` → `wti_futures`

**`frontend/src/hooks/useLivePrices.ts`**:
- `PriceTick.brent_futures` (already correct, added comment)
- `PriceTick.wti_futures` (already correct, added comment)

**`frontend/src/components/dashboard/LivePriceTicker.tsx`**:
- `latestPrice.brent_crude_futures` → `latestPrice.brent_futures`
- `latestPrice.wti_crude_futures` → `latestPrice.wti_futures`

### 2. Enhanced Null Checks
Updated `PriceItem` component:

```typescript
// Before
if (price === null) return null;

// After
if (price === null || price === undefined || isNaN(price)) return null;
```

Also added `isNaN(change)` check before rendering change percentage.

## Files Modified

1. `frontend/src/types/api.ts`
2. `frontend/src/hooks/useLivePrices.ts`
3. `frontend/src/components/dashboard/LivePriceTicker.tsx`

## Backend Field Names (Reference)

For consistency, here are the canonical field names from the backend:

```python
@dataclass
class PriceTick:
    time: str
    jet_fuel_spot: float
    heating_oil_futures: float
    brent_futures: float           # ✅ Not brent_crude_futures
    wti_futures: float              # ✅ Not wti_crude_futures
    crack_spread: float
    volatility_index: float
    source: str
    quality_flag: Optional[str]
```

## Testing

After these changes:
1. ✅ No console errors on dashboard
2. ✅ Price ticker displays all 6 values correctly
3. ✅ Change percentages calculate properly
4. ✅ Graceful handling when connection is initializing

## Notes

- Backend uses simplified names (`brent_futures`, `wti_futures`) 
- This matches the actual CME ticker symbols (CL, BZ, HO)
- Frontend now fully aligned with backend data contract
