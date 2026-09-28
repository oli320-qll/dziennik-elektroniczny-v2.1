import streamlit as st
import sqlite3

# --- KONFIGURACJA STRONY ---
st.set_page_config(page_title="Prywatny Dziennik Szkolny", page_icon="📚", layout="wide")

# --- INICJALIZACJA BAZY DANYCH ---
def init_db():
    conn = sqlite3.connect('szkola_klon.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Tabela użytkowników
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS uzytkownicy (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        role TEXT, # admin, nauczyciel, uczen, rodzic
        full_name TEXT
    )''')
    
    # Tabela ocen
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS oceny (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uczen_username TEXT,
        przedmiot TEXT,
        ocena REAL,
        waga INTEGER,
        opis TEXT
    )''')
    
    # Tabela frekwencji
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS frekwencja (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uczen_username TEXT,
        data TEXT,
        status TEXT # Obecny, Nieobecny, Spóźnienie
    )''')
    
    # Dodanie domyślnych użytkowników testowych (jeśli baza jest pusta)
    cursor.execute("SELECT COUNT(*) FROM uzytkownicy")
    if cursor.fetchone()[0] == 0:
        domyslne_konta = [
            ("admin", "admin123", "admin", "Administrator Systemu"),
            ("nauczyciel", "nauczyciel123", "nauczyciel", "Jan Kowalski (Matematyka)"),
            ("uczen", "uczen123", "uczen", "Adam Nowak (Uczeń)"),
            ("rodzic", "rodzic123", "rodzic", "Anna Nowak (Rodzic)")
        ]
        cursor.executemany("INSERT INTO uzytkownicy (username, password, role, full_name) VALUES (?, ?, ?, ?)", domyslne_konta)
        conn.commit()
        
    return conn

conn = init_db()
cursor = conn.cursor()

# --- STAN SESJI (LOGOWANIE) ---
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# --- EKRAN LOGOWANIA ---
if not st.session_state.logged_in:
    st.title("📚 Elektroniczny Dziennik - Panel Prywatny")
    st.write("Zaloguj się używając danych testowych lub konta stworzonego przez administratora.")
    
    with st.form("login_form"):
        username_input = st.text_input("Login")
        password_input = st.text_input("Hasło", type="password")
        submit = st.form_submit_button("Zaloguj się")
        
        if submit:
            cursor.execute("SELECT role, full_name FROM uzytkownicy WHERE username=? AND password=?", (username_input, password_input))
            user = cursor.fetchone()
            if user:
                st.session_state.logged_in = True
                st.session_state.username = username_input
                st.session_state.role = user[0]
                st.session_state.full_name = user[1]
                st.success("Zalogowano pomyślnie!")
                st.rerun()
            else:
                st.error("Błędny login lub hasło!")
                
    st.info("Konta testowe:\n- Admin: `admin` / `admin123`\n- Nauczyciel: `nauczyciel` / `nauczyciel123`\n- Uczeń: `uczen` / `uczen123`\n- Rodzic: `rodzic` / `rodzic123`")

# --- PANEL GŁÓWNY PO ZALOGOWANIU ---
else:
    st.sidebar.title("Panel Użytkownika")
    st.sidebar.write(f"Witaj, **{st.session_state.full_name}**!")
    st.sidebar.caption(f"Rola: {st.session_state.role.upper()}")
    
    # Menu w zależności od roli
    role = st.session_state.role
    menu_options = []
    
    if role == "admin":
        menu_options = ["Zarządzanie użytkownikami", "Podgląd bazy danych"]
    elif role == "nauczyciel":
        menu_options = ["Wystaw ocenę", "Wprowadź frekwencję"]
    elif role == "uczen":
        menu_options = ["Moje oceny", "Moja frekwencja"]
    elif role == "rodzic":
        menu_options = ["Oceny dziecka", "Frekwencja dziecka", "Usprawiedliwienia"]
        
    choice = st.sidebar.radio("Nawigacja", menu_options)
    
    st.sidebar.markdown("---")
    if st.sidebar.button("Wyloguj się"):
        st.session_state.logged_in = False
        st.rerun()

    # ================= WIDOK: ADMIN =================
    if role == "admin":
        st.header("🛠️ Panel Administratora")
        
        tab1, tab2 = st.tabs(["Dodaj użytkownika", "Lista użytkowników"])
        
        with tab1:
            st.subheader("Utwórz nowe konto")
            with st.form("new_user_form"):
                new_user = st.text_input("Login")
                new_pass = st.text_input("Hasło", type="password")
                new_name = st.text_input("Imię i nazwisko / Nazwa")
                new_role = st.selectbox("Rola w systemie", ["nauczyciel", "uczen", "rodzic", "admin"])
                submit_user = st.form_submit_button("Utwórz konto")
                
                if submit_user:
                    try:
                        cursor.execute("INSERT INTO uzytkownicy (username, password, role, full_name) VALUES (?, ?, ?, ?)", 
                                       (new_user, new_pass, new_role, new_name))
                        conn.commit()
                        st.success(f"Utworzono konto dla {new_name}!")
                    except sqlite3.IntegrityError:
                        st.error("Użytkownik o takim loginie już istnieje!")
                        
        with tab2:
            st.subheader("Wszyscy użytkownicy w systemie")
            cursor.execute("SELECT username, role, full_name FROM uzytkownicy")
            users = cursor.fetchall()
            st.table(users)

    # ================= WIDOK: NAUCZYCIEL =================
    elif role == "nauczyciel":
        st.header("👨‍🏫 Panel Nauczyciela")
        
        if choice == "Wystaw ocenę":
            st.subheader("Wpisywanie oceny uczniowi")
            
            # Pobierz listę uczniów
            cursor.execute("SELECT username, full_name FROM uzytkownicy WHERE role='uczen'")
            uczniowie = {row[1]: row[0] for row in cursor.fetchall()}
            
            if not uczniowie:
                st.warning("Brak uczniów w bazie. Poproś administratora o dodanie kont uczniów.")
            else:
                with st.form("ocena_form"):
                    wybrany_uczen_name = st.selectbox("Wybierz ucznia", list(uczniowie.keys()))
                    przedmiot = st.selectbox("Przedmiot", ["Matematyka", "Język polski", "Informatyka", "Historia", "Biologia"])
                    ocena = st.selectbox("Ocena", [1.0, 2.0, 3.0, 3.5, 4.0, 4.5, 5.0, 6.0])
                    waga = st.slider("Waga oceny", 1, 3, 1)
                    opis = st.text_input("Opis (np. Sprawdzian, Odpowiedź)")
                    
                    submit_ocena = st.form_submit_button("Zapisz ocenę")
                    
                    if submit_ocena:
                        uczen_username = uczniowie[wybrany_uczen_name]
                        cursor.execute("INSERT INTO oceny (uczen_username, przedmiot, ocena, waga, opis) VALUES (?, ?, ?, ?, ?)",
                                       (uczen_username, przedmiot, ocena, waga, opis))
                        conn.commit()
                        st.success(f"Dodano ocenę {ocena} z przedmiotu {przedmiot} dla ucznia {wybrany_uczen_name}!")

        elif choice == "Wprowadź frekwencję":
            st.subheader("Moduł frekwencji")
            cursor.execute("SELECT username, full_name FROM uzytkownicy WHERE role='uczen'")
            uczniowie = cursor.fetchall()
            
            if not uczniowie:
                st.warning("Brak uczniów w bazie.")
            else:
                with st.form("frekwencja_form"):
                    data_wpisu = st.date_input("Data lekcji")
                    frekwencja_dane = {}
                    for u in uczniowie:
                        frekwencja_dane[u[0]] = st.radio(f"Uczeń: {u[1]}", ["Obecny", "Nieobecny", "Spóźnienie"], horizontal=True, key=u[0])
                    
                    submit_freq = st.form_submit_button("Zapisz frekwencję")
                    if submit_freq:
                        for u_name, status in frekwencja_dane.items():
                            cursor.execute("INSERT INTO frekwencja (uczen_username, data, status) VALUES (?, ?, ?)",
                                           (u_name, str(data_wpisu), status))
                        conn.commit()
                        st.success("Zapisano frekwencję dla wszystkich uczniów!")

    # ================= WIDOK: UCZEŃ =================
    elif role == "uczen":
        st.header("🎓 Panel Ucznia")
        
        if choice == "Moje oceny":
            st.subheader("Twoje oceny i średnie")
            cursor.execute("SELECT przedmiot, ocena, waga, opis FROM oceny WHERE uczen_username=?", (st.session_state.username,))
            oceny = cursor.fetchall()
            
            if not oceny:
                st.info("Brak wpisanych ocen w systemie.")
            else:
                st.table(oceny)
                
        elif choice == "Moja frekwencja":
            st.subheader("Twoja frekwencja")
            cursor.execute("SELECT data, status FROM frekwencja WHERE uczen_username=?", (st.session_state.username,))
            freq = cursor.fetchall()
            if not freq:
                st.info("Brak wpisów frekwencji.")
            else:
                st.table(freq)

    # ================= WIDOK: RODZIC =================
    elif role == "rodzic":
        st.header("👪 Panel Rodzica")
        st.write("Podgląd postępów Twojego dziecka (Adam Nowak - `uczen`)")
        
        # Na potrzeby demo zakładamy, że rodzic widzi konto ucznia o loginie 'uczen'
        dziecko_username = "uczen"
        
        if choice == "Oceny dziecka":
            st.subheader("Oceny")
            cursor.execute("SELECT przedmiot, ocena, waga, opis FROM oceny WHERE uczen_username=?", (dziecko_username,))
            oceny = cursor.fetchall()
            if not oceny:
                st.info("Brak ocen dziecka.")
            else:
                st.table(oceny)
                
        elif choice == "Frekwencja dziecka":
            st.subheader("Frekwencja")
            cursor.execute("SELECT data, status FROM frekwencja WHERE uczen_username=?", (dziecko_username,))
            freq = cursor.fetchall()
            if not freq:
                st.info("Brak danych o frekwencji.")
            else:
                st.table(freq)
                
        elif choice == "Usprawiedliwienia":
            st.subheader("Usprawiedliwianie nieobecności")
            st.info("Wybierz nieobecność do usprawiedliwienia:")
            cursor.execute("SELECT id, data, status FROM frekwencja WHERE uczen_username=? AND status='Nieobecny'", (dziecko_username,))
            nieobecnosci = cursor.fetchall()
            
            if not nieobecnosci:
                st.success("Brak nieobecności do usprawiedliwienia!")
            else:
                for n in nieobecnosci:
                    col1, col2 = st.columns([3, 1])
                    col1.write(f"Data: {n[1]} (Status: {n[2]})")
                    if col2.button("Usprawiedliw", key=n[0]):
                        cursor.execute("UPDATE frekwencja SET status='Usprawiedliwiony' WHERE id=?", (n[0],))
                        conn.commit()
                        st.success(f"Usprawiedliwiono nieobecność z dnia {n[1]}!")
                        st.rerun()
