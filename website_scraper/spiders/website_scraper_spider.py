import os
import scrapy
import re
from urllib.parse import urlparse, urljoin
import random

class WebsiteScraperSpider(scrapy.Spider):
    name = 'website_scraper'

    custom_settings = {
        "ROBOTSTXT_OBEY": False,
        "DOWNLOAD_DELAY": 0.5,  # Base delay before each request
        "CONCURRENT_REQUESTS": 4,
    }

    def __init__(self, url=None, *args, **kwargs):
        super(WebsiteScraperSpider, self).__init__(*args, **kwargs)
        if url:
            self.start_urls = [url]
            self.allowed_domains = [urlparse(url).netloc]
        else:
            url = input("Enter the URL to scrape: ").strip()
            self.start_urls = [url]
            self.allowed_domains = [urlparse(url).netloc]

    def parse(self, response):
        if response.status != 200:
            self.log(f"Failed to scrape {response.url} with status {response.status}", level=scrapy.log.WARNING)
            return
        
        self.log(f"Currently scraping: {response.url}")

        # Save HTML content
        self.save_file(response, response.body, "html")

        # Find and follow all links
        for link in response.css('a::attr(href)').getall():
            full_url = urljoin(response.url, link)
            if self.allowed_domains[0] in full_url:
                yield scrapy.Request(url=full_url, callback=self.parse)

        # Download assets (CSS, JS, Images)
        yield from self.download_assets(response)

        # Extract potential API endpoints
        yield from self.extract_api_endpoints(response)

        # Handle dynamic content
        self.handle_dynamic_content(response)

        # Scrape backend files
        yield from self.download_backend_files(response)

    def download_assets(self, response):
        """Download static files like CSS, JS, and images with domain handling."""
        asset_types = {
            'link[rel="stylesheet"]::attr(href)': "css",
            'script[src]::attr(src)': "js",
            'img::attr(src)': "image"
        }

        for selector, file_type in asset_types.items():
            for asset in response.css(selector).getall():
                full_url = urljoin(response.url, asset)
                if self.allowed_domains[0] in full_url:
                    yield scrapy.Request(url=full_url, callback=self.save_asset, meta={'file_type': file_type})

    def extract_api_endpoints(self, response):
        """Capture API endpoints using regex."""
        api_patterns = [
            r'https?://[^\s]+api[^\s]*',
            r'(?<=["\'])(https?://[^\s]+api[^\s]*)',
            r'api\s*=\s*["\'](https?://[^\s]+)[\s"\']*',
        ]

        api_endpoints = set()
        for pattern in api_patterns:
            api_endpoints.update(re.findall(pattern, response.text))

        for api_endpoint in api_endpoints:
            if self.allowed_domains[0] in api_endpoint:
                yield scrapy.Request(api_endpoint, callback=self.save_api_response)

    def handle_dynamic_content(self, response):
        """Look for inline JavaScript variables for dynamic content."""
        dynamic_data_pattern = r'var\s+(\w+)\s*=\s*({.*?});'  # Simple pattern to match JavaScript objects
        dynamic_content = re.findall(dynamic_data_pattern, response.text)

        for content in dynamic_content:
            self.log(f"Dynamic content found: {content}")

    def download_backend_files(self, response):
        """Download backend files like PHP, Node.js, Python files, etc."""
        backend_file_patterns = [
            r'https?://[a-zA-Z0-9.-]+/.+\.(php|py|js|ts|html)',  # Match PHP, Python, JavaScript, HTML
            r'/[a-zA-Z0-9.-]+\.(php|py|js|ts)'  # Match backend files in URL path
        ]

        backend_files = set()
        for pattern in backend_file_patterns:
            backend_files.update(re.findall(pattern, response.text))

        for file_url in backend_files:
            full_url = urljoin(response.url, file_url)
            if self.allowed_domains[0] in full_url:
                yield scrapy.Request(full_url, callback=self.save_backend_file)

    def get_domain_folder(self, url):
        """Construct the output folder based on the domain."""
        domain = urlparse(url).netloc
        return os.path.join("output", domain)

    def save_file(self, response, content, file_type):
        """Save HTML or other text-based files."""
        parsed_url = urlparse(response.url)
        domain_folder = self.get_domain_folder(response.url)
        path = parsed_url.path.strip("/") or "index.html"

        if not path.endswith(f".{file_type}"):
            path += f".{file_type}"

        save_path = os.path.join(domain_folder, path)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with open(save_path, "wb") as f:
            f.write(content)
        self.log(f"Saved file: {save_path}")

    def save_asset(self, response):
        """Save static files like CSS, JS, and images."""
        parsed_url = urlparse(response.url)
        domain_folder = self.get_domain_folder(response.url)
        path = parsed_url.path.strip("/")
        save_path = os.path.join(domain_folder, path)

        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with open(save_path, "wb") as f:
            f.write(response.body)
        self.log(f"Saved asset: {save_path}")

    def save_api_response(self, response):
        """Save API responses."""
        parsed_url = urlparse(response.url)
        domain_folder = self.get_domain_folder(response.url)
        path = parsed_url.path.strip("/")
        save_path = os.path.join(domain_folder, path)

        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with open(save_path, "wb") as f:
            f.write(response.body)
        self.log(f"Saved API response: {save_path}")

    def save_backend_file(self, response):
        """Save backend files."""
        parsed_url = urlparse(response.url)
        domain_folder = self.get_domain_folder(response.url)
        path = parsed_url.path.strip("/")
        save_path = os.path.join(domain_folder, path)

        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with open(save_path, "wb") as f:
            f.write(response.body)
        self.log(f"Saved backend file: {save_path}")