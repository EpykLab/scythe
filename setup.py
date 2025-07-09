import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("./requirements.txt", "r", encoding="utf-8") as f:
    install_requires = f.read().splitlines()

setuptools.setup(
    name="scythe-ttp",
    version="0.7.0",
    author="EpykLab",
    author_email="cyber@epyklab.com",
    description="An extensible framework for emulating attacker TTPs with Selenium.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/EpykLab/scythe",

    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Topic :: Security",
        "Framework :: Pytest",
    ],

    python_requires=">=3.8",

    packages=setuptools.find_packages(exclude=["tests*", "examples*"]),

    install_requires=install_requires,

    # Entry points can be used to create command-line scripts
    # For example, you could create a CLI to run tests
    # entry_points={
    #     "console_scripts": [
    #         "ttp-runner=ttp_framework.cli:main",
    #     ],
    # },
)
