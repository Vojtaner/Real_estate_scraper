from typing import Union
import ttkbootstrap as ttk
import tkinter as tk
from ttkbootstrap import ttk, Style, StringVar, IntVar
from PIL import ImageTk, UnidentifiedImageError, Image
import webbrowser
import sqlite3
import pandas as pd
import json
from datetime import datetime


class FilterTab(ttk.Frame):
    def __init__(self, parent, database, data_callback):
        super().__init__(master=parent)
        self.data_callback = data_callback
        self.check_button_sets = []
        self.database_name = database
        self.text_data = self.prepare_data()
        self.dict_of_check_frames = self.create_dict_for_checkbuttons()
        self.main_filter_frame = tk.Frame(self, relief=tk.GROOVE, borderwidth=3, background="green")
        self.main_filter_frame.pack(expand=True, fill="both")
        self.generate_checkbutton_frames(self.dict_of_check_frames)

        # Ceny
        self.subframe_price_filter = ttk.LabelFrame(self.main_filter_frame, text="Cena")
        self.subframe_price_filter.pack(expand=True, fill="both")
        self.generate_scales()

        # Tlačítko na filtrování
        self.btn = ttk.Button(self.main_filter_frame, text="Filtruj", command=lambda: self.create_query())
        self.btn.pack(expand=True, fill="both")

        self.filter_value_dict = {}
        self.filter_value_list = []
        self.number_items_to_filter_dict = {}

        self.PriceFilterList = [0, 40000000]
    def prepare_data(self):
        db = sqlite3.connect(self.database_name)
        data1 = pd.read_sql_query('''SELECT general_info,
                                                key,
                                                Metry_čtvereční,
                                                Typ_nabídky,
                                                Typ_nemovitosti,
                                                Dispozice,
                                                preference,
                                                Region
                                                FROM FilteredItems''', db)
        new_data = data1.to_dict(orient='records')
        data = []

        for item in new_data:
            general_info = json.loads(item['general_info'])
            key = item["key"]
            Dispozice = item["Dispozice"]
            Metry_čtvereční = item["Metry_čtvereční"]
            Typ_nabídky = item["Typ_nabídky"]
            Typ_nemovitosti = item["Typ_nemovitosti"]
            preference = item["preference"]
            Region = item["Region"]

            data.append({"general_info": general_info, "key": key, "Typ_nemovitosti": Typ_nemovitosti,
                         "Dispozice": Dispozice, "Metry_čtvereční": Metry_čtvereční, "Typ_nabídky": Typ_nabídky,"Region": Region})
        return data

    def create_list_for_query(self, value, name, filter_name):
        value = value.get()
        value_to_list = {name: value}
        new_choice = {filter_name: value_to_list}
        self.filter_value_list.append(new_choice)
        return self.filter_value_list

    def create_query(self):
        for item in self.filter_value_list:
            key, value = list(item.items())[0]
            self.filter_value_dict.setdefault(key, {}).update(value)
        self.cleaned_data = {key: {k: v for k, v in inner_dict.items() if v != 0} for key, inner_dict in
                             self.filter_value_dict.items()}
        self.keys_assigned = {outer_key: list(inner_dict.keys()) for outer_key, inner_dict in self.cleaned_data.items()}

        # nejprve inicializuje všechny hodnoty jako plné, nebo vybrané uživatelem
        Typ_nemovitosti = self.keys_assigned.get("Typ_nemovitosti", self.final_dict["Typ_nemovitosti"])
        Dispozice = self.keys_assigned.get("Dispozice", self.final_dict["Dispozice"])
        Typ_nabídky = self.keys_assigned.get("Typ_nabídky", self.final_dict["Typ_nabídky"])
        region = self.keys_assigned.get("Region", self.final_dict["Region"])


        # hlídá, aby filtr měl buď všechny hodnoty nebo jen ty vybrané, nikdy prázdné!!
        Typ_nemovitosti = Typ_nemovitosti if Typ_nemovitosti else self.final_dict["Typ_nemovitosti"]
        Dispozice = Dispozice if Dispozice else self.final_dict["Dispozice"]
        Typ_nabídky = Typ_nabídky if Typ_nabídky else self.final_dict["Typ_nabídky"]
        region = region if region else self.final_dict["Region"]


        query = """SELECT * FROM FilteredItems WHERE Typ_nemovitosti IN ({0})
                                                AND Dispozice IN ({1})
                                                AND Typ_nabídky IN ({2})
                                                AND Region IN ({3}) 
                                                AND IntFirstPrice >= {4}
                                                AND IntFirstPrice <= {5}
                                                AND preference = 'NEZAŘAZENO' LIMIT 60""".format(
            ",".join(["'{}'".format(val) for val in Typ_nemovitosti]),
            ",".join(["'{}'".format(val) for val in Dispozice]),
            ",".join(["'{}'".format(val) for val in Typ_nabídky]),
            ",".join(["'{}'".format(val) for val in region]),
            ",".join(["{}".format(self.PriceFilterList[0])]),
            ",".join(["{}".format(self.PriceFilterList[1])]))
        print(query)
        self.data_callback(query)

    def create_dict_for_checkbuttons(self):
        list_for_checkbuttons_frames = ['Typ_nemovitosti', 'Dispozice', 'Typ_nabídky', 'Region']
        self.final_dict = {}
        for frame in list_for_checkbuttons_frames:
            text = list(set([checkbutton[frame] for checkbutton in self.text_data]))
            self.final_dict[frame] = text
        return self.final_dict

    def generate_keys_from_general_data(self):
        for dict_data in self.text_data:
            keys = list(dict_data["general_info"].keys())
            general_info_set = set(keys)
            key_not_to_display = ["url", "image_name", "Inzerát", "image", "Cena", "Lokalita objektu"]
            clear_list = general_info_set.difference(key_not_to_display)
        return {"Obecné informace": clear_list}

    def generate_checkbutton_frames(self, dict_of_frames: dict):
        # self.dict_of_checkframes = dict_of_frames
        for frame in self.dict_of_check_frames:
            gen_LabelFrame = ttk.LabelFrame(self.main_filter_frame, text=frame)
            gen_LabelFrame.pack(expand=True, fill="both", ipady=15)
            self.generate_check_buttons(gen_LabelFrame, self.dict_of_check_frames[frame], f"{frame}_value_list",
                                        var="int")

    def generate_scales(self):
        self.price_values_labels = []
        self.name_price_list=[]
        for _, i in enumerate(["Minimální cena", "Maximální cena"]):
            var = tk.IntVar()
            self.price_values_labels.append(ttk.Label(self.subframe_price_filter)) # creates list of price_value labels
            self.price_label = ttk.Label(self.subframe_price_filter, text=i)

            self.price_label.grid(padx=20, row=_, column=0)
            price_slide = ttk.Scale(self.subframe_price_filter, from_=0, to=4000000, orient="horizontal",
                                    variable=var,
                                    command=lambda value=var,
                                                   text = i,
                                                   label=self.price_values_labels[_],: (self.format_to_thousands(
                                        value, label,text),self.save_values(text,value)))
            price_slide.grid(row=_, padx=30, column=1, ipadx=70)

            self.price_values_labels[_].grid(row=_, column=2)
            price_slide.bind('<ButtonRelease>',self.print_scale_price)

    def save_values(self,text,values):
        if text == "Minimální cena":
            self.price_label = "Minimální cena"
        elif text == "Maximální cena":
            self.price_label = "Maximální cena"
        return self.price_label

    # showes number at the end of scale
    def format_to_thousands(self, value, label,text):
        self.label = label
        self.formatted_number = "{:,.0f}".format(float(value))
        label["text"] = self.formatted_number

    def print_scale_price(self, e):
        if self.price_label == "Minimální cena":
            self.PriceFilterList[0] = int(self.formatted_number.replace(',', ''))
        elif self.price_label == "Maximální cena":
            self.PriceFilterList[1] =  int(self.formatted_number.replace(',', ''))
        return self.PriceFilterList

    def generate_check_buttons(self, parent, tags: list, value_list_name: str, var: Union["str", "int"]):
        self.parent = parent
        self.tags = tags
        self.value_list_name = value_list_name
        self.var = var
        list_names = self.tags
        self.value_list = []
        for checkbox in list_names:
            if self.var == "str":
                var = tk.StringVar(value=1)
            elif self.var == "int":
                var = tk.IntVar()
            self.value_list.append((var, checkbox))
            ch = ttk.Checkbutton(self.parent, text=checkbox, variable=var, command=lambda value=var,
                                                                                          name=checkbox,
                                                                                          filter_name=self.parent[
                                                                                              "text"]: self.create_list_for_query(
                value, name, filter_name))
            ch.pack(fill="both", side=tk.LEFT, padx=20)

