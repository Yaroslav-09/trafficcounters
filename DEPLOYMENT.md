# Vývoj a bezplatné nasazení

## Aplikace

Aplikace slouží zaměstnancům ke správě sčítačů: mapa, poloha, aktuální stav, historie změn a fotky závad. Naměřené počty lidí ze zařízení zatím nepřijímá.

## Render pro testování

`render.yaml` používá bezplatný web service a bezplatnou PostgreSQL databázi. Migrace běží v build příkazu; Render podporuje samostatný `preDeployCommand` jen u placených web služeb.

Bezplatné služby mají omezení:

- Web se uspí po 15 minutách bez návštěv a jeho lokální soubory nejsou trvalé. Nahrané fotky se proto mohou ztratit po restartu nebo novém nasazení.
- Bezplatná PostgreSQL databáze má limit 1 GB a po 30 dnech vyprší. Po dalších 14 dnech Render její data smaže.
- Při vyčerpání bezplatného limitu může Render službu nebo další buildy pozastavit.

Toto nastavení je určené pro programování a zkoušení s testovacími daty. Důležité záznamy a fotografie si drž také mimo Render. Aktuální limity a případné použití nad bezplatný rámec kontroluj na stránce Billing v Renderu.

Render může automaticky nasadit změny po pushi do připojené Git větve. Samotný GitHub push ukládá kód; `render.yaml` pro tento projekt nevybírá placené plány.

## Lokální vývoj

Lokálně aplikace používá SQLite a `DEBUG=True`. Produkční režim vyžaduje `SECRET_KEY`, `DATABASE_URL` a platný hostitel. Render poskytuje hostname služby automaticky; vlastní doménu přidej přes proměnnou `ALLOWED_HOSTS`. Tajné hodnoty ani `.env` neukládej do GitHubu.

## Ochrana aplikace

Všechny aplikační stránky vyžadují aktivní účet se zapnutým Staff status. Přihlášení se po pěti chybných pokusech pro účet a IP adresu zablokuje na 30 minut. Produkce používá HTTPS a bezpečné session/CSRF cookies. Zaměstnancům nastav dlouhá jedinečná hesla; minimální délka je 12 znaků. Aplikace zatím nepodporuje MFA.

Nahrávané fotky jsou omezené na 8 MB a 25 megapixelů. Pro veřejné nasazení nastav také limit velikosti požadavků na hostingu; aplikační validace sama neomezuje síťový provoz před přijetím souboru.
