from abc import ABC,abstractmethod
from re import search
import httpx

categories_dict = {
    'Byty': ['byt', 'bytu', 'garzonky', 'jednotka'],
    'Domy': ['dům', 'domu', 'chalupa', 'chalupy', 'chata', 'chaty',"chaty/chalupy"],
    'Pozemky': ['pozemek', 'pozemku', 'louka', 'louky', 'pole', 'zahrada', 'zahrady', 'les', 'lesa'],
    'Komerce': ['prostor',"prostoru", 'prostory', 'restaurace', 'kanceláře', 'kancelář', 'objekt', 'objektu','činžák', 'činžáku'],
    'Garáže': ['garáž', 'garáže', 'garážové stání', 'garážových stání', 'parkovací stání']
}

class Webscraper(ABC):
    @abstractmethod
    def get_page_number(self,html):
        """This abstractmethod is replaced by the specific script that helps to get max page number."""
        pass

    def create_page_ranges(self, number_of_pages) -> list:
        """Splits total number of pages into ranges of 100 to avoid HTTP request errors."""
        pages_iteration, pages_rest = divmod(number_of_pages, 100)
        pages_list = []

        for list_range in range(pages_iteration + 1):
            range_start = list_range * 100
            range_end = range_start + (pages_rest if list_range == pages_iteration else 100)
            pages_list.append([range_start, range_end, pages_iteration])

        return pages_list


    def define_category(self,title):
        """
        This method helps sorting multiple words in comprehensive categories for filtering
        """
        for category in categories_dict:
            category_values = categories_dict[category]
            for word in title.replace(",", " ").split(" "):
                if word in category_values:
                    return category
        return "Nezatříděno"


    @abstractmethod
    def parse_base_info(self,html):
        """This abstractmethod is replaced by special parsing prompts based on concrete page that are not in table."""
        pass

    @abstractmethod
    def parse_data_from_table(self, html):
        "This abstractmethod is replaced by parsing script of the table of the specific page."
        pass

    @abstractmethod
    def set_css_parameters(self,pagination: str,primary_key: str,article_url: str,article_box: str):
        "This saves neccessary css parameters used in parsing methods."
        pass

    @abstractmethod
    def set_url_list(self,urls: list):
        "This methods works as setter for url list of pages."
        pass

class IdnesWebScraper(Webscraper):
    def get_page_number(self,html) -> int:
        pages = html.css(self.pagination)
        page_list = [page.text() for page in pages]
        max_page = max([int(item) for item in page_list if item.isdigit()])
        return max_page

    def parse_data_from_table(self,html) -> dict:
        table_values = html.css('div[class*="b-definition"] dd')
        trimmed_values = ["".join(value.text().split()) for value in table_values]
        value_list = [item.replace('Spočítathypotéku', '') for item in trimmed_values]
        table_headers = html.css('div[class*="b-definition"] dt')
        header_list = [header.text() for header in table_headers]
        table_dict = dict(zip(header_list, value_list))
        return table_dict

    def parse_base_info(self, html):
        """Creates dict of information as:
         - title
         - square_meters
         - disposition
         - price
         - title_image
         - category
         - url
         - location"""
        try:
            title = html.css_first("h1.b-detail__title").text().strip().replace('\xa0', '')
        except AttributeError:
            title = "Neuvedeno"

        square_meters = search(r'\b([\d.,?]+)\s*m[2²]\b', title)
        square_meters = square_meters.group() if square_meters is not None else "Neuvedeno"
        square_meters = search(r'\d+', square_meters).group() if square_meters != "Neuvedeno" else "Neuvedeno"

        try:
            region = search(r'"listing_localityRegion":"(.*?)"', html.text()).group(1)
        except AttributeError:
            region = "Neuvedeno"

        dispozice = search(r'\b\d+[+](?:\d+|kk)\b', title)
        dispozice = dispozice.group() if dispozice is not None else "Neuvedeno"

        offer = "".join(title.split()[0]).upper()

        try:
            location = html.css_first("p.b-detail__info").text().strip()
        except AttributeError:
            location = "Neuvedeno"

        price = html.css_first("p.b-detail__price strong").text().replace(" ", "")
        price = search(r'\d+', price)
        price = str(price.group()) if price is not None else "Neuvedeno"
        url = html.css_first('link').attrs["href"]
        title_image = html.css_first("a.carousel__item").attrs["href"]
        image_name = title_image.split("/")[-1]
        image_name = image_name.split("?")[0]
        estate_catergory = self.define_category(title)

        base_info_dict = {"Typ": offer, "Inzerát": title, "Město": location, "Cena": price, "url": url,
                          "image": title_image, "image_name": image_name, "Dispozice": dispozice,
                          "Plocha": square_meters, "Typ nemovitosti": estate_catergory, "Region": region}
        return base_info_dict

    def set_css_parameters(self, pagination: str, primary_key: str, article_url: str, article_box: str):
        self.pagination = pagination
        self.primary_key = primary_key
        self.article_url = article_url
        self.article_box = article_box

    def set_url_list(self, urls: list):
        self._url_list = urls
        return self._url_list