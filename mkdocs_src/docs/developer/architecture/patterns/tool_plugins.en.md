---
title: Tool plugins
description: Atomic Tool contracts, multi-service packages, transactional discovery, process-owned execution, generated codecs, and compiled frontend renderers.
---

# 🧰 Tool plugins

Tools package an **atomic calculation** behind a typed, versioned contract. The caller supplies a complete scenario; the backend computes a result without obtaining portfolio data or authority on the caller's behalf.

This capability is experimental, but its boundaries are integrated in current source: transport models, multi-service discovery, schema export and generated codecs, authenticated API routes, a per-process executor, worker/process-tree ownership, catalogue cards, per-service frontend routes, and compiled custom renderers. The bundled `PacAllocatorTool` currently exposes a single service, `pac_allocator`. Source integration still does **not** replace runtime evidence for every cancellation race or kernel-level descendant-cleanup scenario.

## 🎯 Scope and authority

All calculation inputs must be explicit and packed before dispatch. A calculation must not receive a principal, database session, provider, or service-layer dependency. Authentication belongs at the API boundary: `get_current_user` performs the authenticated-user database lookup there, not in the calculation child.

The current contract excludes:

- Portfolio writes and automatic broker orders.
- Chained Tools, workflows, or a Tool state machine.
- Runtime fetching or service-layer enrichment inside a calculation.
- A schema, prefill, jobs, or cancellation endpoint, or an MCP server.

A future service-layer integration is not part of this contract. The backend owns calculation semantics; a Tool-specific frontend owns its form, host, and result presentation.

## 🗺️ Source map

Paths below are relative to the repository root.

| Source | Responsibility |
|--------|----------------|
| `backend/app/schemas/tools.py` | Descriptors, policies, batch envelopes, errors, metrics, and diagnostics DTOs. |
| `backend/app/services/tools/base.py` | `ToolPlugin`, `ToolService`, `ToolExecutionContext`, and typed definition/execution errors. |
| `backend/app/services/tools/registry.py` | Staged registration claims, quarantine, definition validation, and the published snapshot. |
| `backend/app/services/tools/schema.py` | Pydantic schema profile, local references, operation discovery, and fingerprinting. |
| `backend/app/services/tools/schema_export.py` | Build-only Tool manifest and schema bundles derived from registry definitions. |
| `backend/app/services/tools/catalog.py` | Read-only catalogue projection and effective operation limits. |
| `backend/app/services/tools/wire.py` | Unicode-safe bounded JSON and sanitized validation issues. |
| `backend/app/services/tools/executor.py` | Per-process admission, item tickets, lane scheduling, absolute deadlines, handshake, cancellation, and cleanup ownership. |
| `backend/app/services/tools/worker.py` | Child handshake, version-pin checks, validation, computation, and result frames. |
| `backend/app/services/tools/process_tree.py` | Owned process identities, descendant tracking, and termination checks. |
| `backend/app/services/tool_plugins/pac_allocator.py` | Current packaged plugin with one complete public service and code-based compute dispatch. |
| `backend/app/api/v1/tools.py` | Bounded transport handlers, authentication dependencies, and disconnect handling. |
| `backend/app/api/v1/router.py` | Inclusion of the Tool router in the API v1 router. |
| `backend/app/api/v1/auth.py` | `get_current_user`, the authentication dependency used by all Tool routes. |
| `backend/app/main.py` | API prefix mounting, off-event-loop catalogue initialization, and executor shutdown in the lifespan's `finally` block. |
| `backend/app/services/provider_registry.py` | Shared discovery and `register_plugin`; existing domain base-class aliases are imported lazily. |
| `frontend/scripts/generate-tools-client.mjs` | Strict codec generation and the generated code/version-to-codec map. |
| `frontend/src/lib/api/tool-contract-map.generated.ts` | Generated service identities, schema fingerprints, UI versions, and codecs. |
| `frontend/src/lib/features/tools/contracts.ts` | Runtime catalogue validation, compiled-contract compatibility, and typed execution preparation. |
| `frontend/src/lib/features/tools/registry.ts` | Source-owned compiled renderer registrations and renderer resolution. |
| `frontend/src/lib/features/tools/ToolsHub.svelte` | One catalogue card per returned service descriptor. |
| `frontend/src/lib/features/tools/presentation.ts` | Stable `/tools/<tool_code>` frontend route construction. |
| `frontend/src/routes/(app)/tools/[tool_code]/+page.svelte` | Dynamic per-service Tool host route. |
| `frontend/src/lib/components/ui/DocsLink.svelte` | Language-aware documentation URLs and an optional localized fallback. |

