Release Workflow
================

Release State
-------------

``yardmaster release init`` parses the GitHub issue title and writes the planned
versions into ``.yardmaster/release.json``. Subsequent ``release run`` commands
can reuse this state when specs are not supplied.

Pre-Release Steps
-----------------

The pre-release phase performs the following actions:

- For alpha major releases, create a release branch using
  ``flatcar-build-scripts/mirror-repos-branch``.
- Tag each channel release via ``flatcar-build-scripts/tag-release`` using
  ``VERSION``, ``SDK_VERSION``, and ``CHANNEL`` environment variables.
- Trigger Jenkins builds for SDK or packages as needed.

Post-Release Steps
------------------

The post-release phase runs after pre-release steps complete. The current
implementation reuses the same validation flow and Jenkins triggers as needed.

SDK Resolution
--------------

Yardmaster determines SDK versions by inspecting the previous release stream and
reading ``version.txt`` from release URLs. For new streams, it may consult tags
from the local scripts repository to locate the latest compatible SDK.
