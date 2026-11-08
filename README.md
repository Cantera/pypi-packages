# Cantera PyPI Packages

This repo contains setup to build and publish packages to PyPI. It uses [`cibuildwheel`](https://cibuildwheel.pypa.io/en/stable/) to manage the builds.

Docker images for the manylinux builds are hosted at <https://github.com/Cantera/cantera-base-manylinux>.

For macOS and Windows, the Python script in this repo builds and installs the required dependencies for Cantera wheel builds.

Build these dependencies with:

```sh
uv run build_dependencies.py /path/to/project
```

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and the
native compiler toolchain first. macOS also requires Ninja. The script uses
Python 3.12 or newer and uv installs CMake 4.4 into the script environment.
Windows builds use the Visual Studio 18 2026 generator.

Edit `dependencies.toml` to change native dependency versions. The file is loaded
relative to the script, so the command works from any working directory.
Dependencies install into `<PROJECT_PATH>/cache/<name>/<version>`. Successful
installs have completion records; missing or outdated records cause a clean
rebuild. Changes to the script, configuration, platform, CMake version, or build
settings invalidate those records. Rebuilding HDF5 also rebuilds HighFive.

Archives needed for uncached dependencies download concurrently using httpx2,
then build in dependency order. Archives are extracted without stripping path components. The unique shallowest
`CMakeLists.txt` identifies the source root, and CMake uses its `build`
subdirectory. Logs report download URLs, selected roots, and build commands.
Working directories use `RUNNER_TEMP` when set, or the system temporary directory.
Failed builds retain their working directory for inspection; successful builds
remove it.

The script prints dependency environment settings and appends them to
`GITHUB_ENV` in GitHub Actions. For local downstream builds, set the printed
variables in your shell.
