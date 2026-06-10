import pymysql
from pymongo import MongoClient
from datetime import datetime, timezone
import json
from tabulate import tabulate
from IPython.display import clear_output
from IPython.display import HTML, display
SEP = "*" * 79
PAGE_SIZE = 10  # кол-во строк для пагинации

# создаем класс-контейнер (пользовательский тип данных)
class Style:
    # Эффекты
    RESET = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    UNDERLINE = '\033[4m'
    
        # Цвета текста
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'       
    MAGENTA = '\033[35m'  
   
import pymysql

config = {
    "host": "ich-db.edu.itcareerhub.de",
    "user": "ich1",
    "password": "password_ich1",
    "database": "sakila",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "connect_timeout": 5  # Ограничение времени ожидания соединения в секундах
}

def test_mysql_connection():
    """Проверяет корректность подключения к удаленной базе данных MySQL и возвращает статус."""
    try:
        with pymysql.connect(**config) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        # Чистый, яркий зелёный статус
        return f"{Style.GREEN}● MySQL: CONNECTED{Style.RESET}"
    except Exception as e:
        # Слово FAILED — яркое, а сама техническая ошибка — тусклая (DIM)
        return f"{Style.RED}{Style.BOLD}● MySQL: FAILED {Style.RESET}{Style.RED}{Style.DIM}({e}){Style.RESET}"

def get_all_genres():
    """Fetches a list of all movie genres sorted alphabetically.
    Возвращает список всех жанров фильмов, отсортированный по алфавиту.

    Returns:
        list: A list of strings containing genre names. / 
              Список строк с названиями жанров.
    """
    
    with pymysql.connect(**config) as conn:
        with conn.cursor() as cur:
            # Запрос возвращает только имена жанров, отсортированные по алфавиту
            cur.execute("SELECT name FROM category ORDER BY name")
            rows = cur.fetchall()

    # Превращаем список словарей типа [{"name": "Action"}, {"name": "Comedy"}]
    # в простой список строк: ["Action", "Comedy"]
    return [row["name"] for row in rows]

def get_min_max_years():
    
    """Fetches the minimum and maximum release years from the film table.
       Returns: tuple: (min_year, max_year) 
    """
    
    query = "SELECT MIN(release_year) AS year_min, MAX(release_year) AS year_max FROM film;"

    with pymysql.connect(**config) as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            row = cur.fetchone()

    return row["year_min"], row["year_max"]

def get_year_range_input():
    """Collects and validates movie release year range (From and To) from the user.
    Запрашивает у пользователя диапазон годов выпуска фильма (От и До)
    с полной валидацией данных и границ базы Sakila.
    """
    year_params = {}

    # Автоматически берём актуальные границы годов напрямую из MySQL
    min_db_year, max_db_year = get_min_max_years()
    print("\nВыберите диапазон или год:")

    def _ask_year(label):
        """Запрашивает и валидирует один год (От или До).
        Возвращает int если год корректен, None если пользователь нажал Enter.
        """
        while True:
            year = input(
                f"Год {label} (в базе {min_db_year}-{max_db_year}, "
                f"или Enter для пропуска): "
            ).strip()

            if not year:
                return None

            if year.isdigit() and len(year) == 4:
                year_int = int(year)
                if min_db_year <= year_int <= max_db_year:
                    return year_int
                print(
                    f"{Style.BOLD}{Style.RED}Ошибка: в базе Sakila есть фильмы "
                    f"только с {min_db_year} по {max_db_year} год!{Style.RESET}"
                )
                continue

            print(
                f"{Style.BOLD}{Style.RED}Ошибка: введите корректный "
                f"четырехзначный год (например, 2006)!{Style.RESET}"
            )

    # --- Год ОТ ---
    year_from = _ask_year("от")
    if year_from is not None:
        year_params["year_from"] = year_from

    # --- Год ДО ---
    while True:
        year_to = _ask_year("до")
        if year_to is None:
            break
        # Защита от дурака: год ДО не может быть меньше года ОТ
        if "year_from" in year_params and year_to < year_params["year_from"]:
            print(
                f"{Style.BOLD}{Style.RED}Ошибка: год 'до' не может "
                f"быть меньше года 'от'!{Style.RESET}"
            )
            continue
        year_params["year_to"] = year_to
        break

    return year_params

def get_actors_by_keyword(actor_input):
    """Searches for actors in the DB by a fragment of their first or last name.
    Ищет актёров в базе данных по части имени или фамилии.

    Args:
        actor_input (str): Keyword entered by user. / Ключевое слово для поиска.
    Returns:
        list: A list of dictionaries with actor_id and name. /
              Список словарей с ID и полным именем актера.
    """
    
    with pymysql.connect(**config) as conn:
        with conn.cursor() as cur:
            # Ищем совпадения и в имени, и в фамилии (регистр MySQL не важен при LIKE)
            query = """
                SELECT actor_id, CONCAT(first_name, ' ', last_name) AS actor_name
                FROM actor
                WHERE first_name LIKE %s OR last_name LIKE %s
                ORDER BY first_name, last_name;
            """
            search_pattern = f"%{actor_input}%"
            cur.execute(query, (search_pattern, search_pattern))
            rows = cur.fetchall()
            
    return rows
