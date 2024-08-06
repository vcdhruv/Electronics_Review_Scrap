from flask import Flask , render_template , redirect , url_for , request
import requests
from bs4 import BeautifulSoup
import logging
import time
import os
import csv

app = Flask(__name__)
logging.basicConfig(
    filename="scrapper.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(funcName)s - %(lineno)d",
    datefmt="%Y-%M-%d %H:%M:%S"
)
site_url = "https://www.flipkart.com"
base_url = "https://www.flipkart.com/search?q="


def fetch_with_retry(url):
    while True:
        response = requests.get(url)
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 1))
            logging.warning(f"Rate limited. Retrying after {retry_after} seconds.")
            time.sleep(retry_after)
        else:
            return response

@app.route('/',methods=['GET'])
def index_page():
    return render_template('index.html')

@app.route('/reviews',methods=['POST'])
def review():
    if request.method == 'POST':
        try:
            f = None
            user_searched = request.form["search"]
            search_string = user_searched.replace(" ","")
            logging.info(f"User searched {search_string}")

            main_url = base_url + search_string
            main_url_res = fetch_with_retry(main_url)
            # logging.info(f"Response of {main_url} is {main_url_res}")

            if main_url_res.status_code != 200:
                logging.error(f"Failed to fetch main url : {main_url}")
                # return "Error : Failed to fetch search results from Flipkart",500

            soup = BeautifulSoup(main_url_res.text,"html.parser")
            soup.find_all("div",{"class":"cPHDOP col-12-12"})

            bigbox = soup.find_all("div",{"class":"cPHDOP col-12-12"})
            if len(bigbox) < 3:
                logging.error("Not enough records found on the search page.")
                # return "Error: Not enough products found",404
            
            del bigbox[0:2]
            go_to_particular_page_links = []
            for i in bigbox:
                try:
                    page_link = i.div.div.div.a["href"]
                    logging.info(f"product link  : {site_url + page_link}")
                    go_to_particular_page_links.append(site_url + page_link)
                except Exception as e:
                    logging.warning(f"Could not find href in bigbox : {e}")

            if not go_to_particular_page_links:
                logging.error("No product links found")
                return "<h1>Not Enough Reviews</h1>"
            
            product_link = go_to_particular_page_links[0]
            product_link_res = fetch_with_retry(product_link)
            # logging.info(f"Response of {product_link} is {product_link_res}")
            if product_link_res.status_code != 200:
                logging.error(f"Failed to fetch product page : {product_link}")
                # return "Error : Failed to fetch product page",500
            
                        
            mobile_soup = BeautifulSoup(product_link_res.text,"html.parser")

            reviews_list = mobile_soup.find_all("div",{"class":"col EPCmJX"})
            # reviews_list = mobile_soup.find_all(lambda tag: tag.name == 'div' and tag.get('class') and any('EPCmJX' in c for c in tag['class']))
            logging.info(f"review list length : {len(reviews_list)}")
            # logging.info(f"review list 2 : {rl}")

            try:  
                f = open(f"{user_searched}.csv","w",encoding="utf-8")
                f.write("Name,Ratings,Comment,Descriptions\n")
            except Exception as e:
                logging.error(e)
                return None
            final_reviews_list = []
            for i in reviews_list:
                review = {
                    'Product':search_string,
                    'Name':"N/A",
                    'Ratings':"N/A",
                    'Comment':"N/A",
                    'Description':"N/A"
                }

                try:
                    review["Name"] = i.find("div",{"class":"row gHqwa8"}).div.p.text
                except:
                    logging.warning("Name not found")
                
                try:
                    review["Ratings"] = i.div.div.text
                except:
                    logging.warning("Ratings not found")
                
                try:
                    review["Comment"] = i.div.p.text
                except:
                    logging.warning("Comment not found")
                
                try:
                    review["Description"] =  i.find("div",{"class":"ZmyHeo"}).div.div.text
                except:
                    logging.warning("Description not found")
                
                
                logging.info(f"Appending to result : {review}")
                final_reviews_list.append(review)

            logging.info("exporing data to csv file locally")
            for i in final_reviews_list:
                f.write(i["Name"]+",")
                f.write(i["Ratings"]+",")
                f.write(i["Comment"]+",")
                f.write(i["Description"]+"\n")
            logging.info(f"Final Review List To Be Added : {final_reviews_list}")
            
                
            return render_template('results.html',results = final_reviews_list)
        except Exception as e:
            logging.error(e)
        finally:
            if f is not None:
                f.close()
                logging.info("file is closed successfully")

if __name__ == "__main__":
    app.run(host="0.0.0.0")