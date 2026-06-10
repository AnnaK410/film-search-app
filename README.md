# 🎬 Film Search App — DB "sakila"

An interactive console application for searching movies from the **MySQL Sakila** database, with query logging powered by **MongoDB**.

Built as a final academic project demonstrating clean Python architecture, dual-database integration, and a polished terminal UX.

---

## ✨ Features

- **Search by keyword** — find movies by partial title match, paginated 10 at a time
- **Search by genre & year range** — browse all genres and database year bounds before filtering
- **Search by actor & year range** — find an actor by name fragment, then filter their filmography
- **Film detail view** — select any displayed film to read its full description
- **MongoDB query logging** — every search (including empty results) is recorded with timestamp, parameters, result count, and pages viewed
- **Statistics dashboard** — three tabular reports:
  - Top 5 most frequent queries
  - Top 5 most recent unique queries
  - Search type popularity breakdown
- **Color-coded terminal UI** — ANSI styling with connection status indicators at startup

---

## 🗂️ Project Structure

```
cinema_backend.py          # Single-file application (Jupyter Notebook compatible)
│
├── Style                  # ANSI color/style constants (class)
│
├── Block 1 — MySQL connection
│   ├── config             # Connection parameters
│   └── test_mysql_connection()
│
├── Block 2 — Search functions (MySQL)
│   ├── Helper functions
│   │   ├── get_all_genres()
│   │   ├── get_min_max_years()
│   │   ├── get_year_range_input()     # with inner _ask_year()
│   │   ├── get_actors_by_keyword()
│   │   ├── get_search_inputs()        # unified input collector
│   │   ├── build_search_summary()
│   │   ├── paginate_results()
│   │   ├── paginate_actors()
│   │   ├── build_sql_filters()        # universal WHERE builder
│   │   ├── get_sort_direction()
│   │   └── select_film_from_list()
│   │
│   └── Core search functions
│       ├── search_film_by_keyword()
│       ├── search_film_by_genre_and_years()
│       ├── search_film_by_actor_and_year()
│       ├── get_film_description()
│       └── display_results()
│
├── Block 3 — MongoDB connection
│   ├── MONGO_CONFIG / COLLECTION_NAME
│   ├── get_mongo_client()
│   └── test_mongo_connection()
│
├── Block 4 — MongoDB logging & analytics
│   ├── log_query()
│   ├── get_top_queries()
│   ├── get_recent_queries()
│   └── get_search_type_popularity()
│
├── Block 5 — Statistics display (Tabulate)
│   ├── _format_params()
│   ├── _TYPE_LABELS
│   ├── _show_top_queries()
│   ├── _show_recent_queries()
│   ├── _show_type_popularity()
│   └── display_stats()
│
└── Block 6 — Main menu
    └── main_menu()
```

---

## 🛠️ Technologies

| Component    | Technology          |
|--------------|---------------------|
| Language     | Python 3.x          |
| Movie data   | MySQL (Sakila DB)   |
| Query logs   | MongoDB             |
| MySQL driver | `pymysql`           |
| MongoDB driver | `pymongo`         |
| Table output | `tabulate`          |
| Notebook UI  | `IPython.display`   |

---

## ⚙️ Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/film-search-app.git
   cd film-search-app
   ```

2. **Install dependencies:**
   ```bash
   pip install pymysql pymongo tabulate ipython
   ```

3. **Configure database credentials** in `cinema_backend.py`:

   ```python
   # MySQL — Block 1
   config = {
       "host": "your-mysql-host",
       "user": "your-user",
       "password": "your-password",
       "database": "sakila",
       ...
   }

   # MongoDB — Block 3
   MONGO_CONFIG = {
       "host": "your-mongo-host",
       "username": "your-user",
       "password": "your-password",
       "authSource": "your-auth-db",
   }
   MONGO_DB_NAME = "your_db"
   COLLECTION_NAME = "your_collection_name"
   ```

---

## ▶️ Running the App

**In a Jupyter Notebook** (recommended — uses `IPython.display` for the title header and `clear_output` for screen clearing):

Open `cinema_backend.py` or copy it into a notebook cell and run the last cell:
```python
main_menu()
```

**As a plain Python script:**
```bash
python cinema_backend.py
```
> Note: `clear_output()` has no effect outside Jupyter, but the app will still run correctly.

---

## 🗄️ MongoDB Log Format

Every search is recorded in the following structure:

```json
{
  "timestamp": "2025-05-01T15:34:00+00:00",
  "search_type": "keyword",
  "params": {
    "keyword": "matrix"
  },
  "results_count": 3,
  "total_viewed": 3
}
```

Supported `search_type` values: `keyword`, `genres-years`, `actor`, `actor-years`.

---

## 📊 Statistics

Accessible from the main menu → option **4**. Displays three reports:

- **Top 5 Most Frequent Queries** — grouped by type + parameters, with average results found and viewed
- **Top 5 Most Recent Queries** — last unique searches with timestamps
- **Search Type Popularity** — total usage count per search method

---

## 🧱 Architecture Decisions

**Why functions, not classes for search logic?**
Each search operation is a standalone flow (collect input → query DB → paginate → log). Using plain functions keeps each step visible and easy to test independently. A class would add structure without benefit here.

**Why a universal `build_sql_filters()` builder?**
All three search types share the same filter parameters (genre, year_from, year_to, actor_id, keyword). Centralizing WHERE-clause generation eliminates duplication and makes adding new filters a single-point change.

**Why log empty results too?**
Analytics should reflect real user behavior — including failed searches. Empty-result logs help identify gaps in the database or unclear UI.

---

## 📸 Demo

### Главное меню
![Main Menu](Screenshots/Menu.png)

### Результаты поиска
![Search Results 1](Screenshots/search_results_1.png)
![Search Results 2](Screenshots/search_results_2.png)
![Search Results 3](Screenshots/search_results_3.png)

### Статистика запросов
![Statistics](Screenshots/statistics.png)

---

## 📋 Requirements

- Python 3.8+
- Access to a MySQL server with the [Sakila sample database](https://dev.mysql.com/doc/sakila/en/)
- Access to a MongoDB instance

---

## 👩‍💻 Author

**Anna Konyuchenko**  
Final project — IT Career Hub, Group 051225
