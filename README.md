# 🛍️ Comparison Scraper

A backend automation script built with **Flask** that scrapes and compares product data from **eBay** and **Amazon** based on a brand or category search. The script extracts the top 10 product titles, prices, and URLs from each platform, saves the data in **JSON**, and automatically writes it to a **Google Sheet** using the **Google Sheets API**.

## 🚀 Features

- 🔍 Scrapes product **titles**, **prices**, and **URL links** from eBay and Amazon
- 📦 Extracts top **10 products** from each platform (configurable for more)
- 🧠 Compares product data based on price and title
- 📁 Saves output in:
  - `JSON` file
  - Google Sheets (via **Google Sheets API**)
- 🔁 Brand/category-based search input
- ⚙️ Lightweight and easy to deploy

## 🛠️ Tech Stack

- **Python**
- **Flask**
- **BeautifulSoup**
- **Requests**
- **Google Sheets API**


## ⚙️ Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone https://github.com/umr-se/comparison-scraper.git
   cd comparison-scraper
   ```
2. **Install Requirements.txt:**
   ```bash
   pip install -r requirements.txt
   ```
3. **Run**
   ```bash
   flask --app "app" run
   ```
4. **Result**      
![Screenshot 2025-05-19 134845](https://github.com/user-attachments/assets/172390e5-2c10-4a28-9dda-6c6e73d28667)
![Screenshot 2025-05-19 134933](https://github.com/user-attachments/assets/357956e0-c0f2-44f0-bf9d-7e82e1e97a24)


