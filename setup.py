#!/usr/bin/env python3
# This script was automatically generated by packaging.
# Manual additions:
# - Support environment markers
# - Use lib3to2 if running from Python 2

import glob
import os
import re
import sys
import shutil
import subprocess

from distutils.version import LooseVersion

try:
    from setuptools import setup, Command
except ImportError:
    from distutils.core import setup, Command

try:
    from configparser import RawConfigParser
except ImportError:
    from ConfigParser import RawConfigParser

try:
    import multiprocessing
    NUM_PROCESSES = multiprocessing.cpu_count()
except (ImportError, NotImplementedError):
    NUM_PROCESSES = 1

try:
    from lib3to2.main import main as lib3to2_main

    def run_3to2(args=[]):
        return lib3to2_main("lib3to2.fixes", BASE_ARGS_3TO2 + args)
except ImportError:
    def run_3to2(args=[]):
        return subprocess.call(["3to2"] + BASE_ARGS_3TO2 + args)

# For environment markers
import platform #@UnusedImport

python_version = "%s.%s" % sys.version_info[:2]
python_full_version = sys.version.split()[0]

PY2K_DIR = "py2k"
USE_AWKWARD_DUET_WORKAROUNDS = True
BASE_ARGS_3TO2 = [
    "-w", "-n", "--no-diffs",
    "-j", str(NUM_PROCESSES),
]

MULTI_OPTIONS = set([
    ("global", "commands"),
    ("global", "compilers"),
    ("global", "setup_hooks"),
    ("metadata", "platform"),
    ("metadata", "supported_platform"),
    ("metadata", "classifier"),
    ("metadata", "requires_dist"),
    ("metadata", "provides_dist"),
    ("metadata", "obsoletes_dist"),
    ("metadata", "requires_external"),
    ("metadata", "project_url"),
    ("files", "packages"),
    ("files", "modules"),
    ("files", "scripts"),
    ("files", "extra_files"),
])

ENVIRON_OPTIONS = set([
    ("metadata", "classifier"),
    ("metadata", "requires_dist"),
    ("metadata", "provides_dist"),
    ("metadata", "obsoletes_dist"),
    ("metadata", "requires_python"),
    ("metadata", "requires_external"),
])

if USE_AWKWARD_DUET_WORKAROUNDS:
    # Awkward Duet 1.1a2 fails with properties (getter followed by a setter).
    BASE_ARGS_3TO2 += ["-x", "funcdecorator"]

    def fix_func_annotations(file_list):
        """Remove empty func_annotations.

        AttributeError: 'property' object has no attribute 'func_annotations'
        Needed until Awkward Duet gets fixed.
        """
        if not isinstance(file_list, list):
            file_list = [file_list]

        for file in file_list:
            f = open(file, "rb")
            try:
                contents = f.read()
            finally:
                f.close()

            new_contents = re.sub(
                br"[ \t]*\w+\.func_annotations = {}\r?\n",
                b"",
                contents
            )

            if len(new_contents) != len(contents):
                f = open(file, "wb")
                try:
                    contents = f.write(new_contents)
                finally:
                    f.close()

    _run_3to2 = run_3to2

    def run_3to2(args=[]):
        _run_3to2(args)
        fix_func_annotations(args)


def split_multiline(value):
    """Split a multiline string into a list, excluding blank lines.
    """
    return [element for element in
            (line.strip() for line in value.split("\n"))
            if element]


def eval_environ(value):
    """Evaluate environment markers.
    """
    def eval_environ_str(value):
        parts = value.split(";")
        if len(parts) < 2:
            new_value = parts[0]
        else:
            expr = parts[1].lstrip()
            if not re.match("^((\\w+(\\.\\w+)?|'.*?'|\".*?\")\\s+"
                            "(in|==|!=|not in)\\s+"
                            "(\\w+(\\.\\w+)?|'.*?'|\".*?\")"
                            "(\s+(or|and)\s+)?)+$", expr):
                raise ValueError("bad environment marker: %r" % (expr,))
            expr = re.sub(r"(platform.\w+)", r"\1()", expr)
            new_value = parts[0] if eval(expr) else None
        return new_value

    if isinstance(value, list):
        new_value = []
        for element in value:
            element = eval_environ_str(element)
            if element is not None:
                new_value.append(element)
    elif isinstance(value, str):
        new_value = eval_environ_str(value)
    else:
        new_value = value

    return new_value


