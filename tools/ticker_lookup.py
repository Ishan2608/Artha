import os
import pandas as pd

# Global dictionary for O(1) lookup.
_lookup_table: dict[str, dict] = {}
_listings_path = os.path.join("data", "listings", "INDIA_LIST.csv")

def _load_listings() -> None:
    """
    Loads stock market listings from a CSV file into a global in-memory dictionary.
    
    Reads 'INDIA_LIST.csv', cleans formatting anomalies (like 'N/A' strings and 
    '.0' float suffixes on security codes), and maps each company's name, NSE symbol, 
    BSE symbol, and BSE code to a unified data dictionary. This enables instant O(1) 
    lookups across different identifiers without repeatedly accessing the disk.
    """
    global _lookup_table

    # 1: Check if file exists
    if not os.path.exists(_listings_path):
        print(f"Warning: {_listings_path} not found. Ticker lookup will return no results.")
        return
    
    # 2: Read and clean the CSV
    df = pd.read_csv(_listings_path, dtype=str)
    df = df.replace(["N/A", "nan", "NA", "-", "NaN"], "")
    df = df.fillna("")

    # 3: Iterate through rows
    for index, row in df.iterrows():
        
        # 4: Extract and strip variables
        isin = str(row.get('ISIN', '')).strip()
        company_name = str(row.get('Company_Name', '')).strip()
        nse_symbol = str(row.get('NSE_Symbol', '')).strip()
        bse_symbol = str(row.get('BSE_Symbol', '')).strip()
        bse_code_raw = str(row.get('Security Code', '')).strip()
        
        # 5: Fix the BSE Code float issue ("890232.0" -> "890232")
        if bse_code_raw.endswith(".0"):
            bse_code = bse_code_raw[:-2]
        else:
            bse_code = bse_code_raw

        # 6: Skip empty ISINs
        if not isin:
            continue

        # 7: Create the entry dictionary
        entry = {
            "company_name": company_name,
            "nse_symbol": nse_symbol,
            "bse_symbol": bse_symbol,
            "bse_code": bse_code,
            "isin": isin
        }

        # 8: Add to lookup table under all available keys
        if company_name:
            _lookup_table[company_name.lower()] = entry
        if nse_symbol:
            _lookup_table[nse_symbol.lower()] = entry
        if bse_symbol:
            _lookup_table[bse_symbol.lower()] = entry
        if bse_code:
            _lookup_table[bse_code] = entry

    # 9: Initialization message
    print(f"Loaded {len(_lookup_table)} lookup keys from INDIA_LIST.")


def search_ticker(query: str) -> list[dict]:
    """
    Searches the in-memory lookup table for a stock using a user's query.
    
    Args:
        query (str): The company name, ticker symbol, or security code to search for.
        
    Returns:
        list[dict]: A list of up to 5 matching company dictionaries. Results are 
                    prioritized by exact matches, followed by prefix matches 
                    (starts with), and then substring matches (contains). 
                    Duplicates are filtered out using the company's ISIN.
    """
    # 10: Lazy load if empty
    if not _lookup_table:
        _load_listings()

    # 11: Clean query
    query_lower = query.strip().lower()
    if not query_lower:
        return []

    # 12: Exact match check (O(1) speed)
    if query_lower in _lookup_table:
        return [_lookup_table[query_lower]]

    # 13: Setup for fuzzy search
    starts_with = []
    contains = []
    seen_isins = set()

    # 14 & 15: Fuzzy match iteration
    for key, entry in _lookup_table.items():
        current_isin = entry['isin']
        
        if current_isin in seen_isins:
            continue
            
        if key.startswith(query_lower):
            starts_with.append(entry)
            seen_isins.add(current_isin)
        elif query_lower in key:
            contains.append(entry)
            seen_isins.add(current_isin)

    # 16: Combine and limit results
    return (starts_with + contains)[:5]

# Run on import
_load_listings()


# TEST THE FUNCTIONS USING THIS CODE.
if __name__ == "__main__":
    print("\n--- Testing Exact Match (TCS) ---")
    results = search_ticker("TCS")
    for r in results: print(r)

    print("\n--- Testing Partial/Fuzzy Match (HDFC) ---")
    results = search_ticker("HDFC")
    for r in results: print(r)

    print("\n--- Testing BSE Code Match (500180) ---")
    results = search_ticker("500180")
    for r in results: print(r)

    print("\n--- Testing Invalid Query ---")
    results = search_ticker("FAKECOMPANYNAME123")
    print(results)
