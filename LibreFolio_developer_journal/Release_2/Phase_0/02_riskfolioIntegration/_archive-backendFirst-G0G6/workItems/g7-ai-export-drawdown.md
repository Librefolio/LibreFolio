# G7 - Deterministic Drawdown and AI Export Recovery Analysis

**Status**: deferred to Risk Assessment
**Origin**: Phase 0 AI Export runtime deep audit

`asset.drawdown_recovery` must remain absent from the public AI Export analysis
catalog until the Risk Assessment layer exposes deterministic drawdown episodes.
Do not approximate recovery from price-bucket minimum/maximum values.

## Required Risk output

- integrate the canonical `RISK_DRAWDOWN` signal/metric;
- peak value and observation date;
- trough value and observation date;
- drawdown depth;
- peak-to-trough duration;
- current drawdown;
- recovered percentage;
- remaining distance to the previous peak;
- open/closed episode state;
- maximum episode in the selected period;
- comparable historical episodes when available.

## Future AI Export integration

Reintroduce `asset.drawdown_recovery` only after the Risk output above has a
versioned schema, deterministic period semantics, explicit coverage/failure
semantics, and tests. The analysis must consume those Risk facts directly and
may add trend/volatility context without recomputing drawdown in the prompt or
AI Export serializer.
