# **ADR 0001: Dynamic USD-to-HBAR Test Account Funding**

**Date:** 2025-12-12
**Status:** Accepted
**Context:** Python test suite for Hedera Agent Kit requires reliable test account funding that remains stable across
HBAR price fluctuations.

---

## **1. Context and Problem**

### **The Problem**

Hedera network transaction fees are **fixed in USD**, not HBAR. When the price of HBAR fluctuates, the number of HBARs
required to pay for the same transaction changes:

- **HBAR price increase**: Tests fail because hardcoded HBAR amounts are insufficient
- **HBAR price decrease**: Tests waste funds by over-allocating HBAR

Previously, test accounts were funded with hardcoded HBAR values (e.g., `Hbar(50)`, `Hbar(100)`), which led to:

1. **Test instability**: Tests failed during price volatility
2. **Manual maintenance**: Developers had to update funding amounts when prices changed
3. **Inconsistent coverage**: No systematic approach to calculating required amounts

### **Goal**

Implement a **dynamic funding system** that:

1. Converts USD amounts to HBAR at runtime using live exchange rates
2. Ensures tests have sufficient funds regardless of HBAR price
3. Provides predictable, documented funding amounts based on actual operation costs

---

## **2. Decision**

### **2.1 USD-to-HBAR Conversion Service**

**Decision:** ✅ **Implement `UsdToHbarService` for dynamic conversion**

**Implementation:** [`python/test/utils/usd_to_hbar_service.py`](file:///python/test/utils/usd_to_hbar_service.py)

The service:

- Fetches the current HBAR/USD exchange rate from the Hedera Mirror Node at test session start
- Provides a `usd_to_hbar(usd_amount)` method for runtime conversion
- Caches the rate to avoid repeated API calls during test execution

**Usage Pattern:**

```python
from test.utils.usd_to_hbar_service import UsdToHbarService

# Test account funding
initial_balance = Hbar(UsdToHbarService.usd_to_hbar(1.75))
```

---

### **2.2 Operation Fees Reference**

**Decision:** ✅ **Document all Hedera operation costs in USD**

**Implementation:** [`python/test/utils/OPERATION_FEES.md`](file:///python/test/utils/OPERATION_FEES.md)

A centralized reference document listing USD costs for all Hedera operations used by the Hedera Agent Kit SDK (state for
12.12.2025):

| Service   | Operation            | USD Cost |
|-----------|----------------------|----------|
| Crypto    | CryptoCreate         | $0.05    |
| Crypto    | CryptoTransfer       | $0.0001  |
| Token     | TokenCreate          | $1.00    |
| Token     | TokenMint (NFT)      | $0.02    |
| Consensus | ConsensusCreateTopic | $0.01    |
| Contract  | ContractCreate       | $1.00    |

---

### 2.3 Standardized Balance Tiers

**Decision:** ✅ **Introduce `BALANCE_TIERS` for consistent funding levels**

**Implementation:** [`python/test/utils/setup/langchain_test_config.py`](file:///python/test/utils/setup/langchain_test_config.py)

To further standardize test funding and avoid "magic numbers" scattered throughout the codebase, we introduced named tiers for funding amounts.

**Tiers:**
- **MINIMAL** ($0.50): Basic operations (single transfer, simple query)
- **STANDARD** ($5.00): Most common test scenarios (token operations, multiple transfers)
- **ELEVATED** ($10.00): Complex operations (NFT minting, multiple token operations)
- **MAXIMUM** ($20.00): Heavy operations (contract deployments, extensive token operations)

**Usage Pattern:**

```python
from test.utils.setup.langchain_test_config import BALANCE_TIERS
from test.utils.usd_to_hbar_service import UsdToHbarService

# Test account funding using a tier
initial_balance = Hbar(UsdToHbarService.usd_to_hbar(BALANCE_TIERS["STANDARD"]))
```

## **3. Implementation Details**

### **3.1 Service Initialization**

The `UsdToHbarService` is initialized once per test session via a pytest fixture in `conftest.py`:

```python
@pytest.fixture(scope="session", autouse=True)
async def initialize_usd_service():
    """Initialize the USD to HBAR conversion service for all tests."""
    await UsdToHbarService.initialize()
```

### **3.2 Exchange Rate Source**

The service fetches the exchange rate from the Hedera Mirror Node:

```python
mirrornode = HederaMirrornodeServiceDefaultImpl(LedgerId.TESTNET)
resp = await mirrornode.get_exchange_rate()
rate = resp["current_rate"]["cent_equivalent"] / resp["current_rate"]["hbar_equivalent"] / 100
```

### **3.3 Test File Updates**

All 88 test files (39 integration + 49 E2E) were updated to use the service:

**Before:**

```python
DEFAULT_EXECUTOR_BALANCE = Hbar(50, in_tinybars=False)
```

**After:**

```python
from test.utils.usd_to_hbar_service import UsdToHbarService

DEFAULT_EXECUTOR_BALANCE = Hbar(UsdToHbarService.usd_to_hbar(1.75))
```

## **4. Consequences**

### **Positive**

- ✅ **Test stability**: Tests no longer fail due to HBAR price fluctuations
- ✅ **Self-documenting**: USD amounts clearly indicate operation costs
- ✅ **Maintainability**: Adding new tests follows a clear funding pattern
- ✅ **Cost efficiency**: Funding is right-sized, not over-allocated

### **Negative**

- ⚠️ **Network dependency**: Tests require Mirror Node access at startup
- ⚠️ **Session-scoped rate**: Rate is fixed for the session; long sessions during volatility may have stale rates

### **Mitigations**

- Mirror Node is highly available and rate fetch is resilient
- Test sessions are typically short enough (< 1h) to avoid stale rates

---

## **5. References**

- [OPERATION_FEES.md](file:///python/test/utils/OPERATION_FEES.md) — Hedera operation USD costs
- [usd_to_hbar_service.py](file:///python/test/utils/usd_to_hbar_service.py) — Conversion service implementation
- [Hedera Pricing](https://hedera.com/fees) — Official Hedera fee schedule
