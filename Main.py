import requests
# from DataCalculator import Item,Price,DataCalculator
from Webscraper import IdnesWebScraper
from DatabaseManager import DataCalculator
from selectolax.parser import HTMLParser
from aiolimiter import AsyncLimiter
import httpx
import asyncio
from RequestsManager import RequestsManager
import re
from ImagaManager import ImageManager

#method chaining
#DRY
#dokumentace
#is/get/set
#private atributes
#one purpose method


idnes = IdnesWebScraper()
idnes.set_css_parameters(article_box="div.c-products__inner",article_url="a.c-products__link",primary_key= "Číslo zakázky",pagination= "a.paging__item span.btn__text")
idnes.set_url_list(["https://reality.idnes.cz/s/stredocesky-kraj/?page=","https://reality.idnes.cz/s/liberecky-kraj/?page="])

"--------------------------------"
DataCalculator = DataCalculator()
DataCalculator.set_scraped_web("idnes", idnes)

"--------------------------------"

UserAgent = ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/42.0.2311.135 Safari/537.36 Edge/12.246",
              "Mozilla/5.0 (X11; CrOS x86_64 8172.45.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.64 Safari/537.36",
              "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_2) AppleWebKit/601.3.9 (KHTML, like Gecko) Version/9.0.2 Safari/601.3.9",
              "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36",
              "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:15.0) Gecko/20100101 Firefox/15.0.1"]


Asyn_requests = RequestsManager(UserAgent)

"--------------------------------"

ImgMan = ImageManager("C:\\Users\\vojte\\PycharmProjects\\Webscraping\\Reality OOP\\pictures")


async def main():
    """This function does the main logic for downloading and saving records. Parametr K regulates indirectly
     number of pages to be donwloaded togeather with substracting from 1-98 in for loop."""
    rate_limit = AsyncLimiter(50, 1)
    async with httpx.AsyncClient() as client:
        url_and_page_range = {}
        for url in idnes.url_list:
            page_html_text = await Asyn_requests.get_page(client, f'{url}1', rate_limit)
            html = HTMLParser(page_html_text)
            max_page = idnes.get_page_number(html)
            page_range = idnes.create_page_ranges(max_page)
            url_and_page_range[url] = page_range
        task_pages_url = []
        for base_url in url_and_page_range:
            # K = url_and_page_range[base_url][0][2]
            K = 0
            C = 0
            while C <= K:
                for page_number in range(url_and_page_range[base_url][C][0], url_and_page_range[base_url][C][1]-97):
                # for page_number in range(url_and_page_range[base_url][C][0],url_and_page_range[base_url][C][1]):
                    page_url = f'{base_url}{page_number}'
                    task_pages_url.append(asyncio.ensure_future(Asyn_requests.get_page(client, page_url, rate_limit)))
                C += 1

        page_html_text_list = await asyncio.gather(*task_pages_url)

        article_url_list = []
        for page_html_text in page_html_text_list:
            html = HTMLParser(page_html_text)
            products = html.css(idnes.article_url)

            for item in products:
                article_url = f'{item.css_first(idnes.article_url).attributes["href"]}'
                article_url_list.append(article_url)

        downloaded_article_urls = DataCalculator.get_urls_from_items()
        cleaned_article_url_list = DataCalculator.extract_unique_articles_url(downloaded_article_urls, article_url_list)

        if cleaned_article_url_list == []:

            return print(f"No new real estates available. Everything is already downloaded.")

        tasks_articles = []
        for article_url_source in cleaned_article_url_list:
            tasks_articles.append((asyncio.ensure_future(Asyn_requests.get_page(client, article_url_source, rate_limit))))

        article_html_text_list = await asyncio.gather(*tasks_articles)

        for article_html_text in article_html_text_list:
            DataCalculator.add_data(article_html_text, "idnes")

        print(f"Already in database: {len(downloaded_article_urls)}")
        print(f"Real estates added: {len(article_html_text_list)}")


if __name__ == "__main__":
    asyncio.run(main())
    DataCalculator.insert_percentile_index()
    DataCalculator.price_per_m2()
    DataCalculator.calculate_percentile()
    DataCalculator.create_filter_table()
    DataCalculator.set_price_to_int()

    ImgMan.get_list_of_json_item_from_db(table="FilteredItems",column="general_info",item="image")
    ImgMan.clean_urls_and_download()


