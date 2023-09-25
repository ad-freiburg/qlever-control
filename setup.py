from setuptools import find_packages, setup


def read(fname: str) -> str:
    with open(fname, "r", encoding="utf-8") as f:
        return f.read()


setup(
    name="qlever-control",
    version="0.0.1",
    url="https://github.com/ad-freiburg",
    description="Control everything that QLever does",
    long_description=read("README.md"),
    long_description_content_type="text/markdown",
    author="University of Freiburg, Chair of Algorithms and Data Structures",
    author_email="ad-freiburg@informatik.uni-freiburg.de",
    include_package_data=True,
    packages=find_packages(exclude=["tests*"]),
    package_data={"Qleverfiles": ["Qleverfile*"]},  # TODO: should be data_file?
    install_requires=[
        "psutil",
        "termcolor",
        "requests",
        "docker",
        "argcomplete",
        "thefuzz",  # Levenshtein Distance
    ],
    scripts=["src/main.py"],
    extras_require={  # ex: pip install qlever_control[mac]
        "mac": [],  # TODO: mac stuff
        "win": [],  # TODO: win execs
    },
    entry_points={
        "console_scripts": [
            "qleverkontrol=main:main_run",
        ],
    },
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Internet :: WWW/HTTP :: Indexing/Search",
    ],
    project_urls={"Source": "https://github.com/ad-freiburg/qlever-control"},
)
