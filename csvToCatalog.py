import csv 

import json
import requests
from functions import getToken
path = "/Users/victorbertels/Downloads/CatalogStructure.csv"
token = getToken()
# Token will be fetched fresh in each function to avoid stale tokens

def readCsv(path):
    with open(path, 'r') as file:
        dict_reader = csv.DictReader(file)
        return list(dict_reader)

def createStructure(rows):
    categoryStructure = {}
    for row in rows:
        category1 = row.get("Category 1")
        category2 = row.get("Category 2")
        plu = row.get("Plu")
        
        # Skip rows with missing data
        if not category1 or not category2 or not plu:
            continue
        
        # Initialize Category 1 if it doesn't exist
        if category1 not in categoryStructure:
            categoryStructure[category1] = {}
        
        # Initialize Category 2 if it doesn't exist
        if category2 not in categoryStructure[category1]:
            categoryStructure[category1][category2] = []
        
        # Add PLU to the list if it's not already there
        if plu not in categoryStructure[category1][category2]:
            categoryStructure[category1][category2].append(plu)
    
    return categoryStructure

def saveToJson(structure, output_path):
    with open(output_path, 'w', encoding='utf-8') as file:
        json.dump(structure, file, indent=2, ensure_ascii=False)

def createCatalog(accountId, name):
    headers = {
        'Authorization': f'Bearer {token}'
    }
    url = f'https://api.deliverect.io/catalog/accounts/{accountId}/catalog'
    payload = {"fillType":"EMPTY","menuType":0,"name":name,"internalName":"","description":""}
    response = requests.post(url = url, headers=headers, json=payload)
    catalog_id = response.json()["catalogId"]
    print(f"✓ Created catalog: '{name}'")
    return catalog_id


def getAccountName(accountId):  
    headers = {
        'Authorization': f'Bearer {token}'
    }
    url = f'https://api.deliverect.io/accounts/{accountId}'
    response = requests.get(url = url, headers=headers)
    return response.json()["name"]


def createCategories(accountId, catalogId, categoryName):
    headers = {
        'Authorization': f'Bearer {token}'
    }
    url = f'https://api.deliverect.io/channelCategories'
    payload = {"name": categoryName, "description": "", "menu": catalogId, "account": accountId}
    response = requests.post(url = url, headers=headers, json=payload)
    category_id = response.json()["_id"]
    print(f"  ✓ Created category: '{categoryName}'")
    return category_id



def createSubCategories(accountId, catalogId, categoryId, subCategoryName):
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    url = f"https://api.deliverect.io/catalog/accounts/{accountId}/catalog/{catalogId}/category/{categoryId}/subCategory"
    payload = {"name": subCategoryName, "description": "", "menu": catalogId, "account": accountId}
    response = requests.post(url = url, headers=headers, json=payload)
    response_data = response.json()
    subcategory_id = response_data["id"]
    print(f"    ✓ Created subcategory: '{subCategoryName}' ")
    return subcategory_id

def getAllProducts(accountId):
    all_products = []
    page = 1
    page_size = 500

    headers = {
        'Authorization': f'Bearer {token}'
    }

    while True:
        payload = {
            "page": page,
            "visible": True,
            "max_results": page_size,
            "sort": "-_id"
        }
        resp = requests.post(f"https://api.deliverect.io/catalog/accounts/{accountId}/items",json=payload, headers=headers
        ).json()

        # Try common list keys; adjust to your API’s response shape if needed
        items = resp.get("_items") if isinstance(resp, dict) else []
        
        if not items:
            break

        all_products.extend(items)

        # If the API returns pagination metadata, you can use it too:
        meta = resp.get("_meta", {}) if isinstance(resp, dict) else {}
        total_pages = meta.get("total_pages")
        current_page = meta.get("page")
        total = meta.get("total")

        # Print pagination info
        print(f"📦 Fetching products: Page {current_page}/{total_pages if total_pages else '?'} ({len(items)} items) | Total: {total if total else '?'}")
        
        # Stop if we're on the last page (by meta) or got fewer than a full page
        if (total_pages and current_page and current_page >= total_pages) or len(items) < page_size:
            break

        page += 1
    
    return all_products