See also the [shared registry pattern](registry_pattern.md). Tools specialize that registry rather than inheriting provider capabilities.

## 🧩 Plugin contract

### 🏷️ Metadata

The packaged plugin and its public services are distinct contract levels. `ToolPlugin` owns the package-wide versions and a nonempty `services: tuple[ToolService, ...]`; each `ToolService` is one complete public calculation.

| Owner | Attribute | Contract |
|-------|-----------|----------|
| Packaged plugin | `contract_version` | String SemVer copied into every service descriptor in the package. |
| Packaged plugin | `implementation_version` | Separate string SemVer for the packaged implementation, also copied into every service descriptor. |
| Packaged plugin | `services` | One to sixteen statically declared `ToolService` values. |
| Service | `tool_code` | Stable identifier matching `[a-z][a-z0-9_]*`, at most 64 characters. |
| Service | `name`, `description` | Required human-readable metadata. |
| Service | `name_i18n_key`, `description_i18n_key` | Optional translation keys; both default to `None`. Preserve them in catalogue and frontend integration. |
| Service | `category`, `icon_key` | Required identifiers using the Tool code format. |
| Service | `ui` | `ToolUIDescriptor(kind="custom", component_key=..., version="1.0.0")`, with a service-owned string SemVer at `ui.version`. |
| Service | `documentation` | `ToolDocumentation(path=..., version=...)`, pointing to a real documentation destination. |
| Service | `operations` | A nonempty tuple of `ToolOperationPolicy` objects with unique operation names. |
| Service | `input_type`, `output_type` | Real Pydantic model types or supported model-union type expressions, used to construct `TypeAdapter` instances. |

`contract_version` and `implementation_version` belong to `ToolPlugin`, so every service in one packaged class shares them. UI compatibility is independent: each service owns `ToolUIDescriptor.version`, serialized as `descriptor.ui.version`. It is a SemVer string, not a numeric compatibility flag, and it does **not** inherit from or have to equal `implementation_version`, even when their current values happen to match.

One package may therefore expose multiple complete service definitions and tool codes. The registry expands them independently; the catalogue publishes one descriptor per service; the frontend renders one catalogue card and `/tools/<tool_code>` route per descriptor; and compute resolves the submitted `tool_code` to that service's adapters and policy. These identities share the generic `/api/v1/tools/*` transport routes, not a service-specific backend endpoint.

The current `PacAllocatorTool` declares one service, `pac_allocator`, with its own name, description, category/icon, policies, input/output models, UI descriptor, and documentation descriptor. Its synchronous dispatcher resolves on the service code **and** the declared operation rather than on the shape of the submitted parameters, so a second service added later cannot make it confuse two model pairs.

A `component_key` is an identifier for a source-owned compiled renderer, not a module URL. The descriptor alone does not prove that the current frontend bundle contains a compatible registration.

Documentation paths are relative, extensionless documentation routes. They cannot start with `/` or `mkdocs/`, contain empty interior segments, `.` or `..`, or include a URL, query, fragment, or escape. Documentation has its own semantic version; it is not the schema fingerprint.

### 🧱 Models and operations

Pydantic types are the canonical source for both validation and published schemas:

