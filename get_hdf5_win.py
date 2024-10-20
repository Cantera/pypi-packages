# Copied from h5py. Licensed under the BSD 3-Clause license.
# Copyright (c) 2008 Andrew Collette and contributors
# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:

# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.

# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the
#    distribution.

# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
Script for downloading and building HDF5 on Windows
This does not support MPI, nor non-Windows OSes

This script may not completely clean up after itself, it is designed to run in a
CI environment which thrown away each time
"""

from os import environ, makedirs, walk, getcwd, chdir
from os.path import join as pjoin, exists
from tempfile import TemporaryFile, TemporaryDirectory
from sys import exit, stderr
from shutil import copy
from glob import glob
from subprocess import run
from zipfile import ZipFile
import requests

HDF5_URL = "https://github.com/HDFGroup/hdf5/releases/download/hdf5_{dotted_version}/hdf5-{dashed_version}.zip"
ZLIB_VERSION = environ["ZLIB_VERSION"]
LIBAEC_VERSION = environ["LIBAEC_VERSION"]

CMAKE_CONFIGURE_CMD = [
    "cmake",
    "-DBUILD_SHARED_LIBS:BOOL=ON",
    "-DCMAKE_BUILD_TYPE:STRING=RELEASE",
    "-DHDF5_BUILD_CPP_LIB=OFF",
    "-DHDF5_BUILD_HL_LIB=ON",
    "-DHDF5_BUILD_TOOLS:BOOL=OFF",
    "-DBUILD_TESTING:BOOL=OFF",
    "-DHDF5_BUILD_EXAMPLES:BOOL=OFF",
    "-DHDF5_ENABLE_Z_LIB_SUPPORT=ON",
    "-DHDF5_ENABLE_SZIP_SUPPORT=ON",
    "-DHDF5_ALLOW_EXTERNAL_SUPPORT:STRING=TGZ",
    "-DZLIB_PACKAGE_NAME:STRING=zlib",
    f"-DZLIB_TGZ_NAME:STRING=zlib-${ZLIB_VERSION}.tar.gz",
    f"-DZLIB_TGZ_ORIGPATH:STRING=https://github.com/madler/zlib/releases/download/v${ZLIB_VERSION}",
    "-DZLIB_USE_LOCALCONTENT:BOOL=OFF",
    "-DLIBAEC_PACKAGE_NAME:STRING=libaec",
    f"-DLIBAEC_TGZ_NAME:STRING=libaec-${LIBAEC_VERSION}.tar.gz",
    f"-DLIBAEC_TGZ_ORIGPATH:STRING=https://github.com/MathisRosenhauer/libaec/releases/download/v${LIBAEC_VERSION}",
    "-DLIBAEC_USE_LOCALCONTENT:BOOL=OFF",
]
CMAKE_BUILD_CMD = ["cmake", "--build"]
CMAKE_INSTALL_ARG = ["--target", "install", "--config", "Release"]
CMAKE_INSTALL_PATH_ARG = "-DCMAKE_INSTALL_PREFIX={install_path}"
CMAKE_HDF5_LIBRARY_PREFIX = ["-DHDF5_EXTERNAL_LIB_PREFIX=ct_"]
REL_PATH_TO_CMAKE_CFG = "hdf5-{version}"
DEFAULT_VERSION = "1.14.5"
VSVERSION_TO_GENERATOR = {
    "9": "Visual Studio 9 2008",
    "10": "Visual Studio 10 2010",
    "14": "Visual Studio 14 2015",
    "15": "Visual Studio 15 2017",
    "16": "Visual Studio 16 2019",
    "9-64": "Visual Studio 9 2008 Win64",
    "10-64": "Visual Studio 10 2010 Win64",
    "14-64": "Visual Studio 14 2015 Win64",
    "15-64": "Visual Studio 15 2017 Win64",
    "16-64": "Visual Studio 16 2019",
    "17-64": "Visual Studio 17 2022",
}


def get_dashed_version(version):
    dotted_version = version
    if len(version.split(".")) > 3:
        dashed_version = "-".join(version.rsplit(".", maxsplit=1))
    else:
        dashed_version = version
    return {"dotted_version": dotted_version, "dashed_version": dashed_version}


def download_hdf5(version, outfile):
    file = HDF5_URL.format(**get_dashed_version(version))

    print("Downloading " + file, file=stderr)
    r = requests.get(file, stream=True)
    try:
        r.raise_for_status()
    except requests.HTTPError:
        print(
            "Failed to download hdf5 version {version}, exiting".format(
                version=version
            ),
            file=stderr,
        )
        exit(1)
    else:
        for chunk in r.iter_content(chunk_size=None):
            outfile.write(chunk)


def build_hdf5(version, hdf5_file, install_path, cmake_generator, use_prefix):
    versions = get_dashed_version(version)
    try:
        with TemporaryDirectory() as hdf5_extract_path:
            generator_args = (
                ["-G", cmake_generator] if cmake_generator is not None else []
            )
            prefix_args = CMAKE_HDF5_LIBRARY_PREFIX if use_prefix else []

            with ZipFile(hdf5_file) as z:
                z.extractall(hdf5_extract_path)
            old_dir = getcwd()

            with TemporaryDirectory() as new_dir:
                chdir(new_dir)
                cfg_cmd = (
                    CMAKE_CONFIGURE_CMD
                    + [
                        get_cmake_install_path(install_path),
                        get_cmake_config_path(
                            versions["dashed_version"], hdf5_extract_path
                        ),
                    ]
                    + generator_args
                    + prefix_args
                )
                print(f"Configuring HDF5 version {versions["dotted_version"]}...")
                print(" ".join(cfg_cmd), file=stderr)
                run(cfg_cmd, check=True)

                build_cmd = (
                    CMAKE_BUILD_CMD
                    + [
                        ".",
                    ]
                    + CMAKE_INSTALL_ARG
                )
                print(f"Building HDF5 version {version}...")
                print(" ".join(build_cmd), file=stderr)
                run(build_cmd, check=True)

                print(
                    f"Installed HDF5 version {version} to {install_path}", file=stderr
                )
                chdir(old_dir)
    except OSError as e:
        if e.winerror == 145:
            print("Hit the rmtree race condition, continuing anyway...", file=stderr)
        else:
            raise
    for f in glob(pjoin(install_path, "bin/*.dll")):
        copy(f, pjoin(install_path, "lib"))


def get_cmake_config_path(version, extract_point):
    return pjoin(extract_point, REL_PATH_TO_CMAKE_CFG.format(version=version))


def get_cmake_install_path(install_path):
    if install_path is not None:
        return CMAKE_INSTALL_PATH_ARG.format(install_path=install_path)
    return " "


def hdf5_install_cached(install_path):
    if exists(pjoin(install_path, "lib", "hdf5.dll")):
        return True
    return False


def main():
    install_path = environ.get("HDF5_DIR")
    version = environ.get("HDF5_VERSION", DEFAULT_VERSION)
    vs_version = environ.get("HDF5_VSVERSION")
    use_prefix = True if environ.get("HDF5_USE_PREFIX") is not None else False

    if install_path is not None:
        if not exists(install_path):
            makedirs(install_path)
    if vs_version is not None:
        cmake_generator = VSVERSION_TO_GENERATOR[vs_version]
    else:
        cmake_generator = None

    if not hdf5_install_cached(install_path):
        with TemporaryFile() as f:
            download_hdf5(version, f)
            build_hdf5(version, f, install_path, cmake_generator, use_prefix)
    else:
        print("using cached hdf5", file=stderr)
    if install_path is not None:
        print("hdf5 files: ", file=stderr)
        for dirpath, dirnames, filenames in walk(install_path):
            for file in filenames:
                print(" * " + pjoin(dirpath, file))


if __name__ == "__main__":
    main()
