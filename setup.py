from setuptools import setup, find_packages

setup(
    name="pytrk",
    version="0.1.0",
    packages=find_packages(),
    py_modules=["pytrk"],
    install_requires=[],
    entry_points={
        "console_scripts": [
            "pytrk=pytrk.cli:main"
        ]
    },
    author="Your Name",
    description="A minimal git-like version control system in Python",
    license="MIT",
)