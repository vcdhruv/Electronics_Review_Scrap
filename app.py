from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import logging
import time

app = Flask(__name__)

logging.basicConfig(
    filename="scrapper.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(funcName)s - %(lineno)d",
    datefmt="%Y-%m-%d %H:%M:%S"
)

site_url = "https://www.flipkart.com"
base_url = "https://www.flipkart.com/search?q="
headers = {"User-Agent": "Mozilla/5.0 (X11; CrOS x86_64 12871.102.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.141 Safari/537.36"}

def fetch_with_retry(url):
    while True:
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response
            elif response.status_code == 429:  # Too Many Requests
                retry_after = int(response.headers.get("Retry-After", 1))
                logging.warning(f"Rate limited. Retrying after {retry_after} seconds.")
                print(f"Retrying after { retry_after} seconds")
                time.sleep(retry_after)
            else:
                logging.error(f"Failed to fetch {url} with status code {response.status_code}")
                print("Failed to fetch {url} with status code {response.status_code}")
                return response
        except requests.RequestException as e:
            logging.error(f"Request failed: {e}")
            print(f"Request failed: {e}")
            time.sleep(5)  # Wait before retrying

@app.route('/', methods=['GET'])
def index_page():
    return render_template('index.html')

@app.route('/reviews', methods=['POST'])
def review():
    if request.method == 'POST':
        user_searched = request.form["search"]
        search_string = user_searched.replace(" ", "")
        logging.info(f"User searched {search_string}")

        main_url = base_url + search_string
        main_url_res = fetch_with_retry(main_url)
        if main_url_res.status_code != 200:
            logging.error(f"Failed to fetch main url: {main_url}")
            return "Error: Failed to fetch search results from Flipkart", 500

        soup = BeautifulSoup(main_url_res.text, "html.parser")
        bigbox = soup.find_all("div", {"class": "cPHDOP col-12-12"})
        if len(bigbox) < 3:
            logging.error("Not enough records found on the search page.")
            return "Error: Not enough products found", 404

        del bigbox[0:2]
        go_to_particular_page_links = []
        for i in bigbox:
            try:
                page_link = i.div.div.div.a["href"]
                go_to_particular_page_links.append(site_url + page_link)
            except Exception as e:
                logging.warning(f"Could not find href in bigbox: {e}")

        if not go_to_particular_page_links:
            logging.error("No product links found")
            return "<h1>Not Enough Reviews</h1>", 404

        product_link = go_to_particular_page_links[0]
        product_link_res = fetch_with_retry(product_link)
        if product_link_res.status_code != 200:
            logging.error(f"Failed to fetch product page: {product_link}")
            return "Error: Failed to fetch product page", 500

        mobile_soup = BeautifulSoup(product_link_res.text, "html.parser")
        reviews_list = mobile_soup.find_all("div", {"class": "col EPCmJX"})
        logging.info(f"Review list length: {len(reviews_list)}")

        final_reviews_list = []
        for i in reviews_list:
            review = {
                'Product': search_string,
                'Name': i.find("div", {"class": "row gHqwa8"}).div.p.text if i.find("div", {"class": "row gHqwa8"}) else "N/A",
                'Ratings': i.div.div.text if i.div.div else "N/A",
                'Comment': i.div.p.text if i.div.p else "N/A",
                'Description': i.find("div", {"class": "ZmyHeo"}).div.div.text if i.find("div", {"class": "ZmyHeo"}) else "N/A"
            }
            final_reviews_list.append(review)

        logging.info(f"Final Review List To Be Added: {final_reviews_list}")
        return render_template('results.html', results=final_reviews_list)

if __name__ == "__main__":
    app.run(debug=True)
