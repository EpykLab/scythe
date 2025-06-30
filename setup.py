import setuptools

# Read the contents of your README file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Read the requirements from the requirements.txt file
with open("requirements.txt", "r", encoding="utf-8") as f:
    install_requires = f.read().splitlines()

setuptools.setup(
    # Name of the package
    name="ttp-security-framework",

    # Version of the package
    version="0.1.0",

    # Author information
    author="Your Name / Your Company",
    author_email="your.email@example.com",

    # A short, one-sentence summary of the package
    description="An extensible framework for emulating attacker TTPs with Selenium.",

    # A long description of your package, read from the README file
    long_description=long_description,
    long_description_content_type="text/markdown",

    # The URL for the project's homepage
    url="https://github.com/EpykLab/scythe",

    # The license for the package
    license="MIT", # Or another license like "Apache-2.0"

    # Classifiers help users find your project
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: Information Technology",
        "Topic :: Security",
        "Framework :: Pytest", # If you plan to use pytest for testing
    ],

    # Specify the Python version requirements
    python_requires=">=3.8",

    # Automatically find all packages in the project
    # This will find `ttp_framework`, `ttp_framework.core`, etc.
    packages=setuptools.find_packages(exclude=["tests*", "examples*"]),

    # List of dependencies required by the package
    install_requires=install_requires,

    # Entry points can be used to create command-line scripts
    # For example, you could create a CLI to run tests
    # entry_points={
    #     "console_scripts": [
    #         "ttp-runner=ttp_framework.cli:main",
    #     ],
    # },
)