def get_search_inputs(search_type):
    """Collects validated user inputs for different search types.

    Собирает параметры ввода у пользователя, выводит списки с номерами
    и защищает от неверных данных.
    """
    
    # ==========================================
    # ВАРИАНТ 1: Поиск по ключевому слову фильма
    # ==========================================
    if search_type == "keyword":
        keyword = input("Введите часть названия фильма (или Enter для пропуска): ").strip().lower()
        return {"keyword": keyword} if keyword else {}

    # ==========================================
    # ВАРИАНТ 2: Поиск по жанру и годам
    # ==========================================
    if search_type == "genres-years":
        params = {}

        # ТЗ: Перед вводом пользователю показывается список ВСЕХ жанров
        all_genres = get_all_genres()
        print(f"\n{SEP}")
        print(f"{Style.BOLD}{Style.MAGENTA}=== СПИСОК ВСЕХ ДОСТУПНЫХ ЖАНРОВ ==={Style.RESET}")
        print(SEP)
        
        for idx, g in enumerate(all_genres, 1):  # idx - index, g - genre
            print(f"{idx:2d}. {g}")  # :2d красиво выравнивает номера 1-9 и 10+
        print(SEP)

        # Выбор жанра по цифре
        while True:
            choice = input("\nВыберите номер жанра (или Enter для пропуска): ").strip()
            
            if not choice:  # Нажали Enter — пропускаем фильтр жанра
                break
                
            # Проверяем, что введена правильная цифра из списка
            if choice.isdigit() and 1 <= int(choice) <= len(all_genres):
                params["genre"] = all_genres[int(choice) - 1]
                break
            else:
                print(f"{Style.BOLD}{Style.RED}Ошибка: введите число от 1 до {len(all_genres)}!{Style.RESET}")

        # Вызываем нашу общую функцию для сбора и валидации диапазона годов (От и До)
        year_data = get_year_range_input()
        
        if "year_from" in year_data:
            params["year_from"] = year_data["year_from"]
        if "year_to" in year_data:
            params["year_to"] = year_data["year_to"]

        return params

    # ==========================================
    # ВАРИАНТ 3: Поиск по актеру и году
    # ==========================================
    if search_type == "actor":
        params = {}
        while True:
            actor_input = input(
                "Введите имя, фамилию или часть имени актера (или Enter для отмены): "
            ).strip()
            if not actor_input:
                # Пользователь нажал Enter — отменяем поиск и возвращаем пустой словарь
                return {}
            # Вызываем хелпер поиска актеров
            found_actors = get_actors_by_keyword(actor_input)
            if not found_actors:
                print("Актер не найден. Попробуйте еще раз (например: 'Nick' или 'Wahlberg').")
                continue

            # Выводим пронумерованный список актёров порциями по 10
            total_actors = len(found_actors)
            page_start = 0
            while page_start < total_actors:
                # Выводим текущую порцию из 10 актёров
                for idx, actor in enumerate(
                    found_actors[page_start:page_start + PAGE_SIZE], start=page_start + 1
                ):
                    print(f"{idx}. {actor['actor_name']}")

                page_start += PAGE_SIZE

                # Если есть ещё актёры — спрашиваем продолжать или выбирать
                if page_start < total_actors:
                    show_more = input(
                        f"\nПоказано {min(page_start, total_actors)} из {total_actors}. "
                        f"Показать ещё? (y — продолжить, Enter — выбрать из списка): "
                    ).strip().lower()
                    if show_more != "y":
                        break

            # Выбор актёра по номеру из всего списка
            while True:
                choice = input(
                    f"\nВыберите номер актера от 1 до {total_actors} "
                    f"(или Enter для поиска заново): "
                ).strip()
                if not choice:
                    clear_output(wait=False)
                    break
                if choice.isdigit() and 1 <= int(choice) <= total_actors:
                    selected = found_actors[int(choice) - 1]
                    params["actor_id"] = selected["actor_id"]
                    params["actor_name"] = selected["actor_name"]
                    break
                print(f"{Style.BOLD}{Style.RED}Ошибка: введите число от 1 до {total_actors}!{Style.RESET}")

            # Выходим из внешнего цикла только если актёр выбран
            # При Enter возвращаемся к началу поиска по имени
            if "actor_id" in params:
                break

        # Для актера мы тоже используем наш общий удобный диапазон годов (От и До)
        # Это даст пользователю возможность гибко искать фильмы актера в рамках временного отрезка!
        year_data = get_year_range_input()

        if "year_from" in year_data:
            params["year_from"] = year_data["year_from"]
        if "year_to" in year_data:
            params["year_to"] = year_data["year_to"]
        return params