- Every `BaseModel`, including nested models, must forbid extra fields. The schema check walks the adapter's core schema; validating only the outer model is insufficient.
- Each schema root must resolve to an object with `additionalProperties: false`, or a union of such model roots. Use a discriminated model union when operations have different input shapes.
- Every input root must require an `operation` string literal or literal enum. It must have **no default**.
- The complete set of input operation values must exactly match the declared policies. Neither an undocumented operation nor an unreachable policy is accepted.
- Input and output validation use the real adapters. Do not substitute handwritten JSON Schema or handwritten TypeScript transport types.

`ToolOperationPolicy` requires `pure=True`, carries a `deterministic` flag, and fixes `deduplication` to `"none"`. It also declares input/output byte limits and queue, soft, and hard deadlines. Determinism metadata does not enable caching or shared execution.

### ⏱️ Synchronous computation

Implement synchronous `compute(tool_code, parameters, context)` and return a complete `BaseModel` result belonging to the selected service's output contract. Dispatch only declared service-code and input-model combinations. Coroutine implementations are rejected during definition validation.

The class must be constructible with no arguments. Discovery checks this with signature binding without constructing the plugin. Worker construction is a single attempt; the Tool registry's instance helper likewise does not retry a constructor after `TypeError`.

`ToolExecutionContext` contains an execution identifier, monotonic soft and hard deadlines, and a cancellation callback. Call **`context.checkpoint()` without arguments** at bounded intervals. It raises `ToolExecutionError("execution_limit", retryable=True)` when cancellation is observed or the soft deadline has elapsed. It is cooperative: it does not itself terminate a process at the hard deadline.

A reusable calculation library can accept a no-argument checkpoint callback without depending on Tool types. Constructors, imports, and calculation code must respect the same authority and job-lifetime boundaries.

## 🔎 Discovery and version lifecycle

`ToolPluginRegistry` extends `AbstractPluginRegistry`, selects the `tool_plugins` discovery folder, and registers packaged classes with `register_plugin(ToolPluginRegistry)`. Its static declaration is the `services` tuple; publication expands each service into a definition keyed by that service's `tool_code`.

Discovery is transactional:

1. The shared registry discovers modules; Tool registration stages claims attributed to the calling module, not merely to a class's mutable `__module__`.
2. Every packaged claim is expanded into its declared services. Canonical code collisions are collected across all service claims, including claims made by a module whose import subsequently failed.
3. **Every claimant to a duplicate code is quarantined.** There is no first-wins or last-wins selection. Resolution prioritizes `duplicate_code`, then `import_failed`, then definition validation.
4. Claims from failed imports cannot become usable partial registrations. Unrelated healthy definitions remain available.
5. Publication creates a code-sorted, read-only service-definition mapping and a tuple of sanitized failures. New registration claims are closed after publication.

Each expanded definition retains both the packaged class and its `ToolService`. Definition validation checks a concrete `ToolPlugin` class, synchronous computation, the zero-argument constructor signature, real adapters, schema validity, operation agreement, and the service's complete descriptor metadata. One invalid service is quarantined without hiding a healthy sibling service. The shared registry keeps its existing domain base-class aliases lazy; importing the registry is not permission for a Tool to import or use provider services.

The schema fingerprint is SHA-256 over canonical JSON containing `input_schema`, `output_schema`, and sorted operation names. It is generated from the schemas, not supplied by a plugin author. Input schemas use Pydantic's **validation** mode; output schemas use **serialization** mode. Both include the Draft 2020-12 `$schema` declaration.

Only resolvable local references are accepted, including discriminator mappings. `$id`, `$dynamicRef`, and `$recursiveRef` are rejected. There is no additional `jsonschema` validator dependency: Pydantic and `TypeAdapter` remain the schema source and validators.

The registry constructs each descriptor with package-owned `contract_version` and `implementation_version`, service-owned `ui` and `documentation`, and a generated fingerprint. Keep all four version/fingerprint concerns deliberate: a fingerprint detects schema/operation changes, the implementation pin identifies the live packaged code, and `descriptor.ui.version` selects a compatible compiled UI contract. None is automatic compatibility negotiation or hot replacement.

