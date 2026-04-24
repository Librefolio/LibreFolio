# Ingest Registry

> Records every source file ingested into the wiki, with its git hash at ingest time.
> Purpose: detect drift between the ingested snapshot and the current state of the source.
>
> **How to check drift for a source:**
> ```bash
> git diff {hash} HEAD -- {source-path}
> ```
> A non-empty diff means the source has changed since it was ingested.
> Significant changes → consider re-ingesting the source.
>
> For untracked files (external articles, PDFs in raw/): hash = `untracked`, no drift check possible.

| Source Path | Git Hash at Ingest | Date | Wiki Page |
|-------------|-------------------|------|-----------|
| _(empty — first ingest will populate this)_ | | | |