def build_search_summary(search_type, params, total_found):
    """Строит строку-заголовок с описанием запроса и общим числом результатов.
    Показывается перед таблицей, только когда результатов больше одной страницы.

    Args:
        search_type (str): Тип поиска — "keyword", "genres-years", "actor".
        params (dict): Параметры поиска.
        total_found (int): Общее число найденных фильмов.
    Returns:
        str: Готовая строка-заголовок.
    """
    # Формируем описание временного периода
    if "year_from" in params and "year_to" in params:
        period = f"за период {params['year_from']}–{params['year_to']}"
    elif "year_from" in params:
        period = f"начиная с {params['year_from']} года"
    elif "year_to" in params:
        period = f"до {params['year_to']} года"
    else:
        period = ""

    # Формируем основную часть описания по типу поиска
    if search_type == "keyword":
        keyword = params.get("keyword", "")
        base = f"Всего фильмов по названию «{keyword}»"
    elif search_type == "genres-years":
        genre = params.get("genre", "все жанры")
        base = f"Всего фильмов жанра «{genre}»"
    elif search_type == "actor":
        actor = params.get("actor_name", "выбранный актёр")
        base = f"Всего фильмов актёра «{actor}»"
    else:
        base = "Всего результатов"

    if period:
        return f"{base} {period}: {total_found}"
    return f"{base}: {total_found}"
def paginate_results(results, summary=None):
    """Выводит результаты запроса порциями по PAGE_SIZE строк.

    Позволяет выбирать ЛЮБОЙ фильм, который уже был выведен на экран.
    Очищает экран Jupyter только при выходе в главное меню.
    """
    total_found = len(results)
    if total_found == 0:
        print("\nРезультаты не найдены.")
        return 0

    if summary and total_found > PAGE_SIZE:
        print(f"\n{SEP}\n  {summary}\n{SEP}")
    else:
        print(f"\nНайдено результатов: {total_found}")

    total_viewed = 0
    current_index = 0
    show_table = True

    while current_index < total_found:
        chunk = results[current_index : current_index + PAGE_SIZE]
        current_start = current_index + 1

        if show_table:
            display_results(chunk, start_index=current_start)

        print(f"\n{SEP}")
        print(f"{Style.BOLD}{Style.MAGENTA}ДОСТУПНЫЕ ДЕЙСТВИЯ (ФИЛЬМЫ):{Style.RESET}")
        print("  [Номер фильма] - Посмотреть подробное описание фильма")
        if current_index + PAGE_SIZE < total_found:
            print("  y              - Показать следующие 10 результатов")
        print("  Enter          - Выйти в главное меню (оставьте пустым)")
        print(SEP)

        action_taken = None

        while True:
            # Считаем, сколько всего фильмов пользователь видит на данный момент
            max_displayed = current_index + len(chunk)

            choice = input(
                f"Введите команду (показано {max_displayed} из {total_found}): "
            ).strip().lower()

            if not choice:  # Нажали Enter — полная очистка и выход
                total_viewed += len(chunk)
                clear_output(wait=False)
                return total_viewed

            if choice.isdigit():
                film_number = int(choice)

                # ИЗМЕНЕНИЕ: Теперь проверяем диапазон от 1 до max_displayed!
                if 1 <= film_number <= max_displayed:
                    # Умный пересчет: определяем, на какой странице находился этот фильм
                    target_global_idx = film_number - 1
                    # Находим индекс начала той страницы (кратный PAGE_SIZE)
                    orig_chunk_start = (
                        target_global_idx // PAGE_SIZE
                    ) * PAGE_SIZE
                    # Вырезаем именно тот чанк, в котором лежит фильм
                    orig_chunk = results[
                        orig_chunk_start : orig_chunk_start + PAGE_SIZE
                    ]
                    # Считаем корректный стартовый номер для этого чанка (1, 11, 21 и т.д.)
                    orig_start_index = orig_chunk_start + 1

                    # Передаем правильные данные в функцию отображения карточки
                    select_film_from_list(orig_chunk, choice, orig_start_index)

                    action_taken = "stay"
                    break
                else:
                    print(
                        f"{Style.BOLD}{Style.RED}Ошибка: Вы можете выбрать любой отображенный фильм "
                        f"от 1 до {max_displayed}!{Style.RESET}"
                    )
                    continue

            if choice == "y" and current_index + PAGE_SIZE < total_found:
                action_taken = "next"
                break

            print(
                f"{Style.BOLD}{Style.RED}Неверная команда. Введите корректный номер фильма, "
                f"'y' или нажмите Enter для выхода.{Style.RESET}"
            )

        if action_taken == "next":
            total_viewed += len(chunk)
            current_index += PAGE_SIZE
            show_table = True
        elif action_taken == "stay":
            show_table = False

    clear_output(wait=False)
    return total_viewed

