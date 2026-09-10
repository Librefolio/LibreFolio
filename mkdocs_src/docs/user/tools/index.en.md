---
title: Tools
description: Standalone calculations, compatibility, diagnostics, and timing in the experimental Tool platform.
---

# 🧰 Tools

A **Tool** is a standalone calculation: you supply the data for one operation, and it returns a result or a structured error. It is not an instruction to modify your portfolio.

The Tool platform is **experimental**. Its implemented [PAC allocator](pac-allocator/index.md) pilot provides a manual interface for analyzing an exact initial allocation state. It is intentionally narrower than a solver: it does not propose trades, optimize an allocation, or assess trade feasibility. Any future solver would be a separate capability with its own contract and interface.

## 🧭 Availability and compatibility

The catalogue describes the tools the backend can make available, their supported operations, their versions, and their limits. A working registry or an empty catalogue is not a calculator; an illustrative or demonstration plugin is not a completed financial feature.

A usable Tool needs both a compatible backend operation and its matching **tool-specific interface** in the frontend.

| Situation | What it means |
|---|---|
| The catalogue contains a tool with a compatible interface | Its declared operations can be presented by that interface; the entry does not promise additional features. |
| The catalogue is empty | No tools are being offered by that catalogue. |
| A tool is unavailable | The backend could not offer that plugin under the current contract and policy. Other healthy tools can remain available. |
| The frontend does not recognize the interface or its version | The tool must be treated as unavailable in that frontend, not opened through a guessed or generic form. |
| A request no longer matches the advertised versions | It is a compatibility error, not a result for your scenario. |

The frontend owns each tool's form and result presentation. The backend owns the calculation and validates its inputs and outputs. A catalogue entry does not download arbitrary interface code or create a generic form automatically.

## 📦 Prepare the inputs first

Each operation receives a complete, explicitly prepared set of inputs. Check the required values, units, dates, and other fields described by the individual tool before submitting them.

The calculation's contract does not give it your signed-in user, database access, or a data provider to fill in missing values. Authentication happens at the API boundary, outside the calculation. Data collection and preparation must happen **before** the operation starts.

In particular:

- Manual values are inputs to that calculation, not saved portfolio transactions.
- Do not assume that missing prices, exchange rates, or holdings will be fetched automatically.
- The tool-specific interface is responsible for helping you enter and review the inputs; it must not silently substitute a different scenario.
- Scenario values belong in the compute request, not in documentation URLs, diagnostic metadata, or logs.

The Tool contract excludes portfolio writes and automatic broker orders. A result does not create a transaction, change a holding, or execute a trade.

## ⚙️ One operation, one calculation

A Tool operation is **atomic**: its inputs are prepared beforehand and its execution produces one outcome. The platform does not currently provide a workflow that chains tools together or maintains a multi-step calculation state machine.

A batch can contain several independent operations, including operations from different tools. Each item has its own outcome. Identical inputs still represent separate jobs: they are not combined into one calculation or served from a shared cross-user result cache.

### 🧾 Interpreting results

A platform **success** means that the operation returned an output accepted by its contract. It does not necessarily mean that the scenario is ready to use, financially feasible, or suitable for trading.

For example, an analysis operation can successfully report that information is missing or that the supplied scenario is invalid. An initial-valuation readiness result is not proof of trade feasibility or a completed optimization.

A platform **error** means that the calculation could not deliver an accepted outcome. Invalid parameters, an unavailable tool, a full queue, a timeout, a crashed worker, invalid output, and failed cleanup are different error conditions.

Do not interpret a timeout, worker crash, or cleanup failure as “the scenario is infeasible” or “more financial inputs are needed.” Those are platform failures, not financial conclusions.

### ⏳ Capacity and deadlines

The catalogue publishes the effective limits. These are execution budgets, **not measured performance guarantees**. An individual operation can have stricter limits than the platform defaults.

| Initial platform default | Limit |
|---|---|
| Items in one batch | 1–4 |
| Concurrent execution lanes | 2 per API process |
| Pending items | Up to 8 per API process |
| Per-user admission | One batch and up to 4 pending items |
| Parameters for one item | 128 KiB |
| Result for one item | 256 KiB |
| Queue budget | 5 seconds |
| Hard job budget | 5 seconds, including cold startup |
| Cooperative soft budget | 4 seconds |
| Cleanup budget | 2 seconds; capacity remains occupied during cleanup |
| Server request budget | 20 seconds |
| Tool-specific client timeout | 25 seconds |

The capacity limits apply to **one API process**, not to the whole installation. They are not a global instance limit or a guarantee of operating-system memory isolation.

If the queue is full, allow the current work to finish before trying again. Repeatedly submitting the same inputs does not bypass admission limits or make the work share an execution.

## 🔎 Read-only diagnostics

The diagnostics contract is available to **every authenticated user with an active account**. It is not restricted to administrators. Catalogue access and computation use the same active-account authentication boundary.

Diagnostics provide a read-only snapshot of:

- Loaded tool descriptors, versions, schemas, and effective policies.
- Sanitized plugin-discovery failures.
- Execution-pool availability, active and queued work, pending items, degraded lanes, and terminal-item counters.
- A runtime identifier and an explicit `api_process` scope.

The snapshot describes the API process that answered the request. Its counters are not installation-wide totals and should not be read as your personal calculation history.

`completed` counts **all terminal items**, including failures and cancellations. `failed` is the subset that did not end in platform success, so do not add the two counters. A terminal item can still have physical cleanup outstanding; the counter is not confirmation that its worker and descendants have been released.

Diagnostics do **not** expose scenario inputs, computed results, cookies, raw traces, or raw logs. They are not a job browser and provide no probe, reset, repair, or cancellation controls. They do not replace the application's existing support features.

## ⏱️ Understanding timing information

Timing fields describe **backend measurements**, in milliseconds. When timing information is presented, distinguish the phases of an individual item from the duration of the whole request.

| Per-item field | Meaning |
|---|---|
| `queue_wait_ms` | Time spent waiting before execution. |
| `startup_ms` | Worker startup time up to the accepted ready handshake. |
| `input_validation_ms` | Time spent checking the operation's input. |
| `compute_ms` | Time measured for the plugin calculation. |
| `output_validation_ms` | Time spent checking the returned output. |
| `serialization_ms` | Time measured for encoding the output. |
| `execution_ms` | Time from allocation of an execution lane until cleanup begins, including startup. |
| `cleanup_ms` | Time measured for releasing the job and its child work. |
| `total_ms` | Elapsed time since this item was admitted, measured when its outcome is recorded. |

An unobserved phase is **`null`**, meaning that no measurement is available. It must not be displayed as an invented zero. A missing compute measurement does not prove that a calculation took no time.

The batch's `server_processing_ms` is a separate server-side duration. Do not add the durations of parallel items and present the sum as request latency: their executions can overlap. Likewise, phase and aggregate fields are not all independent quantities to add together.

A browser's network round trip is another measurement. It includes transport time and is not interchangeable with backend calculation time or `server_processing_ms`.

## 📖 Documentation and language

LibreFolio's frontend documentation links follow the application's selected language rather than forcing an English URL. A tool declares a documentation path relative to the documentation root.

Language-aware links and published translations are separate concerns: a link does not create a missing translation. Tool-specific documentation must describe the operations actually available, and its language versions must be published separately.

This overview does not imply that a dedicated guide, compatible interface, or completed calculator already exists for every advertised or experimental plugin.
