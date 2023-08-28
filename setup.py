from setuptools import find_packages, setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name="AsyncSwayIPC",
    version="0.1",
    description="A fast asynchronous IPC library for Sway",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Troels Bjørnskov",
    author_email="troels@bjoernskov.org",
    url="https://github.com/trbjo/AsyncSwayIPC",
    packages=find_packages(),
    install_requires=[
        "Orjson",
    ],
    python_requires=">=3.6",
    package_data={
        "": ["settings.json"],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
)
