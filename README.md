# Yoix.py - Minimal Static Site Generator 

**This is a pre-release. Do not use for production environments yet.**

Pythonic static site generator designed for minimalists.

## Installation

You can install yoix using pip:

```bash
pip install yoix
```

## Usage

### Command Line

You can also use the command-line interface:

```bash
# Using default directories (includes/partials and public)
yoix

# Specify custom directories
yoix --input content --output public --partials includes/partials --templates includes/templates

# Using short options
yoix -i path/to/content -o path/to/public -p path/to/partials -t path/to/templates

# Show help
yoix --help
```

## Development

To set up for development:

```bash
# Clone the repository
git clone https://github.com/crock/yoix.py yoix
cd yoix

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
source ./venv/bin/activate

# Install in development mode with test dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## License

This project is licensed under the MIT License - see the [LICENSE](https://github.com/crock/yoix-core/blob/main/LICENSE) file for details.