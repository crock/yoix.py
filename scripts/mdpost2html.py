#! ./venv/bin/python3
import frontmatter
import os
import sys
import re
import json
import click
import mistune
import shutil
from slugify import slugify
from datetime import datetime

TEMPLATES_DIR = os.path.join(os.getcwd(), "includes", "templates")
SITE_DIR = os.path.join(os.getcwd(), "public")

BASE_URL = "https://croc.io"

posts = []
post_schemas = []
post_cards = []

if not os.path.exists(TEMPLATES_DIR):
    print(f"Templates directory {TEMPLATES_DIR} does not exist")
    sys.exit(1)
if not os.path.exists(SITE_DIR):
    print(f"Site directory {SITE_DIR} does not exist")
    sys.exit(1)

templates = []
for file in os.listdir(TEMPLATES_DIR):
    if file.endswith(".html"):
        templates.append(file.replace(".html", ""))

print(templates)

def get_blog_post_schema(post):
    return {
        "@type": "BlogPosting",
        "@id": f"{BASE_URL}/posts/{post['slug']}/#BlogPosting",
        "mainEntityOfPage": f"{BASE_URL}/posts/{post['slug']}/",
        "headline": post["title"],
        "name": post["title"],
        "description": post["meta:description"],
        "datePublished": post["date:iso"],
        "dateModified": post["date:iso"],
        "url": f"{BASE_URL}/posts/{post['slug']}/",
        "author": {
            "@type": "Person",
            "@id": f"{BASE_URL}/#Person",
            "name": post["author"]
        },
        "publisher": {
                "@type": "Organization",
                "@id": "https://croc.io",
                "name": "Croc Studios",
                "logo": {
                    "@type": "ImageObject",
                    "@id": "https://croc.io/img/CS_LOGO.png",
                    "url": "https://croc.io/img/CS_LOGO.png",
                    "width": "125",
                    "height": "125"
                }
        },
        "url": f"{BASE_URL}/posts/{post['slug']}/",
        "isPartOf": {
            "@type": "Blog",
            "@id": f"{BASE_URL}/blog/",
            "name": "Blog | Croc Studios",
            "publisher": {
                "@type": "Organization",
                "@id": "https://croc.io",
                "name": "Croc Studios"
            }
        },
        "keywords": post["meta:keywords:json"]
    }

def get_blog_post_html(variables):
    template = read_template("post-card")
    for key, value in variables.items():  
        if key == "meta:keywords:json":
            template = template.replace("{{" + key + "}}", json.dumps(value))
        elif key == "jsonLdSchema":
        	template = template.replace("{{" + key + "}}", json.dumps(value))
        else:
            template = template.replace("{{" + key + "}}", value)
    return template

def read_input_directory(path):
    markdown_files = []
    for file in os.listdir(path):
        if file.endswith(".md"):
            markdown_files.append(file)
    return markdown_files

def read_template(template):
    with open(os.path.join(TEMPLATES_DIR, f"{template}.html"), "r") as f:
        return f.read()
    
def write_blog_index(variables):
    template = read_template("blog-index")
    for key, value in variables.items():
        if key == "meta:keywords:json":
            template = template.replace("{{" + key + "}}", json.dumps(value))
        elif key == "jsonLdSchema":
        	template = template.replace("{{" + key + "}}", json.dumps(value))
        else:
            template = template.replace("{{" + key + "}}", value)
    with open(os.path.join(SITE_DIR, "blog", "index.html"), "w") as f:
        f.write(template)

def write_page(path, variables):
    template = read_template("post")
    for key, value in variables.items():
        if key == "meta:keywords:json":
            template = template.replace("{{" + key + "}}", json.dumps(value))
        elif key == "jsonLdSchema":
        	template = template.replace("{{" + key + "}}", json.dumps(value))
        else:
            template = template.replace("{{" + key + "}}", value)
    if not os.path.exists(path):
        os.makedirs(path)
    with open(os.path.join(path, "index.html"), "w") as f:
        f.write(template)

def copy_image_to_public(image_path, input_dir):
    """Copy image file to public/img directory, maintaining subdirectories"""
    if not image_path:
        return image_path
        
    # Convert relative path to absolute path based on input directory
    abs_image_path = os.path.join(input_dir, image_path)
    
    if not os.path.exists(abs_image_path):
        print(f"Warning: Image not found: {abs_image_path}")
        return image_path
        
    # Create public/img directory if it doesn't exist
    public_img_dir = os.path.join(SITE_DIR, "img")
    if not os.path.exists(public_img_dir):
        os.makedirs(public_img_dir)
    
    # Preserve any subdirectories in the image path
    rel_path = os.path.relpath(abs_image_path, input_dir)
    dest_path = os.path.join(public_img_dir, rel_path)
    
    # Create subdirectories if needed
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    
    # Copy the file
    shutil.copy2(abs_image_path, dest_path)
    print(f"Copied image: {rel_path} -> /img/{rel_path}")
    
    # Return the new public URL path
    return f"/img/{rel_path}"

