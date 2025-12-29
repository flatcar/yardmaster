CLI Reference
=============

Global Usage
------------

.. code-block:: bash

   yardmaster --help
   yardmaster -c /path/to/config.yaml status

Release Commands
----------------

.. code-block:: bash

   yardmaster release init https://github.com/org/repo/issues/1234
   yardmaster release run --pre alpha:4627.0.0 beta:4593.1.0 stable:4459.2.4
   yardmaster release run --post alpha:4627.0.0 beta:4593.1.0 stable:4459.2.4

Status
------

.. code-block:: bash

   yardmaster status
   yardmaster status --show-sdk

SDK Utilities
-------------

.. code-block:: bash

   yardmaster sdk determine alpha:4627.0.0 beta:4593.1.0

Retag
-----

.. code-block:: bash

   yardmaster retag alpha

Jenkins
-------

.. code-block:: bash

   yardmaster jenkins pr-build flatcar scripts 12345 --job release
