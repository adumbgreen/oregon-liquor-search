from bs4 import BeautifulSoup as Soup
from requests.sessions import Session
import json
import re
import sys


INITIAL_URL = "http://www.oregonliquorsearch.com/home.jsp"
BUTTON_REQUEST_URL = "http://www.oregonliquorsearch.com/servlet/WelcomeController"
SEARCH_INITIATE_URL = "http://www.oregonliquorsearch.com/servlet/FrontController?view=global&action=search&radiusSearchParam=10&productSearchParam={}&locationSearchParam=&btnSearch=Search"


def find_item(name):
    with Session() as session:
        session.get(INITIAL_URL)

        # press the 'I'm 21 or older' button

        session.post(BUTTON_REQUEST_URL, data={
            "btnSubmit": "I'm 21 or older"
        })

        # search for some liquor.
        # GET /servlet/FrontController
        # onsubmit="setLocationCookie(); return validateSearch();"

        # function setLocationCookie()
        # {
        #   // check if checkbox is turned on
        #   if (document.getElementById("default").checked)
        #   {
        #       // set cookie
        #       createCookie("dsiLocation",document.getElementById("location").value,365);
        #   }
        #   else
        #   {
        #       // if cookie exists, unset it
        #       createCookie("dsiLocation","",365);
        #   }
        # }
        # function validateSearch()
        # {
        #     var valid = true;
        #     if (document.getElementById("product").value == "" && document.getElementById("location").value == "")
        #     {
        #       alert("Please specify a product and/or a location.");
        #       document.getElementById("product").focus();
        #       valid = false;
        #     }
        #     return valid;
        # }

        # based on this, we can ignore these two calls and skip straight to the request. there's no magic here.
        # after a search in the browser, we get a couple of 302s that send us to different URLs, the final of which
        # provides us with an ID. requests will follow these for us automatically.

        # from there, we want to change the pageSize GET param to 100 so that we can see everything on 1 page hopefully
        # one of the GET parameters that is required for some reason is not just the item code, but also the number of
        # results (rowCount)??
        # but luckily the JSP page gives us this in a select element, so we will just snatch that and
        # add '&pageSize=100' to see everything at once.

        # TODO: make this work with multiple paegs.
        #  but on the other hand, why are you using this if supply isn't an issue?

        response = session.get(SEARCH_INITIATE_URL.format(name))
        html = Soup(response.text, features="html.parser")

        # caveat: if we try to search a direct newItemCode, the select element to change the page size won't
        # include the code? we'll need to tease them out and add them ourselves if they're not there.

        product_desc = "".join(html.find('th', {'id': 'product-desc'}).get_text().split())
        new_item_code = product_desc.split("(")[0].replace("Item", "").strip()
        item_code = re.findall(r"\((\w+)\):", product_desc)

        new_url = 'http://www.oregonliquorsearch.com' + html.find('select', {'name': 'pageSize'}).attrs['onchange'].split("'")[1] + '100'

        if 'itemCode' not in new_url:
            new_url += '&itemCode={}'.format(item_code)
        if 'newItemCode' not in new_url:
            new_url += '&newItemCode={}'.format(item_code, new_item_code)

        response = session.get(new_url)

        html = Soup(response.text, features="html.parser")
        results_table = html.find('table', {'class': 'list'})
        data = []

        for row in results_table.find_all('tr'):
            # tr >
            #      td: store no. (img if store in store)
            #      td: city
            #      td: address
            #      td: zip
            #      td: phone
            #      td: hours
            #      td: quantity

            new_record = {}

            cols = row.find_all('td')

            if not cols:
                # probably the header row
                continue

            if cols[0].find_all('img'):
                new_record['store_in_a_store'] = True

            cols = [ele.text.strip() for ele in cols]
            new_record.update({
                'store_number': cols[0],
                'city': cols[1],
                'address': cols[2],
                'zip': cols[3],
                'phone': cols[4],
                'hours': cols[5],
                'quantity': int(cols[6].strip()) if cols[6].strip() else 0
            })
            if new_record['quantity'] > 0:
                data.append(new_record)

        return data


def main():
    if len(sys.argv) <= 1:
        print("No arguments specified.")
        exit(-1)

    dump = False
    args = sys.argv[1:]
    queries = [arg for arg in args if arg != '--dump']
    if '--dump' in args:
        dump = True

    for query in queries:
        data = find_item(query)
        if dump:
            print(json.dumps(data))

    # blantons_data = find_item('blanton')
    # macallan_data = find_item('99900390375')  # Macallan 12 Double Cask
    # print(pprint.pprint(blantons_data))


if __name__ == '__main__':
    main()
