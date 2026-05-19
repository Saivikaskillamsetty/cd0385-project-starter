from setuptools import find_packages, setup

setup(
    name="content-to-tasks-bot",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "anthropic>=0.28.0",
        "notion-client>=2.2.1",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "python-dotenv>=1.0.0",
        "lxml>=5.0.0",
    ],
    entry_points={
        "console_scripts": [
            "bot=bot.cli:main",
        ],
    },
    python_requires=">=3.10",
)
