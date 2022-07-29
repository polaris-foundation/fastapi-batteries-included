import toml

config: dict = toml.load("pyproject.toml")
print(config["tool"]["poetry"]["version"])
