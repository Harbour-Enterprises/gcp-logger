# Install build dependencies

```bash
pip install -r requirements-build.txt
```

# Erase previous build

```bash
rm -rf src/dist
```

# Bump package version

```bash
bump2version patch --verbose
```

# Build package

```bash
python -m build src
```

# Upload package to PyPi

```bash
python -m twine upload --repository superlogs src/dist/*
```
