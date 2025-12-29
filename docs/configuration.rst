Configuration
=============

Yardmaster uses a YAML configuration file, typically ``.yardmaster.yaml``.

Key Sections
------------

``repositories``
  Metadata about the upstream repos. The ``scripts`` entry is used for tagging.

``paths``
  Local paths used by Yardmaster. ``build_scripts`` must point to the
  ``flatcar-build-scripts`` checkout and ``scripts`` must point to the
  ``scripts`` checkout.

``jenkins``
  Jenkins connection settings and job names. Credentials are usually supplied
  via ``JENKINS_USER`` and ``JENKINS_TOKEN`` environment variables.

``channels``
  Per-channel release URLs and descriptions used by status and SDK detection.

``sdk``
  Controls SDK auto-detection and fallback behavior.

``validation``
  Release validation toggles (unique channels, version progression checks).

Minimal Example
---------------

.. code-block:: yaml

   paths:
     build_scripts: /path/to/flatcar-build-scripts
     scripts: /path/to/scripts

   jenkins:
     url: http://jenkins.example.com:8080
     username: ${JENKINS_USER}
     token: ${JENKINS_TOKEN}

   channels:
     alpha:
       release_url: https://alpha.release.flatcar-linux.net