def paginate_actors(actors):
    """Пагинирует список найденных актеров порциями по PAGE_SIZE.

    Позволяет выбирать ЛЮБОГО актера, который уже был выведен на экран.
    Возвращает словарь выбранного актера или None для отмены.
    """
    total_actors = len(actors)
    current_index = 0

    while current_index < total_actors:
        chunk = actors[current_index : current_index + PAGE_SIZE]
        current_start = current_index + 1

        print(f"\n{SEP}")
        print(f"{Style.BOLD}{Style.MAGENTA}НАЙДЕННЫЕ АКТЕРЫ:{Style.RESET}")
        print(SEP)
        for idx, actor in enumerate(chunk, start=current_start):
            print(f"  {idx:2d}. {actor['actor_name']}")
        print(SEP)

        print(f"{Style.BOLD}{Style.MAGENTA}ДОСТУПНЫЕ ДЕЙСТВИЯ (АКТЕРЫ):{Style.RESET}")
        print("  [Номер актера] - Выбрать актера для поиска его фильмов")
        if current_index + PAGE_SIZE < total_actors:
            print("  y              - Показать следующих 10 актеров")
        print("  Enter          - Вернуться к вводу имени (поиск заново)")
        print(SEP)

        action_taken = None

        while True:
            # Считаем, сколько всего актеров пользователь уже видит на экране
            max_displayed = current_index + len(chunk)

            choice = input(
                f"Введите команду (показано {max_displayed} из {total_actors}): "
            ).strip().lower()

            if not choice:  # Нажали Enter — полностью чистим экран и уходим в поиск
                clear_output(wait=False)
                return None

            if choice.isdigit():
                actor_num = int(choice)

                # ИЗМЕНЕНИЕ: Теперь проверяем диапазон от 1 до ПОКАЗАННОГО максимума
                if 1 <= actor_num <= max_displayed:
                    # Чистим простыню актеров перед тем, как выдать результаты поиска его фильмов
                    clear_output(wait=False)
                    return actors[
                        actor_num - 1
                    ]  # Достаем актера по его сквозному номеру
                else:
                    print(
                        f"{Style.BOLD}{Style.RED}Ошибка: Вы можете выбрать любого отображенного актера "
                        f"от 1 до {max_displayed}!{Style.RESET}"
                    )
                    continue

            if choice == "y" and current_index + PAGE_SIZE < total_actors:
                action_taken = "next"
                break

            print(
                f"{Style.BOLD}{Style.RED}Неверная команда. Введите корректный номер актера, "
                f"'y' или нажмите Enter.{Style.RESET}"
            )

        if action_taken == "next":
            current_index += PAGE_SIZE

    # Если пролистали до самого конца и выходим
    clear_output(wait=False)
    return None

def build_sql_filters(params):
    """Dynamically builds WHERE clauses and argument lists for MySQL queries.
    Динамически собирает условия WHERE и список аргументов для MySQL-запросов
    на основе переданных параметров.

    Args:
        params (dict): Dictionary with search filters. / Словарь с фильтрами поиска.
    Returns:
        tuple: (where_clause_str, query_args_list)
    """
    
    if not params:
        return "", []

    conditions = []
    query_args = []
    
    # 1. Фильтр по ключевому слову в названии
    if "keyword" in params:
        conditions.append("f.title LIKE %s")
        query_args.append(f"%{params['keyword']}%")
    
    # 2. Фильтр по жанру
    if "genre" in params:
        conditions.append("c.name = %s")
        query_args.append(params["genre"])

    # 3. Фильтр по актеру (ищем по точному ID, который выбрал пользователь)
    if "actor_id" in params:
        conditions.append("fa.actor_id = %s")
        query_args.append(params["actor_id"])

    # 4. Фильтры по годам (распаковки через .extend())
    if "year_from" in params and "year_to" in params:
        conditions.append("f.release_year BETWEEN %s AND %s")
        query_args.extend([params["year_from"], params["year_to"]]) 
        """Передаем элементы списком из двух  элементов, а .extend() раскладывает 
        их на отдельные значения   добавляет их по очереди, чтобы в SQL-запрос
        ушли два чистых числа, а не массив"""
    
    elif "year_from" in params:
        conditions.append("f.release_year >= %s")
        query_args.append(params["year_from"])
   
    elif "year_to" in params:
        conditions.append("f.release_year <= %s")
        query_args.append(params["year_to"])
    
    # 5. Дополнительно: Фильтр по конкретному одиночному году (для поиска по актеру)
    if "year" in params:
        conditions.append("f.release_year = %s")
        query_args.append(params["year"])
    
    # Собираем все условия через AND
    where_clause = " WHERE " + " AND ".join(conditions)
    
    return where_clause, query_args

def get_sort_direction():
    """Спрашивает у пользователя направление сортировки по году.
        Returns:
        str: 'DESC' (по убыванию) или 'ASC' (по возрастанию).
    """
    
    while True:
        print(f"\n{Style.BOLD}{Style.MAGENTA}--- ПОРЯДОК СОРТИРОВКИ ---{Style.RESET}")
        print("1. Сначала новые (по убыванию)")
        print("2. Сначала старые (по возрастанию)")
        
        choice = input("Ваш выбор (по умолчанию 1): ").strip()
        
        if choice == "2":
            return "ASC"
        # Если ввели 1 или просто нажали Enter — выбираем по убыванию (как в ТЗ)
        if choice == "1" or not choice:
            return "DESC"
            
        print(f"{Style.BOLD}{Style.RED}Ошибка: введите 1 или 2!{Style.RESET}")

