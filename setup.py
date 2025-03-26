from setuptools import setup, find_packages

setup(
    name="yt-stats-wrangler",
    version="0.1.0",
    author="Christian Duenas",
    author_email="christianduenas1998@gmail.com",
    description="A Python package to collect and wrangle YouTube video and channel statistics using the YouTube Data API v3",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/ChristianD37/yt-stats-wrangler",
    packages=find_packages(),
    install_requires=[
        "pandas>=1.0.0",
        "google-api-python-client",
        "isodate"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
