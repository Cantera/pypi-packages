#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["cmake>=4.4,<4.5", "httpx2"]
# ///
"""Build the native dependencies for macOS and Windows Cantera wheels."""

import argparse
import asyncio
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

import httpx2

SCRIPT = Path(__file__).resolve()
CONFIG = SCRIPT.with_name("dependencies.toml")
VERSION_KEYS = (
    "hdf5",
    "libaec",
    "zlib",
    "highfive",
    "sundials",
    "yaml-cpp",
    "fmt",
    "eigen",
)
MARKER = ".build-complete.json"


def load_versions(path: Path = CONFIG) -> dict[str, str]:
    versions = tomllib.loads(path.read_text(encoding="utf-8")).get("versions", {})
    if not isinstance(versions, dict):
        raise TypeError(f"{path}: versions must be a TOML table")
    for name in VERSION_KEYS:
        value = versions.get(name)
        if not isinstance(value, str) or not re.fullmatch(
            r"[0-9]+(?:\.[0-9]+)+", value
        ):
            raise ValueError(
                f"{path}: versions.{name} must be a dotted numeric version string"
            )
    return versions


@dataclass(frozen=True)
class Dependency:
    name: str
    url: str
    prefix: Path
    options: tuple[str, ...]


def hdf5_dependency(versions: dict[str, str], prefix: Path) -> Dependency:
    hdf5 = versions["hdf5"]
    libaec = versions["libaec"]
    zlib = versions["zlib"]
    return Dependency(
        name="hdf5",
        url=f"https://github.com/HDFGroup/hdf5/releases/download/hdf5_{hdf5}/hdf5-{hdf5}.tar.gz",
        prefix=prefix,
        options=(
            "-DHDF5_ENABLE_Z_LIB_SUPPORT:BOOL=ON",
            "-DHDF5_ENABLE_SZIP_SUPPORT:BOOL=ON",
            "-DHDF5_BUILD_EXAMPLES:BOOL=OFF",
            "-DHDF5_BUILD_TOOLS:BOOL=OFF",
            "-DBUILD_TESTING:BOOL=OFF",
            "-DHDF5_ALLOW_EXTERNAL_SUPPORT:STRING=TGZ",
            "-DZLIB_PACKAGE_NAME:STRING=zlib",
            f"-DZLIB_TGZ_NAME:STRING=zlib-{zlib}.tar.gz",
            f"-DZLIB_TGZ_ORIGPATH:STRING=https://github.com/madler/zlib/releases/download/v{zlib}",
            "-DZLIB_USE_LOCALCONTENT:BOOL=OFF",
            "-DLIBAEC_PACKAGE_NAME:STRING=libaec",
            f"-DLIBAEC_TGZ_NAME:STRING=libaec-{libaec}.tar.gz",
            f"-DLIBAEC_TGZ_ORIGPATH:STRING=https://github.com/MathisRosenhauer/libaec/releases/download/v{libaec}",
            "-DLIBAEC_USE_LOCALCONTENT:BOOL=OFF",
            "-DHDF_PACKAGE_NAMESPACE:STRING=ct_",
        ),
    )


def highfive_dependency(highfive: str, prefix: Path, hdf5_prefix: Path) -> Dependency:
    return Dependency(
        name="highfive",
        url=f"https://github.com/highfive-devs/highfive/archive/refs/tags/v{highfive}.tar.gz",
        prefix=prefix,
        options=(
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            f"-DHDF5_ROOT={hdf5_prefix.as_posix()}",
            "-DHIGHFIVE_USE_BOOST:BOOL=OFF",
            "-DHIGHFIVE_UNIT_TESTS:BOOL=OFF",
            "-DHIGHFIVE_EXAMPLES:BOOL=OFF",
            "-DHIGHFIVE_BUILD_DOCS:BOOL=OFF",
        ),
    )