The catalogue publishes full schemas, including their local definitions and references. It clamps operation limits to the platform policy and reserves output time within the hard deadline. An unusable effective operation policy makes that definition unavailable in the catalogue projection. Effective limit values are not additional inputs to the schema fingerprint.

## 🌐 API and result contract

The route module declares handlers on a `/tools` router. `api/v1/router.py` includes that router, and `main.py` mounts the API v1 router with `API_V1_PREFIX`. The configured Tool API paths are:

| Method and path | Purpose |
|-----------------|---------|
| `GET /api/v1/tools/catalog` | Catalogue version `"2"`, effective policy, one full descriptor per healthy service, and coarse unavailable summaries. |
| `POST /api/v1/tools/compute` | One heterogeneous batch of atomic calculation items. |
| `GET /api/v1/tools/diagnostics` | Sanitized, read-only diagnostics for the API process handling the request. |

**All three handlers depend on `get_current_user`. Diagnostics does not require an administrator.** The mount and executor dependency are present in source; this is not a claim that these endpoints have passed runtime verification.

At startup, the application initializes the catalogue with `await asyncio.to_thread(ToolPluginRegistry.get_snapshot)`. This is discovery, not worker prewarming. The lifespan wraps its serving `yield` in `try/finally` and awaits `shutdown_tool_executor()` on exit.

### 📦 Batches and outcomes

A request carries `request_id` and one to four items. Each item includes:

- A distinct `correlation_id`.
- `tool_code`, `contract_version`, `implementation_version`, and `schema_fingerprint`.
- Its own JSON `parameters`, allowing different Tools and operations in one batch.

For a returned batch, `ToolExecutor.compute` gathers one task per input item in submission order and retains `request_id`; `_identity` copies each item's correlation and version pins into its result. The DTOs additionally enforce distinct correlations and bounded arrays; those checks alone do not establish input-to-response order or cardinality.

Results discriminate on `status`: `"success"` carries `result`, while `"error"` carries `error`. These payloads are exclusive. A success requires `execution_id`; a failure can have no execution identifier when execution never started. The child rechecks all four Tool identity fields against its own discovered definition.

`success_count` and `failed_count` count **platform outcomes**, not domain readiness. A valid domain response such as `invalid` or `needs_input` can be a platform success. Likewise, a domain's initial-valuation `ready` status must not be presented as proof of trade feasibility or an optimized plan.

### 🧯 Error boundaries

| Area | Platform error codes |
|------|----------------------|
| Lookup and availability | `unknown_tool`, `tool_unavailable`, `version_mismatch`, `service_unavailable` |
| Parameters | `invalid_parameters`, `input_limit_exceeded` |
| Admission and waiting | `queue_full`, `queue_timeout` |
| Execution | `execution_limit`, `execution_timeout`, `worker_crashed`, `execution_failed` |
| Output | `invalid_output`, `output_limit_exceeded` |
| Termination | `cleanup_failed` |

A crash, hard timeout, invalid output, or failed cleanup is a platform failure. Do not turn it into a domain answer such as “infeasible” or “needs more input.”

Transport failures are distinct from per-item results. The route rejects malformed JSON, duplicate object keys, and nonfinite numbers as invalid requests. It bounds received bytes, sanitizes envelope validation failures, and applies request deadlines. Whole-request errors include HTTP `400` for invalid JSON, `413` for oversized input, and `422` for an invalid envelope. A top-level `queue_full` execution error is mapped to `429`; other raised execution errors and request deadline failures use `503`.

Per-item `ToolError` exposes a code, `retryable`, and bounded validation issues. The sanitizer omits input values, validator context, URLs, and raw messages. It returns at most 32 issues, each with at most 16 safe path segments; `issue_count` retains the total issue count.

The handler watches for client disconnection and cancels the awaited computation task. The executor propagates cancellation to item tasks and signals owned jobs; tickets and cleanup callbacks govern capacity release. Cancellation alone is not evidence that physical cleanup has completed.

### 🔬 Process-local diagnostics

