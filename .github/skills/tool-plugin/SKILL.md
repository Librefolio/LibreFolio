---
name: tool-plugin
description: Create or extend a LibreFolio atomic Tool plugin in backend/app/services/tool_plugins/. Covers Pydantic contracts, isolated execution, compiled UI binding, diagnostics and generated codecs.
---

# Atomic Tool plugins

Use when adding or changing a Tool plugin, not an Asset/FX/BRIM provider.

## Read the actual contract first

- `backend/app/services/tools/base.py`
- `backend/app/schemas/tools.py`
- `backend/app/services/tools/registry.py`
- `backend/app/services/tools/schema.py`
- `mkdocs_src/docs/developer/architecture/patterns/tool_plugins.en.md`

Code is authoritative. Never turn an old plan or a successful test-only fixture into
a claim that the real Tool is integrated.

## Model and compute boundary

1. Define actual Pydantic input/output models in the appropriate schema module.
   All nested models forbid extra fields. A strict model or a required-discriminator
   union is supported; a free-form schema dictionary is not a plugin contract.
2. Require `operation` explicitly, without a default, and declare the matching
   `ToolOperationPolicy` entries. Do not advertise unfinished operations.
3. Derive the plugin from `ToolPlugin[Input, Output]`; expose `input_type` and
   `output_type`, including the actual annotated output union when applicable.
4. Implement synchronous `compute(parameters, context)`. Forward `context.checkpoint`
   into reusable pure numerical kernels rather than importing the Tool runtime there.
5. Return a complete model. Output is serialized and revalidated at the process
   boundary; unchecked `model_construct` is not a validation bypass.

The API authenticates the caller. The worker receives no principal, DB session,
provider client, request, cookie or ambient portfolio authority. Collect every
required datum through authorized domain APIs before submitting the item.
No financial writes, live provider fetch, broker order or service-layer lookup belongs
inside a current Tool computation.

## Static declaration and discovery

Put the thin wrapper in `backend/app/services/tool_plugins/` and register it with
`@register_plugin(ToolPluginRegistry)`. Reuse this registry specialization; do not
introduce another discovery system.

Required metadata:

- Stable lowercase `tool_code`.
- Exact contract and implementation versions.
- Plain `name`/`description`, optional `name_i18n_key`/`description_i18n_key`.
- Category and compiled icon key.
- `ToolUIDescriptor(kind="custom", component_key=..., ui_contract_version=...)`.
- `ToolDocumentation(path=..., version=...)`, relative to the MkDocs root.
- A nonempty tuple of operation policies.

Initialization takes no user parameters and is attempted once. Never recover a
constructor `TypeError` by silently trying another signature.

Do not compute, fetch data or run a self-test at import/registration. Claims remain
private until discovery finishes. Import failures and invalid declarations are
quarantined; every distinct claimant of a colliding code loses. Re-registering the
same class object is not a new claimant.

Pydantic is the source and validator; no additional `jsonschema` dependency is needed.
Published schemas are derived from the TypeAdapters, use resolved local references
and must fit the supported export profile. Do not provide handwritten replacement
input/output JSON Schema.

## Atomic execution and resources

Each accepted compute item has its own job, even when two parameter sets are equal.
There is no physical deduplication or cross-user/request result cache.

Jobs run concurrently within the declared capacity. Queue time starts at the same
batch admission origin; it is not renewed for each execution wave. Hard time includes
cold process start/import, validation, computation and output work.

Child processes and threads are allowed only inside the owned job's cleanup domain.
They must not detach or survive job completion. Cleanup applies to success, failure,
timeout, observed disconnect and shutdown. A live/unreaped descendant is not a
successfully released execution slot.

Report financial availability through the domain output. Execution limits, crashes,
invalid output and failed cleanup are platform errors, never fabricated infeasibility
or a zero-valued result. Aborting the HTTP request stops client waiting; it is not a
server cancellation acknowledgement.

Metrics belong to the platform envelope: measured queue/startup/compute/output/
execution/cleanup and item/batch elapsed durations. Missing observations remain null.
Do not add timing fields to a numerical result or sum parallel job times into latency.

## Typed client and custom UI

After an authorized API/schema change, use the existing `./dev.py api sync` pipeline.
Export the real bundled model roots and generated code/version-to-codec mapping.
Never write PAC/domain TypeScript fields or a fake endpoint to force schema generation.

Preserve required literals, nested extra-forbid, nullable versus omitted fields and
conditional output shapes. JSON Schema/Pydantic lengths count Unicode code points,
not JavaScript UTF-16 units. Reject lone surrogates before encoding; compact UTF-8
must not repair, normalize or silently shorten raw text. Validate input without sending
default-expanded parser output in place of the original draft.

Register only compiled component imports. Compatibility checks exact code, contract,
schema fingerprint and UI key/version; the request separately pins the live implementation.
An unknown/incompatible renderer is unavailable, not a reason to execute arbitrary
server-provided code or fall back to a generic financial form.

Use the existing `DocsLink` component so links follow the frontend language.
Keep all financial calculations in the backend. Guard result application by account
generation, component identity, request sequence and draft revision.

## Completion evidence

- New or repaired tests go through `test-author`; follow actual runner ownership.
- MkDocs pages go through `docs-writer`; English sources and explicit translation workflow.
- Verify authorized-user diagnostics without exposing scenarios, traces or credentials.
- Exercise the real plugin through catalog, compute, worker, codec and its approved UI.
- Test exact correlation/order/cardinality and failure isolation, not global DB counts.
- Respect shared server/codegen/build/i18n/runner leases; isolated worktrees do not isolate runtime.
- Do not mark a real pilot complete using an empty registry or a disposable demonstration plugin.
