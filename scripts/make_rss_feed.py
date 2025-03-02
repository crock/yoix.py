#! ./venv/bin/python
import os
import json
import datetime
import click
from lib.rfeed import *

class Content(Extension):
	def get_namespace(self):
		return {"xmlns:content": "http://purl.org/rss/1.0/modules/content/"}

class ContentItem(Serializable):
	def __init__(self, content):
		Serializable.__init__(self)
		self.content = content

	def publish(self, handler):
		Serializable.publish(self, handler)
		self._write_element("content:encoded", self.content)

SITE_DIR = os.path.join(os.getcwd(), "public")

BASE_URL = "https://croc.io"

feed_items = []

def get_posts():
	posts = []
	posts_json_path = os.path.join(SITE_DIR, "posts", "posts.json")
	if not os.path.exists(posts_json_path):
		return posts
	with open(posts_json_path, "r") as f:
		posts = json.load(f)
	return posts

@click.command()
def main():
	posts = get_posts()

	# RFC822 format for RSS pubDate: e.g., Sun, 27 Oct 2024 19:45:57 GMT
	date_format = "%a, %d %b %Y %H:%M:%S GMT"

	# iso format: 2025-01-25T00:00:00
	iso_format = "%Y-%m-%dT%H:%M:%S"

	for post in posts:
		# Parse the ISO date and convert to UTC/GMT
		pub_date = datetime.datetime.strptime(post["date:iso"], iso_format)
		pub_date = pub_date.replace(tzinfo=datetime.timezone.utc)
		
		item = Item(
			title = post["title"],
			link = post["url"], 
			description = post["meta:description"],
			author = post["author"],
			guid = Guid(post["url"]),
			pubDate = pub_date,
			extensions = [ContentItem(post["content"])]
		)
		feed_items.append(item)
		
	feed = Feed(
    	title = "Croc Studios Blog RSS Feed",
    	link = "https://croc.io/feeds/rss.xml",
    	description = "The official RSS feed for the Croc Studios blog",
    	language = "en-US",
    	lastBuildDate = datetime.datetime.now(datetime.timezone.utc),
    	items = feed_items,
    	extensions = [Content()]
    )
    
	with open(os.path.join(SITE_DIR, "feeds", "rss.xml"), "w") as f:
		f.write(feed.rss())
		print("RSS feed generated successfully")

if __name__ == "__main__":
	main()