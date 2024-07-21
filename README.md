# Cantera PyPI Packages

This repo contains setup to build and publish packages to PyPI. It uses [`cibuildwheel`](https://cibuildwheel.pypa.io/en/stable/) to manage the builds.

Docker images for the manylinux builds are hosted at <https://github.com/Cantera/hdf5-boost-manylinux>.

For macOS and Windows, the scripts in this repo will build and install the required HDF5 dependencies for Cantera wheel builds. On macOS, we support `szip` (via `libaec`) and `zlib`. On Windows, we only support `zlib`.