def sundials_dependency(sundials: str, prefix: Path, system: str) -> Dependency:
    options = (
        "-DEXAMPLES_INSTALL=OFF",
        "-DEXAMPLES_ENABLE_C=OFF",
        "-DBUILD_ARKODE=OFF",
        "-DBUILD_CVODE=OFF",
        "-DBUILD_IDA=OFF",
        "-DBUILD_KINSOL=OFF",
        "-DBUILD_CPODES=OFF",
        "-DBUILD_FORTRAN_MODULE_INTERFACE=OFF",
    )
    if system == "Darwin":
        options += (
            "-DENABLE_LAPACK=ON",
            "-DBLA_VENDOR=Apple",
            "-DSUNDIALS_LAPACK_CASE=LOWER",
            "-DSUNDIALS_LAPACK_UNDERSCORES=NONE",
        )
    return Dependency(
        name="sundials",
        url=f"https://github.com/LLNL/sundials/releases/download/v{sundials}/sundials-{sundials}.tar.gz",
        prefix=prefix,
        options=options,
    )


def yaml_cpp_dependency(yaml: str, prefix: Path) -> Dependency:
    return Dependency(
        name="yaml-cpp",
        url=f"https://github.com/jbeder/yaml-cpp/archive/refs/tags/yaml-cpp-{yaml}.tar.gz",
        prefix=prefix,
        options=(
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            "-DCMAKE_INSTALL_LIBDIR:STRING=lib",
            "-DYAML_CPP_FORMAT_SOURCE:BOOL=OFF",
            "-DBUILD_TESTING:BOOL=OFF",
            "-DBUILD_SHARED_LIBS:BOOL=ON",
        ),
    )


def fmt_dependency(fmt: str, prefix: Path) -> Dependency:
    return Dependency(
        name="fmt",
        url=f"https://github.com/fmtlib/fmt/releases/download/{fmt}/fmt-{fmt}.zip",
        prefix=prefix,
        options=(
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DFMT_DOC:BOOL=OFF",
            "-DFMT_TEST:BOOL=OFF",
            "-DBUILD_SHARED_LIBS:BOOL=ON",
        ),
    )


def eigen_dependency(eigen: str, prefix: Path) -> Dependency:
    return Dependency(
        name="eigen",
        url=f"https://gitlab.com/libeigen/eigen/-/archive/{eigen}/eigen-{eigen}.tar.bz2",
        prefix=prefix,
        options=(
            "-DEIGEN_BUILD_DOC:BOOL=OFF",
            "-DEIGEN_BUILD_DEMOS:BOOL=OFF",
            "-DEIGEN_BUILD_CMAKE_PACKAGE:BOOL=ON",
            "-DBUILD_TESTING:BOOL=OFF",
        ),
    )


def dependency_specs(
    project: Path, versions: dict[str, str], system: str
) -> list[Dependency]:
    prefixes = {
        name: project / "cache" / name / version for name, version in versions.items()
    }
    return [
        hdf5_dependency(versions, prefixes["hdf5"]),
        highfive_dependency(
            versions["highfive"], prefixes["highfive"], prefixes["hdf5"]
        ),
        sundials_dependency(versions["sundials"], prefixes["sundials"], system),
        yaml_cpp_dependency(versions["yaml-cpp"], prefixes["yaml-cpp"]),
        fmt_dependency(versions["fmt"], prefixes["fmt"]),
        eigen_dependency(versions["eigen"], prefixes["eigen"]),
    ]


def extract_source(archive: Path, staging: Path) -> Path:
    """Extract without stripping names, then select the unique top-level CMake project."""
    staging.mkdir()
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as source:
            # Check all entries before writing, including Windows drive/UNC paths.
            for member in source.infolist():
                name = member.filename
                target = staging / name
                if (
                    PureWindowsPath(name).drive
                    or "\\" in name
                    or not target.resolve().is_relative_to(staging.resolve())
                    or (member.external_attr >> 16) & 0o170000 == 0o120000
                ):
                    raise ValueError(f"Unsafe ZIP entry in {archive}: {name}")
            source.extractall(staging)
    else:
        with tarfile.open(archive, "r:*") as source:
            source.extractall(staging, filter="data")

    candidates = [
        p for p in staging.rglob("CMakeLists.txt") if p.is_file() and not p.is_symlink()
    ]
    if not candidates:
        raise ValueError(f"{archive}: no CMakeLists.txt found")
    depth = min(len(p.relative_to(staging).parts) for p in candidates)
    roots = sorted(p for p in candidates if len(p.relative_to(staging).parts) == depth)
    if len(roots) != 1:
        raise ValueError(
            f"{archive}: ambiguous source roots: " + ", ".join(str(p) for p in roots)
        )
    root = roots[0].parent
    print(f"Source root for {archive.name}: {root}", flush=True)
    return root