def extract_markdown_images(content):
    """Extract image paths from markdown content"""
    # Match both ![alt](path) and <img src="path"> patterns
    md_image_pattern = r'!\[.*?\]\((.*?)\)'
    html_image_pattern = r'<img.*?src=["\'](.*?)["\'].*?>'
    
    images = []
    images.extend(re.findall(md_image_pattern, content))
    images.extend(re.findall(html_image_pattern, content))
    return images

def parse_markdown_post(path, input_dir):
    with open(path, "r", encoding='utf-8') as f:
        mdpost = frontmatter.load(f, encoding='utf-8')
    
    # Extract and copy images from content
    content_images = extract_markdown_images(mdpost.content)
    for img_path in content_images:
        new_path = copy_image_to_public(img_path, input_dir)
        mdpost.content = mdpost.content.replace(img_path, new_path)
    
    # Handle featured image in metadata if present
    if "image" in mdpost.metadata:
        new_image_path = copy_image_to_public(mdpost.metadata["image"], input_dir)
        mdpost.metadata["image"] = new_image_path
    
    mdpost.content = mistune.html(mdpost.content)
    return mdpost

@click.command()
@click.option('--input', type=click.Path(exists=True), required=True, help="Input directory containing markdown files")
@click.option('--output', type=click.Path(exists=True), required=True, help="Output directory to save html files")
@click.option('--templates', type=click.Path(exists=True), default=TEMPLATES_DIR, required=False, help="Templates directory")
@click.option('--site', type=click.Path(exists=True), default=SITE_DIR, required=False, help="Site directory")
@click.option('--help', is_flag=True, help="Show help message and exit")
def main(input, output, templates, site, help):
    if help:
        click.echo(main.get_help(click.Context(main)))
        sys.exit(0)
    
    markdown_files = read_input_directory(input)

    print(f"Found {len(markdown_files)} markdown files")

    for file in markdown_files:
        md_file = os.path.join(input, file)
        print(f"Processing {md_file}")
        mdpost = parse_markdown_post(md_file, input)
        if "customSlug" in mdpost.metadata:
            slug = mdpost.metadata["customSlug"]
        else:
            slug = slugify(md_file.replace(".md", ""))

        url = f"{BASE_URL}/posts/{slug}/"

        metavars = {
            "date:iso": datetime.strptime(str(mdpost.metadata["publishDate"]), "%Y%m%d").isoformat(),
            "date:readable": datetime.strptime(str(mdpost.metadata["publishDate"]), "%Y%m%d").strftime("%B %d, %Y"),
            "title": mdpost.metadata["title"],
            "content": mdpost.content,
            "url": url,
            "slug": slug,
        } # metadata variables

        if "image" in mdpost.metadata:
            metavars["meta:og:image"] = mdpost.metadata["image"]
        else:
            metavars["meta:og:image"] = ""  
        if "description" in mdpost.metadata:
            metavars["meta:description"] = mdpost.metadata["description"]
        else:
            metavars["meta:description"] = ""   
        if "author" in mdpost.metadata:
            metavars["author"] = mdpost.metadata["author"]
        else:
            metavars["author"] = "Alex Crocker"
        if "tags" in mdpost.metadata:
            metavars["meta:keywords"] = ", ".join(mdpost.metadata["tags"])
            metavars["meta:keywords:json"] = mdpost.metadata["tags"]
        else:
            metavars["meta:keywords"] = ""
            metavars["meta:keywords:json"] = []
        if "canonical" in mdpost.metadata:
            metavars["meta:canonical"] = mdpost.metadata["canonical"]
        else:
            metavars["meta:canonical"] = url
            
        posts.append(metavars)

    sorted_posts = sorted(posts, key=lambda x: x["date:iso"], reverse=True)

    with open(os.path.join(output, "posts.json"), "w") as f:
        print(f"Writing {len(sorted_posts)} posts to {os.path.join(output, 'posts.json')}")
        json.dump(sorted_posts, f, indent=4)

    for post in sorted_posts:
        post_schema = get_blog_post_schema(post)
        post_cards.append(get_blog_post_html(post))
        post_schemas.append(post_schema)
        post["jsonLdSchema"] = post_schema
        fp = os.path.join(output, post["slug"])
        write_page(fp, post)
        print(f"Wrote {fp}/index.html")

    metavars = {
        "blogPostsSchema": json.dumps(post_schemas),
        "url": f"{BASE_URL}",
        "posts": "\n".join(post_cards),
    }
    write_blog_index(metavars)

if __name__ == "__main__":
    main()