`ToolDiagnosticsResponse` has `scope="api_process"`, an opaque runtime identifier, the effective policy, loaded descriptors, sanitized registration failures, and a pool snapshot.

Pool fields report availability, active, queued, pending, degraded lanes, completed, and failed counts. They describe one API process, **not global deployment capacity**. The catalogue exposes only coarse unavailable summaries; diagnostics adds safe filenames and bounded failure reasons.

`_item_finished` increments `completed` for every tracked item task that reaches a terminal state, including cancellation or an exception. `failed` is the subset without a platform-success result, not an additional disjoint total. These counters can advance while physical cleanup remains outstanding; `completed` does not certify process termination or released capacity.

Diagnostics must not expose submitted scenarios, results, cookies, raw traces, or logs. It is not a probe, reset, repair, or other mutation interface.

## 🔤 JSON and generation boundary

`wire.py` validates values before encoding: string keys, JSON-compatible values, finite numbers, valid Unicode scalars, and bounded nesting. Surrogate code points are rejected rather than replaced.

Encoding produces compact UTF-8 JSON with sorted keys, `ensure_ascii=False`, `allow_nan=False`, and compact separators. Limits are measured in **encoded bytes during encoding**, not characters. Parsing rejects duplicate keys and nonfinite values; `decode_json` additionally validates the decoded value.

The API's envelope check deliberately excludes heterogeneous parameter contents from its early string validation. This allows per-item parameter validation to retain its own error boundary rather than promoting every invalid parameter string into an envelope error.

Before dispatch, validation must be a gate, not a scenario rewrite. Preserve the original parameter values, text, and explicit choices rather than replacing them with a validator's transformed or default-populated output. Canonical encoding can change whitespace and key order; it must not change the scenario. Inside the child, `_validated_input` builds the typed model and checks that its operation still matches the original JSON operation.

### ⚙️ Generation requirements

`schema_export.py` roots the real registry adapters in a **build-only OpenAPI 3.1 document with `paths: {}`**. It emits one manifest entry per `(tool_code, contract_version)` service identity with the schema fingerprint, `componentKey`, `uiVersion`, operation names, and separate validation/serialization schema roots. This is a build artifact, not a runtime schema endpoint.

`frontend/scripts/generate-tools-client.mjs` validates that manifest, generates strict Zod transport and service codecs, and publishes `generated-tools.ts` with `tool-contract-map.generated.ts` as one generation. The literal map is keyed by service code and contract version and points to that service's input/output codecs. `implementation_version` is intentionally not a renderer or codec key; the client reads it from the live descriptor and pins it separately in every compute request.

Cross-language acceptance must match for valid inputs, valid outputs, and error envelopes:

- Reject unknown fields in nested models, not only at the envelope boundary.
- Validate Unicode scalar content before canonical JSON or dispatch.
- Apply string bounds in Unicode code points, not JavaScript UTF-16 `length`.
- Do not send transformed/defaulted validation output in place of the caller's original scenario.
- Preserve discriminators, correlation identifiers, versions, fingerprints, and exclusive success/error shapes.

Do not maintain a second handwritten I/O contract beside the Pydantic models. Canonical encoding is not evidence of request deduplication: deduplication remains disabled.

## ⚙️ Isolated execution

### 🧵 Worker primitives

`ToolWorkerJob` carries bounded parameter bytes and server-owned identity, deadlines, and limits. It has no principal, database session, or provider handle.

`execute_tool_job` is a child-only entry point run in an owned spawn process. It rejects invocation outside a multiprocessing child. On POSIX, it creates a fresh session with `setsid` and sends a `ready` frame containing execution and process identity. The executor checks the execution identifier, PID, process group, and creation time before sending the start ACK (`b"\x00"`). Plugin discovery and computation wait for that ACK. On non-POSIX systems, this entry point reports `service_unavailable`; it is not a portable process-containment implementation.

Once started, the child:

