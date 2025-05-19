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
   


