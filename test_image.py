import os
from dotenv import load_dotenv
load_dotenv()
from bot.image_handler import process_article_image

if __name__ == "__main__":
    print("Testing image handler...")
    url = process_article_image("", "Future of AI in Technology")
    print(f"Result URL: {url}")