def get_cfg_option(config, section, option):
    if config.has_option(section, option):
        value = config.get(section, option)
    else:
        option = option.replace("_", "-")
        if config.has_option(section, option):
            value = config.get(section, option)
        else:
            if (section, option) in MULTI_OPTIONS:
                return []
            else:
                return ""
    if (section, option) in MULTI_OPTIONS:
        value = split_multiline(value)
    if (section, option) in ENVIRON_OPTIONS:
        value = eval_environ(value)
    return value


def cfg_to_args(config):
    """Compatibility helper to use setup.cfg in setup.py.

    This functions uses an existing setup.cfg to generate a dictionnary of
    keywords that can be used by distutils.core.setup(**kwargs).  It is used
    by generate_setup_py.

    *file* is the path to the setup.cfg file.  If it doesn't exist,
    PackagingFileError is raised.
    """

    # XXX ** == needs testing
    D1_D2_SETUP_ARGS = {
        "name": ("metadata",),
        "version": ("metadata",),
        "author": ("metadata",),
        "author_email": ("metadata",),
        "maintainer": ("metadata",),
        "maintainer_email": ("metadata",),
        "url": ("metadata", "home_page"),
        "description": ("metadata", "summary"),
        "long_description": ("metadata", "description"),
        "download_url": ("metadata",),
        "classifiers": ("metadata", "classifier"),
        "platforms": ("metadata", "platform"),  # **
        "license": ("metadata",),
        "requires": ("metadata", "requires_dist"),
        "install_requires": ("metadata", "requires_dist"),  # setuptools
        "provides": ("metadata", "provides_dist"),  # **
        "obsoletes": ("metadata", "obsoletes_dist"),  # **
        "package_dir": ("files", "packages_root"),
        "packages": ("files",),
        "scripts": ("files",),
        "py_modules": ("files", "modules"),  # **
    }

    kwargs = {}
    for arg in D1_D2_SETUP_ARGS:
        if len(D1_D2_SETUP_ARGS[arg]) == 2:
            # The distutils field name is different than packaging's.
            section, option = D1_D2_SETUP_ARGS[arg]
        else:
            # The distutils field name is the same as packaging's.
            section = D1_D2_SETUP_ARGS[arg][0]
            option = arg

        in_cfg_value = get_cfg_option(config, section, option)

        if not in_cfg_value:
            # There is no such option in the setup.cfg.
            if arg == "long_description":
                filenames = get_cfg_option(config, section, "description_file")
                if filenames:
                    in_cfg_value = []
                    for filename in filenames.split():
                        fp = open(filename)
                        try:
                            in_cfg_value.append(fp.read())
                        finally:
                            fp.close()
                    in_cfg_value = "\n\n".join(in_cfg_value)
            else:
                continue
        elif arg == "package_dir" and in_cfg_value:
            in_cfg_value = {"": in_cfg_value}

        kwargs[arg] = in_cfg_value

    return kwargs


# 3to2 stuff

def write_py2k_header(file_list):
    """Modify shebang and add encoding cookie if needed.
    """
    if not isinstance(file_list, list):
        file_list = [file_list]

    python_re = re.compile(br"^(#!.*\bpython)(.*)([\r\n]+)$")
    coding_re = re.compile(br"coding[:=]\s*([-\w.]+)")
    new_line_re = re.compile(br"([\r\n]+)$")
    version_3 = LooseVersion("3")

    for file in file_list:
        if not os.path.getsize(file):
            continue

        rewrite_needed = False
        python_found = False
        coding_found = False
        lines = []

        f = open(file, "rb")
        try:
            while len(lines) < 2:
                line = f.readline()
                match = python_re.match(line)
                if match:
                    python_found = True
                    version = LooseVersion(match.group(2).decode() or "2")
                    if version >= version_3:
                        line = python_re.sub(br"\g<1>2\g<3>", line)
                        rewrite_needed = True
                elif coding_re.search(line):
                    coding_found = True
                lines.append(line)
            if not coding_found:
                match = new_line_re.search(lines[0])
                newline = match.group(1) if match else b"\n"
                line = b"# -*- coding: utf-8 -*-" + newline
                lines.insert(1 if python_found else 0, line)
                rewrite_needed = True
            if rewrite_needed:
                lines += f.readlines()
        finally:
            f.close()

        if rewrite_needed:
            f = open(file, "wb")
            try:
                f.writelines(lines)
            finally:
                f.close()


