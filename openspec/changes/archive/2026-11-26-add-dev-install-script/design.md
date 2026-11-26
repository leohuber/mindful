# Design

## Context

`scripts/build_addon.py` writes `dist/mindful.ankiaddon` from an explicit file allowlist. The release installer targets the normal Anki base and expects a versioned release archive; it is not suitable for this temporary workflow. The installed Anki 26.09.4 launcher advertises `-b/--base`, but its process lifetime and behavior with another instance require validation.

## Goals / Non-Goals

**Goals:**

- Exercise exactly the built archive in an isolated Anki base.
- Make ownership and cleanup of temporary data explicit and safe.
- Keep the workflow testable without launching Anki in unit tests.

**Non-Goals:**

- Copying or syncing an existing profile, installing into the normal base, or changing the release installer.
- Live source reload, persistent development profiles, and automatic cleanup of previously retained directories.
- Cross-platform launcher support in this change.

## Decisions

1. **Build, then extract into a private temporary base.** A Python development script can invoke the existing builder, create a unique temporary directory, and extract the resulting archive into `addons21/mindful`. Use the archive rather than copying or symlinking the source, so missing packaged files are observable. The script must use only its newly created directory for installation and cleanup; reject unsafe archive entries rather than extracting outside it.

2. **Launch the macOS Anki executable directly with `--base`.** Use the executable at `/Applications/Anki.app/Contents/MacOS/Anki`, pass the temporary base as a distinct argument, and wait for the actual Anki session to end. Report a missing executable or failed launch clearly. Refuse to start when Anki is already running or its state cannot be determined, preventing single-instance forwarding from silently defeating isolation. Verify the supported launcher really remains tied to the GUI session; if it delegates or detaches, monitor the actual session reliably or retain the directory rather than assuming it has ended.

3. **Dispose after a confirmed successful session.** Tell the developer the temporary location and that all data there is disposable. Once the actual Anki session is confirmed to have exited successfully, remove only the directory created for that invocation. On an interrupted, failed, or uncertain session, retain it and print its path when cleanup cannot be shown safe; never delete it while Anki may still use it. A fresh empty base avoids copying real collection data; warn against enabling sync because it can affect remote data.

4. **Separate orchestration from external operations for unit tests.** Use temporary directories and substitutes for process inspection, building, and launching to exercise sequencing, isolation, failures, and cleanup. Validate the real macOS launcher separately with a manual smoke check using a disposable base and Anki closed, without touching the normal installation.

## Risks / Trade-offs

- **Anki process handoff or concurrent start** → Check for existing processes before launching, verify actual launcher behavior on the supported version, and retain the sandbox whenever session termination is uncertain. Avoid claiming isolation based solely on a successful child exit.
- **Unrecoverable test data after normal exit** → Clearly announce automatic deletion and document that the base is disposable.
- **Interruption leaves temporary files** → Report retained paths where possible; manual removal is outside the command's automatic cleanup scope.
- **Fresh collections lack real-world data** → Developers create test data in the sandbox; copying real profiles is explicitly outside this change.

## Migration Plan

Add the command and documentation without altering existing install paths. Remove the development command to roll back; retained temporary directories can be inspected and removed manually after confirming that no Anki process uses them.