async def download(client: httpx2.AsyncClient, url: str, destination: Path) -> None:
    print(f"Downloading {url}", flush=True)
    try:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            with destination.open("wb") as output:
                async for chunk in response.aiter_bytes():
                    output.write(chunk)
    except BaseException:
        destination.unlink(missing_ok=True)
        print(
            f"Download failed for {url}; working directory retained: {destination.parent}",
            file=sys.stderr,
            flush=True,
        )
        raise


async def download_archives(
    dependencies: list[Dependency], workdirs: dict[str, Path]
) -> None:
    async with httpx2.AsyncClient(follow_redirects=True, timeout=120) as client:
        results = await asyncio.gather(
            *(
                download(
                    client,
                    dependency.url,
                    workdirs[dependency.name] / dependency.url.rsplit("/", 1)[-1],
                )
                for dependency in dependencies
            ),
            return_exceptions=True,
        )
    # Let every transfer close before raising, and never build after a failed download.
    for result in results:
        if isinstance(result, BaseException):
            raise result


def run_command(command: list[str], env: dict[str, str]) -> None:
    print(f"Running: {subprocess.list2cmdline(command)}", flush=True)
    subprocess.run(command, env=env, check=True)


def is_complete(dependency: Dependency, fingerprint: str) -> bool:
    try:
        return json.loads((dependency.prefix / MARKER).read_text(encoding="utf-8")) == {
            "fingerprint": fingerprint
        }
    except (OSError, ValueError):
        return False


def build_dependency(
    dependency: Dependency,
    fingerprint: str,
    cmake: str,
    generator: str,
    env: dict[str, str],
    work: Path,
) -> None:
    try:
        if dependency.prefix.exists():
            shutil.rmtree(dependency.prefix)
        dependency.prefix.mkdir(parents=True)
        archive = work / dependency.url.rsplit("/", 1)[-1]
        source = extract_source(archive, work / "source")
        build = source / "build"
        build.mkdir(exist_ok=True)
        run_command(
            [
                cmake,
                "-S",
                str(source),
                "-B",
                str(build),
                "-G",
                generator,
                "-DCMAKE_BUILD_TYPE=Release",
                f"-DCMAKE_INSTALL_PREFIX={dependency.prefix.as_posix()}",
                *dependency.options,
            ],
            env,
        )
        run_command(
            [
                cmake,
                "--build",
                str(build),
                "--target",
                "install",
                "--config",
                "Release",
            ],
            env,
        )
        (dependency.prefix / MARKER).write_text(
            json.dumps({"fingerprint": fingerprint}), encoding="utf-8"
        )
    except BaseException:
        print(
            f"Build failed for {dependency.name}; working directory retained: {work}",
            file=sys.stderr,
            flush=True,
        )
        raise
    else:
        shutil.rmtree(work)


def build_all(
    dependencies: list[Dependency],
    fingerprint: str,
    cmake: str,
    generator: str,
    env: dict[str, str],
) -> None:
    hdf5_rebuild = any(
        dependency.name == "hdf5" and not is_complete(dependency, fingerprint)
        for dependency in dependencies
    )
    if hdf5_rebuild:
        for dependency in dependencies:
            if dependency.name == "highfive":
                (dependency.prefix / MARKER).unlink(missing_ok=True)

    pending = []
    for dependency in dependencies:
        if is_complete(dependency, fingerprint):
            print(f"Using cached {dependency.name}: {dependency.prefix}", flush=True)
        else:
            pending.append(dependency)
    if not pending:
        return

    workdirs = {
        dependency.name: Path(
            tempfile.mkdtemp(
                prefix=f"{dependency.name}-",
                dir=env.get("RUNNER_TEMP") or None,
            )
        )
        for dependency in pending
    }
    asyncio.run(download_archives(pending, workdirs))
    for dependency in pending:
        build_dependency(
            dependency, fingerprint, cmake, generator, env, workdirs[dependency.name]
        )


