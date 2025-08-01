from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="invictus",
    version="0.0.1",
    author="Dojo Planner",
    author_email="admin@dojoplanner.com",
    description="Complete Brazilian Jiu-Jitsu dojo management system for ERPNext",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/power19/invictus",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Framework :: ERPNext",
        "Topic :: Office/Business",
    ],
    python_requires=">=3.8",
    install_requires=[
        # Dependencies will be handled by ERPNext/Frappe
    ],
    include_package_data=True,
    zip_safe=False,
)