1. Resolves the definition and verifies the requested versions and fingerprint.
2. Bounds and decodes input, validates it with the input adapter in strict mode, and verifies the operation.
3. Constructs the plugin once and calls synchronous `compute`, with checkpoints around the execution phases.
4. Requires a model result, serializes through the output adapter, encodes bounded JSON, and validates the emitted bytes with the output adapter in strict mode.
5. Checks the hard deadline and cancellation before returning a result frame. Exceptions become sanitized platform failures.

The worker closes its pipe endpoints on exit. **A result frame is not a cleanup acknowledgement.**

### 🧹 Descendant cleanup

`OwnedProcessTree` tracks the multiprocessing root, its fresh process group, and captured descendants. Process identities include PID and creation time; session adoption verifies that the group belongs to the worker and is not the supervisor's own group.

Cleanup observes recursive descendants and group members, requests termination, escalates to a kill if needed, and checks for observed termination within its deadline. Only then does it join and close the root process handle. A `False` cleanup result retains the handles instead of pretending the job is gone. These methods perform blocking I/O and must run off the event loop.

Plugin-created processes and threads are allowed only within the job's lifetime. No detached or daemonized work may outlive the job. The supervisor must clean up the entire owned subtree after success, error, timeout, abort, and shutdown.

!!! warning "Ownership is not a security sandbox"

    These POSIX primitives manage the lifetime of packaged plugin work. They do not establish an OS memory sandbox, filesystem isolation, or permission to run arbitrary untrusted plugins. Descendant tracking does not make detaching work a supported escape from job ownership.

### 📏 Supervisor and budgets

`ToolExecutor` coordinates admission, queueing, absolute deadlines, cancellation, and cleanup for one API process. Its constructor starts no workers. Each physical job has one I/O owner, `_run_owned_job`, dispatched through `asyncio.to_thread`; its `finally` path attempts cleanup even after a successful result.

The executor creates an independent task per batch item and gates execution through a bounded queue of lane tokens. Every item that reaches execution gets a distinct non-daemon spawn process, even for identical inputs; there is no coalescing or cross-user cache. Queue deadlines use the batch's shared admission time, effective operation limits, and the request deadline. The hard job budget includes cold process startup. `_job_finished` returns a lane and its admission credit only after confirmed cleanup; an unconfirmed outcome quarantines the job instead of silently recycling capacity.

Each item task has an `_ItemTicket` and a registered done callback. If cancellation occurs before the coroutine starts, or before it owns a physical job, `_item_finished` still releases its admission credit. Once a job is attached to the ticket, physical cleanup owns that release, preventing a premature or double refund. Queue bookkeeping also returns an acquired lane when no job was started.

Shutdown closes admission, cancels tracked item tasks, signals owned jobs, and waits within the cleanup budget. Jobs with unconfirmed termination remain quarantined. The process-local executor reference is cleared only when its pending count reaches zero. These source paths do not replace runtime verification of cancellation races or descendant cleanup.

The following are initial `ToolPlatformPolicy` defaults, not measured throughput or latency guarantees:

| Limit or budget | Default |
|-----------------|---------|
| Items per batch | 1–4 |
| Worker lanes per API process | 2 |
| Pending items per API process | 8 |
| Concurrent batches / pending items per principal | 1 / 4 |
| Parameters per item / result per item | 128 KiB / 256 KiB |
| JSON nesting depth | 32 |
| Ingress / shared queue budget | 2 s / 5 s |
| Hard job budget, including startup | 5 s |
| Cooperative soft budget / output reserve | 4 s / 1 s |
| Cleanup / response reserve | 2 s / 2 s |
| Server request / Tool-specific client budget | 20 s / 25 s |

The policy validates budget and envelope coherence. Catalogue operation limits can be stricter than platform limits. The frontend Tool client applies `client_timeout_ms` to the compute request; it remains a client transport budget, not a throughput or completion guarantee.

### 📊 Timing metrics

Per-item metrics are `queue_wait_ms`, `startup_ms`, `input_validation_ms`, `compute_ms`, `output_validation_ms`, `serialization_ms`, `execution_ms`, `cleanup_ms`, and `total_ms`. They are measured monotonic durations in milliseconds, not estimates derived from the requested budgets. An unobserved phase is `null`, not an invented zero.

