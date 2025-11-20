import streamlit as st
import requests
import tempfile
import os
from functions import getToken
from csvToCatalog import (
    getAccountName, readCsv, createStructure, createCatalog, 
    createCategories, createSubCategories, getAllProducts, 
    findProductIdbyPlu, getEtag, patchSubCategory
)

# Developer account ID
DEVELOPER_ACCOUNT_ID = "690ca201b9c6f85ca05b6eb1"

def checkAccountAccess(accountId):
    """Check if we can access the account"""
    try:
        account_name = getAccountName(accountId)
        return True, account_name
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            return False, None
        raise
    except Exception as e:
        
        return False, None

def main():
    st.set_page_config(
        page_title="Catalog Importer",
        page_icon="📦",
        layout="centered"
    )
    
    st.title("📦 Catalog Importer")
    st.markdown("Upload a csv and I will create a catalog structure for you.")
    st.markdown("This assumes the products you want to add in there already exist in the account.")
    st.markdown("Expected headers in the CSV file: **Category 1, Category 2, Plu**")
    
    # Download template CSV
    try:
        with open("template.csv", "r", encoding="utf-8") as template_file:
            template_data = template_file.read()
            st.download_button(
                label="📥 Download CSV Template",
                data=template_data,
                file_name="catalog_template.csv",
                mime="text/csv",
                help="Download a template CSV file to see the expected structure with example data"
            )
    except FileNotFoundError:
        st.warning("Template CSV file not found")
    except Exception as e:
        st.error(f"Error loading template: {str(e)}")
    
    st.markdown("---")
    
    # Input fields
    account_id = st.text_input(
        "Account ID",
        placeholder="Enter your Deliverect account ID",
        help="Your Deliverect account ID"
    )
    
    menu_name = st.text_input(
        "Catalog Name",
        placeholder="Enter catalog/menu name",
        help="Name for the new catalog/menu"
    )
    
    csv_file = st.file_uploader(
        "Upload CSV File",
        type=['csv'],
        help="Upload your catalog structure CSV file with Category 1, Category 2, and Plu columns"
    )
    
    # st.markdown("---")
    # st.markdown(f"**Developer Account ID:** `{DEVELOPER_ACCOUNT_ID}`")
    
    # Check account access when account ID is provided
    if account_id:
        with st.spinner("Checking account access..."):
            has_access, account_name = checkAccountAccess(account_id)
        
        if not has_access:
            st.error("❌ Cannot access this account")
            st.warning(
                f"""
                **Account Access Required**
                
                This account is not linked to the developer account. Please link your account 
                to the developer account ID: `{DEVELOPER_ACCOUNT_ID}`
                """
            )
        else:
            st.success(f"✅ Importing for account: **{account_name}**")
    
    st.markdown("---")
    
    # Check if all fields are ready
    all_ready = account_id and menu_name and csv_file
    
    # Show status messages
    if not all_ready:
        if account_id and menu_name and not csv_file:
            st.info("👆 Please upload a CSV file to start the import")
        elif account_id and not menu_name:
            st.info("👆 Please enter a catalog name")
        elif not account_id:
            st.info("👆 Please enter your account ID")
    
    # Start import button - always visible, enabled only when ready
    if st.button("🚀 Start Import", type="primary", use_container_width=True, disabled=not all_ready):
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.csv') as tmp_file:
                tmp_file.write(csv_file.getvalue())
                tmp_path = tmp_file.name
            
            try:
                # Progress tracking
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Create log area for detailed feedback
                st.markdown("### 📋 Import Log")
                log_placeholder = st.empty()
                log_messages = []
                
                def add_log(message):
                    import time
                    timestamp = time.strftime('%H:%M:%S')
                    log_messages.append(f"[{timestamp}] {message}")
                    # Display last 50 messages in a code block for better readability
                    with log_placeholder.container():
                        st.code("\n".join(log_messages[-50:]), language=None)
                
                # Step 1: Read CSV
                status_text.text("📄 Reading CSV file...")
                add_log("📄 Reading CSV file...")
                rows = readCsv(tmp_path)
                progress_bar.progress(10)
                add_log(f"✓ Loaded {len(rows)} rows from CSV")
                st.success(f"✓ Loaded {len(rows)} rows from CSV")
                
                # Step 2: Create structure
                status_text.text("🔧 Building category structure...")
                add_log("🔧 Building category structure...")
                structure = createStructure(rows)
                progress_bar.progress(20)
                add_log(f"✓ Created structure with {len(structure)} main categories")
                st.success(f"✓ Created structure with {len(structure)} main categories")
                
                # Step 3: Create catalog
                status_text.text("📋 Creating catalog...")
                add_log(f"📋 Creating catalog: '{menu_name}'...")
                new_menu_id = createCatalog(account_id, menu_name)
                progress_bar.progress(30)
                add_log(f"✓ Created catalog: '{menu_name}'")
                st.success(f"✓ Created catalog: '{menu_name}'")
                
                # Step 4: Fetch products
                status_text.text("🛒 Fetching all products...")
                add_log("🛒 Fetching all products...")
                
                # Custom getAllProducts with logging
                all_products = []
                page = 1
                page_size = 500
                token = getToken()
                headers = {'Authorization': f'Bearer {token}'}
                
                while True:
                    payload = {
                        "page": page,
                        "visible": True,
                        "max_results": page_size,
                        "sort": "-_id"
                    }
                    resp = requests.post(f"https://api.deliverect.io/catalog/accounts/{account_id}/items", json=payload, headers=headers).json()
                    
                    items = resp.get("_items") if isinstance(resp, dict) else []
                    if not items:
                        break
                    
                    all_products.extend(items)
                    meta = resp.get("_meta", {}) if isinstance(resp, dict) else {}
                    total_pages = meta.get("total_pages")
                    current_page = meta.get("page")
                    total = meta.get("total")
                    
                    # Show pagination progress
                    log_msg = f"📦 Page {current_page}/{total_pages if total_pages else '?'} - {len(items)} items (Total so far: {len(all_products)})"
                    add_log(log_msg)
                    status_text.text(log_msg)
                    
                    if (total_pages and current_page and current_page >= total_pages) or len(items) < page_size:
                        break
                    
                    page += 1
                
                progress_bar.progress(50)
                add_log(f"✓ Loaded {len(all_products)} products total")
                st.success(f"✓ Loaded {len(all_products)} products")
                
                # Step 5: Process categories
                status_text.text("📂 Processing categories and subcategories...")
                add_log("📂 Processing categories and subcategories...")
                total_operations = sum(1 + len(cat2) for cat2 in structure.values())
                progress_increment = 40 / max(total_operations, 1)
                current_progress = 50
                
                results = {
                    "categories_created": 0,
                    "subcategories_created": 0,
                    "products_added": 0,
                    "errors": []
                }
                
                category_count = 0
                total_categories = len(structure)
                
                for category1_name, category2_dict in structure.items():
                    category_count += 1
                    try:
                        add_log(f"📁 [{category_count}/{total_categories}] Processing category: {category1_name}")
                        status_text.text(f"Processing category {category_count}/{total_categories}: {category1_name}")
                        new_category_id = createCategories(account_id, new_menu_id, category1_name)
                        results["categories_created"] += 1
                        add_log(f"  ✓ Created category: '{category1_name}'")
                        current_progress += progress_increment
                        progress_bar.progress(min(int(current_progress), 90))
                        
                        subcategory_count = 0
                        total_subcategories = len(category2_dict)
                        
                        for category2_name, plu_list in category2_dict.items():
                            subcategory_count += 1
                            try:
                                add_log(f"    [{subcategory_count}/{total_subcategories}] Processing subcategory: {category2_name}")
                                new_sub_category_id = createSubCategories(account_id, new_menu_id, new_category_id, category2_name)
                                results["subcategories_created"] += 1
                                add_log(f"    ✓ Created subcategory: '{category2_name}'")
                                
                                # Get etag for the subcategory
                                try:
                                    etag = getEtag(new_sub_category_id)
                                    add_log(f"      ✓ Retrieved etag for subcategory")
                                except Exception as etag_error:
                                    error_msg = f"Failed to get etag for subcategory '{category2_name}': {str(etag_error)}"
                                    add_log(f"      ❌ {error_msg}")
                                    results["errors"].append(error_msg)
                                    # Skip adding products if we can't get etag
                                    current_progress += progress_increment
                                    progress_bar.progress(min(int(current_progress), 90))
                                    continue
                                
                                subProducts = []
                                
                                add_log(f"      🔍 Looking up {len(plu_list)} PLUs...")
                                found_count = 0
                                for plu in plu_list:
                                    product_id = findProductIdbyPlu(all_products, plu)
                                    if product_id:
                                        subProducts.append(product_id)
                                        found_count += 1
                                
                                if subProducts:
                                    add_log(f"      ✓ Found {found_count}/{len(plu_list)} products")
                                    patchSubCategory(new_sub_category_id, subProducts, etag)
                                    results["products_added"] += len(subProducts)
                                    add_log(f"      ✓ Added {len(subProducts)} products to subcategory")
                                else:
                                    add_log(f"      ⚠ No products found for {len(plu_list)} PLUs")
                                
                                current_progress += progress_increment
                                progress_bar.progress(min(int(current_progress), 90))
                            except Exception as e:
                                error_msg = f"Error in subcategory '{category2_name}': {str(e)}"
                                add_log(f"      ❌ {error_msg}")
                                results["errors"].append(error_msg)
                    except Exception as e:
                        error_msg = f"Error in category '{category1_name}': {str(e)}"
                        add_log(f"  ❌ {error_msg}")
                        results["errors"].append(error_msg)
                
                progress_bar.progress(100)
                status_text.text("✅ Import completed!")
                add_log("✅ Catalog import completed!")
                
                # Show results
                st.balloons()
                st.success("🎉 Catalog import completed successfully!")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Categories Created", results["categories_created"])
                with col2:
                    st.metric("Subcategories Created", results["subcategories_created"])
                with col3:
                    st.metric("Products Added", results["products_added"])
                
                if results["errors"]:
                    st.warning(f"⚠️ {len(results['errors'])} error(s) occurred:")
                    for error in results["errors"]:
                        st.text(f"• {error}")
                
            except Exception as e:
                st.error(f"❌ Error during import: {str(e)}")
                st.exception(e)
            finally:
                # Clean up temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

if __name__ == "__main__":
    main()