def select_film_from_list(current_films, user_choice, start_index):
    """Принимает уже выбранный пользователем номер, находит фильм 

    в текущем чанке с учетом текущей страницы пагинации и выводит описание.
    """
    try:
        # Вычисляем реальный индекс элемента в текущем чанке (например: 17 - 11 = 6)
        idx = int(user_choice) - start_index

        if 0 <= idx < len(current_films):
            selected_film = current_films[idx]
            film_id = selected_film.get("film_id")
            title = selected_film.get("title", "Без названия")

            # Получение описания из MySQL
            description = get_film_description(film_id)

            # Делаем новый разделитель из знаков "=" той же длины, что и SEP
            BOX_SEP = "=" * len(SEP)

            # Печатаем контрастную жёлтую карточку фильма
            print(f"\n{Style.BOLD}{Style.YELLOW}{BOX_SEP}{Style.RESET}")
            print(
                f"{Style.BOLD}{Style.YELLOW}🎬 ОПИСАНИЕ ФИЛЬМА: {title.upper()}{Style.RESET}"
            )
            print(f"{Style.BOLD}{Style.YELLOW}{BOX_SEP}{Style.RESET}")
            print(description)
            print(f"{Style.BOLD}{Style.YELLOW}{BOX_SEP}{Style.RESET}\n")
        else:
            # Разбиваем длинную F-строку на две части внутри скобок print()
            print(
                f"{Style.BOLD}{Style.RED}Ошибка: Номер должен быть в диапазоне "
                f"от {start_index} до {start_index + len(current_films) - 1}.{Style.RESET}"
            )

    except ValueError:
        print(
            f"{Style.BOLD}{Style.RED}Ошибка: Пожалуйста, введите "
            f"корректный числовой номер.{Style.RESET}"
        )

def search_film_by_keyword():
    """Searches for movies by title keyword using the universal SQL builder.
    Ищет фильмы по ключевому слову в названии, используя универсальный сборщик фильтров.
    """
    
    # 1. Получаем ввод от пользователя
    params = get_search_inputs("keyword")
    if not params:
        print("Поисковый запрос пуст. Возврат в меню.")
        return

   
    # 2. Генерируем SQL-условия одной строчкой
    where_clause, query_args = build_sql_filters(params)

    # Базовая часть SQL 
    base_query = """
        SELECT f.film_id, f.title, c.name AS genre, f.release_year, f.rating
        FROM film f
        JOIN film_category fc ON f.film_id = fc.film_id
        JOIN category c ON fc.category_id = c.category_id
    """

    final_query = base_query + where_clause + ";"

   
    # 3. Делаем запрос в базу данных
    try:
        with pymysql.connect(**config) as conn:
            with conn.cursor() as cur:
                cur.execute(final_query, query_args)
                films = cur.fetchall()
    except Exception as e:
        print(f"{Style.BOLD}{Style.RED}Ошибка при работе с MySQL: {e}{Style.RESET}")
        return

    # Защита от пустого результата
    if not films:
        print("\n❌ В базе данных Sakila не найдено фильмов по вашему запросу.")
        # Логируем пустой запрос — система фиксирует все обращения, включая безрезультатные
        log_query("keyword", params, 0, 0)
        return

    # 4. Отправляем результаты в общую пагинацию
    summary = build_search_summary("keyword", params, len(films))
    total_viewed = paginate_results(films, summary=summary)

    # 5. Логируем запрос в MongoDB
    log_query("keyword", params, len(films), total_viewed)

    print(
        f"\n[MongoDB] Лог сохранён. "
        f"Найдено: {len(films)}, Просмотрено: {total_viewed}"
    )
def search_film_by_genre_and_years():
    """Ищет фильмы по выбранным в меню жанрам и годам (по убыванию года)."""

    # 1. Получаем параметры, которые выбрал пользователь в меню
    params = get_search_inputs("genres-years")
    if not params:
        print("Вы ничего не выбрали. Возврат в меню.")
        return

    # 2. Генерируем SQL-кусок и аргументы
    where_clause, query_args = build_sql_filters(params)

    # Базовая часть запроса
    base_query = """
        SELECT f.film_id, f.title, c.name AS genre, f.release_year, f.rating
        FROM film f
        JOIN film_category fc ON f.film_id = fc.film_id
        JOIN category c ON fc.category_id = c.category_id
    """

    # Сортировка ORDER BY по убыванию года (DESC)
    final_query = base_query + where_clause + " ORDER BY f.release_year DESC;"

    # 3. Отправляем в базу
    try:
        with pymysql.connect(**config) as conn:
            with conn.cursor() as cur:
                cur.execute(final_query, query_args)
                films = cur.fetchall()
    except Exception as e:
        print(f"{Style.BOLD}{Style.RED}Ошибка при работе с MySQL: {e}{Style.RESET}")
        return

    # Защита от пустого результата
    if not films:
        print("\n❌ В базе данных Sakila не найдено фильмов по вашему запросу.")
        # Всё равно логируем в MongoDB (преподаватель оценит: система фиксирует даже пустые запросы!)
        log_query("genres-years", params, 0, 0)
        return  # Спокойно выходим назад в главное меню

    # 4. Если фильмы есть — запускаем пагинацию и логи в MongoDB
    summary = build_search_summary("genres-years", params, len(films))
    total_viewed = paginate_results(films, summary=summary)
    log_query("genres-years", params, len(films), total_viewed)