def generate_py2k(config, py2k_dir=PY2K_DIR, overwrite=False, run_tests=False):
    if os.path.isdir(py2k_dir):
        if not overwrite:
            return
    else:
        os.makedirs(py2k_dir)

    file_list = []
    test_scripts = []

    packages_root = get_cfg_option(config, "files", "packages_root")

    for name in get_cfg_option(config, "files", "packages"):
        name = name.replace(".", os.path.sep)
        py3k_path = os.path.join(packages_root, name)
        py2k_path = os.path.join(py2k_dir, py3k_path)
        if not os.path.isdir(py2k_path):
            os.makedirs(py2k_path)
        for fn in os.listdir(py3k_path):
            path = os.path.join(py3k_path, fn)
            if not os.path.isfile(path):
                continue
            if not os.path.splitext(path)[1].lower() == ".py":
                continue
            new_path = os.path.join(py2k_path, fn)
            shutil.copy(path, new_path)
            file_list.append(new_path)

    for name in get_cfg_option(config, "files", "modules"):
        name = name.replace(".", os.path.sep) + ".py"
        py3k_path = os.path.join(packages_root, name)
        py2k_path = os.path.join(py2k_dir, py3k_path)
        dirname = os.path.dirname(py2k_path)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        shutil.copy(py3k_path, py2k_path)
        file_list.append(py2k_path)

    for name in get_cfg_option(config, "files", "scripts"):
        py3k_path = os.path.join(packages_root, name)
        py2k_path = os.path.join(py2k_dir, py3k_path)
        dirname = os.path.dirname(py2k_path)
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        shutil.copy(py3k_path, py2k_path)
        file_list.append(py2k_path)

    setup_py_path = os.path.abspath(__file__)

    for pattern in get_cfg_option(config, "files", "extra_files"):
        for path in glob.glob(pattern):
            if os.path.abspath(path) == setup_py_path:
                continue
            py2k_path = os.path.join(py2k_dir, path)
            py2k_dirname = os.path.dirname(py2k_path)
            if not os.path.isdir(py2k_dirname):
                os.makedirs(py2k_dirname)
            shutil.copy(path, py2k_path)
            filename = os.path.split(path)[1]
            ext = os.path.splitext(filename)[1].lower()
            if ext == ".py":
                file_list.append(py2k_path)
            if (os.access(py2k_path, os.X_OK) and
                re.search(r"\btest\b|_test\b|\btest_", filename)
            ):
                test_scripts.append(py2k_path)

    run_3to2(file_list)
    write_py2k_header(file_list)

    if run_tests:
        for script in test_scripts:
            subprocess.check_call([script])


# End of 3to2 stuff


def main():
    class Py2KCommand(Command):
        description = "convert Python 3 source into Python 2"
        user_options = []

        def initialize_options(self):
            pass

        def finalize_options(self):
            pass

        def run(self):
            generate_py2k(config, overwrite=True, run_tests=True)

    config = RawConfigParser()
    fp = open("setup.cfg")
    try:
        config.readfp(fp)
    finally:
        fp.close()

    if sys.version_info.major < 3:
        generate_py2k(config)
        packages_root = get_cfg_option(config, "files", "packages_root")
        packages_root = os.path.join(PY2K_DIR, packages_root)
        config.set("files", "packages_root", packages_root)
        cmdclass = {}
    else:
        cmdclass = {"py2k": Py2KCommand}

    setup(cmdclass=cmdclass, **cfg_to_args(config))


if __name__ == "__main__":
    sys.exit(main())