class ListFrame(ttk.Frame):
    def __init__(self, parent, item_height, database_name):
        super().__init__(master=parent)
        self.pack(expand=True, fill="both")
        self.database_name = database_name
        self.item_height = item_height
        # widget data
        self.text_data = self.prepare_data()
        self.item_number = len(self.text_data)
        self.list_height = self.item_number * self.item_height

        # canvas
        self.canvas = tk.Canvas(self, background="red", scrollregion=(0, 0, self.winfo_width(), self.list_height))
        self.canvas.pack(expand=True, fill="both")

        # widget display frame
        self.frame = ttk.Frame(self)
        self.newest_price()


        for dict, dict_data in enumerate(self.text_data):
            self.create_item(dict).pack(expand=True, fill='both', padx=10, pady=4)
        # scrollbar
        self.scrollbar = ttk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.place(relx=1, rely=0, relheight=1, anchor="ne")

        # events
        self.canvas.bind_all('<MouseWheel>', lambda event: self.canvas.yview_scroll(-int(event.delta / 60), 'units'))
        self.bind('<Configure>', self.update_size)

    def update_size(self, event):
        if self.list_height >= self.winfo_height():
            height = self.list_height
            self.canvas.bind_all('<MouseWheel>',
                                 lambda event: self.canvas.yview_scroll(-int(event.delta / 60), 'units'))
            self.scrollbar.place(relx=1, rely=0, relheight=1, anchor='ne')
        else:
            height = self.winfo_height()
            self.canvas.unbind_all('<MouseWheel>')
            self.scrollbar.place_forget()
        self.canvas.create_window((0, 0),
                                  window=self.frame,
                                  anchor="nw",
                                  width=self.winfo_width(),
                                  height=height,
                                  )
    def create_item(self, dict):
        # grid layout
        self.list_frame = tk.Frame(self.frame, highlightbackground="#C2C7CC", highlightthickness=1)
        self.list_frame.rowconfigure(0)
        self.list_frame.columnconfigure(0, weight=1)
        self.list_frame.columnconfigure(1, weight=3)
        self.list_frame.columnconfigure(2, weight=5)

        style = Style()
        style.configure("TRadiobutton", font=("arial", 11, "bold"))
        var = StringVar()
        radiobutton_frame = ttk.Label(self.list_frame)
        radiobutton_frame.grid(column=0, row=0, sticky="w")

        favourite_radiobutton = ttk.Radiobutton(radiobutton_frame, bootstyle="success", variable=var, value=1,
                                                text="SLEDOVAT", command=lambda value="SLEDUJI",
                                                                                key=self.text_data[dict]["key"]: self.insert_preference_and_refresh(value, key))
        favourite_radiobutton.grid(row=0, column=0, ipady=5, sticky="w", padx=10, pady=10)

        hide_radiobutton = ttk.Radiobutton(radiobutton_frame, bootstyle="dangerous", variable=var, value=0,
                                           text="NESLEDOVAT", command=lambda value="NESLEDUJI",key=self.text_data[dict]["key"]: self.insert_preference_and_refresh(value,
                                                                                                                key))
        hide_radiobutton.grid(row=1, column=0, ipady=5, sticky="w", padx=10, pady=10)

        try:
            img = Image.open(
                f"C:\\Users\\vojte\\PycharmProjects\\Webscraping\\Reality OOP\\pictures\\{self.text_data[dict]['general_info']['image_name']}")
        except (FileNotFoundError, UnidentifiedImageError):
            img = Image.open(
                "empty_image.png")

        resized_image = img.resize((400, 400), Image.LANCZOS)
        FinalImage = ImageTk.PhotoImage(resized_image)

        ImageLable = tk.Label(self.list_frame, image=FinalImage)
        ImageLable.image = FinalImage
        ImageLable.grid(column=1, row=0, padx=10, pady=10, sticky="w")

        info_frame = ttk.Frame(self.list_frame)
        info_frame.rowconfigure(3)

        info_frame.columnconfigure(0)
        info_frame.columnconfigure(1)
        info_frame.columnconfigure(2)
        info_frame.grid(column=2, row=0, pady=15, sticky="nw")

        Title_Frame = ttk.Frame(info_frame)
        Title_Frame.grid(row=0, columnspan=3, sticky="ew")

        LinkIcon = Image.open("LinkIcon.png")
        LinkIcon = LinkIcon.resize((20, 20), Image.LANCZOS)
        LinkIcon = ImageTk.PhotoImage(LinkIcon)
        IconLink_Label = ttk.Label(Title_Frame, image=LinkIcon, cursor="hand2")
        IconLink_Label.image = LinkIcon
        IconLink_Label.grid(row=0, column=0, rowspan=2,padx=10, sticky="nwes")

        IconLink_Label.bind("<Button-1>",lambda e: webbrowser.open_new_tab(self.text_data[dict]["general_info"]["url"]))

        title_label = ttk.Label(Title_Frame, text=self.text_data[dict]["title"], font=("Arial", 20, "bold"))
        title_label.grid(column=1, row=0,rowspan=2, columnspan=2, sticky="nwse")

        Price_Frame = ttk.LabelFrame(Title_Frame,text="CENY K DATU",bootstyle="secondary")
        Price_Frame.grid(row=0, column=3,columnspan=2, sticky="n",padx=20)
        key = self.text_data[dict]["key"]
        FirstPrice_Label = ttk.Label(Price_Frame, text=f"{self.format_date(self.prices_data[key]['date_old'])} - {self.format_price(self.prices_data[key]['price_old'])}", anchor="w",font=("Arial", 8), foreground="#807878", width=25)
        FirstPrice_Label.grid(row=0, column=1, sticky="nwse")

        NewestPrice_Label = ttk.Label(Price_Frame, text=f"{self.format_date(self.prices_data[key]['date_new'])} - {self.format_price(self.prices_data[key]['price_new'])}", anchor="w",font=("Arial", 8), foreground="#807878", width=25)
        NewestPrice_Label.grid(row=1, column=1, sticky="nwse",)

        Percentil_Frame = ttk.LabelFrame(Title_Frame, text="% LEVNĚJŠÍCH\nV KATEGORII", bootstyle="secondary")
        Percentil_Frame.grid(row=0, column=5, sticky="n")

        Percentil_Label = ttk.Label(Percentil_Frame, text=f"{self.text_data[dict]['CheaperEstates']}", anchor="w", font=("Arial", 10,"bold"),foreground="#000000",width=10)
        Percentil_Label.grid(row=0, column=1, sticky="we")

        # vytváří barevné labely
        ColoredLabel_Dict = {"DISPOZICE": "Dispozice", "REGION": "Region", "CENA": "FirstPrice",
                             "ROZLOHA": "Metry_čtvereční", "NABÍDKA": "Typ_nabídky", "KATEGORIE": "Typ_nemovitosti"}
        ColoredLabel_List = list(ColoredLabel_Dict)
        NumColumns = 3
        NumRows = (len(ColoredLabel_Dict) // NumColumns) + 1
        i = 0
        for row in range(1, NumRows):
            for col in range(NumColumns):
                idx = row * NumColumns + col
                Titel_LabelFrame = ttk.LabelFrame(info_frame, text=ColoredLabel_List[i], bootstyle="success")
                Titel_LabelFrame.grid(row=row, column=col, sticky="nw", padx=10, pady=4)
                ChoseContent = ColoredLabel_Dict[ColoredLabel_List[i]]
                Content_Label = ttk.Label(Titel_LabelFrame, text=self.text_data[dict][ChoseContent], anchor="center",
                                          font=("Arial", 11, "bold"),
                                          foreground="#E63D2E", width=18)
                Content_Label.pack(ipadx=15, ipady=3)
                i += 1

        # přidává podrobné informace
        GeneralInfo_LabelFrame = ttk.Label(info_frame)
        GeneralInfo_LabelFrame.grid(row=3, columnspan=3, pady=10, sticky="w")

        hidden_informations = ["image", "url", "Inzerát", "response_content", "image_name", "Číslo zakázky", "","Cena","Region","Typ","Dispozice","Plocha","Typ nemovitosti"]
        keys_list = list(self.text_data[dict]["general_info"].keys())
        keys_list = sorted([key for key in keys_list if key not in hidden_informations])
        num_columns = 2
        num_rows = (len(keys_list) // num_columns) + 1

        for i in range(num_rows):
            for j in range(num_columns):
                idx = i * num_columns + j
                if idx < len(keys_list):
                    key = keys_list[idx]
                    value = self.text_data[dict]["general_info"][key]
                    if value == '':
                        value = "Ano"
                    elif len(value) >= 43:
                        value = value[:43]
                    InfoTitle = ttk.Label(GeneralInfo_LabelFrame, text=f"{key}:", font=("Arial", 11, "bold"))
                    InfoTitle.grid(row=i, column=j * 2, sticky="e", padx=2, pady=2)
                    InfoValue = ttk.Label(GeneralInfo_LabelFrame, text=f"{value}", font=("Arial", 11))
                    InfoValue.grid(row=i, column=j * 2 + 1, sticky="w", padx=2, pady=2)

        return self.list_frame
    def newest_price(self):
        conn = sqlite3.connect("estate-database.sqlite")
        cursor = conn.cursor()

        data_new = cursor.execute("""SELECT key, MAX(date_created) AS newest_date, value
        FROM Price GROUP BY key;""").fetchall()

        data_old = cursor.execute("""SELECT key, date_downloaded AS first_date, FirstPrice
        FROM FilteredItems GROUP BY key;""").fetchall()

        # Convert fetched data to dictionaries
        dict_new = [{'key': key, 'date': date, 'price': price} for key, date, price in data_new]
        dict_old = [{'key': key, 'date': date, 'price': price} for key, date, price in data_old]

        # Create a dictionary to store data based on keys
        data_dict = {}

        # Populate data_dict with data from dict_new for keys present in dict_old
        for entry in dict_new:
            key = entry['key']
            if key in [item['key'] for item in dict_old]:
                if key not in data_dict:
                    data_dict[key] = {'key': key}
                data_dict[key]['date_new'] = entry['date']
                data_dict[key]['price_new'] = entry['price']

        # Update data_dict with data from dict_old
        for entry in dict_old:
            key = entry['key']
            if key not in data_dict:
                data_dict[key] = {'key': key}
            data_dict[key]['date_old'] = entry['date']
            data_dict[key]['price_old'] = entry['price']

        # Convert data_dict to the desired format
        self.prices_data = data_dict

        return self.prices_data
    def callback(self, url):
        url = self.text_data[dict]["general_info"]["url"]
        webbrowser.open_new_tab(url)
    def format_date(self,date):
        input_DateFormat = "%Y-%m-%d %H:%M:%S.%f"
        output_format = "%d/%m/%Y"
        parsed_date = datetime.strptime(date, input_DateFormat)
        date = parsed_date.strftime(output_format)
        return date
    def format_price(self,price):
       price =  "{:,.2f} Kč".format(int(price)) if price != "Neuvedeno" else price
       return price
    def prepare_data(self,
        query='''SELECT general_info, key, Metry_čtvereční, Typ_nabídky, Typ_nemovitosti, Dispozice, preference,title,FirstPrice,Cena_za_metr,date_downloaded,CheaperEstates,Region FROM FilteredItems WHERE preference = "NEZAŘAZENO" LIMIT 50'''):
        db = sqlite3.connect(self.database_name)
        data1 = pd.read_sql_query(query, db)
        new_data = data1.to_dict(orient='records')
        self.text_data = []

        for item in new_data:
            general_info = json.loads(item['general_info'])
            key = item["key"]
            Dispozice = item["Dispozice"]
            Metry_čtvereční =f"{item['Metry_čtvereční']} m²"
            Typ_nabídky = item["Typ_nabídky"]
            Typ_nemovitosti = item["Typ_nemovitosti"]
            title = item["title"]
            FirstPrice = self.format_price(item["FirstPrice"])
            Cena_za_metr = item["Cena_za_metr"]
            Date = self.format_date(item["date_downloaded"])
            try: CheaperEstates = str("{:.0f}".format(int(item["CheaperEstates"])))+" %"
            except: CheaperEstates = item["CheaperEstates"]
            Region = item["Region"]
            self.text_data.append({"general_info": general_info, "key": key, "Typ_nemovitosti": Typ_nemovitosti,
                                   "Dispozice": Dispozice, "Metry_čtvereční": Metry_čtvereční, "Typ_nabídky": Typ_nabídky,
                                   "title": title,"FirstPrice": FirstPrice,"Cena_za_metr":Cena_za_metr,"CheaperEstates":CheaperEstates,"Region":Region,"date_downloaded": Date})
        return self.text_data
    def recreate_widgets(self):
        for dict, dict_data in enumerate(self.text_data):
            self.create_item(dict).pack(expand=True, fill='both', padx=10, pady=4)

        self.item_number = len(self.text_data)

        self.list_height = self.item_number * self.item_height
        self.canvas.configure(scrollregion=(0, 0, self.winfo_width(), self.list_height))
    def update_data_and_refresh(self, query):
        self.text_data = self.prepare_data(query)
        self.query = query
        self.clear_widgets(self.frame)
        self.recreate_widgets()  # Update the data
        return self.query
    def clear_widgets(self, frame):
        # select all frame widgets and delete them
        for widget in frame.winfo_children():
            widget.destroy()

    def insert_preference_and_refresh(self, value, key):
        # Connect to the SQLite database
        conn = sqlite3.connect("estate-database.sqlite")
        cursor = conn.cursor()

        # Check if the age column exists in the table
        check_column_query = """
        PRAGMA table_info(Item)
        """
        cursor.execute(check_column_query)

        columns = [column[1] for column in cursor.fetchall()]

        # If 'age' column doesn't exist, add it
        if 'preference' not in columns:
            add_column_query = """
            ALTER TABLE FilteredItems
            ADD COLUMN Preference TEXT
            """
            cursor.execute(add_column_query)
            conn.commit()

        # Update the age for the specific row
        update_query = """
        UPDATE FilteredItems
        SET preference = ?
        WHERE key = ?
        """
        cursor.execute(update_query, (value, key))
        conn.commit()
        # Close the connection
        conn.close()

    def save_sorting(self):
        try:
            query = self.query
        except AttributeError:
            query = '''SELECT general_info, key, Metry_čtvereční, Typ_nabídky, Typ_nemovitosti, Dispozice, preference,title,FirstPrice,Cena_za_metr,date_downloaded,CheaperEstates,Region FROM FilteredItems WHERE preference = "NEZAŘAZENO" LIMIT 50'''
        self.text_data = self.prepare_data(query)
        self.clear_widgets(self.frame)
        self.recreate_widgets()


class FavouriteTab(ListFrame):

    def __init__(self, parent, item_height=460, database_name="estate-database.sqlite",):
        super().__init__(parent, item_height, database_name)

    def prepare_data(self,
        query = '''SELECT general_info, key, Metry_čtvereční, Typ_nabídky, Typ_nemovitosti, Dispozice, preference,title,FirstPrice,Cena_za_metr,date_downloaded,CheaperEstates,Region FROM FilteredItems WHERE preference = "SLEDUJI"'''):
        db = sqlite3.connect(self.database_name)
        data1 = pd.read_sql_query(query, db)
        new_data = data1.to_dict(orient='records')
        self.text_data = []

        for item in new_data:
            general_info = json.loads(item['general_info'])
            key = item["key"]
            Metry_čtvereční = f"{item['Metry_čtvereční']} m²"
            Dispozice = item["Dispozice"]
            Typ_nabídky = item["Typ_nabídky"]
            Typ_nemovitosti = item["Typ_nemovitosti"]
            title = item["title"]
            FirstPrice = self.format_price(item["FirstPrice"])
            Cena_za_metr = item["Cena_za_metr"]
            input_Date = item["date_downloaded"]
            input_DateFormat = "%Y-%m-%d %H:%M:%S.%f"
            output_format = "%d/%m/%Y"
            parsed_date = datetime.strptime(input_Date, input_DateFormat)
            Date = parsed_date.strftime(output_format)
            CheaperEstates = str("{:.0f}".format(int(item["CheaperEstates"])))+" %"
            Region = item["Region"]

            self.text_data.append({"general_info": general_info, "key": key, "Typ_nemovitosti": Typ_nemovitosti,
                                   "Dispozice": Dispozice, "Metry_čtvereční": Metry_čtvereční, "Typ_nabídky": Typ_nabídky,
                                   "title": title,"FirstPrice": FirstPrice,"Cena_za_metr":Cena_za_metr,"CheaperEstates":CheaperEstates,"Region":Region,"date_downloaded": Date})
        return self.text_data
    def save_sorting(self):
        self.text_data = self.prepare_data()
        self.clear_widgets(self.frame)
        self.recreate_widgets()

class UnFollowed(ListFrame):
    def __init__(self, parent, item_height=550, database_name="estate-database.sqlite",):
        super().__init__(parent, item_height, database_name)

    def prepare_data(self,
        query = '''SELECT general_info, key, Metry_čtvereční, Typ_nabídky, Typ_nemovitosti, Dispozice, preference,title,FirstPrice,Cena_za_metr,date_downloaded,CheaperEstates,Region FROM FilteredItems WHERE preference = "NESLEDUJI"'''):
        db = sqlite3.connect(self.database_name)
        data1 = pd.read_sql_query(query, db)
        new_data = data1.to_dict(orient='records')
        self.text_data = []

        for item in new_data:
            general_info = json.loads(item['general_info'])
            key = item["key"]
            Metry_čtvereční = f"{item['Metry_čtvereční']} m²"
            Dispozice = item["Dispozice"]
            Typ_nabídky = item["Typ_nabídky"]
            Typ_nemovitosti = item["Typ_nemovitosti"]
            title = item["title"]
            FirstPrice = self.format_price(item["FirstPrice"])
            Cena_za_metr = item["Cena_za_metr"]
            input_Date = item["date_downloaded"]
            input_DateFormat = "%Y-%m-%d %H:%M:%S.%f"
            output_format = "%d/%m/%Y"
            parsed_date = datetime.strptime(input_Date, input_DateFormat)
            Date = parsed_date.strftime(output_format)
            try:CheaperEstates = str("{:.0f}".format(int(item["CheaperEstates"]))) + " %"
            except:CheaperEstates = item["CheaperEstates"]
            Region = item["Region"]

            self.text_data.append({"general_info": general_info, "key": key, "Typ_nemovitosti": Typ_nemovitosti,
                                   "Dispozice": Dispozice, "Metry_čtvereční": Metry_čtvereční, "Typ_nabídky": Typ_nabídky,
                                   "title": title,"FirstPrice": FirstPrice,"Cena_za_metr":Cena_za_metr,"CheaperEstates":CheaperEstates,"Region":Region,"date_downloaded": Date})
        return self.text_data
    def save_sorting(self):
        self.text_data = self.prepare_data()
        self.clear_widgets(self.frame)
        self.recreate_widgets()

if __name__ == "__main__":
    window = tk.Tk()
    window.geometry("1200x500")

    notebook = ttk.Notebook(window)

    unfollowed_data = UnFollowed(notebook, 460, "estate-database.sqlite")
    favourite_data = FavouriteTab(notebook, 460, "estate-database.sqlite")
    main_data = ListFrame(notebook, 460, "estate-database.sqlite")
    data_filter = FilterTab(notebook, "estate-database.sqlite", main_data.update_data_and_refresh)

    test = ttk.Frame(notebook).pack(anchor="nw")
    mn = ttk.Button(test, text="OBNOVIT/ULOŽIT",command=lambda:(unfollowed_data.save_sorting(),favourite_data.save_sorting(),main_data.save_sorting())).pack()

    notebook.add(data_filter, text="Filter nemovitostí")
    notebook.add(main_data, text="Hlavní nabídka")
    notebook.add(favourite_data, text="Oblíbené nemovitosti")
    notebook.add(unfollowed_data, text="Nesledované nemovitosti")
    notebook.pack(expand=True, fill="both")

    window.mainloop()