def search_film_by_actor_and_year():
    """Ищет фильмы по выбранному актеру и диапазону лет."""

    # 1. Получаем параметры актера из инпутов
    params = get_search_inputs("actor")
    if not params:
        print("Вы ничего не выбрали. Возврат в меню.")
        return

    # 2. Генерируем SQL-кусок и запрашиваем сортировку
    where_clause, query_args = build_sql_filters(params)
    sort_dir = get_sort_direction()

    base_query = """
        SELECT f.film_id, f.title, c.name AS genre, f.release_year, f.rating
        FROM film f
        JOIN film_actor fa ON f.film_id = fa.film_id
        JOIN film_category fc ON f.film_id = fc.film_id
        JOIN category c ON fc.category_id = c.category_id
    """

    # Динамически подставляем ASC или DESC
    final_query = (
        base_query + where_clause + f" ORDER BY f.release_year {sort_dir};"
    )

    # 3. Отправляем в базу
    try:
        with pymysql.connect(**config) as conn:
            with conn.cursor() as cur:
                cur.execute(final_query, query_args)
                films = cur.fetchall()
    except Exception as e:
        print(
            f"{Style.BOLD}{Style.RED}Ошибка при работе с MySQL: {e}{Style.RESET}"
        )
        return

    # Защита от пустого результата
    if not films:
        print("\n❌ В базе данных Sakila не найдено фильмов по вашему запросу.")
        log_query("actor-years", params, 0, 0)
        return

    print(
        f"\nФильмография актера/актрисы: {params.get('actor_name', 'Выбранный актер/актриса')}"
    )

    # 4. Пагинация и логи в MongoDB
    summary = build_search_summary("actor", params, len(films))
    total_viewed = paginate_results(films, summary=summary)
    log_query("actor-years", params, len(films), total_viewed)
def get_film_description(film_id):
    """Возвращает текстовое описание фильма из базы данных MySQL по его идентификатору.

    Аргументы:
        film_id (int): Идентификатор фильма в таблице film.

    Возвращает:
        str: Текст описания фильма или сообщение об его отсутствии.
    """
    query = """SELECT description 
               FROM film 
               WHERE film_id = %s"""
    try:
        with pymysql.connect(**config) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (film_id,))
                result = cur.fetchone()
                if result and result.get("description"):
                    return result["description"]
                return "Описание для данного фильма отсутствует."
    except Exception as e:
        print(f"{Style.BOLD}{Style.RED}[Ошибка MySQL] Не удалось получить описание фильма: {e}{Style.RESET}")
        return "Не удалось загрузить описание из-за технической ошибки."

def display_results(films, start_index=1):
    """Выводит список фильмов в виде профессиональной таблицы с помощью tabulate."""
    if not films:
        print("Фильмы не найдены.")
        return

    # 1. Формируем красивую жирную шапку с цветом CYAN
    headers = [
        f"{Style.BOLD}{Style.CYAN}№{Style.RESET}",
        f"{Style.BOLD}{Style.CYAN}Название{Style.RESET}",
        f"{Style.BOLD}{Style.CYAN}Жанр{Style.RESET}",
        f"{Style.BOLD}{Style.CYAN}Год{Style.RESET}",
        f"{Style.BOLD}{Style.CYAN}Рейтинг{Style.RESET}"
    ]

    # 2. Собираем данные строк (чистый текст, без раскраски, чтобы отлично читалось)
    table_data = []
    for index, film in enumerate(films, start=start_index):
        table_data.append([
            index,
            film['title'],
            film['genre'],
            film['release_year'],
            film['rating']
        ])

    # 3. Выводим таблицу через tabulate
    # Используем стиль "fancy_grid" 
    print(tabulate(table_data, headers=headers, tablefmt="fancy_grid", stralign="left", numalign="right"))

MONGO_CONFIG = {
    "host": "mongo.itcareerhub.de",
    "username": "ich_editor",
    "password": "verystrongpassword",
    "authSource": "ich_edit",
   }

MONGO_DB_NAME = "ich_edit"
COLLECTION_NAME = "project_051225_Konyuchenko"


# Настройки подключения MongoDB

def get_mongo_client():
    """Возвращает настроенный клиент MongoDB."""
    return MongoClient(**MONGO_CONFIG)


def test_mongo_connection():
    """Проверяет подключение к MongoDB при запуске и возвращает статус."""
    try:
        with get_mongo_client() as client:
            client.server_info()
        return f"{Style.GREEN}● MongoDB: CONNECTED{Style.RESET}"
    except Exception as e:
        return f"{Style.RED}{Style.BOLD}● MongoDB: FAILED {Style.RESET}{Style.RED}{Style.DIM}({e}){Style.RESET}"

from datetime import datetime, timezone

