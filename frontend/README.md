# Artha Frontend

Streamlit-based frontend for the Artha backend API.

---

## Structure

```
frontend/
├── app.py                   # Entry point — run this with streamlit
├── config.py                # API base URL, all endpoint paths, theme tokens
├── utils/
│   ├── api_client.py        # Every backend HTTP call, centralised here
│   └── formatters.py        # Plotly chart builder, timestamp/file helpers
├── components/
│   ├── auth_page.py         # Login / register screen
│   ├── chat_page.py         # Conversation interface and suggestion chips
│   ├── sidebar.py           # File upload, context injection, session controls
│   └── chart_card.py        # Plotly chart rendering from agent data blocks
└── styles/
    └── main.css             # Full dark theme injected into Streamlit
```

---

## Dependencies

```bash
pip install streamlit plotly requests
```

---

## Running

Make sure the backend is already running on `http://localhost:8000`, then:

```bash
cd frontend
streamlit run app.py
```

Opens at `http://localhost:8501`.

To point the frontend at a different backend URL, change `BASE_URL` in `config.py`.
