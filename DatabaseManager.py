from datetime import datetime
from selectolax.parser import HTMLParser
from pony import orm
import sqlite3
from os.path import normpath
import json

db = orm.Database()
# orm.set_sql_debug(True)

class Item(db.Entity):
    "Initizializes base table item in the database."
    key = orm.PrimaryKey(str)
    title = orm.Optional(str)
    prices = orm.Set("Price")
    Dispozice = orm.Optional(str)
    Metry_čtvereční = orm.Optional(str)
    general_info = orm.Optional(orm.Json)
    Typ_nabídky = orm.Optional(str)
    Typ_nemovitosti = orm.Optional(str)
    date_downloaded = orm.Required(datetime)
    preference = orm.Optional(str)
    FirstPrice = orm.Required(str)
    Region = orm.Optional(str)
    # PercentilIndex = orm.Optional(int)

    def __str__(self):
        print(self.key)
class Price(db.Entity):
    "Initizializes base table price in the database."
    date_created = orm.Required(datetime)
    value = orm.Required(str)
    key = orm.Required(Item)

db.bind(provider="sqlite", filename="estate-database.sqlite", create_db=True)
db.generate_mapping(create_tables=True)

class DataCalculator:
    """This class is responsible for all calculations (creating,adding,deleting) of columns in the database."""
    def __init__(self):
        self.web_instances = {}
    def add_primary_key(self, new_product):
        "This ensures creating unique primary key for each item - as url end."
        url = new_product["url"]
        if url[-1] != "/":
            url += "/"
        url_parts = url.split("/")
        last_part_url = normpath(url_parts[-2])
        return last_part_url
    def set_scraped_web(self,web_name,instance_name):
        "Adds web to the dictionary of possible scraping webpages."
        if web_name in self.web_instances:
            raise ValueError("Instance already added in the dictionary")
        self.web_instances[web_name] = instance_name
    def primary_key_to_web(self,scraped_web: str, new_product):
        web = self.web_instances[scraped_web]
        key_name = web.primary_key
        return new_product[key_name]
    def add_data(self,article_html, scraped_web:str):
        """Adds data to the database"""
        html = HTMLParser(article_html)
        web = self.web_instances[scraped_web]
        table_data = web.parse_data_from_table(html)
        basic_info = web.parse_base_info(html)
        new_product = {**table_data,**basic_info}

        try:
            with orm.db_session:
                primary_key = self.primary_key_to_web(scraped_web, new_product)
                item = Item(
                    key=self.add_primary_key(new_product),
                    FirstPrice=new_product["Cena"],
                    title=new_product["Inzerát"],
                    general_info=new_product,
                    Dispozice=new_product["Dispozice"],
                    Metry_čtvereční=new_product["Plocha"],
                    Typ_nabídky=new_product["Typ"],
                    Typ_nemovitosti=new_product["Typ nemovitosti"],
                    date_downloaded=datetime.now(),
                    preference="NEZAŘAZENO",
                    Region=new_product["Region"])
        except orm.TransactionIntegrityError as err:
            print(new_product)
            print("ERROR: Item exists", err)

        with orm.db_session:
            item_entity = Item.get(key=item.key)
            Price(date_created=datetime.now(), value=new_product["Cena"], key=item_entity)
    def get_urls_from_items(self):
        """Gets url from general_info column in Item table stored as JSON"""
        urls = []
        with orm.db_session:
            items = Item.select()
            for item in items:
                try:
                    item_json_str = json.dumps(item.general_info)
                    item_json = json.loads(item_json_str)
                    url = item_json.get('url')
                    if url:
                        urls.append(url)
                except json.JSONDecodeError as err:
                    print(f"ERROR occurred: {err}")
            return urls
    def extract_unique_articles_url(self,downloaded_article_urls,article_url_list):
        """Returns list of articles that are not downloaded to save requests."""
        if downloaded_article_urls is not None:
            unique_list = [item for item in article_url_list if item not in downloaded_article_urls]
            return unique_list
        return article_url_list
    def add_col_if_not_exists(self,name: str,table: str,type=None):
            conn = sqlite3.connect("estate-database.sqlite")
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table});")
            existing_columns = [column[1] for column in cursor.fetchall()]

            if name not in existing_columns:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {name} {type};")
    def select_colums(self,names:list,table:str):
        conn = sqlite3.connect("estate-database.sqlite")
        cursor = conn.cursor()
        columns = ", ".join(names)
        sql = f"SELECT {columns} FROM {table};"
        cursor.execute(sql)
        data = cursor.fetchall()
        return data
    def delete_columns(self,names: list,table:str):
        conn = sqlite3.connect("estate-database.sqlite")
        cursor = conn.cursor()

        for column in names:
            try:
                sql = f"ALTER TABLE {table} DROP COLUMN {column}"
                cursor.execute(sql)
                print(f"Column {column} successfully deleted")
            except sqlite3.OperationalError as err:
                print(err)
    def delete_table(self,table:str):
        conn = sqlite3.connect("estate-database.sqlite")
        cursor = conn.cursor()
        try:
            sql = f"DROP TABLE {table}"
            cursor.execute(sql)
        except sqlite3.OperationalError as err:
            print(err)
    def insert_percentile_index(self):
        self.add_col_if_not_exists("PercentilIndex",table="Item")
        columns = self.select_colums(["Typ_nabídky","Typ_nemovitosti","Region"],"Item")

        # Process the data and calculate common index
        common_index_map = {}
        current_index = 1

        for row in columns:
            key = tuple(row)
            if key not in common_index_map:
                common_index_map[key] = current_index
                current_index += 1

        # Update the existing table with the calculated index
        update_command = """
            UPDATE Item
            SET PercentilIndex = ?
            WHERE Typ_nabídky = ? AND Typ_nemovitosti = ? AND Region = ?;
            """

        conn = sqlite3.connect("estate-database.sqlite")
        cursor = conn.cursor()

        for row in columns:
            cursor.execute(update_command, (common_index_map[tuple(row)],) + tuple(row))
        # Commit the changes and close the connection
        conn.commit()
        conn.close()
    def price_per_m2(self):
        self.add_col_if_not_exists("Cena_za_metr",table="Item")

        conn = sqlite3.connect("estate-database.sqlite")
        cursor = conn.cursor()
        cursor.execute("UPDATE Item SET Cena_za_metr = FirstPrice/Metry_čtvereční")
        conn.commit()
        conn.close()
    def calculate_percentile(self):
        self.add_col_if_not_exists("CheaperEstates",table="Item")

        conn = sqlite3.connect("estate-database.sqlite")
        cursor = conn.cursor()
        cursor.execute("""SELECT PercentilIndex, Cena_za_metr,
                PERCENT_RANK() OVER(PARTITION BY PercentilIndex ORDER BY Cena_za_metr) AS CheaperEstates FROM Item;
        """)

        percent_rank_data = cursor.fetchall()

        update_query = """
            UPDATE Item
            SET CheaperEstates = ?
            WHERE PercentilIndex = ? AND Cena_za_metr = ?;
        """

        for row in percent_rank_data:
            PercentilIndex = row[0]
            Cena_za_metr = row[1]
            CheaperEstates = int(row[2]*100)
            cursor.execute(update_query, (CheaperEstates, PercentilIndex, Cena_za_metr))

        conn.commit()
        conn.close()
    def create_filter_table(self):
        """Creates FilteredItems table that retains only cheaper estates to avoid overloading the GUI with unneccessary items."""
        conn = sqlite3.connect("estate-database.sqlite")
        cursor = conn.cursor()
        try:
            cursor.execute("""CREATE TABLE FilteredItems AS SELECT * FROM Item WHERE CheaperEstates < 40
            AND (
            Region = 'Liberecký kraj' OR
            Region = 'Středočeský kraj' OR
            Region = 'Liberecký' OR
            Region = 'Středočeský');""")
        except sqlite3.OperationalError as err:
            print(err)
        cursor.close()
    def set_price_to_int(self):
        """Creates new column type INTEGER from FirstPrice TEXT column to allow calculation over prices."""
        conn = sqlite3.connect("estate-database.sqlite")
        cursor = conn.cursor()
        self.add_col_if_not_exists("IntFirstPrice",table="Item")
        self.add_col_if_not_exists("IntFirstPrice", type="INTEGER",table="FilteredItems")
        cursor.execute("""UPDATE Item SET IntFirstPrice = CAST(FirstPrice AS INTEGER);""")
        cursor.execute("""UPDATE FilteredItems SET IntFirstPrice = CAST(FirstPrice AS INTEGER);""")
        conn.commit()
        conn.close()


