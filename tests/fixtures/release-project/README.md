# Isolated release fixture

The target database starts at version `v1` with rows in `customer(name)`. The candidate application `v3` reads `customer(display_name)`. The local target files stand in for the test environment. Release history spans both candidate changes in `changes/`.

Create a fresh target with `python seed.py <target-directory>`. Use only a temporary copy. The project has no remote service or secrets. A release executor must supply the needed migration, check preserved rows and idempotent recovery, then record the actual release result. `release.sh` only deploys the application file; it does not migrate data.
