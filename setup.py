from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="yoix",
    version="0.2.0",
    author="Alex Crocker",
    description="Pythonic static site generator designed for minimalists",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/crock/yoix.py",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "click>=8.0.0",
        "mistune",
        "python-frontmatter",
        "python-slugify",
        "tomli>=1.1.0",
        "yoix-pi==1.0.0",
        "pybars3==0.9.7"
    ],
    extras_require={
        'dev': [
            'pytest>=7.0.0',
            'pytest-cov>=4.0.0',
        ],
    },
    entry_points={
        'console_scripts': [
            'yoix=yoix.cli:main',
        ],
    },
)
