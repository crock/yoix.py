#!/bin/bash

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    
    # Activate virtual environment and install requirements
    source venv/bin/activate
    python3 -m pip install -r requirements.txt
else
    echo "Virtual environment already exists"
    source venv/bin/activate
fi

# Run build commands
echo "Building project..."
python3 scripts/mdpost2html.py --input content --output public/posts # convert markdown blog posts to html
yoixpi # process bbedit persistent includes
python3 scripts/make_rss_feed.py # make rss feed

echo "Build complete!"