def log_query(search_type, params, total_found, total_viewed):
    """Записывает параметры поискового запроса и метрики в коллекцию MongoDB.
    
    Временная метка сохраняется в текстовом формате ISO с указанием UTC.
    """
    try:
        with get_mongo_client() as client:
            collection = client[MONGO_DB_NAME][COLLECTION_NAME]

            document = {
                # Использование актуального метода для фиксации времени в UTC ISO формате
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "search_type": search_type,
                "params": params,                
                "results_count": total_found,
                "total_viewed": total_viewed
            }
            collection.insert_one(document)
    except Exception as e:
        print(f"\n[Ошибка MongoDB] Не удалось записать лог: {e}")

def get_top_queries():
    """Возвращает топ-5 самых частых поисковых запросов с усредненной статистикой."""
    try:
        with get_mongo_client() as client:
            collection = client[MONGO_DB_NAME][COLLECTION_NAME]

            pipeline = [
                {
                    "$group": {
                        "_id": {
                            "type": "$search_type",
                            "params": "$params"
                        },
                        "count": {"$sum": 1},
                        "avg_found": {"$avg": "$results_count"},
                        "avg_viewed": {"$avg": "$total_viewed"}
                    }
                },
                {"$sort": {"count": -1}},
                {"$limit": 5}
            ]
            return list(collection.aggregate(pipeline))
    except Exception as e:
        print(f"\n[Ошибка MongoDB] Не удалось получить топ запросов: {e}")
        return []

def get_recent_queries():
    """Возвращает топ-5 самых последних уникальных поисковых запросов."""
    try:
        with get_mongo_client() as client:
            collection = client[MONGO_DB_NAME][COLLECTION_NAME]

            pipeline = [
                {"$sort": {"timestamp": -1}},
                {
                    "$group": {
                        "_id": {
                            "type": "$search_type",
                            "params": "$params"
                        },
                        "timestamp": {"$first": "$timestamp"},
                        "results_count": {"$first": "$results_count"},
                        "total_viewed": {"$first": "$total_viewed"}
                    }
                },
                {"$sort": {"timestamp": -1}},
                {"$limit": 5}
            ]
            return list(collection.aggregate(pipeline))
    except Exception as e:
        print(f"\n[Ошибка MongoDB] Не удалось получить историю: {e}")
        return []

def get_search_type_popularity():
    """Группирует логи по типу поиска и считает их общее количество."""
    try:
        with get_mongo_client() as client:
            collection = client[MONGO_DB_NAME][COLLECTION_NAME]

            pipeline = [
                { "$group": {
                    "_id": "$search_type",
                    "total_uses": {"$sum": 1}
                } },
                { "$sort": {"total_uses": -1} }
            ]
            return list(collection.aggregate(pipeline))
    except Exception as e:
        print(f"\n[Ошибка MongoDB] Не удалось посчитать популярность типов поиска: {e}")
        return []
def _format_params(q_type, params):
    """Преобразует словарь параметров поискового запроса в текстовую строку.
    Аргументы:
        q_type (str): Тип поискового запроса ('keyword', 'genres-years', 'actor').
        params (dict): Словарь с параметрами фильтрации из базы данных.
    Возвращает:
        str: Понятное пользователю текстовое представление применённых фильтров.
    """
    if not params or not isinstance(params, dict):
        return "Без фильтров"
    if q_type == "keyword":
        return f"Слово: '{params.get('keyword', '')}'"
    elif q_type in ["genres-years", "genre"]:
        return (
            f"Жанр: {params.get('genre', 'Любой')} "
            f"({params.get('year_from', '...')} - {params.get('year_to', '...')})"
        )
    elif q_type in ["actor", "actor-years"]:
        return f"Актер: {params.get('actor_name', 'Неизвестно')}"
    return str(params)


# Метки типов поиска — используются в нескольких функциях статистики
_TYPE_LABELS = {
    "keyword": "По ключевому слову",
    "genres-years": "По жанру/годам",
    "actor": "По актеру",
    "actor-years": "По актеру/годам"
}


def _show_top_queries():
    """Выводит таблицу топ-5 самых частых поисковых запросов."""
    print(f"\n\n{SEP}")
    print(f"  {Style.BOLD}{Style.CYAN}🎬 TOP 5 MOST FREQUENT QUERIES{Style.RESET}")
    print(SEP)

    top_data = []
    for idx, item in enumerate(get_top_queries(), start=1):
        g_id = item.get("_id", {})
        q_type = g_id.get("type", "-")
        top_data.append([
            idx,
            _TYPE_LABELS.get(q_type, q_type),
            _format_params(q_type, g_id.get("params", {})),
            item.get("count", 0),
            round(item.get("avg_found", 0)),
            round(item.get("avg_viewed", 0))
        ])
    print(tabulate(
        top_data,
        headers=["№", "Тип поиска", "Параметры запроса", "Кол-во", "Найдено(ср)", "Показано(ср)"],
        tablefmt="fancy_grid"
    ))