def findProductIdbyPlu(products, plu):
    for product in products:
        if plu == product.get("plu"):
            return product["_id"]
    return None

def getEtag(subCategoryId, retry_count=3, delay=0.5):
    """
    Get etag for a subcategory with retry logic.
    Sometimes the etag might not be immediately available after creation.
    """
    import time
    
    headers = {
        'Authorization': f'Bearer {token}'
    }
    url = f"https://api.deliverect.io/channelCategories/{subCategoryId}"
    
    for attempt in range(retry_count):
        try:
            response = requests.get(url=url, headers=headers)
            
            # Check if request was successful
            response.raise_for_status()
            
            data = response.json()
            
            # Check if _etag exists in response
            if "_etag" in data:
                return data["_etag"]
            elif "etag" in data:
                return data["etag"]
            elif "_ETag" in data:
                return data["_ETag"]
            else:
                # If this is not the last attempt, wait and retry
                if attempt < retry_count - 1:
                    time.sleep(delay)
                    continue
                else:
                    raise KeyError(
                        f"_etag not found in response for subcategory {subCategoryId}. "
                        f"Response keys: {list(data.keys())}. "
                        f"Full response: {data}"
                    )
        except requests.exceptions.HTTPError as e:
            if attempt < retry_count - 1:
                time.sleep(delay)
                continue
            else:
                raise Exception(f"Failed to get etag after {retry_count} attempts: {str(e)}")
    
    raise Exception(f"Failed to get etag for subcategory {subCategoryId} after {retry_count} attempts")


def patchSubCategory(subCategoryId, subProducts, etag):
    headers = {
        'Authorization': f'Bearer {token}',
        'If-Match': etag
    }
    url = f"https://api.deliverect.io/channelCategories/{subCategoryId}"
    payload = {"subProducts": subProducts}
    response = requests.patch(url = url, headers=headers, json=payload)
    print(f"      ✓ Added {len(subProducts)} products to subcategory")

if __name__ == "__main__":
    print("🚀 Starting catalog import process...\n")
    
    # Read CSV file
    print("📄 Reading CSV file...")
    rows = readCsv(path)
    print(f"✓ Loaded {len(rows)} rows from CSV\n")
    
    # Create nested structure
    print("🔧 Building category structure...")
    structure = createStructure(rows)
    print(f"✓ Created structure with {len(structure)} main categories\n")
    
    # Create catalog
    account_id = "67e527dc3acf4b582fdc360b"
    print("📋 Creating catalog...")
    new_menu_id = createCatalog(account_id, "test menudddd")
    print()
    
    # Fetch all products
    print("🛒 Fetching all products...")
    all_products = getAllProducts(account_id)
    print(f"✓ Loaded {len(all_products)} products\n")
    
    # Method 1: Loop over Category 1 (keys)
    print("📂 Processing categories and subcategories...\n")
    for category1_name, category2_dict in structure.items():
        print(f"📁 Category 1: {category1_name}")
        new_category_id = createCategories(account_id, new_menu_id, category1_name)
        
        # Method 2: Loop over Category 2 (nested keys)
        for category2_name, plu_list in category2_dict.items():
            new_sub_category_id = createSubCategories(account_id, new_menu_id, new_category_id, category2_name)
            etag = getEtag(new_sub_category_id)
            subProducts = []
            
            # Method 3: Loop over PLUs (list)
            found_count = 0
            for plu in plu_list:
                product_id = findProductIdbyPlu(all_products, plu)
                if product_id:
                    subProducts.append(product_id)
                    found_count += 1
            
            if subProducts:
                patchSubCategory(new_sub_category_id, subProducts, etag)
            else:
                print(f"      ⚠ No products found for {len(plu_list)} PLUs")
        print()  # Empty line between categories
    
    print("✅ Catalog import completed!")
    
   