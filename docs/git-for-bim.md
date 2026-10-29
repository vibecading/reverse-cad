# Review before sync: version control for building models

Status: design note, nothing built. Claims about the Revit API marked
*(check)* are from the API documentation and have not been tried.

## The problem

A shared Revit model works like a repository where everyone pushes straight to
`main`. Each *Synchronize with Central* writes a person's changes into the one
central model with no review, no diff and no way to see afterwards what a given
sync did. On one person's model this is fine. On a team model it is where
deleted walls, moved levels and broken families come from, and nobody can say
which sync did it.

Agents make this worse. An agent that edits a model through the API (pyRevit
scripts, MCP servers, the vendors' own assistants) produces exactly the change
a reviewer would most want to see before it lands.

What software teams have and building teams lack is small: a change set you
can look at before it merges (red for removed, green for added), a log of who
changed what, and a way to say no.

## What exists

- **Bonsai (BlenderBIM) Git**: revisions, branches and a 3D diff for models
  that are native IFC files. Works, but only if the team models in IFC.
- **ifcmerge** (Bruno Postle): three-way merge of IFC files, again for native
  IFC; a Revit export changes too much between exports to merge.
- **A common data environment on a git forge** (forgejo plus IDS checks and BCF
  issues) has been proposed by the same author; not built.
- **Speckle** keeps versions of models sent from Revit and other tools. Not
  reviewed for this note: it versions what you send it, it does not stand in
  front of Revit's own sync.
- For Revit's own worksharing no tool was found that reviews a change set
  before it reaches the central model.

## MVP: a Revit add-in that reviews before sync

1. **Collect.** Subscribe to `Application.DocumentChanged`. Each event gives
   the ids of added, modified and deleted elements. Keep a running change set
   since the last sync, per document.
2. **Remember what will be deleted.** A deleted element's geometry can no
   longer be read. Keep a cache of each element's bounding box (and later a
   coarse mesh) refreshed at every sync and on every modify, so deleted ones
   can still be drawn.
3. **Show.** A dockable pane lists the change set by category and level; a 3D
   view highlights added elements green, modified amber, deleted red. Draw the
   highlights with `DirectContext3D` (transient graphics) *(check)* so the
   review itself never edits the model: a view override inside a transaction
   would become part of the next sync.
4. **Gate.** `DocumentSynchronizingWithCentral` fires before a sync and can be
   cancelled *(check: `IsCancellable`)*. If the current change set has not been
   approved in the pane, cancel with a message that opens the pane. Approval
   records the reviewer and the sync comment.
5. **Journal.** On `DocumentSynchronizedWithCentral`, write the change set as
   one JSON file per changed element (category, type, key parameters, location,
   bounding box, the element's `UniqueId`) into a git repository next to the
   project, and commit it with the sync comment as the message. `git log` is
   then the model's history, and any two commits can be diffed and drawn red
   and green.

Known gaps: *Reload Latest* pulls others' changes without the sync events, so
the change set must be rebuilt from the journal; elements changed by Revit's
own regeneration (joins, hosted elements) appear as modified without anyone
touching them and need filtering; worksets and element ownership are left to
Revit.

What it does not give: branches. A central model has one line of history.
An agent's work can still be reviewed: run the agent on a detached copy,
collect its change set the same way, and replay the approved part on the real
model as a script.

## In an application built on a parameter graph

The reverse-engineering tools here already describe a building as text: named
parameters, expressions over them, and the geometry generated from that. A
model stored this way is version-controlled for free:

- **the diff is semantic**: `W: 8.74 -> 9.00` instead of a binary blob;
- **the geometric diff is computed**, not stored: generate both versions, compare
  element by element, draw removed red and added green;
- **merge conflicts are found by the dependency graph** (`tools/dag.py`): two
  branches that change different parameters feeding the same element conflict
  even though the text merges cleanly, and the tool can say so;
- **checks travel with the model**: the `truth` values and rule checks in a
  spec are tests that run on every commit.

That is the case for keeping the model as data, not code, in a future
application: git, review and agents come with it.

## On the office's own git server

No new server is needed. An office runs GitLab CE, Gitea or Forgejo on its
own machine; the model files live there like code. Two pieces make it a
review gate:

- on workstations, `pg` is registered as git's merge driver and diff
  converter for model files, so merges stop on design conflicts and diffs
  show evaluated models;
- on the server, a CI job runs on every merge request: the model's checks,
  the design diff with a red/green picture, and a dry-run merge against the
  target branch. A server merges with plain git when someone presses its
  merge button, so the merge driver never runs there; the CI job with
  "pipelines must succeed" is what enforces review.

Both are in vibecading-model (`ci/`), tested on a local repository: the job
fails on a failing check and on a design conflict. For an office without IT
staff the lightest package is Forgejo with one CI runner; not packaged yet.

## Next steps

1. Prototype the semantic and geometric diff on two versions of an existing
   spec (no Revit needed).
2. Try the three *(check)* API points in a Revit sandbox before writing the add-in.
3. Ask two or three teams that work on shared Revit models how they find out
   what a bad sync did today, before building anything.
