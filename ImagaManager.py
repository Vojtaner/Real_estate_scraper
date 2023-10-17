import os
import concurrent.futures
import urllib.request
import pandas as pd
import sqlite3
import json
import re

class ImageManager:
    """Class responsible for downloading images to a folder."""
    def __init__(self,output_directory):
        self.output_directory = output_directory
    def get_list_of_json_item_from_db(self,table:str,column:str,item:str):
        """Returns list of urls found in the database in specified table and column containing JSON format data."""
        conn = sqlite3.connect("estate-database.sqlite")
        sql = pd.read_sql_query(f"SELECT {column} FROM {table}", conn)
        picture_urls = [json.loads(row)[item] for row in sql[column]]
        list_urls = [value for value in picture_urls if value != "Neuvedeno"]
        return list_urls
    def clean_urls_and_download(self):
        """Controls downloaded images and retains non downloaded urls. These are downloaded using concurrent approach."""
        list_urls = self.get_list_of_json_item_from_db(table="FilteredItems", column="general_info", item="image")
        os.makedirs(self.output_directory, exist_ok=True)

        # Check and remove images that already exist in the output directory
        filtered_urls = []
        for url in list_urls:
            image_name = url.split("/")[-1]
            image_name = image_name.split("?")[0]
            if image_name not in os.listdir(self.output_directory):
                filtered_urls.append(url)
        filtered_image_urls = [url for url in filtered_urls if not url.endswith('.mp4')]

        # Download and save images
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_url = {executor.submit(self.download_image, url, 60): url for url in filtered_image_urls}
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    image_path = future.result()
                except Exception as exc:
                    print('%r generated an exception: %s' % (url, exc))
                else:
                    print('%r image downloaded and saved to %s' % (url, image_path))

    def download_image(self, url, timeout):
        """Responsible for requesting data and saving them to the folder."""
        with urllib.request.urlopen(url, timeout=timeout) as conn:
            image_data = conn.read()
            image_name = str(re.search(r"/([^/]+)\.jpg", url).group(1)) + ".jpg"
            image_path = os.path.join(self.output_directory, image_name)
            with open(image_path, 'wb') as f:
                f.write(image_data)
            return image_path