# Лічильники людей — Django-проєкт

Interní evidence sčítačů pro firmu: mapa ČR, klienti, typy zařízení,
jejich aktuální stav a historie kontrol i změn.

## Як це влаштовано (логіка)

- `Counter` eviduje sčítač, jeho stav, polohu, klienta a typ zařízení.
- `Client` a `CounterType` jsou spravovatelné v administraci `/admin/`.
  Klienty ani typy se nemažou, pokud jsou přiřazené ke sčítači; lze je deaktivovat.
- Seznam sčítačů umožňuje hledat, filtrovat podle stavu/klienta/typu a termínu
  kontroly, řadit a procházet výsledky po stránkách. Mapa má filtr stavů;
  vnější kroužek značky ukazuje ověření (modrý = ověřeno, šedý = chybí,
  oranžový = po termínu).
- `CounterInspection` ukládá datum, výsledek, poznámku a termín další kontroly.
  Výsledek „Zjištěna závada“ přepne sčítač do poruchy; výsledek „V pořádku“
  jej vrátí do provozu. Změna se zároveň zaznamená do historie stavu.
- Přístup k provozním stránkám mají pouze aktivní uživatelé označení jako
  `Staff`; jejich účty se spravují přes Django administraci.

## Запуск локально в PyCharm

1. Розпакуй архів і відкрий папку `trafficcounters` в PyCharm
   (File → Open).
2. Створи віртуальне середовище (PyCharm зазвичай сам запропонує,
   або вручну):
   ```
   python -m venv venv
   venv\Scripts\activate      # Windows
   source venv/bin/activate   # macOS/Linux
   ```
3. Встанови залежності:
   ```
   pip install -r requirements.txt
   ```
4. Застосуй міграції (створить файл бази `db.sqlite3`):
   ```
   python manage.py migrate
   ```
5. Створи адміністратора (для входу в `/admin/`):
   ```
   python manage.py createsuperuser
   ```
6. Запусти сервер:
   ```
   python manage.py runserver
   ```
7. Відкрий у браузері: http://127.0.0.1:8000/

За замовчуванням карта центрована на Києві — зміни координати в
`counters/templates/counters/map.html` (рядок з `setView`), якщо
фірма в іншому місті.

## Хостинг

Проєкт вже готовий до простого деплою (є `Procfile`, `whitenoise`
для статики, `gunicorn` у requirements). Прості безкоштовні/дешеві
варіанти для старту:

- **Render.com** — Blueprint у `render.yaml`; для виробничого
  використання обери платні сервіси з постійним сховищем та резервними копіями.
- **Railway.app** — так само, деплой прямо з GitHub, автоматично
  визначає Procfile.
- **PythonAnywhere** — простий безкоштовний хостинг саме для
  Django/Python, зручний для новачків.
- Свій VPS (наприклад DigitalOcean/Hetzner) + gunicorn + nginx —
  якщо потрібен повний контроль і більше ресурсів.

**Перед деплоєм на реальний сервер обов'язково:**
1. Встанови `DEBUG=False` через змінну середовища.
2. Передай у середовище окремий `SECRET_KEY` і адресу PostgreSQL у `DATABASE_URL` — секрети не додавай до GitHub.
3. Установи `ALLOWED_HOSTS` для реального домену та `CSRF_TRUSTED_ORIGINS` для HTTPS-адреси.
4. Виконай `python manage.py collectstatic` і застосуй міграції.

## Що варто розглянути перед виробничим запуском

- Rozdělení práv mezi běžné pracovníky, editory a administrátory.
- MFA nebo přihlášení přes firemní SSO a ochrana proti opakovaným pokusům o přihlášení.
- Zálohy databáze i fotografií a ověřený postup obnovy.
- Automatická data ze sčítačů (počty osob za den) — současná aplikace
  eviduje zařízení a jejich údržbu, nepřijímá jejich provozní statistiky.