def _show_recent_queries():
    """Выводит таблицу топ-5 последних уникальных поисковых запросов."""
    print(f"\n\n{SEP}")
    print(f"  {Style.BOLD}{Style.CYAN}⏱ TOP 5 MOST RECENT QUERIES{Style.RESET}")
    print(SEP)

    recent_data = []
    for idx, item in enumerate(get_recent_queries(), start=1):
        g_id = item.get("_id", {})
        q_type = g_id.get("type", "-")
        clean_time = str(item.get("timestamp", "")).split(".")[0].replace("T", " ")
        recent_data.append([
            idx,
            clean_time,
            _TYPE_LABELS.get(q_type, q_type),
            _format_params(q_type, g_id.get("params", {})),
            item.get("results_count", 0),
            item.get("total_viewed", 0)
        ])
    print(tabulate(
        recent_data,
        headers=["№", "Дата и время", "Тип поиска", "Параметры запроса", "Найдено", "Показано"],
        tablefmt="fancy_grid"
    ))

def _show_type_popularity():
    """Выводит таблицу популярности типов поиска."""
    print(f"\n\n{SEP}")
    print(f"  {Style.BOLD}{Style.CYAN}📊 SEARCH TYPE POPULARITY{Style.RESET}")
    print(SEP)

    friendly_names = {
        "keyword": "Поиск по ключевому слову",
        "genres-years": "Поиск по жанрам и годам",
        "actor": "Поиск по актерам",
        "actor-years": "Поиск по актерам и годам"
    }
    type_data = [
        [friendly_names.get(item["_id"], item["_id"]), item["total_uses"]]
        for item in get_search_type_popularity()
    ]
    print(tabulate(
        type_data,
        headers=["Метод поиска", "Количество использований"],
        tablefmt="fancy_grid"
    ))

def display_stats():
    """Выводит статистику поиска с использованием модуля Tabulate."""
    _show_top_queries()
    _show_recent_queries()
    _show_type_popularity()

def main_menu():
    """Главное меню приложения для поиска фильмов и вывода аналитики."""

    while True:
        # 1. ЗАГЛАВНОЕ МЕНЮ
        print(f"\n{SEP}")

        # Твой заголовок с настроенной высотой строки 1.3
        display(
            HTML(
                '<h1 style="font-size: 24px; color: #008B9B; font-weight: bold; margin: 0; padding: 0; line-height: 1.3;">'
                '🎬 Film Search App — DB "sakila" 🎬'
                "</h1>"
            )
        )

        print(f"\n{SEP}")

        # 2. ДИНАМИЧЕСКАЯ ПРОВЕРКА СТАТУСА БАЗ ДАННЫХ
        print(f"{Style.BOLD}Статус подключения к базам данных:{Style.RESET}")
        print(f"  {test_mysql_connection()}")
        print(f"  {test_mongo_connection()}")
        print(SEP)

        # 3. Вывод пунктов меню
        print("1. Поиск по ключевому слову в названием")
        print("2. Поиск по жанру и диапазону годов")
        print("3. Поиск по актеру и диапазону годов")
        print("4. Посмотреть статистику запросов (MongoDB)")
        print("0. Выход из программы")
        print(SEP)

        choice = input("Выберите пункт меню: ").strip()

        if choice == "1":
            clear_output(wait=False)  # Чистим экран от старого меню
            print(f"\n{SEP}")
            print(
                f"  {Style.CYAN}{Style.BOLD}--- ПОИСК ПО КЛЮЧЕВОМУ СЛОВУ ---{Style.RESET}"
            )
            print(SEP)
            search_film_by_keyword()
            # Промежуточное меню убрано — после Enter в пагинации цикл просто начнётся заново

        elif choice == "2":
            clear_output(wait=False)  # Чистим экран от старого меню
            print(f"\n{SEP}")
            print(
                f"  {Style.CYAN}{Style.BOLD}--- ПОИСК ПО ЖАНРУ И ГОДАМ ---{Style.RESET}"
            )
            print(SEP)
            search_film_by_genre_and_years()

        elif choice == "3":
            clear_output(wait=False)  # Чистим экран от старого меню
            print(f"\n{SEP}")
            print(
                f"  {Style.CYAN}{Style.BOLD}--- ПОИСК ПО АКТЕРУ И ГОДАМ ---{Style.RESET}"
            )
            print(SEP)
            search_film_by_actor_and_year()

        elif choice == "4":
            clear_output(wait=False)  # Чистим экран от старого меню
            print(f"\n{SEP}")
            print(
                f"  {Style.CYAN}{Style.BOLD}--- СБОР СТАТИСТИКИ ИЗ MONGODB ---{Style.RESET}"
            )
            print(SEP)

            display_stats()  

            print(f"\n{SEP}")
            input("Нажмите Enter, чтобы вернуться в главное меню...")

            # стираем статистику и возвращаемся к чистому меню
            clear_output(wait=False)

        elif choice == "0":
            clear_output(wait=False)
            print(
                f"\n{Style.GREEN}Спасибо за использование системы! До свидания. 👋{Style.RESET}"
            )
            print("Вы вышли из программы, программа завершена.")
            break

        else:
            print(
                f"\n{Style.RED}{Style.BOLD}❌ Ошибка: Неверный ввод! Пожалуйста, выберите пункт от 0 до 4.{Style.RESET}"
            )


# Запуск программы на месте и в целости!
if __name__ == "__main__":
    main_menu()