def environment_settings(dependencies: list[Dependency], system: str) -> dict[str, str]:
    paths = {
        dependency.name: dependency.prefix.as_posix() for dependency in dependencies
    }
    settings = {
        name: paths[key]
        for name, key in (
            ("HDF5_ROOT", "hdf5"),
            ("HighFive_ROOT", "highfive"),
            ("SUNDIALS_ROOT", "sundials"),
            ("YAML_CPP_ROOT", "yaml-cpp"),
            ("Eigen3_ROOT", "eigen"),
            ("FMT_ROOT", "fmt"),
        )
    }
    if system == "Darwin":
        library_path = ":".join(
            f"{paths[name]}/lib" for name in ("hdf5", "sundials", "yaml-cpp", "fmt")
        )
        settings.update(
            MACOSX_DEPLOYMENT_TARGET="11.0", REPAIR_LIBRARY_PATH=library_path
        )
    else:
        settings.update(
            {
                f"{key}_LIB_DIR": f"{paths[name]}/bin"
                for key, name in (
                    ("HDF5", "hdf5"),
                    ("SUNDIALS", "sundials"),
                    ("YAML_CPP", "yaml-cpp"),
                    ("FMT", "fmt"),
                )
            }
        )
    return settings


def export_environment(settings: dict[str, str]) -> None:
    text = "".join(f"{name}={value}\n" for name, value in settings.items())
    print(text, end="", flush=True)
    if destination := os.environ.get("GITHUB_ENV"):
        with open(destination, "a", encoding="utf-8", newline="\n") as output:
            output.write(text)


def build_fingerprint(
    config: Path,
    system: str,
    architecture: str,
    cmake_version: str,
    generator: str,
    settings: dict[str, str],
) -> str:
    digest = hashlib.sha256(SCRIPT.read_bytes() + b"\0" + config.read_bytes())
    digest.update(
        json.dumps(
            [system, architecture, cmake_version, generator, settings], sort_keys=True
        ).encode()
    )
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "project_path",
        type=Path,
        help="Project directory containing the dependency cache",
    )
    args = parser.parse_args()
    system = platform.system()
    if system not in {"Darwin", "Windows"}:
        parser.error(f"Unsupported build platform: {system}; expected macOS or Windows")
    project = args.project_path.resolve()
    if any(c in str(project) for c in "\r\n"):
        parser.error("Project path must not contain newlines")
    versions = load_versions()
    # Resolve the native binary from the uv-managed package, never a system CMake.
    from cmake import CMAKE_BIN_DIR

    cmake = str(Path(CMAKE_BIN_DIR) / ("cmake.exe" if system == "Windows" else "cmake"))
    cmake_version = subprocess.run(
        [cmake, "--version"], check=True, capture_output=True, text=True
    ).stdout.strip()
    print(cmake_version, flush=True)
    generator = "Ninja" if system == "Darwin" else "Visual Studio 18 2026"
    dependencies = dependency_specs(project, versions, system)
    settings = environment_settings(dependencies, system)
    env = os.environ.copy()
    if system == "Darwin":
        env["MACOSX_DEPLOYMENT_TARGET"] = settings["MACOSX_DEPLOYMENT_TARGET"]
    fingerprint = build_fingerprint(
        CONFIG, system, platform.machine(), cmake_version, generator, settings
    )
    build_all(dependencies, fingerprint, cmake, generator, env)
    export_environment(settings)


if __name__ == "__main__":
    try:
        main()
    except (
        OSError,
        httpx2.HTTPError,
        TypeError,
        ValueError,
        subprocess.CalledProcessError,
        tarfile.TarError,
        zipfile.BadZipFile,
    ) as error:
        sys.exit(f"Dependency build failed: {error}")
