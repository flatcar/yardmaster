Getting Started
===============

Requirements
------------

- Python 3.9+
- ``uv`` for environment and dependency management (recommended)

Install (from source)
---------------------

.. code-block:: bash

   uv venv .venv
   source .venv/bin/activate
   uv pip install -e .

Initialize Configuration
------------------------

Yardmaster expects a ``.yardmaster.yaml`` file in the working directory.

.. code-block:: bash

   yardmaster init

Export required environment variables for Jenkins and optional GPG signing:

.. code-block:: bash

   export JENKINS_USER=...
   export JENKINS_TOKEN=...
   export GPG_KEY_ID=...

Quick Release Flow
------------------

.. code-block:: bash

   yardmaster release init https://github.com/org/repo/issues/1234
   yardmaster release run --pre alpha:4627.0.0 beta:4593.1.0 stable:4459.2.4
   yardmaster release run --post alpha:4627.0.0 beta:4593.1.0 stable:4459.2.4