The child measures its validation, computation, and serialization phases. The executor records queue wait from admission, startup through the accepted `ready` frame, execution from lane allocation until cleanup begins, and cleanup duration. `total_ms` measures elapsed time from item admission to its recorded outcome, not from HTTP request arrival. For API calls, batch `server_processing_ms` uses the request start supplied by the route. Neither these timings nor result counts are a benchmark or SLA.

Do not sum parallel item durations and label the sum as request latency: their execution windows can overlap. Phase measurements and aggregate fields can overlap too. Browser network round-trip time is a distinct observation, not another name for `compute_ms` or the batch's `server_processing_ms`.

## 🖥️ Frontend and documentation

Frontend compatibility first resolves the exact service code and contract version in the generated contract map, then compares the schema fingerprint, `descriptor.ui.component_key`, string SemVer `descriptor.ui.version`, and operation set. The request separately pins the live `descriptor.implementation_version`; UI version is never inferred from it.

`registry.ts` accepts only source-owned literal component imports. A registration repeats the service code, contract version, component key, and UI SemVer and must agree with the generated contract before it can bind a catalogue descriptor. Duplicate code/version registrations, cross-tool component-key collisions, missing registrations, and mismatches stay unavailable. A server descriptor never becomes an arbitrary module URL, and incompatibility never falls back to a generic generated financial form.

The current compiled registry binds no components at all: the prototype interfaces were removed, so `pac_allocator` resolves as unavailable with `renderer_missing` while its backend service stays listed in the catalogue. When a custom component exists, it owns domain-specific input and result presentation while the backend owns the calculation. A descriptor and schema still do not make a service usable until its generated contract and compiled renderer registration are present and compatible.

Tool catalogue cards and the opened Tool host expose only the compatibility pair
`Backend/API <contract_version> · UI <ui.version>`. Keep `implementation_version` in
**Plugin diagnostics** rather than the public compatibility label: it identifies the deployed
implementation but is not the frontend contract users need to match.

Use `DocsLink` for documentation destinations. It builds `/mkdocs/` URLs from the current language and a relative path rather than forcing English. For an EN-only destination, a caller can supply an existing localized destination through `localizedFallbackPath`; the helper selects that fallback for non-English languages. It does not discover missing pages automatically.

Keep submitted financial data out of documentation URLs, logs, and HTML attributes. Documentation metadata identifies a page and its version, not a scenario transport channel.

## ✅ Addition and integration checklist

The following work must be completed and verified before presenting a new Tool as available:

- [ ] Define the atomic boundary and pack every required input before dispatch. Exclude ambient authority and side effects.
- [ ] Declare package-wide contract/implementation versions and a nonempty service tuple; give every service complete metadata, policies, models, UI SemVer, and documentation.
- [ ] Define strict nested models, operation discriminators without defaults, and matching operation policies.
- [ ] Register the packaged class and verify service expansion, healthy siblings, failed imports, duplicate-code quarantine, invalid definitions, and closed registration.
- [ ] Implement a zero-argument constructor and synchronous code-based dispatch with bounded checkpoints and job-scoped child work.
- [ ] Verify input/output adapters, schema references, fingerprints, Unicode and byte limits, safe errors, and unchanged caller scenarios.
- [ ] Integrate generated codecs and the compiled renderer map; verify acceptance parity, unsupported renderer/version handling, and language-aware documentation links.
- [ ] Verify authenticated route mounting, response order/cardinality/pins, platform-versus-domain outcomes, and process-local diagnostic privacy.
- [ ] Verify genuine parallel execution, distinct workers for identical items, admission limits, cold startup deadlines, cancellation, crashes, invalid output, and subtree cleanup on every exit path.
- [ ] Integrate documentation navigation and cross-boundary targets, then run the project's established tests and documentation checks when runtime verification is authorized.

Treat passing those checks as evidence to gather during integration, not as a consequence of adding a descriptor or writing a guide.
