---
id: 2026-11-25-file-upload-source
date: 2026-11-25
area: data-ingestion
scope: apps/api
status: accepted
task: "140"
---

# An uploaded file becomes a data source that can be synced again

## Situation

The admin panel could ingest a spreadsheet: `POST /api/v1/admin/ingest/upload`
read the file, put the listings into the catalogue and answered how many
landed. That was the end of it. The file itself was written to a temporary
file and deleted in the `finally` block, and no data source was created.

The other half of the product already existed: a data source of type
`file_upload` names a file, the sync reads that file through the shared
import chain and writes what it finds into the catalogue and the cache. The
source's config carries the file name (`file_path` or `filename`), the sheet
and the header row.

So the two halves did not meet. An operator who uploaded a spreadsheet got
its listings once, and a source of type `file_upload` could only be created
by hand - with the name of a file that had to be put into the uploads
directory of the deployment by hand as well. The panel's "sync" button on
such a source answered "the file of the source is not there".

## Options

1. **The upload endpoint keeps the file and creates the source.** The bytes
   are written under the uploads directory, and a `DataSourceDB` row of type
   `file_upload` is created (or updated) whose config names that file. The
   existing sync then reads it.
2. **The sync of a `file_upload` source reads a url instead of a path.** The
   config would carry a url; the sync would download it. The upload endpoint
   would not change at all.
3. **The upload endpoint keeps the file but creates no source.** The operator
   still has to create the source by hand; only the copy step is automated.
4. **The sync learns to read the uploaded file from the cache.** The file is
   not kept at all, and the source points at what the ingest already wrote.

## Reasoning

Option 2 was rejected first: it turns a local file into a network fetch. A
source that reads a url has to pass the SSRF checks, needs the file to be
reachable from the deployment, and fails the moment the machine that holds it
is not available. The file is already in the hands of the deployment — the
upload endpoint is the only place it exists — so reading it back from there
is the shorter path with fewer failure modes. It also breaks the security
model the data-sources router already enforces: `_resolve_source_file`
refuses any file outside the uploads directory, precisely so that a config
written by an operator cannot ask the deployment to read an arbitrary file.
A url would route around that boundary.

Option 4 was rejected because it makes the source a fiction. A source that
names a file has to be able to name a file that is there; a source that
points at the cache cannot be re-read after a restart of the deployment, and
its sync would answer with whatever the ingest happened to leave behind.

Option 3 automates half of the work and leaves the operator with the part
that is fiddly: creating the source row by hand, in the panel, with a file
path they have to know. That is the state the product is in today.

Option 1 is what was built. The upload already knows the bytes, the file
name, the sheet and the header row — everything the config of a source
carries. Writing the file and creating the row is the same knowledge applied
in one place.

The shape that this leaves behind is worth naming: **the upload is the
creation of a source, not a side effect of one.** A spreadsheet uploaded
twice with the same name is one source whose file and config were replaced,
not two sources. The source's `total_records` is the number of listings the
file carried.

## Evidence

Measured, not assumed:

- `apps/api/api/routers/admin.py:341` — `ingest_file_upload` writes the bytes
  to a `NamedTemporaryFile` and deletes it in the `finally` block; it creates
  no `DataSourceDB` row.
- `apps/api/api/routers/data_sources.py:439` — the sync of a `file_upload`
  source reads `config["file_path"] or config["filename"]` and resolves it
  through `_resolve_source_file`, which refuses a file outside
  `settings.uploads_dir` and a file that is not there.
- `apps/api/api/routers/data_sources.py:320` — `_run_sync` writes the
  properties it read into the vector store and into the cache, and counts
  the listings the source carries. The sync side of the feature already
  works; what was missing was a file for it to read.
- `apps/api/db/models.py:2085` — `DataSourceDB` carries the config as JSON
  and the docstring names the shape for a file upload:
  `{"filename": ..., "file_path": ..., "size_bytes": ..., "sheet_name": ...}`.

## Decision

The upload endpoint keeps the file it read under
`settings.uploads_dir / "sources" / <name><suffix>` and creates (or updates)
a data source of type `file_upload` whose config names that file, the sheet
and the header row. The answer carries the id and the name of the source, so
the panel can name it.

The keeping of the file is best-effort and reported: the ingest has already
succeeded by the time the file is written, so a file that cannot be kept
does not turn a successful upload into a failure — the answer says that no
source was created and why. A source that names a file that is not there is
worse than no source at all, so the failure is never silent.

## Consequences

- The panel's source list carries the uploaded sheet after the upload, and
  the "sync" button on it works.
- The file lives in the uploads directory of the deployment. A deployment
  that does not keep that directory across a container recreate loses the
  file, and the source then answers "the file of the source is not there" —
  honestly, and with the reason.
- The properties of the upload land in the catalogue twice over the lifetime
  of the source: once through the ingest, once through the first sync. The
  sync filters the listings the catalogue already holds, so a second sync
  adds nothing new.

## Revisit when

- The deployment mounts the uploads directory on a volume that survives a
  recreate — then the last consequence is gone and the note above is
  historical.
- A second kind of file arrives (a `.geojson`, a PDF) and the loaders read
  it; the config of a source already has the room for it.
