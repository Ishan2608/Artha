# Day 1

## Project Directory Setup

### Update `pip` version.
> python.exe -m pip install --upgrade pip  

### Setup virtual environment using python
Setup a virtual environment to maintain a separate package of dependencies, for this folder specifically to maintain consistency of version of packages, regardless of what happens in other parts of the PC.
Command:
> python -m venv <IDENTIFIER_FOR_THIS_VIRTUAL_ENV>
> python -m venv venv

- `-m` tells PC to user built in python venv module.
- To create requirements.txt file: `pip freeze > requirements.txt`

## Understand Pydantic

### Type Enforcing.
Python library for data parsing and type validation. Useful to enforce a predefined data structure/format between functions, and frontend and backend.
- **BaseModel:** The fundamental class of Pydantic. Inheriting from it transforms a standard Python class into a strictly validated data schema.
- **Field(..., description="..."):** The Field function applies additional constraints and metadata to an attribute. The ellipsis (...) as the first argument is a Python syntax convention used by Pydantic to explicitly declare that the field is required and has no default value. The description parameter is utilized by frameworks like FastAPI to automatically generate interactive API documentation (Swagger UI).
- **Optional:** Imported from Python's typing module, it indicates that a field can either hold its specified type or be None.
- **Any:** Indicates that a value can be of any data type without failing validation. dict[str, Any] means a dictionary where the keys are strings, but the values can be anything (integers, strings, lists, etc.).

### Project Settings
Pydantic provides BaseSettings class to build our custom class, that reads environment variables and .env file and initialize the environment variables for the project without us having to do it manually anywhere in the project. Just inherit from class, define variables like this:
> KEY_NAME_IN_ENV: TYPE

Inside the class, you define another class with name -> `Config` to clearly define from where to get the data. Without this, Pydantic only reads form system's environment variables. To read from your specific .env file named `.env`:
> env_file = ".env"

In the file defining this code, just instantiate the class, by creating a object from it. Other files simply import this object.

## Conversation Session Storage

In development mode, we maintain an in-memory session, i.e., in RAM. Data is lost when program stops running.

> `defaultdict` is a subclass of Python's built-in dict class, located in the standard collections module. It overrides the `__missing__(key)` method to automatically provide a default value for a nonexistent key, completely eliminating standard KeyError exceptions during key access.
> When you instantiate a defaultdict, you pass it a callable argument known as the default_factory (such as list, int, or a custom lambda function). If you attempt to access a key that does not currently exist in the dictionary, it executes the default_factory to generate a base value, maps that new value to the missing key, and returns it.

```
{
    "session_id": {
        "history": [
            {
              "role": "user" | "assistant" | "system",
              "content": str
            },
        ],
        "files": [
            { 
              "file_id": str, 
              "filepath": str, 
              "filename":str 
            },
        ]
    }
}
```

# Day 2

## Getting List of Securities on Indian Stock Market.
1. Get the list of all companies listed on **BSE** using the following link: [BSE_SITE](https://www.bseindia.com/corporates/List_Scrips.html)
    - Select `Segment = Equity T+1` and `Status = Active`
2. Get the list of all companies listed on **NSE** using the following link: [NSE_SITE](https://www.nseindia.com/static/market-data/securities-available-for-trading)
    - Select the First file: `Securities available for Equity segment (.csv)`

## Cleaning And Merging the Lists.
- Each company has a ISIN number, which uniquely identifies it in the world. Both downloaded CSV files have this.
- Both had different columns names for same columns. E.g., In NSE List = Symbol, and in BSE List = Security Id. Had to rename names for consistency.
- BSE List (CSV file) was terrible. Extra leading commas at the end of each row confused pandas. It had to be significantly cleaned.
- A merged CSV file was created using the JOIN on the ISIN column.

## Ticker Builders for Getting Right Data.
Implemented functions to take a Company Name, even if incomplete, and return its ticker according to exchange.

## Implement Stock Data Fetching Tools.
- Historical OHLC Data.
- ESG Reports
- Financials
- Corporate Actions
- Base Analyses
- Share Holders Data
- Upcoming Events.

> To run a file from a folder, keeping the Root Folder as the Root Folder during compile time so that imports from other folders are resolved properly, use this command: python -m tools.stock_data

## Implement Web Search and News Search
- Both Tavily and NewsAPI have their respective Python SDK.
- Build client object for both.
- Get results based on query.
- Filter individual result in result, including data in cleaned manner and returning the list of cleaned results.

## Implement RAG
- Use Chromas DB
- Implement rag_engine.py in utils.
- Implement document_search.py in tools.

## Implement Time Series Forcasting Model Tool.
- Import Amazon's t5 tiny model.
- Update test_tools.py
