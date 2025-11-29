from setuptools import setup, find_packages

setup(
    name="nslogger",
    version="1.0.0",
    description="Financial Data Logging & Management Library",
    author="narasimharao.allaka",
    packages=find_packages(),
    install_requires=[
        "pandas>=1.5.0",
        "setuptools>=65.0"
    ],
    python_requires=">=3.8",
    include_package_data=True,
    package_data={
        "": ["*.py"],
    }
)